#!/usr/bin/env python3
"""Check and fast-forward this installed skill; never discard local changes."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


REPOSITORY = "https://github.com/NiHaiMaker/psd-to-unity-ui.git"
REMOTE_REF = "refs/remotes/origin/main"
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
TRUSTED_ORIGINS = {
    "https://github.com/nihaimaker/psd-to-unity-ui",
    "git@github.com:nihaimaker/psd-to-unity-ui",
    "ssh://git@github.com/nihaimaker/psd-to-unity-ui",
}


class StopUpdate(Exception):
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason


class Git:
    def __init__(self, directory, timeout):
        self.directory = directory
        self.timeout = timeout
        self.env = dict(os.environ)
        self.env.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"})
        self.env.setdefault("GIT_SSH_COMMAND", "ssh -oBatchMode=yes")

    def run(self, *args, allow_failure=False, network=False):
        try:
            result = subprocess.run(
                ["git", "-C", str(self.directory), *args],
                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=self.timeout, check=False,
            )
        except FileNotFoundError:
            raise StopUpdate("unavailable", "git_not_found") from None
        except subprocess.TimeoutExpired:
            raise StopUpdate("unavailable", "fetch_timeout" if network else "git_timeout") from None
        except OSError:
            raise StopUpdate("unavailable", "git_unavailable") from None
        if result.returncode and not allow_failure:
            # Git errors can contain URLs or credential-helper output. Do not echo them.
            raise StopUpdate("unavailable" if network else "blocked",
                             "fetch_failed" if network else "git_command_failed")
        return result

    def text(self, *args):
        try:
            return self.run(*args).stdout.decode("utf-8").strip()
        except UnicodeDecodeError:
            raise StopUpdate("blocked", "invalid_git_output") from None

    def is_ancestor(self, older, newer):
        result = self.run("merge-base", "--is-ancestor", older, newer, allow_failure=True)
        if result.returncode not in (0, 1):
            raise StopUpdate("blocked", "history_unavailable")
        return result.returncode == 0


def trusted_origin(value):
    value = value.lower().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    return value in TRUSTED_ORIGINS


def local_state(git, result):
    root = git.run("rev-parse", "--show-toplevel", allow_failure=True)
    if root.returncode:
        raise StopUpdate("blocked", "not_git_repository")
    try:
        actual_root = Path(os.fsdecode(root.stdout).strip()).resolve()
    except (OSError, ValueError):
        raise StopUpdate("blocked", "invalid_repository_path") from None
    if actual_root != git.directory:
        raise StopUpdate("blocked", "skill_directory_is_not_repository_root")
    result["current_head"] = git.text("rev-parse", "HEAD")
    result["current_version"], result["legacy_version"] = version_at(git, "HEAD", legacy=True)
    branch = git.run("symbolic-ref", "--short", "HEAD", allow_failure=True)
    result["branch"] = branch.stdout.decode("utf-8", errors="replace").strip()
    if branch.returncode or result["branch"] != "main":
        raise StopUpdate("blocked", "main_branch_required")
    origins = git.run("remote", "get-url", "--all", "origin", allow_failure=True)
    urls = origins.stdout.decode("utf-8", errors="replace").splitlines()
    if origins.returncode or len(urls) != 1 or not trusted_origin(urls[0]):
        raise StopUpdate("blocked", "untrusted_origin")
    if git.run("status", "--porcelain=v1", "--untracked-files=all").stdout:
        raise StopUpdate("blocked", "local_changes")
    if git.text("rev-parse", "--is-shallow-repository") == "true":
        raise StopUpdate("blocked", "shallow_history")
    for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
        marker_path = Path(git.text("rev-parse", "--git-path", marker))
        if not marker_path.is_absolute():
            marker_path = git.directory / marker_path
        if marker_path.exists():
            raise StopUpdate("blocked", "git_operation_in_progress")


def version_at(git, commit, legacy=False):
    entry = git.text("ls-tree", commit, "--", "VERSION")
    if not entry:
        if legacy:
            return "0.0.0", True
        raise StopUpdate("blocked", "remote_version_missing")
    if not entry.startswith(("100644 blob ", "100755 blob ")):
        raise StopUpdate("blocked", "invalid_version_file")
    try:
        value = git.run("show", f"{commit}:VERSION").stdout.decode("utf-8")
    except UnicodeDecodeError:
        raise StopUpdate("blocked", "invalid_version_encoding") from None
    if value.endswith("\n"):
        value = value[:-1]
    if value.endswith("\r"):
        value = value[:-1]
    if not VERSION_PATTERN.fullmatch(value):
        raise StopUpdate("blocked", "invalid_version")
    return value, False


def version_numbers(version):
    return tuple(int(part) for part in version.split("."))


def fetch(git):
    git.run("fetch", "--no-tags", "--no-recurse-submodules", "origin",
            f"+refs/heads/main:{REMOTE_REF}", network=True)
    return git.text("rev-parse", "--verify", f"{REMOTE_REF}^{{commit}}")


def inspect_remote(git, result):
    remote_head = fetch(git)
    result["target_commit"] = remote_head
    result["remote_version"], _ = version_at(git, remote_head)
    return remote_head


def check(git, result):
    local_state(git, result)
    remote_head = inspect_remote(git, result)
    local_head = result["current_head"]
    if not git.is_ancestor(local_head, remote_head):
        if git.is_ancestor(remote_head, local_head):
            raise StopUpdate("local_ahead", "local_commits_ahead")
        raise StopUpdate("blocked", "diverged_history")
    local_version = version_numbers(result["current_version"])
    remote_version = version_numbers(result["remote_version"])
    if remote_version < local_version:
        raise StopUpdate("local_ahead", "remote_version_older")
    if remote_version == local_version:
        if local_head != remote_head:
            raise StopUpdate("blocked", "changed_commit_without_version_increment")
        raise StopUpdate("current", "already_current")
    result.update(status="update_available", reason="newer_version_available")


def update(git, result, target):
    if not COMMIT_PATTERN.fullmatch(target):
        raise StopUpdate("blocked", "full_target_commit_required")
    local_state(git, result)
    original_head = result["current_head"]
    remote_head = inspect_remote(git, result)
    result["latest_remote_commit"] = remote_head
    result["latest_remote_version"] = result["remote_version"]
    result["target_commit"] = target
    target_check = git.run("cat-file", "-t", target, allow_failure=True)
    if target_check.returncode or target_check.stdout.strip() != b"commit":
        raise StopUpdate("blocked", "target_commit_unavailable")
    if not git.is_ancestor(target, remote_head):
        raise StopUpdate("blocked", "target_not_on_remote_main")
    result["remote_version"], _ = version_at(git, target)
    if version_numbers(result["remote_version"]) <= version_numbers(result["current_version"]):
        raise StopUpdate("blocked", "target_version_not_newer")
    if not git.is_ancestor(original_head, target):
        raise StopUpdate("blocked", "target_not_fast_forward")
    # Recheck edits, branch and origin after the network wait, before changing files.
    fresh = {}
    local_state(git, fresh)
    if fresh["current_head"] != original_head:
        raise StopUpdate("blocked", "local_head_changed")
    merged = git.run("merge", "--ff-only", "--no-edit", "--no-stat",
                     "--no-overwrite-ignore", target, allow_failure=True)
    updated_head = git.text("rev-parse", "HEAD")
    result["previous_head"] = original_head
    result["current_head"] = updated_head
    result["current_version"], result["legacy_version"] = version_at(git, "HEAD", legacy=True)
    result["local_clean"] = not bool(git.run("status", "--porcelain=v1", "--untracked-files=all").stdout)
    if merged.returncode or updated_head != target or not result["local_clean"]:
        raise StopUpdate("blocked", "update_incomplete_inspect_local_state")
    result.update(status="updated", reason="confirmed_target_installed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "update"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--skill-dir", type=Path, default=Path(__file__).resolve().parents[1])
        subparser.add_argument("--timeout", type=int, default=25, help="Timeout in seconds per Git command (default: 25).")
        if command == "update":
            subparser.add_argument("--target-commit", required=True, help="Full commit SHA shown by check and accepted by the user.")
    args = parser.parse_args()
    result = {"status": "blocked", "reason": None, "repository": REPOSITORY,
              "current_version": None, "current_head": None,
              "remote_version": None, "target_commit": None}
    try:
        if not 1 <= args.timeout <= 180:
            raise StopUpdate("blocked", "timeout_must_be_between_1_and_180")
        directory = args.skill_dir.expanduser().resolve()
        if not directory.is_dir():
            raise StopUpdate("blocked", "skill_directory_missing")
        git = Git(directory, args.timeout)
        if args.command == "check":
            check(git, result)
        else:
            update(git, result, args.target_commit)
    except StopUpdate as exc:
        result.update(status=exc.status, reason=exc.reason)
    except (OSError, ValueError):
        result.update(status="blocked", reason="local_state_unavailable")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] in {"current", "update_available", "local_ahead", "updated"} else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Read PSD/PSB structure without saving or recompositing the source document."""

import argparse
from collections import defaultdict
from contextlib import ExitStack
import hashlib
import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import sys


PREVIEW_NOTE = (
    "PSD cached merged image only; it may be stale and is not a recomposition "
    "or a validation of the current layers. ICC conversion to sRGB is applied "
    "when supported."
)


def load_psd_image(dependency_path):
    if dependency_path:
        candidate = Path(dependency_path).expanduser().resolve()
        if not (candidate / "psd_tools" / "__init__.py").is_file():
            raise ValueError("--psd-tools-path must contain the psd_tools package")
        sys.path.insert(0, str(candidate))
    elif importlib.util.find_spec("psd_tools") is None:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = Path(local_app_data) / "CodexTools" / "python-psd-tools"
            if candidate.is_dir():
                sys.path.insert(0, str(candidate))
    try:
        from psd_tools import PSDImage
    except ImportError as exc:
        raise RuntimeError(
            "PSD dependency unavailable: install scripts/requirements.txt into "
            "this Python environment or pass --psd-tools-path. " + str(exc)
        ) from exc
    return PSDImage


def validate_paths(args):
    source = Path(args.source).expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in {".psd", ".psb"}:
        raise ValueError("source must be an existing .psd or .psb file")
    outputs = {}
    for label in ("output", "preview"):
        value = getattr(args, label)
        if value:
            raw_path = Path(value).expanduser()
            path = raw_path.resolve()
            if path == source:
                raise ValueError(f"--{label} must not overwrite the source")
            if path in outputs.values():
                raise ValueError("--output and --preview must use different files")
            if os.path.lexists(raw_path) or path.exists():
                raise FileExistsError(f"--{label} already exists: {path}")
            outputs[label] = path
    for label, path in outputs.items():
        if os.name == "nt" and (
            any(":" in part for part in path.parts[1:]) or path.is_reserved()
        ):
            raise ValueError(f"--{label} must be a normal file, not a device or alternate data stream")
        expected = ".json" if label == "output" else ".png"
        if path.suffix.lower() != expected:
            raise ValueError(f"--{label} must end with {expected}")
        if not path.parent.is_dir():
            raise ValueError(f"--{label} parent directory does not exist: {path.parent}")
    return source, outputs


def collect_layers(container, parent_indexes=(), parent_names=(), parent_visible=True):
    records = []
    for index, layer in enumerate(container):
        indexes = parent_indexes + (index,)
        names = parent_names + (layer.name,)
        own_visible = bool(layer.visible)
        effective_visible = parent_visible and own_visible
        layer_id = layer.layer_id
        records.append({
            "index_path": "/".join(map(str, indexes)),
            "path": "/".join(names),
            "name_path": list(names),
            "id": layer_id if layer_id >= 0 else None,
            "name": layer.name,
            "kind": layer.kind,
            "bbox": list(layer.bbox),
            "own_visible": own_visible,
            "effective_visible": effective_visible,
            "opacity": int(layer.opacity),
            "text": layer.text if layer.kind == "type" else None,
        })
        if layer.is_group():
            records.extend(collect_layers(layer, indexes, names, effective_visible))
    return records


def duplicate_warnings(records):
    warnings = []
    for field, code in (("name", "duplicate_name"), ("id", "duplicate_id")):
        occurrences = defaultdict(list)
        for record in records:
            if record[field] is not None:
                occurrences[record[field]].append(record["index_path"])
        for value, paths in occurrences.items():
            if len(paths) > 1:
                warnings.append({"code": code, "value": value, "index_paths": paths})
    return warnings


def inspect(source, want_preview, dependency_path):
    psd_image = load_psd_image(dependency_path)
    with source.open("rb") as stream:
        hasher = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
        digest = hasher.hexdigest()
        stream.seek(0)
        psd = psd_image.open(stream)
    records = collect_layers(psd)
    preview_bytes = None
    if want_preview:
        if not psd.has_preview():
            raise ValueError("PSD has no cached merged preview; no recomposition was attempted")
        merged = psd.topil()
        if merged is None:
            raise ValueError("PSD cached merged preview is unavailable; no recomposition was attempted")
        if merged.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16"}:
            merged = merged.convert("RGB")
        buffer = BytesIO()
        merged.save(buffer, format="PNG")
        preview_bytes = buffer.getvalue()
    report = {
        "schema_version": 1,
        "source": {"path": source.as_posix(), "sha256": digest},
        "canvas": {
            "width": psd.width,
            "height": psd.height,
            "color_mode": psd.color_mode.name,
            "depth": psd.depth,
        },
        "layer_count": len(records),
        "record_conventions": {
            "index_path": "Zero-based sibling indexes in psd-tools order; stable for the same structure, not after reordering.",
            "path": "Human-readable names; name_path preserves literal slashes and index_path disambiguates duplicates.",
            "bbox": "[left, top, right, bottom] in PSD canvas pixels.",
            "effective_visible": "Own visibility AND ancestor visibility; does not evaluate opacity, masks or pixel coverage.",
            "opacity": "Own opacity in the range 0..255.",
            "id": "null means no assigned ID; only assigned IDs are checked for duplicates.",
        },
        "layers": records,
        "warnings": duplicate_warnings(records),
        "preview": {
            "cached_merged_available": bool(psd.has_preview()),
            "exported": want_preview,
            "note": PREVIEW_NOTE,
        },
    }
    return (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), preview_bytes


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="existing PSD/PSB; opened read-only")
    parser.add_argument("--output", help="new JSON file; default: UTF-8 stdout")
    parser.add_argument("--preview", help="new PNG of the cached merged image; never recomposites")
    parser.add_argument("--psd-tools-path", help="directory containing the psd_tools package")
    args = parser.parse_args()
    try:
        source, outputs = validate_paths(args)
        report, preview = inspect(source, "preview" in outputs, args.psd_tools_path)
        # Validate and encode everything before exclusively creating any artifact.
        # 'xb' also rejects files created after validation; existing files are never replaced.
        with ExitStack() as stack:
            handles = {key: stack.enter_context(path.open("xb")) for key, path in outputs.items()}
            if "output" in handles:
                handles["output"].write(report)
            if "preview" in handles:
                handles["preview"].write(preview)
        if "output" not in outputs:
            sys.stdout.write(report.decode("utf-8"))
        return 0
    except Exception as exc:
        print(f"inspect_psd: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

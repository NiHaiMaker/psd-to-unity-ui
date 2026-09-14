# PSD 到 Unity UI

面向 Codex 的 PSD/PSB → Unity UGUI 工作流 Skill。支持首次制作、人工修正整理稿后续作，以及已有 PSD、Prefab、绑定代码的持续维护。

本仓库提供执行规则、溯源模板和只读图层检查脚本。PSD 编辑、Prefab 导出和代码绑定复用目标环境的现有工具；它不是独立的 PSD 转换器，也没有后台文件监听或通用自动合并器。

## 安装与 Git 维护

需要 Git 和能够加载自定义 Skill 的 Codex 环境。下面以本工作流当前使用的 `$CODEX_HOME/skills` 目录为例；未设置 `CODEX_HOME` 时使用用户目录下的 `.codex/skills`。其他部署请使用其实际识别的技能目录。

首次安装，目标目录应尚不存在。在 PowerShell 中执行：

```powershell
$skillHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$skillPath = Join-Path $skillHome 'skills/psd-to-unity-ui'
git clone https://github.com/NiHaiMaker/psd-to-unity-ui.git $skillPath
```

仓库访问需要相应的 GitHub 权限。安装后在 Codex 中检查是否能选择或调用 `$psd-to-unity-ui`；如果当前会话尚未识别，重新打开会话或重启应用后检查。

已安装且已关联本仓库时，可在保留本地修改的前提下更新：

```powershell
git -C $skillPath status --short
git -C $skillPath pull --ff-only
```

以上命令沿用前面定义的 `$skillPath`。维护自己修改过的规则时，先检查差异再提交：

```powershell
git -C $skillPath diff
git -C $skillPath add SKILL.md references templates scripts agents README.md .gitignore .gitattributes
git -C $skillPath commit -m "Update PSD to Unity workflow"
git -C $skillPath push
```

只维护此 Skill 目录，不将整个 Codex 配置目录、凭据、第三方依赖或项目美术资源提交到仓库。

## 如何使用

完整制作：

```text
使用 $psd-to-unity-ui，把指定 PSD 整理为 750×1334，调用项目已有工具输出 Prefab。
列出减法、布局、适配及对应功能影响供我确认，然后完成绑定和已明确的功能。
工程内不新增流程辅助脚本。
```

常见维护请求：

| 目标 | 示例 |
|---|---|
| 只整理 PSD | 使用 $psd-to-unity-ui，本次只整理这份 PSD，不生成 Prefab。 |
| 继续人工修正版 | 我改了 `_UI.psd`，以这份修正版继续导出，更新原修改说明。 |
| 更新已有界面 | 用新的源 PSD 更新现有界面，先生成临时 Prefab，列出合并清单。 |
| 记录适配修正 | 我改了正式 Prefab 的适配，检查显示并维护原修改说明。 |
| 仅改功能代码 | 只修改这个按钮的点击逻辑，沿用现有有效绑定。 |

提供源文件与项目位置，并说明本次需要完成的阶段。模块名、面板名和设备范围能从项目可靠推断时会沿用；业务行为以明确需求为准。

## 完整流程

1. **保留源文件并整理 PSD。** 默认设计画布为 750×1334，另存 `<原名>_UI.psd`；重名时使用时间戳，PSB 保留扩展名。根据用途整理命名、分组、绑定标记及候选 Item。只改名任务保留原尺寸和结构。
2. **导出前检查整理稿。** 检查人工修正、视觉、命名和导入约束。用户修正后的稿件作为续作输入；通用纠错可反馈到 Skill，单页选择记录在该界面说明中。
3. **使用现有工具导出视觉 Prefab。** 核对图片、字体、图层效果与引用。图片根据内容和导入设置判断复用，不能只看同名文件是否存在。
4. **确认正式修改清单。** 列明节点取舍、Item、布局、适配、资源更新及功能影响；实际写入前重新核对资产，保留确认期间新增的无冲突调整。
5. **完成减法与布局。** 保留需要的视觉和运行引用，按职责精简绑定，落实 Item 模板及实例方案，配置锚点与既有布局组件。
6. **完成绑定。** 现有工具生成代码 → 修复本次变化影响的必要手写引用 → Unity 编译通过且类型可加载 → 刷新 Prefab 引用 → 检查。
7. **实现其余功能并验证。** 在已确认范围内继续实现功能，不为代码阶段二次确认；分别报告视觉、适配、编译、引用与运行检查的实际结果。

节点更名或类型变化造成的手写代码编译错误，在绑定刷新前处理；生成文件始终由工具维护。

## 已有界面如何维护

| 变化来源 | 处理方式 |
|---|---|
| 源 PSD 更新 | 保留旧稿，参考已有人工修正生成新整理稿；已有正式 Prefab 时隔离导出临时候选。 |
| 人工修改 `_UI.psd` | 核验当前修正版后续作，不从源稿重新生成覆盖修正。 |
| PSD 更新合并到正式 Prefab | 对比后按确认清单合并，保留已有适配与布局；每次合并执行现有绑定流程。 |
| 用户已修改正式 Prefab 适配 | 以保存后的设置为准，检查并记录；纯适配变化不重导出、不重跑绑定。 |
| 只修改手写功能代码 | 核实现有节点与绑定仍满足需求后，直接修改并验证。 |
| 修改过多，需要重建 | Agent 说明原因、恢复范围和引用影响，用户明确确认后执行。 |

成功合并、绑定和检查后，删除本次临时 Prefab，只保留正式 Prefab。正式资源依赖的图片、字体、材质继续保留。候选导出不覆盖正式或 Common 资源；共享图片的变化需检查其他页面的引用影响。

## 固定的两份修改说明

每个界面长期维护以下文件，各一份：

- `01-PSD修改说明.md`：源文件、整理稿、图层修改、人工修正、版本指纹及导出前检查。
- `02-Prefab减法与布局说明.md`：导出事件、正式改动清单、减法与布局依据、绑定执行、适配修订及验证。

新一轮源稿更新也在原文件内追加记录，用记录编号关联历史，不按轮次另建一套 MD。候选状态与正式状态分别标明；SHA-256 只用于识别版本，不能恢复旧文件或替代实际差异检查。

实际说明保存在目标项目允许的报告目录，位于 Unity 导入范围之外。本仓库仅保存通用模板。

## 目录

```text
psd-to-unity-ui/
├── SKILL.md                         执行入口与阶段路由
├── agents/openai.yaml              Codex 显示信息与调用提示
├── references/                     PSD、Prefab、PLink 与维护细则
├── templates/                      两份固定说明的模板
└── scripts/
    ├── inspect_psd.py              只读图层检查脚本
    └── requirements.txt            检查脚本依赖
```

`agents/openai.yaml` 不创建独立 Agent。由执行任务的 Agent 按 Skill 推进流程。

## 只读检查脚本

脚本输出画布、图层层级、类型、可见性、文字和源文件 SHA-256，可选输出 PSD 内缓存的合成预览。它不修改 PSD、不重新合成图像，也不调用 Unity。

在已具备 Python 的环境中，可将依赖安装到本机外部缓存：

```powershell
$psdToolRoot = Join-Path $env:LOCALAPPDATA 'CodexTools/python-psd-tools'
python -m pip install --target $psdToolRoot -r (Join-Path $skillPath 'scripts/requirements.txt')

python (Join-Path $skillPath 'scripts/inspect_psd.py') '<输入PSD路径>' `
  --output '<新的图层报告.json>' `
  --preview '<新的预览.png>'
```

替换示例中的占位路径。输出父目录必须已存在，输出文件必须是新文件；已有可用依赖直接复用。脚本也支持 `--psd-tools-path` 指定依赖目录。缓存合成图可能陈旧，不能代替保存后视觉核验或 Unity 显示检查。

## 环境与验证范围

- 需要可保留 Photoshop 图层结构的编辑能力，以及项目现有的 Prefab 导出、代码绑定工具。本仓库不包含 Photoshop、Unity、PSUIResolver、XUGUI 或 Coplay。
- PLink 接入复用已有 PSUIResolver 与 XUGUI，Unity Editor 交互按项目要求使用 Coplay MCP。其他项目按实际工具和项目规则接入。
- 不向 Unity `Assets` 新增流程辅助脚本或永久菜单；正常生成的绑定代码与明确要求的功能代码属于允许交付内容。项目专用外部自动化脚本放在 Unity 导入范围之外。
- 遵守目标项目规则和版本控制边界；本 Skill 不代替项目规范，也不自动执行 SVN 提交或其他版本调度。
- 当前版本已完成 Skill 结构、文档链接和场景推演检查。最新版完整工作流尚未完成一次真实界面的端到端验证；静态检查、Editor 生成、编译、PlayMode 和设备适配分别记录，不能互相替代。

详细执行规则以 [SKILL.md](SKILL.md) 及其路由资料为准。许可见 [LICENSE](LICENSE)。

# PLink 接入与生成边界

仅在目标项目实际使用 PLink、PSUIResolver 或 XUGUI 且任务命中时读取。本文是个人 Skill 的接入导航，不覆盖目标仓库 `.cursor/`；API、可选包和工具入口以当前项目规则及源码为准。

## 读取路由

下列路径相对于本次目标项目根，不是本 Skill 目录：

| 当前任务 | 目标项目资料 |
|---|---|
| PSD 导入、资源导出 | `.cursor/skills/plink-psd-to-ugui/SKILL.md` 及其要求的直接资料 |
| Prefab、节点、代码生成、界面逻辑 | `.cursor/skills/plink-ui-panels/SKILL.md`、`reference.md`、`examples.md` |
| 编写 PLink 手写实体或修改编辑器工具 | `.cursor/skills/plink-framework/SKILL.md` 及其要求的资料 |
| 资源加载与生命周期 | 项目当前 `plink-assetmiddleware`；启用 YooAsset 时再按路由读 `plink-yooasset` |
| Unity Editor 操作 | `.cursor/rules/ai-workflow.mdc` 与 `.cursor/docs/conventions/coplay-mcp-unity-playmode.md` |

缺少某份资料时不能假设已安装对应能力，应检查目标项目的替代入口及工具源码。若目标项目要求 Coplay MCP，所有 Unity Editor 交互只通过 Coplay；不得改用 batchmode、另一自动化通道或直接编辑资源 YAML 绕过。保持 Enter Play Mode Options、Reload Domain、Reload Scene 不变，除非用户明确授权修改。

## 资源与导入

优先复用目标项目现有的 PSUIResolver；旧 PSD2UI 只用于明确的兼容需求，不因本 Skill 自动安装或替换导入工具。

以下是 PLink 固定输出矩阵的导航，执行前与目标仓库现行规则及导入器配置核对：

| 产物 | 相对项目根的路径 |
|---|---|
| Sprite / Texture 切图 | `client/Assets/AZ_RProject/Arts/UI/Images/<Module>/` |
| SpriteAtlas | `client/Assets/AZ_RProject/Res/Atlas/<Module>/` |
| UI Prefab | `client/Assets/AZ_RProject/Res/UI/<Module>/` |
| 项目内编辑器工具（仅用户明确要求新增项目脚本时） | `client/Assets/AZ_RProject/Scripts/Editor/UI/<Module>/` |
| 生成绑定及按需求实现的 Hot UI 功能代码 | `client/Assets/AZ_RProject/Scripts/Hot/UI/<PanelName>/` |

工程内编辑器工具路径仅作条件导航，本个人流程直接复用已有导出和绑定实现，不新增工程内辅助脚本或永久菜单。完整流程包括现有生成器产出的绑定代码；具体功能代码按需求实现。项目专用自动化脚本位于目标项目允许的工具/任务目录、Unity 导入范围之外。要求 Coplay MCP 的项目仍只使用 Coplay；脚本放到外部不改变 Editor 操作通道。

PSD 源路径沿用项目明确约定及用户指定位置，不从旧样例推导统一存储目录。盘点已有图片与 Common 资源，再决定复用或导出：

- 同名、同路径或文件存在不足以证明可复用。核对实际切图内容（含尺寸、透明区域）及影响显示的导入设置（如 Sprite / Texture 类型、切片与九宫格边界、PPU、压缩）；能证明与当前 PSD 的预期输出一致才复用。缺失、已变化或暂不能证明一致的图片先隔离导出，对比后确定去向。
- 候选导出阶段对正式图片及 Common 资源只读复用，不覆盖文件或改动其导入设置。正式图片更新、导入设置调整及 Prefab 改引用纳入用户确认清单；共享图片仅当前页面需要变化时，优先生成该页面专用资源，避免影响其他页面。确需更新共享资源时，先查清引用范围并在同一清单中说明影响。
- 更新原资源时保留其 `.meta` / GUID；新建独立资源使用新身份，不复制旧 GUID。Sprite 切片变化还需核对实际子资源引用，不能只看主资源 GUID。不同层同名、图片复用、Sprite 与 RawImage 分流均检查最终输出及引用。

生成图集时核对 `Include In Build`；项目使用 YooAsset SBP 时按项目资源流程核对 `TrackSpriteAtlasDependencies`。UI 制作不隐含授权发布或重建整个资源包，涉及打包配置变更按任务边界另行处理。

### 现有导出入口

调用前执行 [导出前整理稿检查](psd-preparation.md#导出前整理稿检查)，确保实际输入是已核验版本；直接调用导出工具、临时导出与重导入验证均适用。

核对 `client/Assets/A_PLink_Public/Scripts/Editor/PSUIResolver/Editor/Importer/` 下当前实现。PSD Inspector 的 `Generate Prefab` 由 `PS2UIResolver.PsImporterEditor.ExecuteExportNow(importer, true)` 执行切图与 Prefab 输出，该入口当前为私有方法。外部自动化需要控制图片复用时，沿用现有服务链：

`PsFileParser.Parse` → `PsLayerTreeBuilder.BuildTree` → `PsTextureExportService.ExportTextures` → `PsPrefabExportService.GeneratePrefab`。

这些服务当前位于 `PS2UIResolver`，部分类型为 internal；核对签名后可从外部 Coplay 脚本反射调用，不向 `Assets` 添加桥接脚本。服务接收 `PsImporterSettings`（通常取自 importer.settings）和 `PsProjectSettings.instance`；检查导出结果的 `Cancelled`、Prefab 生成的布尔结果和保存后的实际资源。document 用完需 Dispose。按需导出缺失或变化图片时，最终 Prefab 仍使用完整图层树与完整资源映射，包含已核验的复用资源和新导出资源，不能只传本次导出图层集合；暂不能证明一致的图片也按上述规则隔离导出比较。

## 节点与代码

以目标 XUGUI 生成器的扫描逻辑为准；目前标准协议是名称的最后一个下划线分段：

| 节点名示例 | 生成用途 |
|---|---|
| `Content_g` | GameObject 引用 |
| `Confirm_b` | UIEventTriggerListener；不是 Unity Button 字段 |
| `Progress_c` | 当前节点的受支持 UI 组件 |
| `Cell_@` | 列表项生成边界及独立 Item 代码 |

`_c` 当前常见识别顺序为 ScrollRect、InputField、Text、Image、RawImage、TMP_InputField、TextMeshProUGUI、Slider；必须核对当前源码。Button、Toggle、Dropdown 等不能因为加了 `_c` 就视为受支持。

绑定由运行需求决定：静态装饰和纯容器无需后缀；已有 `_c` 或 `_b` 引用可以访问自身 GameObject，不必另套 `_g` 只为控制同一对象。HorizontalLayoutGroup、VerticalLayoutGroup、LayoutElement、ContentSizeFitter 不属于当前 `_c` 支持列表；仅需 Inspector 配置时不生成引用。确有功能需求需要代码访问时，遵循目标项目允许的手写 Mono partial/组件扩展方式，不能用 `_c` 假装绑定成功。

同一生成作用域内名称唯一且能组成合法 C# 标识符；未标记的父节点不会阻断子节点扫描。使用 `Cell_@`，不要套用旧资料中的 `@Item` 示例。移除全部绑定标记可能触发生成器删除现有 Mono/Auto 文件，执行前核对范围。

## 通用 Item 判定

分类时比较重复控件的结构、字段类型和独立生命周期。只有图片、文字、数量或冷却值不同，且结构能由同一组字段表达时，优先考虑一个可复用 Item；装饰分组或结构明显不同的控件不强行合并。

- `_@` 标记单个 Item 模板根，不标记整个列表容器。选择已有字段完整的样本，内部采用 `Icon_c`、`Count_c`、`Cooldown_c` 等通用字段名，并保留实际的 Image/Text 类型；不要为凑结构伪造文字层或业务字段。
- 同一面板内不能复制多个同名 `Skill_@` 并声称它们自动复用。当前生成器逐个生成父字段和克隆方法，Item 类型名由面板名与 Item 根名称组成，不包含父层级；重复根名可能造成重复成员和类型文件覆盖。
- `SkillRed_@`、`SkillBlue_@` 会生成两个不同 Item 类型；颜色变化本身不应成为拆分类型的理由。确实具有不同结构和职责时，可以使用不同名称分别生成。
- 只做 PSD 分类且要保留全部外观时，可以保留一个 `Skill_@` 模板和其余无绑定标记的参考组。参考组后代同样会被扫描，因此不能在它们里面继续放重复的 `Icon_c` 等标记；使用有区分度、无绑定后缀的资源名称，兼顾切图路径唯一性。命名校验同时检查父面板作用域、每个 Item 的子字段作用域和整个面板的 Item 类型名。

```text
Skills
  Skill_@
    Icon_c
    Cooldown_c
  SkillBlue_Reference
    SkillBlueIcon
    SkillBlueCooldown
```

参考组保留画面，但不是已完成绑定的同类型实例。后续用户要求运行 UI 时，先确定模板、显示数量和差异数据来源，再决定最终 Prefab 的参考节点取舍；保留需要的切图和文本，只有实例方案能够接管它们时才移除参考节点。通过权威生成、编译、刷新得到模板类型，再从模板克隆并填入图标/文本，避免参考与运行实例重复显示。不要将任意参考 GameObject 直接传给克隆帮助方法；当前方法要求其已具有正确的 Item Mono 与序列化引用。

核对当前 Clone/Push 实现：常见 Clone 方法直接 Instantiate 模板并沿用模板父节点；隐藏模板的克隆需要显式激活，并确认它进入正确的布局容器。`UIPanelBaseItem.Push()` 只回收包装对象及引用时，克隆 GameObject 的隐藏、销毁或池化须由明确的所有者处理，不能把 Push 当作 GameObject 回收。模板可作为首个实例，也可隐藏后只用于克隆，须选定一种方式，避免多显示一项或重复回收。

## 生成与刷新

完整制作流程在 Prefab 减法和布局完成后执行本节；已有指定阶段边界时按用户范围处理。复用现有生成与刷新代码，不新增工程内绑定辅助脚本。生成的面板/Item 类和 Mono 属于绑定产物；具体业务功能随后按需求实现。

维护任务按 [已有链条维护](existing-ui-maintenance.md) 区分：每次 PSD 合并到正式 Prefab 后都调用本节工具流程；用户仅调整适配时检查显示、维护原说明，不运行生成或刷新。[仅修改手写功能代码](existing-ui-maintenance.md#仅修改手写功能代码) 且节点、绑定组件与序列化引用需求均未变化时，不运行生成或刷新。用户确认正式 Prefab 改动清单后，对清单内的绑定及功能代码不再二次确认。

当前公开静态入口位于 `client/Assets/A_PLink_Public/Scripts/Editor/XUGUI/UIPrefabOperationEditor.CreateCS.cs`：

`PLink.Editor.UI.UIPrefabOperationEditor.RefreshUIPrefab(prefabAssetPath, finalPanelCsDirectory, isJustCodeGenerate)`。

先传 `true` 生成，依据新生成的字段与类型完成已确认范围内必要的手写引用迁移、删除引用处理或类型适配，待 Unity 编译通过且生成类型可加载，再传 `false` 刷新。没有引用变化则跳过修复；不能因旧手写代码编译失败而等待绑定通过后才修，也不修改生成文件来恢复旧字段。其余功能在绑定通过后实现，清单内修复不二次确认。`finalPanelCsDirectory` 是必须已存在的最终面板代码目录，静态方法不会追加面板名；UI 操作窗口选择的是代码父目录，由窗口追加面板名。当前 `RequestScriptCompilation()` 内实际编译请求被注释，不能依赖方法名或一次刷新调用自动等待新类型编译。

首次生成时使用上述静态入口或 `Tools/Client/UI/UI操作窗口` 明确指定正确目录。仅挂 `UIBasePanelMono` 基类时，Inspector 按类型名定位代码目录会指向基类所在位置；面板专属 Mono 生成并刷新后，再按实际类型使用 Inspector 的按钮。每次执行前核对当前源码，保留目标已有手写文件。

代码生成及必要手写引用修复后，确认 Unity 编译通过，再刷新 Prefab。检查实际 Mono 类型、序列化引用、根 Transform 和 Canvas；不能将“已有生成文件”或“刷新调用没有异常”当作绑定通过。根缩放为零、引用为空或 Prefab 没保存都应使该阶段验收失败。

- `*_Mono.cs`、`*Entity_Auto.cs` 及 Item 的生成文件均按实际覆盖行为保护，不因缺少 `_Auto` 后缀而手改。
- 业务与生命周期写在不会被覆盖的 `*Entity.cs` / Item partial。新增序列化字段使用生成器不会命中的独立手写 Mono partial 或专用组件。
- 可生成引用的节点使用生成字段；不要通过 `Find`、`GetComponentsInChildren` 或按名称遍历来补绑定，也不要手写生成结果。
- 按当前生成器核对命名空间、Prefab 路径与字段名，不复用旧面板的类型名、资源 GUID 或缓存字段。

## 手写行为和适配

面板遵循当前 UIBaseEntity 生命周期及 `[UIPanel]` 要求，保留框架 `isSetSefaArea` 的实际拼写；安全区是否启用按页面布局和需求决定，不能继承某个加载页的关闭设置。

OnShow/OnHide 的基类调用、事件绑定/解绑和回收成对；自定义字段先清理，`base.Dispose()` / `base.Push()` 最后执行。PLink 实体按 EntityFactory/GetNeed 系列创建获取，业务状态通过业务实体或管理器接口变更，业务日志用 `PLink.Core.Log`。

项目同时安装 XUGUIManager.Extension 与 DOTween 时遵循当前 Skill 的 AddClickListener 注册规则，未启用时不引入该依赖。修改框架或编辑器工具前按项目规则检查平台宏和程序集边界。

750×1334 是个人流程的设计基准，不意味着在每个面板任意新增 CanvasScaler 或改动全局 Canvas。核对运行时管理器如何设置 Canvas、相机、缩放与安全区，再选择适配落点。进度条 Filled 类型可以由明确的 Prefab/手写初始化设置，但不得只改表现而漏掉生成引用校验。

至少分开报告 PSD 结构、静态 Prefab、Editor 生成/刷新、编译和 PlayMode 的结果。外部 C# 编译或脚本盘点不能替代 Unity 中的加载、适配和重开验证。

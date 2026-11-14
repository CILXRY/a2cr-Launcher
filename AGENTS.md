# AGENTS.md

给后续接手这个仓库的 AI / 开发者看的说明。先读这份，再读 `docs/CONTRACT.md`
和 `docs/UI.md`。

## 项目概况

- a2Cr Launcher：迷你 Minecraft 启动器，Python 3.14。
- 两套入口：CLI `al`（`a2cr_launcher.cli`）和 Flet 桌面 GUI `al-gui`
  （`a2cr_launcher.ui.gui`）。
- 主分支：`elegant`。
- 启动器数据默认在 `~/.a2CrLauncher`；可用环境变量 `A2CR_ROOT` 整体覆盖。

## 常用命令

```powershell
uv sync
uv run python -m tests.smoke      # 离线冒烟测试，必须全绿
uv run al --help                  # CLI 至少能起来
uv run al-gui                     # 打开 GUI
```

在受限环境里 `uv` 缓存可能不可写，可以直接用项目虚拟环境：

```powershell
.\.venv\Scripts\python.exe -m tests.smoke
.\.venv\Scripts\al.exe --help
```

## 开发/测试用的数据目录

不要为了测试往真实的 `~/.a2CrLauncher` 里塞东西。推荐：

```powershell
$env:A2CR_ROOT = "$PWD\artifacts\demo-root"
uv run al-gui
```

`artifacts/` 只用于临时演示数据，提交前删掉。截图产物放
`docs/screenshots/`，不要放临时日志。

## 目录与职责

| 路径 | 职责 |
|---|---|
| `src/a2cr_launcher/core/` | 下载、HTTP、路径、平台信息 |
| `src/a2cr_launcher/meta/` | 版本列表/版本 JSON/资源索引/继承合并 |
| `src/a2cr_launcher/launch/` | 参数拼装、运行库、安装、进程 |
| `src/a2cr_launcher/java/` | Java 发现与选择 |
| `src/a2cr_launcher/modloader/` | Fabric / Quilt / Forge / NeoForge 安装 |
| `src/a2cr_launcher/modpack/` | Modrinth / CurseForge / HMCL、PCL 导入与更新 |
| `src/a2cr_launcher/instance.py` | 实例元数据、回收站 |
| `src/a2cr_launcher/settings.py` | `settings.json` 读写 |
| `src/a2cr_launcher/services.py` | **UI 唯一允许依赖的入口** |
| `src/a2cr_launcher/ui/` | Flet 界面 |
| `tests/smoke.py` | 离线冒烟测试 |

## 冻结的接口约定

详见 `docs/CONTRACT.md`，这里只列最容易踩的几条：

1. **只增不改**：给现有函数加参数时必须有默认值，不要改现有参数含义和顺序。
2. **UI 只依赖 `services.py`**。不要在 `ui/` 里 import `core/`、`meta/`、
   `launch/`、`java/`、`modpack/`。
3. **回调是 UI 的生命线**：`on_progress`、`on_log`、`on_process` 不要删。
4. **底层不 print**：`core/`、`meta/`、`launch/`、`java/` 里不写 `print`，
   输出交给 CLI/GUI。
5. **路径只有一个来源**：所有目录从 `core/paths.py` 取。
6. 取消下载抛 `core.download.DownloadCancelled`；`services.py` 会重新导出它，
   UI 捕获 `services.DownloadCancelled`。不要把它当成普通 `RuntimeError` 包住。

## GUI 结构

- `ui/gui.py`：`LauncherApp`，负责窗口、导航、数据刷新、后台任务、游戏会话、
  底部状态条。页面函数统一接收 `LauncherApp`。
- `ui/theme.py`：深/浅调色板、Flet Theme、封面渐变。
- `ui/components.py`：卡片、按钮、标签、空状态、封面、logo。
- `ui/state.py`：`LogBus`、`TaskState`、`GameSession`、`StdoutTee`。
- `ui/dialogs.py`：错误/确认对话框、导入更新向导。
- `ui/views/`：首页、实例、版本、日志、设置。
- `ui/utils.py`：纯格式化函数，方便单测。

线程模型：

- 网络/磁盘操作走 `asyncio.to_thread`；
- 工作线程只写 `LogBus` 队列和 `TaskState` 字段，**不要直接碰控件**；
- `_pump_logs` / `_pump_tasks` / `_pump_session` 在事件循环里定时把状态搬到控件。

## Flet 1.1.2 踩坑清单

这个项目用的是 Flet 1.1.2，API 和旧教程差别很大：

1. 颜色是 **`#AARRGGBB`**，不是 `#RRGGBBAA`。写错会得到亮黄色/透明异常。
2. 内边距/外边距用 `ft.Padding.symmetric(...)`、`ft.Margin.symmetric(...)`，
   不是 `ft.padding.symmetric`。
3. `Row(wrap=True)` 的子控件里不要再放 `expand=True`，否则 Flutter 布局会
   渲染成灰色错误块。需要响应式时用 `ResponsiveRow`。
4. `ListView` 在 `expand` 约束不明确时也可能出现灰色占位；版本/日志页现在用
   `Column(scroll=ft.ScrollMode.AUTO)`。
5. `Switch` 的标签样式参数是 `label_text_style`，不是 `label_style`。
6. `FilePicker`、`Clipboard` 是异步 Service，需要 `page.services.append(...)`，
   `await picker.pick_files(...)`。
7. `ft.Icon` 的图标字段是 `icon`，不是 `name`。
8. `Container.offset` 是**相对控件尺寸的比例**，不是像素；hover 上浮用 `-0.012`。
9. 切换主题时 `LauncherApp` 会重建外壳并重新渲染当前页；新增组件不要在模块
   顶层缓存颜色，构建时读 `P` 或 `app.p`。

## 修改 UI 时的习惯

- 所有面向用户的文案和代码注释用中文；注释解释“为什么”，不要复述代码。
- 新页面尽量拆进 `ui/views/`，不要把逻辑堆回 `gui.py`。
- 耗时操作必须有 busy/进度状态，不能让界面看起来卡死。
- 删除实例用回收站（`instance.trash`），不要 `shutil.rmtree`。
- 导入/更新失败要给出可操作提示；已下载文件要可续传。
- 新增/修改界面能力后，同步更新 `docs/UI.md` 和截图。

## 验证底线

任何提交前至少跑：

```powershell
uv run python -m tests.smoke
uv run al --help
```

涉及界面的改动再跑一次 `uv run al-gui`，确认：

- 没有数据目录时能正常创建并显示空状态（issue #4）；
- 五个页面都能切换，不出现灰色错误块；
- 导入预检、实例详情、删除确认对话框能正常打开；
- 深色/浅色主题切换正常。

## 当前状态（2026-11）

- issue #4：已修复，首次启动自动创建目录并显示失败兜底页。
- issue #7：已实现 GUI 导入和整合包更新。
- 整合包更新用 `managed_files` 记录托管文件，只删除哈希未变的旧文件。
- 真实 Minecraft 启动/真实大整合包导入尚未做端到端验证，改动后建议用手上的
  真实实例回归一次。
- issue #8（火绒拦截 Flet 缓存）属于运行环境问题，不是应用崩溃，遇到时提示
  用户检查安全软件。

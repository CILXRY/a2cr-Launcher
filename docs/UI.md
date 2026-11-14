# 图形界面结构

界面使用 Flet 1.1.2 的桌面模式，入口仍然是 `al-gui`（`a2cr_launcher.ui.gui:run`）。

## 目录

| 文件 | 作用 |
|---|---|
| `ui/gui.py` | `LauncherApp`：窗口、导航、数据刷新、后台任务、游戏会话、页脚状态条 |
| `ui/theme.py` | 深色/浅色调色板、Flet Theme、实例封面渐变色 |
| `ui/components.py` | 卡片、按钮、标签、空状态、封面、logo 等可复用控件 |
| `ui/state.py` | `LogBus`、`TaskState`、`GameSession`、`StdoutTee` |
| `ui/dialogs.py` | 错误/确认对话框，导入和更新向导 |
| `ui/views/` | 首页、实例、版本、日志、设置五个页面 |
| `ui/utils.py` | 时间、路径、内存、加载器名称等纯函数 |

页面函数统一接收 `LauncherApp`，返回一个 `ft.Control`。`LauncherApp.render()` 负责
把当前页放进 `AnimatedSwitcher`，切换页面时不重新创建窗口。

## 线程模型

- 所有网络/磁盘操作走 `asyncio.to_thread`；
- 工作线程只写 `LogBus` 队列和 `TaskState` 字段，不直接碰控件；
- 三个 pump 任务在事件循环里运行：
  - `_pump_logs`：每 150ms 批量取日志；
  - `_pump_tasks`：更新底部任务条，任务结束 2.5s 后收起；
  - `_pump_session`：更新游戏时长，发现进程创建后切换“启动中 / 运行中”。

## 导入向导

`ImportDialog` 分三步：

1. `services.inspect_modpack()` 在后台解析压缩包，显示格式/MC 版本/加载器/文件数；
2. 用户确认后，`App.start_import_task()` 启动后台线程，`TaskState` 记录阶段；
3. 对话框每 120ms 轮询 `TaskState`，显示进度、最近日志和取消按钮。

`update_folder` 非空时走更新流程，后端只清理“旧整合包托管且哈希未变”的文件，
不会碰 `saves`、`options.txt` 或玩家自己改过的 mod。

## 主题

调色板在 `theme.DARK` / `theme.LIGHT` 里。切换主题时：

1. 存 `settings.json`；
2. 更新 `ui.set_palette()`；
3. 重建外壳（侧边栏、页脚）并重新渲染当前页。

因此新增组件时不要在模块顶层缓存颜色，要在构建控件时读取 `P` 或 `app.p`。

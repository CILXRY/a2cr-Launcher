# 接口契约

这份文档的目的只有一个：**防止两个人（或两个 AI）把同一件事写出两套实现。**

改这里的任何签名之前，先在群里说一声，改完顺手更新本文件。

---

## 一、冻结的接口

### 下载

```python
# core/download.py
def download(
    targets: list[tuple[str, Path, str, int]],
    *,
    show_progress: bool = True,
    description: str = "下载文件",
    on_progress: Callable[[int, int, str, str], None] | None = None,
) -> bool:
```

- `targets`：`(下载 URL, 保存路径, sha1, 文件大小)`
- `show_progress=True`：CLI 用 rich 打进度条
- `on_progress(done, total, name, status)`：GUI 用，`status ∈ {"success", "skipped", "failed"}`
- 返回 `True` 表示全部成功（含跳过）
- **传了 `on_progress` 就不要往控制台打进度**

### 安装

```python
# launch/install.py
def install(meta: dict, on_progress: Callable | None = None) -> bool:
```

一次性装齐：资源索引 → client.jar → logging 配置 → libraries → assets。失败抛 `RuntimeError`。

### 游戏启动

```python
# launch/process.py
def launch(cmd: list[str], game_dir: Path, on_log=None, on_process=None) -> int:
```

- `on_log(text)`：每读到一行游戏输出就回调一次；不传则打印到控制台
- `on_process(proc)`：进程创建后回调一次，参数是 `subprocess.Popen`，GUI 用它停止游戏
- 返回游戏进程的退出码

### 数据目录

所有目录都从 `core/paths.py` 取。默认根目录是 `~/.a2CrLauncher`，可以用
`A2CR_ROOT` 环境变量整体覆盖（便携版、自动化测试和截图演示用）。
首次启动调用 `create_launcher_dirs()` 创建缺少的目录；issue #4 的问题就出在这里。

### 给界面的入口

```python
# services.py
def list_installed() -> list[str]              # 返回版本号，不是路径
def list_installed_versions() -> list[dict]    # 原版 + 加载器版本，读本地 JSON
def list_instances() -> list[dict]             # 整合包实例，附带 path/loader/mods_count
def inspect_modpack(path) -> dict              # 只解析不安装，给导入预检
def import_modpack(path, name=None, *, on_log=None, on_progress=None, cancel=None,
                   update_folder=None) -> dict
def list_versions(version_type="release", limit=0) -> list[dict]
def list_java_runtimes() -> list[dict]
def install_version(version_id, on_progress=None, cancel=None) -> bool
def launch_version(version_id, max_memory="4G", name="a2Cr", on_log=None,
                   on_process=None, java_path=None) -> int
def launch_instance(folder, max_memory="4G", name="a2Cr", on_log=None,
                    on_process=None, java_path=None) -> int
def trash_instance(folder) -> Path
def load_settings() / save_settings(...) -> dict
```

`services.py` 是 UI 唯一允许依赖的模块。UI 不许直接 import `core/`、`meta/`、`launch/`。

界面需要新增能力时，优先在 `services.py` 加一个薄封装，不要在页面里绕过它。

### 导入进度

`modpack.import_pack(..., on_progress=...)` 的回调签名是：

```python
on_progress(stage: str, done: int, total: int, detail: str)
```

`stage` 目前是 `parse` / `resolve` / `vanilla` / `loader` / `extract` / `files` / `done`。
新增阶段时同步更新 `ui/dialogs.py` 的 `STAGE_LABELS`。

### 取消

`download(..., cancel=callable)` 和 `install(..., cancel=callable)` 在取消时抛出
`core.download.DownloadCancelled`（属于 `RuntimeError` 子类）。`services.py` 会把它
重新导出为 `services.DownloadCancelled`，UI 只能从这里捕获——不要在 `ui/` 里直接
import `core/`。上层必须**先**捕获它，不要把它当成普通下载失败包一层 `RuntimeError`，
否则界面无法区分“取消”和“失败”。已写入的 `.part` 文件会保留，下次继续续传。

### 版本元数据

```python
# meta/versions.py
def get_version_meta(version_id: str, refresh: bool = False) -> dict
```

必须返回**完整的版本 JSON**（含 `libraries`、`arguments`、`logging`、`downloads`、`assetIndex`），不要只返回摘要——拼参数时每一段都会被用到。

---

## 二、约定

1. **只增不改**：给现有函数加可选参数（新参数必须有默认值），不要改现有参数的含义或顺序。
2. **回调是 UI 的生命线**：`on_progress` 被删掉，GUI 会静默退化成"没有进度"，不会报错——所以别删。
3. **路径只有一个来源**：所有目录都从 `core/paths.py` 取，别在别处拼 `Path.home()`。
4. **底层不 print**：`core/`、`meta/`、`launch/`、`java/` 里不许出现 `print`；输出由 `cli.py` / `ui/` 负责。
5. **一种实现**：同一个功能（进度、重试、磁盘校验）只准有一套代码。发现重复，先合并再继续。

---

## 三、目录归属

| 目录 | 负责人 | 说明 |
|---|---|---|
| `core/` `meta/` `launch/` `java/` | 见群 | 改动前通知另一位 |
| `ui/` `services.py` | 界面负责人 | 另一方一般不动 |
| `cli.py` | 共用 | 改子命令先说一声 |

改别人负责的目录：**先打招呼，再动手。** 不要静默改完甩一个 PR。

---

## 四、验证底线

任何 PR 合入前，这三条必须能跑通：

```powershell
uv run python -m tests.smoke          # 离线冒烟测试，必须全绿
uv run al --help                     # CLI 至少能起来
uv run al install --version <某个已装版本>   # 幂等：第二次应全是 skipped
```

涉及界面的改动再加一条：

```powershell
uv run al-gui                        # 窗口能开、能启动、不卡死
```

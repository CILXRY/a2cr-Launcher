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
def launch(cmd: list[str], game_dir: Path, on_log=None) -> int:
```

- `on_log(text)`：每读到一行游戏输出就回调一次；不传则打印到控制台
- 返回游戏进程的退出码

### 给界面的入口

```python
# services.py
def list_installed() -> list[str]              # 返回版本号，不是路径
def install_version(version_id: str, on_progress=None) -> bool
def launch_version(version_id: str, max_memory="4G", name="a2Cr", on_log=None) -> int
```

`services.py` 是 UI 唯一允许依赖的模块。UI 不许直接 import `core/`、`meta/`、`launch/`。

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

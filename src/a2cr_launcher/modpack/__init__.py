"""整合包导入：识别格式 → 装原版 → 装加载器 → 建实例 → 解压 overrides → 下载 mods。

GUI 和 CLI 共用这里。GUI 会额外传入 ``on_progress``、``cancel`` 和
``update_folder``，CLI 不传时行为和以前完全一致。
"""

import hashlib
from pathlib import Path

from a2cr_launcher import instance
from a2cr_launcher.core.download import DownloadCancelled, download
from a2cr_launcher.launch.install import install
from a2cr_launcher.meta.versions import get_version_meta
from a2cr_launcher.modloader import install_loader
from a2cr_launcher.modpack import archive, curseforge, local, modrinth


def detect(path: Path) -> dict:
    """根据压缩包内容判断整合包格式。"""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"找不到整合包文件：{path}")
    if modrinth.is_modrinth(path):
        return modrinth.read(path)
    if curseforge.is_curseforge(path):
        return curseforge.read(path)
    if local.is_local(path):
        return local.read(path)
    raise ValueError("无法识别的整合包格式：支持 Modrinth .mrpack、CurseForge .zip、HMCL/PCL 导出的压缩包")


def _emit(on_progress, stage: str, done: int = 0, total: int = 0, detail: str = "") -> None:
    """统一阶段回调格式：stage 是粗粒度阶段，done/total 用于进度条。"""
    if on_progress is not None:
        on_progress(stage, done, total, detail)


def _check_cancel(cancel) -> None:
    """在长时间步骤之间主动检查取消，让用户点“取消”后不用等整个阶段结束。"""
    if cancel is not None and cancel():
        raise DownloadCancelled("导入已取消")


def _install_vanilla(mc_version: str, log, on_progress=None, cancel=None) -> None:
    """安装原版客户端、资源、运行库和日志配置。"""
    _check_cancel(cancel)
    log(f"安装原版 Minecraft {mc_version} ...")
    meta = get_version_meta(mc_version, refresh=True)

    # install() 内部已经做了资源索引 / client / logging / libraries / assets 的完整安装，
    # 这里直接复用，避免 CLI 和 GUI 各维护一套下载顺序。
    def _download_progress(done, total, name, status):
        _emit(on_progress, "vanilla", done, total, f"{done}/{total}  {name}")

    try:
        install(meta, on_progress=_download_progress, cancel=cancel)
    except DownloadCancelled:
        # 取消不是安装失败，必须原样抛给 GUI，否则界面只会显示“下载失败”
        raise
    except RuntimeError as err:
        raise RuntimeError(f"原版 {mc_version} 没有下载完整：{err}") from err


def _target_path(root: Path, relative: str) -> Path | None:
    """把整合包里的相对路径解析到实例目录内，顺便挡住 ../ 逃逸。"""
    target = (Path(root) / relative).resolve()
    try:
        target.relative_to(Path(root).resolve())
    except ValueError:
        return None
    return target


def _sha1(path: Path) -> str:
    """计算文件 sha1，用于判断文件是否被玩家改过。"""
    try:
        with open(path, "rb") as file:
            return hashlib.file_digest(file, "sha1").hexdigest()
    except OSError:
        return ""


def _managed_entries(directory: Path, files: list[dict]) -> list[dict]:
    """整理整合包托管文件清单，只记录真正能对应到实例目录内的文件。"""
    managed = []
    for item in files:
        relative = item.get("path")
        if not relative or _target_path(directory, relative) is None:
            continue
        managed.append({"path": relative, "sha1": item.get("sha1", "")})
    return managed


def _remove_stale_files(directory: Path, old_managed: list[dict], new_paths: set[str], log) -> None:
    """删除旧整合包托管、但新整合包不再需要的文件。

    只有文件仍然存在且哈希和导入时记录的一致才会删除；玩家自己改过的 mod
    不会被静默清掉。整理包之外的目录（saves、options.txt 等）完全不碰。
    """
    for item in old_managed:
        relative = item.get("path")
        if not relative or relative in new_paths:
            continue
        target = _target_path(directory, relative)
        if target is None or not target.is_file():
            continue
        expected = item.get("sha1") or ""
        if expected and _sha1(target) != expected:
            log(f"保留玩家修改过的文件：{relative}")
            continue
        try:
            target.unlink()
        except OSError as err:
            log(f"清理旧文件失败（已跳过）：{relative}：{err}")


def import_pack(path: Path, name: str | None = None, log=print, on_progress=None,
                cancel=None, update_folder: str | None = None) -> dict:
    """
    导入一个整合包。

    Args:
        path: 整合包压缩包路径
        name: 实例名，为空时用整合包自带的名字；更新已有实例时忽略
        log: 输出日志的函数
        on_progress: ``(stage, done, total, detail)``，给 GUI 显示阶段进度
        cancel: 返回 True 时中止导入（正在运行的 Forge 安装器无法中途杀掉）
        update_folder: 已存在实例的目录名。传入后不新建实例，而是用新整合包更新它

    Returns:
        dict: 实例元数据
    """
    path = Path(path)
    _emit(on_progress, "parse", 0, 1, "解析整合包…")
    log(f"读取整合包：{path.name}")
    plan = detect(path)
    _emit(on_progress, "parse", 1, 1, "解析完成")
    _check_cancel(cancel)

    description = f"{plan['name']}（Minecraft {plan['mc_version']}"
    if plan["loader"] != "vanilla":
        description += f" / {plan['loader']} {plan['loader_version']}"
    log(description + "）")

    if plan["format"] == "curseforge":
        total = len(plan["files"])
        log(f"解析 {total} 个 CurseForge 文件 ...")

        def _progress(done, count):
            _emit(on_progress, "resolve", done, count, f"解析文件地址 {done}/{count}")
            if count and (done == count or done % 20 == 0):
                log(f"  已解析 {done}/{count}")

        plan["files"] = curseforge.resolve_files(plan["files"], on_progress=_progress)
        log("文件地址解析完成")
        _check_cancel(cancel)

    _install_vanilla(plan["mc_version"], log, on_progress=on_progress, cancel=cancel)

    _check_cancel(cancel)
    if plan["loader"] == "vanilla":
        version_id = plan["mc_version"]
    else:
        _emit(on_progress, "loader", 0, 0, f"安装 {plan['loader']} {plan['loader_version']}")
        log(f"安装 {plan['loader']} {plan['loader_version']} ...")
        version_id = install_loader(plan["mc_version"], plan["loader"], plan["loader_version"], log=log)
        _emit(on_progress, "loader", 1, 1, f"{plan['loader']} 安装完成")

    source = {"format": plan["format"], "file": str(path), "pack_version": plan["pack_version"]}

    # 决定这次是新建、续跑还是更新已有实例
    existing = None
    if update_folder:
        existing = instance.load(update_folder)
        if existing is None:
            raise ValueError(f"找不到要更新的实例：{update_folder}")
        log(f"更新已有实例：{existing['folder']}")
    elif not name:
        existing = instance.find_by_source(str(path))
        if existing is not None:
            log(f"继续使用已有实例：{existing['folder']}")

    if existing is not None:
        # 同一个压缩包重复导入（比如上次下载失败）或用户主动更新时，沿用原来的目录
        meta = existing
        meta.update({
            "mc_version": plan["mc_version"],
            "version_id": version_id,
            "loader": {"type": plan["loader"], "version": plan["loader_version"]},
            "source": source,
        })
        if update_folder:
            meta["name"] = meta.get("name") or update_folder
        instance.save(meta)
    else:
        meta = instance.create(
            name or plan["name"],
            plan["mc_version"],
            version_id,
            loader={"type": plan["loader"], "version": plan["loader_version"]},
            source=source,
        )
        log(f"创建实例：{meta['folder']}")

    directory = instance.instance_dir(meta["folder"])

    _emit(on_progress, "extract", 0, 0, "解压整合包文件…")
    if plan["format"] == "local":
        extracted = archive.extract_prefix(path, plan["extract_prefix"], directory,
                                           skip_prefixes=plan["skip_prefixes"])
        log(f"解压整合包文件 {extracted} 个")
    elif plan["overrides"]:
        extracted = archive.extract_overrides(path, plan["overrides"], directory)
        log(f"解压 overrides {extracted} 个文件")
    _emit(on_progress, "extract", 1, 1, "解压完成")
    _check_cancel(cancel)

    targets = []
    for item in plan["files"]:
        target = _target_path(directory, item["path"])
        if target is None:
            continue
        targets.append((item["url"], target, item["sha1"], item["size"]))

    if targets:
        _emit(on_progress, "files", 0, len(targets), "下载整合包文件…")

        def _file_progress(done, total, filename, status):
            _emit(on_progress, "files", done, total, f"{done}/{total}  {filename}")

        ok = download(targets, description="整合包文件", show_progress=False,
                      on_progress=_file_progress, cancel=cancel)
        if not ok:
            raise RuntimeError("整合包里的文件没有下载完整，重新运行导入命令会继续补下")

    # 更新时清掉旧版整合包里已经不需要的 mod；先下载成功再清理，避免失败后两头空
    new_managed = _managed_entries(directory, plan["files"])
    if update_folder and plan["format"] != "local":
        # 本地整合包（HMCL/PCL）没有清单文件，无法判断哪些文件归整合包托管；
        # 这时只覆盖/解压，不做删除，避免误删玩家自己的 mod。
        new_paths = {item["path"] for item in new_managed}
        _remove_stale_files(directory, meta.get("managed_files") or [], new_paths, log)

    meta["managed_files"] = new_managed
    instance.save(meta)

    Path(directory, "mods").mkdir(exist_ok=True)
    _emit(on_progress, "done", 1, 1, "导入完成")
    return meta

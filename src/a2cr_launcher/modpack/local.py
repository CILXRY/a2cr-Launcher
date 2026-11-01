"""HMCL / PCL 导出的整合包（压缩包里带 .minecraft 目录）解析。

这类压缩包一般已经包含 mods、config、options.txt，以及 ``versions/<版本>/<版本>.json``。
我们只需要识别出「Minecraft 版本 + 加载器版本」，文件原样解压进实例目录。
"""

import json
import re
import zipfile
from pathlib import Path

SKIP_PREFIXES = ("versions/", "libraries/", "assets/", "logs/", "crash-reports/", "PCL/")


def _is_versions_entry(name: str) -> bool:
    return name.startswith("versions/") and name.endswith(".json")


def is_local(archive: Path) -> bool:
    try:
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
    except (zipfile.BadZipFile, OSError):
        return False
    if any(name.startswith(".minecraft/") for name in names):
        return True
    if any(name.startswith("minecraft/") for name in names):
        return True
    return any(_is_versions_entry(name) for name in names)


def _match_loader_version(version_id: str, patterns: tuple[str, ...]) -> str:
    """从 PCL 那种 ``1.17.1-Forge_37.1.1`` 的版本名里抠出加载器版本。"""
    for pattern in patterns:
        match = re.search(pattern, version_id, re.IGNORECASE)
        if match:
            return match.group(1)
    return version_id


def _loader_from_meta(meta: dict) -> tuple[str, str, str]:
    """从版本 JSON 里推断 (加载器类型, 加载器版本, 原版版本)。"""
    version_id = str(meta.get("id") or "")
    base = meta.get("inheritsFrom") or version_id
    lowered = version_id.lower()
    main_class = str(meta.get("mainClass") or "").lower()

    if "fabric" in lowered or "fabricmc" in main_class:
        prefix = "fabric-loader-"
        version = version_id[len(prefix):] if version_id.startswith(prefix) else version_id
        if base and version.endswith(f"-{base}"):
            version = version[: -len(base) - 1]
        else:
            version = _match_loader_version(version_id, (r"fabric[_-](?:loader[_-])?([\d][\w.+\-]*)",))
        return "fabric", version, base
    if "quilt" in lowered or "quiltmc" in main_class:
        prefix = "quilt-loader-"
        version = version_id[len(prefix):] if version_id.startswith(prefix) else version_id
        if base and version.endswith(f"-{base}"):
            version = version[: -len(base) - 1]
        else:
            version = _match_loader_version(version_id, (r"quilt[_-](?:loader[_-])?([\d][\w.+\-]*)",))
        return "quilt", version, base
    if "neoforge" in lowered:
        return "neoforge", _match_loader_version(version_id, (r"neoforge[_-]([\d][\w.+\-]*)",)), base
    if "forge" in lowered or "cpw.mods" in main_class:
        return "forge", _match_loader_version(version_id, (r"forge[_-]([\d][\w.+\-]*)",)), base
    return "vanilla", "", base


def _read_pcl_config(z: zipfile.ZipFile, version_dir: str) -> dict:
    """读取 PCL2 写在版本目录里的 config.v1.yml / Setup.ini。"""
    for name in (f"{version_dir}/PCL/config.v1.yml", f"{version_dir}/PCL/Setup.ini"):
        try:
            text = z.read(name).decode("utf-8", errors="replace")
        except KeyError:
            continue
        config = {}
        for line in text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                config[key.strip()] = value.strip().strip("'\"")
        return config
    return {}


def _from_pcl_config(config: dict) -> tuple[str, str, str]:
    mc = config.get("VersionOriginal") or config.get("VersionVanillaName") or ""
    for key, kind in (("VersionFabric", "fabric"), ("VersionQuilt", "quilt"),
                      ("VersionNeoForge", "neoforge"), ("VersionForge", "forge")):
        value = config.get(key, "")
        if value:
            return kind, value, mc
    return "vanilla", "", mc


def read(archive: Path) -> dict:
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        prefix = ".minecraft/" if any(n.startswith(".minecraft/") for n in names) else \
            "minecraft/" if any(n.startswith("minecraft/") for n in names) else ""

        candidates = []
        for name in names:
            if not name.startswith(prefix + "versions/") or not name.endswith(".json"):
                continue
            parts = name[len(prefix + "versions/"):].split("/")
            if len(parts) != 2 or parts[1] != f"{parts[0]}.json":
                continue
            try:
                meta = json.loads(z.read(name))
            except (json.JSONDecodeError, KeyError):
                continue
            if isinstance(meta, dict) and meta.get("id"):
                candidates.append(meta)

        # 优先选带 inheritsFrom（也就是装了加载器）的版本
        candidates.sort(key=lambda meta: 0 if meta.get("inheritsFrom") else 1)
        chosen = candidates[0] if candidates else None

        if chosen is not None:
            loader_type, loader_version, mc_version = _loader_from_meta(chosen)
        else:
            loader_type, loader_version, mc_version = "vanilla", "", ""
            for name in names:
                match = re.match(rf"^{re.escape(prefix)}versions/([^/]+)/PCL/", name)
                if match:
                    config = _read_pcl_config(z, f"{prefix}versions/{match.group(1)}")
                    loader_type, loader_version, mc_version = _from_pcl_config(config)
                    break

    if not mc_version:
        raise ValueError("无法从整合包里识别 Minecraft 版本（没有 versions/*.json，也没有 PCL 配置）")

    return {
        "format": "local",
        "name": Path(archive).stem,
        "pack_version": "",
        "mc_version": mc_version,
        "loader": loader_type,
        "loader_version": loader_version,
        "files": [],
        "overrides": [],
        "archive": Path(archive),
        "extract_prefix": prefix,
        "skip_prefixes": SKIP_PREFIXES,
    }

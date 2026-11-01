"""解析带 inheritsFrom 的版本 JSON。

Fabric / Quilt / Forge / NeoForge 的版本文件都是「子版本 + inheritsFrom 指向原版」
的结构，启动前需要把父版本合并进来，得到一份完整的 meta。
"""

from copy import deepcopy

from a2cr_launcher.meta.versions import get_version_meta


def _merge_arguments(parent: dict, child: dict) -> dict:
    """把父版本和子版本的参数列表拼起来（父在前，子在后）。"""
    parent_args = parent.get("arguments") if isinstance(parent.get("arguments"), dict) else {}
    child_args = child.get("arguments") if isinstance(child.get("arguments"), dict) else {}
    merged = {}
    for key in set(parent_args) | set(child_args):
        merged[key] = list(parent_args.get(key) or []) + list(child_args.get(key) or [])
    return merged


def _merge_libraries(parent: dict, child: dict) -> list:
    """父版本运行库在前，子版本在后；同名的以子版本为准。"""
    libraries: dict[str, dict] = {}
    for library in list(parent.get("libraries") or []) + list(child.get("libraries") or []):
        key = library.get("name") or library.get("downloads", {}).get("artifact", {}).get("path")
        if key is None:
            continue
        libraries[key] = library
    return list(libraries.values())


def _merge(parent: dict, child: dict, base_version: str) -> dict:
    merged = deepcopy(parent)
    merged.update({
        "id": child.get("id", parent.get("id")),
        "type": child.get("type", parent.get("type", "release")),
        "mainClass": child.get("mainClass") or parent.get("mainClass"),
        "libraries": _merge_libraries(parent, child),
        "arguments": _merge_arguments(parent, child),
        "_baseVersion": base_version,
    })
    if child.get("minecraftArguments"):
        merged["minecraftArguments"] = child["minecraftArguments"]
    if child.get("logging"):
        merged["logging"] = child["logging"]
    if child.get("javaVersion"):
        merged["javaVersion"] = child["javaVersion"]
    merged.pop("inheritsFrom", None)
    return merged


def resolve_meta(version_id: str, _stack: tuple[str, ...] = ()) -> dict:
    """
    读取版本 meta，并把 ``inheritsFrom`` 链上的父版本合并进来。

    Returns:
        dict: 合并后的 meta，额外带一个 ``_baseVersion`` 表示最底层的原版版本号。
    """
    if version_id in _stack:
        raise ValueError(f"版本继承出现循环：{' -> '.join(_stack + (version_id,))}")

    meta = get_version_meta(version_id)
    parent_id = meta.get("inheritsFrom")
    if not parent_id:
        meta = deepcopy(meta)
        meta["_baseVersion"] = meta.get("id", version_id)
        return meta

    parent = resolve_meta(parent_id, _stack + (version_id,))
    return _merge(parent, meta, parent.get("_baseVersion", parent_id))

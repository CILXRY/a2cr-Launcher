"""整合包压缩包里的文件操作（安全解压、overrides 合并）。"""

import shutil
import zipfile
from pathlib import Path


def _safe_target(root: Path, member: str) -> Path | None:
    """防止 zip 里的 ../ 把文件写到实例目录外面。"""
    target = (root / member).resolve()
    try:
        target.relative_to(Path(root).resolve())
    except ValueError:
        return None
    return target


def member_names(archive: Path) -> list[str]:
    with zipfile.ZipFile(archive) as z:
        return z.namelist()


def extract_prefix(archive: Path, prefix: str, dest: Path, *, skip_prefixes: tuple[str, ...] = ()) -> int:
    """
    把压缩包里 ``prefix/`` 下的内容解压到 dest。

    Returns:
        解压出来的文件数量
    """
    prefix = prefix.strip("/")
    if prefix:
        prefix += "/"

    count = 0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name = info.filename
            if not name.startswith(prefix) or name.endswith("/"):
                continue
            relative = name[len(prefix):]
            if not relative or any(relative.startswith(skip) for skip in skip_prefixes):
                continue
            target = _safe_target(dest, relative)
            if target is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    return count


def extract_overrides(archive: Path, prefixes: list[str], dest: Path) -> int:
    """按顺序解压多个 overrides 目录（后面的覆盖前面的）。"""
    count = 0
    for prefix in prefixes:
        count += extract_prefix(archive, prefix, dest)
    return count

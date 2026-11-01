"""模组加载器安装入口。"""

from a2cr_launcher.modloader import fabric, forge

FLAVORS = ("fabric", "quilt", "forge", "neoforge")


def install_loader(mc_version: str, flavor: str, loader_version: str | None = None, log=print) -> str:
    """
    安装加载器并返回可以用于启动的版本 id。

    Args:
        mc_version: 原版版本
        flavor: fabric / quilt / forge / neoforge
        loader_version: 加载器版本，Fabric/Quilt 为空时取最新
        log: 输出日志的函数
    """
    if flavor in ("fabric", "quilt"):
        return fabric.install(mc_version, loader_version, flavor=flavor)
    if flavor in ("forge", "neoforge"):
        return forge.install(mc_version, flavor, loader_version, log=log)
    raise ValueError(f"不支持的加载器：{flavor}")

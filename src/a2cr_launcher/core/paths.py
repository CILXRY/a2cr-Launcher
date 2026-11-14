"""
定义启动器所使用的路径。

所有运行时目录都从这里取，避免 UI / CLI / 下载器各拼一套路径。
默认放在用户目录下的 ``.a2CrLauncher``；设置 ``A2CR_ROOT`` 环境变量可以整体改到
别的目录（自动化测试、便携版或截图演示时很有用）。
"""
import os
from pathlib import Path


def _default_root() -> Path:
    """解析启动器根目录，允许用环境变量覆盖，方便测试和便携使用。"""
    override = os.getenv("A2CR_ROOT")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".a2CrLauncher"


# 根目录
ROOT_DIR = _default_root()

# 实例文件夹
INSTANCES_DIR = ROOT_DIR / "instances"

# Minecraft 静态资源文件夹
# 存放一些静态、可重下或者可自动生成的文件
MINECRAFT_STATIC_ASSETS_DIR = ROOT_DIR / ".minecraftStaticAssets"

# 资源文件夹
#   indexes: 资源标识 Json
#   objects: 资源文件
#   skins:   皮肤文件
ASSETS_DIR = MINECRAFT_STATIC_ASSETS_DIR / "assets"
# 运行库文件夹
LIBRARIES_DIR = MINECRAFT_STATIC_ASSETS_DIR / "libraries"
# 版本文件夹
# 根据各个版本罗列的文件夹
#   <version>/client.jar: 版本客户端 Jar
#   <version>/server.jar: 版本服务端 Jar
#   <version>/meta.json: 版本元信息
VERSIONS_DIR = MINECRAFT_STATIC_ASSETS_DIR / "versions"
# 日志配置文件夹
# 各个版本的日志配置
LOG_CONFIGS_DIR = MINECRAFT_STATIC_ASSETS_DIR / "log_configs"

# 启动器设置文件
SETTINGS_FILE = ROOT_DIR / "settings.json"
# 删除实例时先移到这里，避免误删后无法找回
TRASH_DIR = ROOT_DIR / ".trash"

# 首次启动需要创建的全部目录。顺序无所谓，create_launcher_dirs 会逐个创建。
REQUIRED_DIRS = (
    ROOT_DIR,
    INSTANCES_DIR,
    MINECRAFT_STATIC_ASSETS_DIR,
    ASSETS_DIR,
    LIBRARIES_DIR,
    VERSIONS_DIR,
    LOG_CONFIGS_DIR,
    TRASH_DIR,
)


def create_launcher_dirs() -> None:
    """创建启动器需要的目录（幂等）。

    这里故意不吞异常：调用方需要知道是权限问题还是磁盘问题，才能给用户
    一个可操作的提示。issue #4 的根因就是首次启动时目录还不存在。
    """
    for directory in REQUIRED_DIRS:
        Path(directory).mkdir(parents=True, exist_ok=True)

"""
定义启动器所使用的路径
"""
from pathlib import Path

# 根目录
ROOT_DIR = Path.home() / ".a2CrLauncher"

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

from a2cr_launcher import cli

# 打包产物里没有安装元数据，界面靠它兜底显示版本号（见 services.get_launcher_version_code）。
# 发布时若改了 pyproject.toml 的 version，这里要一起改。
__version__ = "0.3.2-beta.1"


def main() -> None:
    cli.main()

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from sys import exit

from requests import RequestException
from rich.console import Console
from rich.table import Table

from a2cr_launcher.core.paths import VERSIONS_DIR, LIBRARIES_DIR, ASSETS_DIR, INSTANCES_DIR, LOG_CONFIGS_DIR
from a2cr_launcher.core.platform_info import current_platform
from a2cr_launcher.launch.arguments import build_arguments
from a2cr_launcher.launch.install import download_client, download_logging, download_assets, download_libraries
from a2cr_launcher.launch.process import launch
from a2cr_launcher.meta.manifest import get_version_manifest
from a2cr_launcher.meta.versions import get_version_meta


def main():
    console = Console()
    parser = ArgumentParser(description='a2cr Minecraft Launcher')
    subparsers = parser.add_subparsers(dest='command')

    # parser.add_argument('launch', action='store')
    version_parser = subparsers.add_parser('version')
    version_parser.add_argument('--limit', default=20, type=int)
    version_parser.add_argument('--type', action='store', default='release')

    install_parser = subparsers.add_parser('install')
    install_parser.add_argument('--version', action='store')

    launch_parser = subparsers.add_parser('launch')
    launch_parser.add_argument('--version', action='store')

    args = parser.parse_args()

    if "unknown" in current_platform():
        print("检测到不支持的系统。")
        exit(1)

    if args.command == 'version':
        try:
            version_list = get_version_manifest(args.type, args.limit)
        except RequestException as err:
            print(f'[Network Error] 无法连接服务器,请检查网络或者代理设置: {err}')
            exit(1)

        version_table = Table(title="Minecraft Version List")
        version_table.add_column("ID")
        version_table.add_column("Type")
        version_table.add_column("Update Time")
        version_table.add_column("Release Time")
        for version in version_list:
            version_table.add_row(version.get('id'), version.get('type'),
                                  datetime.fromisoformat(version["time"]).strftime("%Y-%m-%d %H:%M:%S") if version.get(
                                      "time") else None,
                                  datetime.fromisoformat(version["releaseTime"]).strftime(
                                      "%Y-%m-%d %H:%M:%S") if version.get("releaseTime") else None)

        console.print(version_table)

    elif args.command == 'install':
        print("下载版本", args.version)
        meta = get_version_meta(args.version)
        download_client(meta, VERSIONS_DIR)
        download_logging(meta, LOG_CONFIGS_DIR)
        download_assets(meta, ASSETS_DIR)
        download_libraries(meta, LIBRARIES_DIR)
        print("下载完成。")

    elif args.command == 'launch':
        version = args.version
        game_dir = Path(INSTANCES_DIR, version)
        if not game_dir.is_dir():
            Path(game_dir).mkdir(parents=True, exist_ok=True)
        launch(build_arguments(get_version_meta(version), game_dir), game_dir)

    else:
        parser.print_help()
        exit(1)


if __name__ == '__main__':
    main()

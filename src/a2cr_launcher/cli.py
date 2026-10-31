from argparse import ArgumentParser
from pathlib import Path
from sys import exit

from requests import RequestException

from a2cr_launcher.core.paths import VERSIONS_DIR, LIBRARIES_DIR, ASSETS_DIR, INSTANCES_DIR
from a2cr_launcher.launch.arguments import build_arguments
from a2cr_launcher.launch.install import download_client, download_logging, download_assets, download_libraries
from a2cr_launcher.launch.process import launch
from a2cr_launcher.meta.manifest import get_version_list
from a2cr_launcher.meta.versions import get_version_meta


def main():
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

    if args.command == 'version':
        try:
            version_list = get_version_list(args.type, args.limit)
        except RequestException as err:
            print(f'[Network Error] 无法连接服务器,请检查网络或者代理设置: {err}')
            exit(1)
        print(version_list)

    elif args.command == 'install':
        print("下载版本", args.version)
        meta = get_version_meta(args.version)
        download_client(meta, VERSIONS_DIR)
        download_logging(meta, ASSETS_DIR)
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

import argparse
import sys

import requests

from meta.manifest import get_version_list

parser = argparse.ArgumentParser(description='a2cr Minecraft Launcher')


def main():
    parser.add_argument('versions', action='store')
    parser.add_argument('--limit', default=20, type=int)
    parser.add_argument('--type', action='store', default='release')

    args = parser.parse_args()
    if args.versions:
        try:
            version_list = get_version_list(args.type, args.limit)
        except requests.RequestException as err:
            print(f'[Network Error] 无法连接服务器,请检查网络或者代理设置: {err}')
            sys.exit(1)
        print(version_list)


if __name__ == '__main__':
    main()

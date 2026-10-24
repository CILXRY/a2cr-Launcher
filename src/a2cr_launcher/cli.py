import argparse
from a2cr_launcher.meta.manifest import get_version_list

parser = argparse.ArgumentParser(description='a2cr Minecraft Launcher')
parser.add_argument('versions', action='store')
parser.add_argument('--limit', default=20, type=int)
parser.add_argument('--type', action='store', default='release')

args = parser.parse_args()


def main():
    if args.versions:
        version_list = get_version_list(args.type, args.limit)
        print(version_list)


if __name__ == '__main__':
    main()

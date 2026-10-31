from pathlib import Path
from string import Template

from a2cr_launcher.auth.offline import offline_uuid
from a2cr_launcher.core.paths import VERSIONS_DIR, ASSETS_DIR, LIBRARIES_DIR
from a2cr_launcher.core.platform_info import current_platform
from a2cr_launcher.java.discover import find_java
from a2cr_launcher.launch.classpath import build_classpath
from a2cr_launcher.launch.rules import is_allowed, feature_rule_list


def _build_java_arguments(arg_raw, values, meta, dropped_args):
    arguments = []
    # Java Args
    for arg in arg_raw.get('jvm'):
        if type(arg) is dict:
            if is_allowed([arg["rules"][0]], current_platform()[0], current_platform()[1]):
                if type(arg["value"]) is list:
                    # 这里用extend是指把arg["value"]里的值全部追加给arguments
                    arguments.extend(arg["value"])
                else:
                    arguments.append(arg["value"])
            else:
                dropped_args.append(arg)
        elif type(arg) is str:
            result = Template(arg).substitute(natives_directory=values["natives_directory"],
                                              launcher_name=values["launcher_name"],
                                              launcher_version=values["launcher_version"],
                                              classpath=values["classpath"])
            arguments.append(result)
        else:
            dropped_args.append(arg)

    # Log4J
    if meta.get('logging'):
        arguments.append(Template(meta['logging']['client'].get("argument")).substitute(
            path=str(Path(ASSETS_DIR, "log_configs", meta['logging']['client']["file"]["id"]))))

    # Main Class
    arguments.append(meta.get("mainClass"))

    return arguments


def _build_game_arguments(arg_raw, values):
    arguments = []
    for arg in arg_raw.get('game'):
        if type(arg) is dict:
            result = feature_rule_list([arg], values["current_features"], values["feature_variables"])
            if result: arguments.extend(result)
        elif type(arg) is str:
            result = Template(arg).substitute(auth_player_name=values["auth_player_name"],
                                              version_name=values["version_name"],
                                              game_directory=values["game_directory"],
                                              assets_root=values["assets_root"],
                                              assets_index_name=values["assets_index_name"],
                                              auth_uuid=values["auth_uuid"],
                                              auth_access_token=values["auth_access_token"],
                                              clientid=values["clientid"],
                                              auth_xuid=values["auth_xuid"],
                                              version_type=values["version_type"],
                                              user_type=values["user_type"],
                                              )
            arguments.append(result)
    return arguments


def build_arguments(meta, game_dir: Path, name="a2Cr", ):
    version = meta["id"]
    values = {
        "auth_player_name": name,
        "version_name": version,
        "game_directory": str(game_dir),
        "assets_root": str(ASSETS_DIR),
        "assets_index_name": meta["assetIndex"]["id"],
        "auth_uuid": offline_uuid(name),
        "auth_access_token": "0",
        "clientid": "", "auth_xuid": "",
        "version_type": meta["type"],
        "natives_directory": str(Path(VERSIONS_DIR, version, "natives")),
        "launcher_name": "a2cr-launcher", "launcher_version": "0.1",
        "classpath": build_classpath(meta, LIBRARIES_DIR, current_platform()[0], current_platform()[1],
                                     str(Path(VERSIONS_DIR, version, "client.jar"))),
        "current_features": {"is_demo_user": False, "has_custom_resolution": False, "has_quick_plays_support": False,
                             "is_quick_play_singleplayer": False, "is_quick_play_multiplayer": False,
                             "is_quick_play_realms": False},
        "feature_variables": {"resolution_width": 1920, "resolution_height": 1080, "quickPlayPath": "",
                              "quickPlaySinglePlayer": "", "quickPlayMultiplayer": "", "quickPlayRealms": ""},
        "user_type": "legacy"
    }

    arguments = []
    dropped_args = []  # 排错用的
    arg_raw = meta.get('arguments')

    # Java Execution
    arguments.append(find_java(meta["javaVersion"]["majorVersion"], ))

    # Java Arguments
    arguments.extend(_build_java_arguments(arg_raw, values, meta, dropped_args))

    # Game Arguments
    arguments.extend(_build_game_arguments(arg_raw, values, ))

    return arguments

# if __name__ == "__main__":
#     from a2cr_launcher.meta.versions import get_version_meta
#
#     print(build_arguments(get_version_meta("1.13")))

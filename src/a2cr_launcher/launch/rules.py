from string import Template


def _rule_matches(target_rule, current_os, current_features=None):
    """
    判断一条规则是否符合可用规则
    Args:
        target_rule (dict): {"action": "allow", "features": {"is_demo_user": true}} | {"action": "allow","os": {"name": "osx"}}
        current_os (tuple[str, str]): (当前系统, 当前架构)
        current_features (dict): {"is_demo_user": true}

    Returns:
        bool: 通过结果
    """
    target_os_rule: dict = target_rule.get("os", {})  # 存放系统规则
    target_features: dict = target_rule.get("features", {})  # 存放功能规则

    if target_os_rule:
        if "name" in target_os_rule and target_os_rule["name"] != current_os[0]: return False  # 判断系统规则
        if "arch" in target_os_rule and target_os_rule["arch"] != current_os[1]: return False  # 判断架构规则

    for key, wanted_value in target_features.items():
        if current_features.get(key, False) != wanted_value: return False  # 判断功能规则

    # 全通过则符合规则
    return True


def is_allowed(rules, os_name, os_arch, features=None) -> bool:
    """
    返回一组规则是否可以被允许
    Args:
        features: 当前功能设置
        rules (list[dict]): 规则集 ex: `[{"action": "allow"}, {"action": "disallow", "os": {"name": ""}}]`
        os_name (str): 系统名
        os_arch (str): 系统架构

    Returns:
        bool: (是/否)允许运行规则
    """

    # 空规则集情况
    if not rules:
        return True

    for rule in reversed(rules):
        if _rule_matches(rule, (os_name, os_arch), features):
            return rule.get("action") == "allow"

    return False


def feature_rule_list(target_rules, current_features, variables=None):
    """
    根据已启用的规则集返回参数集
    Args:
        variables (dict): 变量池，用来替换 value 的变量
        target_rules (list[dict]): 目标规则集
        current_features (dict): 已启用的规则集

    Returns:
        list: feature 参数集
    """
    args = []
    for item in target_rules:
        rules = item.get("rules", {})
        value = item.get("value")

        allowed = False
        # 检查值
        for rule in rules:
            action = rule.get("action")
            required = rule.get("features")

            is_match = True
            for key, expected_value in required.items():
                if current_features.get(key) != expected_value:
                    is_match = False
                    break
            if is_match and action == "allow":
                allowed = True
                break

        # 替换值
        if allowed:
            value_to_process = []
            if type(value) == str:
                value_to_process = [value]
            elif type(value) == list:
                value_to_process = value

            for v in value_to_process:
                processed = Template(v).substitute(variables)
                args.append(processed)
    return args


if __name__ == '__main__':
    tr = [{
        "rules": [
            {
                "action": "allow",
                "features": {
                    "is_demo_user": True
                }
            }
        ],
        "value": "--demo"
    },
        {
            "rules": [
                {
                    "action": "allow",
                    "features": {
                        "has_custom_resolution": True
                    }
                }
            ],
            "value": [
                "--width",
                "${resolution_width}",
                "--height",
                "${resolution_height}"
            ]
        },
        {
            "rules": [
                {
                    "action": "allow",
                    "features": {
                        "has_quick_plays_support": True
                    }
                }
            ],
            "value": [
                "--quickPlayPath",
                "${quickPlayPath}"
            ]
        },
        {
            "rules": [
                {
                    "action": "allow",
                    "features": {
                        "is_quick_play_singleplayer": True
                    }
                }
            ],
            "value": [
                "--quickPlaySingleplayer",
                "${quickPlaySingleplayer}"
            ]
        },
        {
            "rules": [
                {
                    "action": "allow",
                    "features": {
                        "is_quick_play_multiplayer": True
                    }
                }
            ],
            "value": [
                "--quickPlayMultiplayer",
                "${quickPlayMultiplayer}"
            ]
        },
        {
            "rules": [
                {
                    "action": "allow",
                    "features": {
                        "is_quick_play_realms": True
                    }
                }
            ],
            "value": [
                "--quickPlayRealms",
                "${quickPlayRealms}"
            ]
        }
    ]
    print(feature_rule_list(tr, {"is_demo_user": True, "has_custom_resolution": True},
                            {"resolution_width": 1920, "resolution_height": 1080}))

# if __name__ == '__main__':
#     cases = [
#         ([], "windows", "x86_64", True),  # 空规则
#         ([{"action": "allow"}], "windows", "x86_64", True),  # 全 allow
#         ([{"action": "disallow"}], "windows", "x86_64", False),  # 全 disallow
#         ([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}], "windows", "x86_64", True),
#         # disallow macOS, cur:windows
#         ([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}], "osx", "x86_64", False),
#         # disallow macOS, cur:macOS
#         ([{"action": "allow", "os": {"name": "windows", "arch": "x86_64"}}], "windows", "x86_64", True),  # allow 64-bit
#         ([{"action": "allow", "os": {"name": "windows", "arch": "x86"}}], "windows", "x86_64", False),
#         # allow 32-bit only
#         ([{"action": "allow", "os": {"name": "windows", "arch": "arm64"}}], "windows", "x86_64", False),  # allow arm64
#         ([{"action": "allow", "os": {"name": "linux"}}], "windows", "x86_64", False),  # allow linux only, cur: windows
#         ([{"action": "disallow", "os": {"name": "linux"}}], "windows", "x86_64", False),
#         # disallow linux only, cur: windows
#         ([{"action": "allow", "os": {"name": "osx"}}, {"action": "allow", "os": {"name": "windows"}}], "osx", "x86_64",
#          True),  # allow windows and macOS, cur: macOS
#         ([{"action": "allow", "os": {"name": "osx"}}, {"action": "allow", "os": {"name": "windows"}}], "linux",
#          "x86_64", False),  # allow windows and macOS, cur: linux
#     ]
#     for rules, o, a, expect in cases:
#         got = is_allowed(rules, o, a)
#         assert got == expect, f"期望 {expect} 实际 {got}: {rules}"
#     print("all passed")
#
#
#     def check(version: str):
#         meta = get_version_meta(version)
#         allowed = [l for l in meta["libraries"] if is_allowed(l.get("rules", []), "windows", "x86_64")]
#         print(meta.get("libraries_len"), "->", len(allowed))
#         print("被排除的:", [l["name"] for l in meta["libraries"] if l not in allowed])
#
#
#     check("26.2")
#     check("1.20.1")
#     check("1.8.9")

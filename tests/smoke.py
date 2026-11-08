"""离线冒烟测试：不联网、不开窗口、不写磁盘。

用法：
    uv run python -m tests.smoke
    uv run pytest tests -q          # 装了 pytest 也可以

这些用例是协作的刹车片：别人（或 AI）大改 core 之后，跑一遍就知道有没有踩回去。
任何新修的 bug，都往这里补一条用例。
"""

import importlib

from a2cr_launcher.launch.rules import feature_rule_list, is_allowed

WIN = ("windows", "x86_64")

# (规则, 系统, 架构, features, 期望)
RULE_CASES = [
    ([], "windows", "x86_64", None, True),
    ([{"action": "allow"}], "windows", "x86_64", None, True),
    ([{"action": "disallow"}], "windows", "x86_64", None, False),
    ([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}],
     "windows", "x86_64", None, True),
    ([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}],
     "osx", "x86_64", None, False),
    ([{"action": "allow", "os": {"name": "windows", "arch": "x86_64"}}],
     "windows", "x86_64", None, True),
    ([{"action": "allow", "os": {"name": "windows", "arch": "x86"}}],
     "windows", "x86_64", None, False),
    ([{"action": "allow", "os": {"name": "windows", "arch": "arm64"}}],
     "windows", "x86_64", None, False),
    ([{"action": "allow", "os": {"name": "linux"}}],
     "windows", "x86_64", None, False),
    # 只有 disallow 且不匹配 → 没人授权 → 排除
    ([{"action": "disallow", "os": {"name": "linux"}}],
     "windows", "x86_64", None, False),
    # 多条 allow：必须跳过不匹配的，继续往前找
    ([{"action": "allow", "os": {"name": "osx"}},
      {"action": "allow", "os": {"name": "windows"}}], "osx", "x86_64", None, True),
    ([{"action": "allow", "os": {"name": "osx"}},
      {"action": "allow", "os": {"name": "windows"}}], "linux", "x86_64", None, False),
    # features：未开 = False，规则要求 True 则不匹配
    ([{"action": "allow", "features": {"is_demo_user": True}}],
     "windows", "x86_64", {"is_demo_user": False}, False),
    ([{"action": "allow", "features": {"is_demo_user": True}}],
     "windows", "x86_64", {"is_demo_user": True}, True),
    # 规则要求 False 也必须能正确匹配
    ([{"action": "allow", "features": {"has_custom_resolution": False}}],
     "windows", "x86_64", {}, True),
]

FEATURE_ITEMS = [
    {"rules": [{"action": "allow", "features": {"is_demo_user": True}}],
     "value": "--demo"},
    {"rules": [{"action": "allow", "features": {"has_custom_resolution": True}}],
     "value": ["--width", "${resolution_width}", "--height", "${resolution_height}"]},
    {"rules": [{"action": "allow", "features": {"is_quick_play_singleplayer": True}}],
     "value": ["--quickPlaySingleplayer", "${quickPlaySingleplayer}"]},
]

FEATURE_VARS = {
    "resolution_width": 1920,
    "resolution_height": 1080,
    "quickPlaySingleplayer": "sv",
}

FEATURE_CASES = [
    ({}, []),
    ({"is_demo_user": True}, ["--demo"]),
    ({"is_demo_user": True, "has_custom_resolution": True},
     ["--demo", "--width", "1920", "--height", "1080"]),
]

IMPORT_MODULES = [
    "a2cr_launcher.cli",
    "a2cr_launcher.services",
    "a2cr_launcher.core.download",
    "a2cr_launcher.core.http_util",
    "a2cr_launcher.core.paths",
    "a2cr_launcher.core.platform_info",
    "a2cr_launcher.launch.arguments",
    "a2cr_launcher.launch.classpath",
    "a2cr_launcher.launch.install",
    "a2cr_launcher.launch.libraries",
    "a2cr_launcher.launch.process",
    "a2cr_launcher.launch.rules",
    "a2cr_launcher.meta.assets",
    "a2cr_launcher.meta.manifest",
    "a2cr_launcher.meta.versions",
    "a2cr_launcher.java.discover",
    "a2cr_launcher.ui.gui",
]


def test_rules():
    for rules, os_name, os_arch, features, expect in RULE_CASES:
        got = is_allowed(rules, os_name, os_arch, features)
        assert got == expect, f"规则求值错误 {rules}: 期望 {expect} 实际 {got}"


def test_feature_rule_list():
    for features, expect in FEATURE_CASES:
        got = feature_rule_list(FEATURE_ITEMS, *WIN, features, FEATURE_VARS)
        assert got == expect, f"条件参数错误 {features}: 期望 {expect} 实际 {got}"


def test_imports():
    for name in IMPORT_MODULES:
        importlib.import_module(name)


def test_services():
    from a2cr_launcher.services import list_installed

    installed = list_installed()
    assert isinstance(installed, list)
    assert all(isinstance(v, str) for v in installed)


def main() -> None:
    tests = [test_rules, test_feature_rule_list, test_imports, test_services]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print("smoke passed")


if __name__ == "__main__":
    main()

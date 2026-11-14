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
    "a2cr_launcher.settings",
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
    "a2cr_launcher.modpack",
    "a2cr_launcher.java.discover",
    "a2cr_launcher.ui.gui",
    "a2cr_launcher.ui.theme",
    "a2cr_launcher.ui.components",
    "a2cr_launcher.ui.state",
    "a2cr_launcher.ui.dialogs",
    "a2cr_launcher.ui.utils",
    "a2cr_launcher.ui.views.home",
    "a2cr_launcher.ui.views.instances",
    "a2cr_launcher.ui.views.logs",
    "a2cr_launcher.ui.views.settings",
    "a2cr_launcher.ui.views.versions",
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


def test_settings_normalize():
    """坏掉的设置要回退到默认值，不能把非法值塞进启动参数。"""
    from a2cr_launcher.settings import DEFAULT_SETTINGS, _normalize

    assert _normalize({"max_memory": "4G"})["max_memory"] == "4G"
    assert _normalize({"max_memory": "4096M"})["max_memory"] == "4096M"
    assert _normalize({"max_memory": "abc"})["max_memory"] == DEFAULT_SETTINGS["max_memory"]
    assert _normalize({"max_memory": "0G"})["max_memory"] == DEFAULT_SETTINGS["max_memory"]
    assert _normalize({"theme": "neon"})["theme"] == DEFAULT_SETTINGS["theme"]
    assert _normalize({"player_name": "  "})["player_name"] == DEFAULT_SETTINGS["player_name"]
    assert _normalize({"window_width": 1})["window_width"] >= 960


def test_ui_utils():
    """界面用的格式化函数不能因为空值/坏时间抛异常。"""
    from a2cr_launcher.ui.utils import (format_date, format_duration, format_relative,
                                        format_size, memory_gb, shorten_path)

    assert format_date(None) == "—"
    assert format_date("2026-11-14T10:00:00Z") == "2026-11-14"
    assert format_duration(0) == "00:00"
    assert format_duration(3661) == "1:01:01"
    assert format_relative(None) == "还没玩过"
    assert format_size(0) == "0 B"
    assert memory_gb("8G") == 8
    assert memory_gb("4096M") == 4
    assert memory_gb("bad") == 4
    assert "..." in shorten_path("C:/a/very/long/path/that/should/be/shortened", 20)


def test_import_detect_missing():
    """不存在的整合包要得到一个明确的 FileNotFoundError，而不是别的异常。"""
    from pathlib import Path

    from a2cr_launcher.modpack import detect

    try:
        detect(Path("definitely-not-a-pack.mrpack"))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("detect() 应该对不存在的文件抛出 FileNotFoundError")


def test_managed_entries():
    """整合包托管文件清单要过滤掉 ../ 逃逸路径。"""
    from pathlib import Path

    from a2cr_launcher.modpack import _managed_entries

    managed = _managed_entries(Path("."), [
        {"path": "mods/example.jar", "sha1": "abc"},
        {"path": "../outside.jar", "sha1": "def"},
        {"path": "", "sha1": "empty"},
    ])
    assert managed == [{"path": "mods/example.jar", "sha1": "abc"}]


def test_download_cancel_before_start():
    """取消检查要在发请求之前生效，不能先写文件再退出。"""
    from pathlib import Path

    from a2cr_launcher.core.download import DownloadCancelled, download

    try:
        download([("http://127.0.0.1:1/never", Path("never-downloaded.bin"), "", 0)],
                 cancel=lambda: True)
    except DownloadCancelled:
        pass
    else:
        raise AssertionError("预置 cancel 时 download 应该抛 DownloadCancelled")
    assert not Path("never-downloaded.bin").exists()


def main() -> None:
    tests = [test_rules, test_feature_rule_list, test_imports, test_services,
             test_settings_normalize, test_ui_utils, test_import_detect_missing,
             test_managed_entries, test_download_cancel_before_start]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print("smoke passed")


if __name__ == "__main__":
    main()

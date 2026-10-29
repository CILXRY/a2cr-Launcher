from a2cr_launcher.meta.versions import get_version_meta


def _os_rule_matches(target_rule, current_os):
    """
    Args:
        target_rule (tuple[str, str]): (目标系统, 目标架构)
        current_os (tuple[str, str]): (当前系统, 当前架构)

    Returns:
        bool: 通过结果
    """
    # 判断系统规则
    if target_rule[0] and target_rule[0] != current_os[0]:
        return False

    # 判断架构规则
    elif target_rule[1] and target_rule[1] != current_os[1]:
        return False

    # 全通过则符合规则
    return True


def is_allowed(rules, os_name, os_arch) -> bool:
    """
    返回一组规则是否可以被允许
    Args:
        rules (list[dict]): 规则 ex: `[{"action": "allow"}, {"action": "disallow", "os": {"name": ""}}]`
        os_name (str): 系统名
        os_arch (str): 系统架构

    Returns:
        bool: (是/否)允许运行规则
    """

    # 空规则集情况
    if not rules:
        return True
    for rule in reversed(rules):
        target_os = rule.get("os", {}).get("name")
        target_arch = rule.get("os", {}).get("arch")
        if _os_rule_matches((target_os, target_arch), (os_name, os_arch)):
            return rule.get("action") == "allow"
    return False


if __name__ == '__main__':
    cases = [
        ([], "windows", "x86_64", True),  # 空规则
        ([{"action": "allow"}], "windows", "x86_64", True),  # 全 allow
        ([{"action": "disallow"}], "windows", "x86_64", False),  # 全 disallow
        ([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}], "windows", "x86_64", True),
        # disallow macOS, cur:windows
        ([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}], "osx", "x86_64", False),
        # disallow macOS, cur:macOS
        ([{"action": "allow", "os": {"name": "windows", "arch": "x86_64"}}], "windows", "x86_64", True),  # allow 64-bit
        ([{"action": "allow", "os": {"name": "windows", "arch": "x86"}}], "windows", "x86_64", False),
        # allow 32-bit only
        ([{"action": "allow", "os": {"name": "windows", "arch": "arm64"}}], "windows", "x86_64", False),  # allow arm64
        ([{"action": "allow", "os": {"name": "linux"}}], "windows", "x86_64", False),  # allow linux only, cur: windows
        ([{"action": "disallow", "os": {"name": "linux"}}], "windows", "x86_64", False),
        # disallow linux only, cur: windows
        ([{"action": "allow", "os": {"name": "osx"}}, {"action": "allow", "os": {"name": "windows"}}], "osx", "x86_64",
         True),  # allow windows and macOS, cur: macOS
        ([{"action": "allow", "os": {"name": "osx"}}, {"action": "allow", "os": {"name": "windows"}}], "linux",
         "x86_64", False),  # allow windows and macOS, cur: linux
    ]
    for rules, o, a, expect in cases:
        got = is_allowed(rules, o, a)
        assert got == expect, f"期望 {expect} 实际 {got}: {rules}"
    print("all passed")


    def check(version: str):
        meta = get_version_meta(version)
        allowed = [l for l in meta["libraries"] if is_allowed(l.get("rules", []), "windows", "x86_64")]
        print(meta.get("libraries_len"), "->", len(allowed))
        print("被排除的:", [l["name"] for l in meta["libraries"] if l not in allowed])


    check("26.2")
    check("1.20.1")
    check("1.8.9")

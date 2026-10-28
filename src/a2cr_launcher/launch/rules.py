from a2cr_launcher.meta.versions import get_version_meta


def _rule_matches(rule, os_name, os_arch) -> bool:
    target_os = rule.get("os", {}).get("name")
    target_arch = rule.get("os", {}).get("arch")
    if target_os and target_os != os_name:
        return False
    elif target_arch and target_arch != os_arch:
        return False
    return True


def is_allowed(rules: list[dict], os_name: str, os_arch: str) -> bool:
    if not rules:
        return True
    for rule in reversed(rules):
        if _rule_matches(rule, os_name, os_arch):
            return rule.get("action") == "allow"
    return False


if __name__ == '__main__':
    cases = [
        ([], "windows", "x86_64", True), # 空规则
        ([{"action": "allow"}], "windows", "x86_64", True), # 全 allow
        ([{"action": "disallow"}], "windows", "x86_64", False), # 全 disallow
        ([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}], "windows", "x86_64", True), # disallow macOS, cur:windows
        ([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}], "osx", "x86_64", False), # disallow macOS, cur:macOS
        ([{"action": "allow", "os": {"name": "windows", "arch": "x86_64"}}], "windows", "x86_64", True), # allow 64-bit
        ([{"action": "allow", "os": {"name": "windows", "arch": "x86"}}], "windows", "x86_64", False), # allow 32-bit only
        ([{"action": "allow", "os": {"name": "windows", "arch": "arm64"}}], "windows", "x86_64", False), # allow arm64
        ([{"action": "allow", "os": {"name": "linux"}}], "windows", "x86_64", False), # allow linux only, cur: windows
        ([{"action": "disallow", "os": {"name": "linux"}}], "windows", "x86_64", False), # disallow linux only, cur: windows
        ([{"action": "allow", "os": {"name": "osx"}},{"action":"allow","os":{"name": "windows"}}], "osx", "x86_64", True), # allow windows and macOS, cur: macOS
        ([{"action": "allow", "os": {"name": "osx"}},{"action":"allow","os":{"name": "windows"}}], "linux", "x86_64", False), # allow windows and macOS, cur: linux
    ]
    for rules, o, a, expect in cases:
        got = is_allowed(rules, o, a)
        assert got == expect, f"期望 {expect} 实际 {got}: {rules}"
    print("all passed")

    def check(version: str):
        meta = get_version_meta(version)
        allowed = [l for l in meta["libraries"] if is_allowed(l.get("rules", []), "windows", "x86_64")]
        print(meta.get("libraries_len"),"->", len(allowed))
        print("被排除的:", [l["name"] for l in meta["libraries"] if l not in allowed])

    check("26.2")
    check("1.20.1")
    check("1.8.9")
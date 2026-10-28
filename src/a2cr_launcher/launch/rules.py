from a2cr_launcher.meta.versions import get_version_meta


def is_allowed(rules: list[dict], os_name: str, os_arch: str, features: dict) -> bool:
    if not rules:
        return True
    else:
        for rule in reversed(rules):
            action = rule.get("action")
            target_os = rule.get("os", {}).get("name", {})
            target_arch = rule.get("os", {}).get("arch", {})
            if action == "disallow":
                if (target_os and target_os == os_name) or (target_arch and target_arch == os_arch):
                    return False
                else:
                    return True
            elif action == "allow" and ((target_os and target_os == os_name) or (target_arch and target_arch == os_arch)):
                return True
    return False


if __name__ == '__main__':
    def check(version):
        meta = get_version_meta(version)
        allowed = [l for l in meta["libraries"] if is_allowed(l.get("rules", []), "windows", "x86_64", {})]
        print(meta.get("libraries_len"), "->", len(allowed))
        # print("被排除的:", [l["name"] for l in meta["libraries"] if l not in allowed])
        # print("未被排除的:", [l["name"] for l in meta["libraries"] if l in allowed])

    check("26.2") # 88
    check("1.20.1") # 64
    check("1.18.2") # 44
    check("1.12.2") # 34
    check("1.8.9") # 34

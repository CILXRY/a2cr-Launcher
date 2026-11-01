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


def feature_rule_list(target_rules, os_name, os_arch, current_features, variables=None):
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
        if not is_allowed(item.get("rules", []), os_name, os_arch, current_features):
            continue
        value = item.get("value")
        value_to_process = [value] if isinstance(value, str) else value
        for v in value_to_process:
            args.append(Template(v).substitute(variables))
    return args

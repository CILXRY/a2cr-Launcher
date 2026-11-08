## 改了什么

<!-- 一两句话说清楚。涉及多个模块就列出来。 -->

## 为什么

<!-- 解决什么问题？关联 issue 就写 #123 -->

## 怎么验的

<!-- 贴命令输出或截图。至少包含： -->
<!-- uv run python -m tests.smoke -->
<!-- uv run al --help -->

```
```

## 检查清单

- [ ] 没有在 `core/` `meta/` `launch/` `java/` 里留下 `print`
- [ ] 没有重复实现已经存在的功能
- [ ] 没有改冻结接口（如果改了，已更新 `docs/CONTRACT.md` 并通知了另一位）
- [ ] `uv run python -m tests.smoke` 全绿
- [ ] 每一段改动我都能解释它为什么存在

# 为 a2Cr Launcher 做贡献

尽管这只是一个个人练习项目，但仍然对你的贡献予以感谢。

## 从 要做什么 开始

这里➡️ 是 [项目 Issues](https://github.com/CILXRY/a2cr-Launcher/issues)，  
你可以对其中的 [Bugs (问题)](https://github.com/CILXRY/a2cr-Launcher/issues?q=is%3Aissue+state%3Aopen+label%3ABug)
进行修复，  
实现其中的 [Features (功能)](https://github.com/CILXRY/a2cr-Launcher/issues?q=is%3Aissue+state%3Aopen+label%3Aenhancement) ，  
又或者只是单纯地 [提出一个想法](https://github.com/CILXRY/a2cr-Launcher/issues/new/choose)。

## 开发

### 1. 环境 & 分支

- **主分支**：`elegant`
- **主分支保护**：
  - 需要 Pull Request 合并 / Require a pull request before merging
  - 需要线性历史 / Require linear history
  - 阻止强制 Push / Block force pushes

```powershell
git switch -c feat/xxx origin/elegant
# ... 改代码 ...
git add -A
git commit -m "feat(xxx): 一句话说清楚做了什么"
git push -u origin feat/xxx
```

- 合并前先 `git fetch && git rebase origin/elegant`

### 2. 确认环境

在克隆代码之后：

```powershell
uv sync                 # 装依赖
uv run al --help        # CLI 能起来就说明环境 OK
uv run al-gui           # 图形界面
uv run python -m tests.smoke   # 冒烟测试，必须全绿
```

### 3. 目录归属

| 目录                              | 说明                         |
|-----------------------------------|------------------------------|
| `core/` `meta/` `launch/` `java/` | 核心逻辑，改动前在群里说一声 |
| `ui/` `services.py`               | 界面相关，另一方一般不动     |
| `cli.py`                          | 共用，加/改子命令先说一声    |

**改别人负责的目录：先打招呼，再动手。** 不要静默改完甩一个 PR。

### 4. 冻结接口

见 [`docs/CONTRACT.md`](docs/CONTRACT.md)。里面列出的签名（`download`、`install`、`services.*`、`get_version_meta`）是两边共用的契约，
**只许加可选参数，不许改语义**。

改之前先通知，改完更新那份文档。

### 5. 提交前自检（硬性）

```powershell
uv run python -m tests.smoke        # 1. 冒烟测试全绿
uv run al --help                    # 2. CLI 能起来
uv run al install --version <已装版本>   # 3. 幂等：第二次全 skipped
```

动到界面的再加：

```powershell
uv run al-gui                       # 4. 窗口能开、能启动、不卡死
```

**没有跑过的改动不要提 PR。** PR 描述里要贴验证结果（命令输出或截图）。

### 6. 禁止事项

1. `core/` `meta/` `launch/` `java/` 里出现 `print`（输出归 `cli.py` / `ui/`）
2. 同一个功能写两套实现（进度、重试、校验……发现重复先合并）
3. 改冻结接口不通知
4. 一个 PR 做三件事、改二十个文件
5. 提了 AI 生成的大段代码，但自己解释不了它在干什么

### 7. 任务怎么写

不好的任务： **"把整合包导入做得稳一点"**

好的任务包含四样：

```
目标：导入 mrpack 时，若实例目录已存在则跳过已下载文件，不重复下载
涉及：src/a2cr_launcher/modpack/local.py
不要动：core/download.py（接口已冻结）
验收：
  1. uv run al import X.mrpack 跑两次
  2. 第二次日志里全是 skipped，不产生网络请求
  3. 实例目录内容不变
```

**"正确"必须是可验证的。** 给不出验收命令，就说明任务还没想清楚。

### 8. 每周同步（10 分钟）

只问三个问题：

1. 这周你打算改哪些 **文件**？
2. 有没有要动 **冻结接口**？
3. 卡在哪？

问文件，不问功能——功能描述会骗人，文件列表不会。

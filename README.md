# a2Cr Launcher

一个使用 Python 制作的 CLI Minecraft 启动器

## 如何开发

### Step 1 克隆源代码和准备开发环境

1. 首先，这个程序是基于 Python
   开发的，因此，这里推荐的开发环境是 [JetBrains PyCharm](https://www.jetbrains.com/pycharm/download/)  
   _[Visual Studio Code](https://code.visualstudio.com) 也是可以的_

2. 其次，是 Python 环境，这里推荐使用 `uv`， 一个极其轻量的 Python 虚拟环境和包管理器。  
   把这段脚本复制到 PowerShell 里即可（桌面右键 --> 终端）

    ```bash
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

3. 再之后，安装 [Git](https://git-scm.com/install/windows) ，这个是用来克隆源代码的工具  
   如果还没有安装的话，点上面链接下载安装包，安装一路下一步就可以

4. 接下来，是仓库的配置  
   如果需要对这个项目开发的话，需要 [Fork 代码](https://github.com/CILXRY/a2cr-Launcher/fork)
   ，也就是给代码仓库创建一个副本。  
   在创建一个 Fork 之后的项目，点击右上角的绿色的 `code`， 复制地址
5. 然后，在文件管理器里找一个存放代码的位置，打开终端

   ```bash
   git clone <刚刚复制的地址> # 比如， git clone https://github.com/CILXRY/a2cr-Launcher
   
   # Git 的配置
   git config --global user.name "你的名字"
   git config --global user.email "你的邮箱" # 设置和 GitHub 相同的邮箱
   ```
6. 最后，在 PyCharm 里打开这个存放代码的文件夹，在终端里运行 `uv run al` 即可。

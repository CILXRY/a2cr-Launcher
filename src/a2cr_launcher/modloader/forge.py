"""Forge / NeoForge 安装。

这两个加载器没有现成的启动 JSON 接口，必须运行官方安装器：它会下载运行库，
再执行一串处理器生成打过补丁的 jar。这里把安装器静默跑在一个临时目录里，
然后把产物（libraries/、versions/）合并进启动器自己的目录。
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import getproxies

import requests

from a2cr_launcher.core.download import download_file
from a2cr_launcher.core.http_util import http_get
from a2cr_launcher.core.paths import LIBRARIES_DIR, ROOT_DIR, VERSIONS_DIR
from a2cr_launcher.java.discover import find_java
from a2cr_launcher.meta.versions import get_version_meta

INSTALLER_URLS = {
    "forge": "https://maven.minecraftforge.net/net/minecraftforge/forge/{mc}-{ver}/forge-{mc}-{ver}-installer.jar",
    "neoforge": "https://maven.neoforged.net/releases/net/neoforged/neoforge/{ver}/neoforge-{ver}-installer.jar",
}


def version_id_for(mc_version: str, flavor: str, loader_version: str) -> str:
    if flavor == "forge":
        return f"{mc_version}-forge-{loader_version}"
    return f"neoforge-{loader_version}"


def _proxy_java_arguments() -> list[str]:
    """安装器是用 Java 的 HttpURLConnection 下载的，不会读 Windows 系统代理，这里手动传进去。"""
    proxies = getproxies()
    proxy = proxies.get("https") or proxies.get("http")
    if not proxy:
        return []
    parsed = urlparse(proxy if "://" in proxy else f"http://{proxy}")
    if not parsed.hostname:
        return []

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    arguments = []
    for scheme in ("http", "https"):
        arguments.extend([f"-D{scheme}.proxyHost={parsed.hostname}", f"-D{scheme}.proxyPort={port}"])
    return arguments


def _safe_console_text(text: str) -> str:
    """控制台编码（中文 Windows 是 GBK）表示不了的字符替换掉，避免安装器输出里的 emoji 让程序崩溃。"""
    if sys.platform == "win32":
        return text.encode("gbk", errors="replace").decode("gbk", errors="replace")
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def _run_installer(java: str, installer: Path, work_dir: Path, log, target_dir: bool = False) -> None:
    launcher_profiles = work_dir / "launcher_profiles.json"
    launcher_profiles.write_text('{"profiles":{},"settings":{},"version":3}', encoding="utf-8")

    command = [java, *_proxy_java_arguments(), "-jar", str(installer), "--installClient"]
    if target_dir:
        # NeoForge 的 --installClient 带一个可选目录参数，不传会装到 %APPDATA%\.minecraft
        command.append(str(work_dir))

    proc = subprocess.Popen(
        command,
        cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    if proc.stdout is not None:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log(_safe_console_text(f"  {line}"))
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"安装器运行失败，退出码 {code}")


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        return
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)


def _installer_sha1(url: str) -> str:
    """从 maven 取安装器的 sha1，下载时校验，避免用到上次下了一半的文件。"""
    try:
        return http_get(url + ".sha1").text.strip().split()[0]
    except (requests.RequestException, ValueError, IndexError):
        return ""


def install(mc_version: str, flavor: str = "forge", loader_version: str | None = None, log=print) -> str:
    """下载并运行官方安装器，把生成的版本和运行库合并到启动器目录。"""
    if not loader_version:
        raise ValueError(f"整合包没有指定 {flavor} 版本")

    version_id = version_id_for(mc_version, flavor, loader_version)
    work_dir = Path(ROOT_DIR, ".installers", version_id)
    work_dir.mkdir(parents=True, exist_ok=True)

    installer = Path(work_dir, "installer.jar")
    url = INSTALLER_URLS[flavor].format(mc=mc_version, ver=loader_version)
    log(f"下载 {flavor} 安装器（{loader_version}）...")
    if download_file(url, installer, _installer_sha1(url)) == "failed":
        raise RuntimeError(f"{flavor} 安装器下载失败：{url}")

    required_java = get_version_meta(mc_version)["javaVersion"]["majorVersion"]
    java = find_java(required_java)
    log(f"运行 {flavor} 安装器（Java {required_java}+）...")
    # NeoForge 的 --installClient 需要显式指定目录，否则会装到 %APPDATA%\.minecraft
    _run_installer(java, installer, work_dir, log, target_dir=(flavor == "neoforge"))

    _copy_tree(Path(work_dir, "libraries"), LIBRARIES_DIR)
    installed = Path(work_dir, "versions", version_id)
    if not installed.is_dir():
        candidates = [path for path in Path(work_dir, "versions").glob("*") if path.is_dir()]
        if not candidates:
            raise RuntimeError("安装器没有生成版本文件，安装失败")
        installed = max(candidates, key=lambda path: path.stat().st_mtime)

    actual_id = installed.name
    version_json = Path(installed, f"{installed.name}.json")
    try:
        actual_id = json.loads(version_json.read_text(encoding="utf-8")).get("id") or actual_id
    except (OSError, json.JSONDecodeError):
        pass

    _copy_tree(installed, Path(VERSIONS_DIR, actual_id))
    shutil.rmtree(work_dir, ignore_errors=True)
    return actual_id

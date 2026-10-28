from platform import system, machine


def current_platform() -> tuple[str, str]:
    cur_system = system()
    cur_arch = machine()
    if cur_system == "Windows":
        cur_system = "windows"
    elif cur_system == "Darwin":
        cur_system = "osx"
    elif cur_system == "Linux":
        cur_system = "linux"

    if cur_arch == "AMD64" or cur_arch == "x86_64":
        cur_arch = "x86_64"
    elif cur_arch == "ARM64" or cur_arch == "aarch64":
        cur_arch = "arm64"
    elif cur_arch == "x86" or cur_arch == "i386" or cur_arch == "i686":
        cur_arch = "x86"

    return cur_system, cur_arch

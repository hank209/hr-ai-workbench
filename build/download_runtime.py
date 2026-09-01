"""构建绿色分发包的内嵌 Python 运行时（runtime/）。

用法：python build/download_runtime.py
- 下载 python-build-standalone 的 CPython 3.11 Windows 版
- 解压到 runtime/python
- 用该解释器安装 build/requirements.txt 到 runtime 内

执行后，双击「启动工作台.bat」即使用内嵌 Python，不依赖用户机器环境。
"""
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "runtime"
PY_DIR = RUNTIME / "python"
PY_EXE = PY_DIR / "python.exe"

API = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "hr-workbench-builder"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def find_asset():
    rel = fetch_json(API)
    for a in rel.get("assets", []):
        name = a["name"]
        if ("cpython-3.11" in name and "x86_64-pc-windows-msvc" in name
                and "install_only" in name and name.endswith(".tar.gz")):
            return a["browser_download_url"], name
    raise RuntimeError("未找到匹配的 CPython 3.11 Windows 资产")


def main():
    if PY_EXE.exists():
        print(f"[build] runtime 已存在：{PY_EXE}")
    else:
        url, name = find_asset()
        print(f"[build] 下载 {name} ...")
        tarball = RUNTIME / name
        RUNTIME.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, tarball)
        print("[build] 解压 ...")
        with tarfile.open(tarball) as tf:
            tf.extractall(RUNTIME)
        try:
            tarball.unlink(missing_ok=True)
        except OSError:
            pass  # 沙箱/回收站不可用时忽略，tarball 保留无害
        # install_only 包解压后是 python/ 目录
        if not PY_EXE.exists():
            # 可能是 python/ 嵌套或其他命名，扫描找到 python.exe
            hits = list(RUNTIME.rglob("python.exe"))
            if not hits:
                raise RuntimeError("解压后未找到 python.exe")
            real = hits[0].parent
            if real != PY_DIR:
                if PY_DIR.exists():
                    shutil.rmtree(PY_DIR)
                real.rename(PY_DIR)
        print(f"[build] Python 就绪：{PY_EXE}")

    # 安装依赖到 runtime 内
    print("[build] 安装依赖 ...")
    subprocess.check_call(
        [str(PY_EXE), "-m", "pip", "install", "--no-warn-script-location",
         "-r", str(ROOT / "build" / "requirements.txt")])
    print("[build] 完成。绿色包已就绪，双击 启动工作台.bat 即可。")


if __name__ == "__main__":
    sys.exit(main())

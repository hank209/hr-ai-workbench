"""一键启动：端口探测(5270起自动+1) → 启动 uvicorn → 健康检查 → 自动打开浏览器。"""
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def port_free(port):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main():
    cfg_path = ROOT / "配置.yaml"
    try:
        import yaml
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    except Exception:
        cfg = {}
    base = int(cfg.get("server", {}).get("port", 5270))
    host = cfg.get("server", {}).get("host", "127.0.0.1")
    auto_browser = bool(cfg.get("server", {}).get("auto_open_browser", True))
    access_password = str(cfg.get("server", {}).get("access_password", "") or "").strip()

    # 局域网/外网暴露必须设访问口令，否则拒绝启动（防止身份证/薪资等敏感数据裸奔）
    if host not in ("127.0.0.1", "localhost") and not access_password:
        print("[人事工作台] 已阻止启动：host 配置为 %s（非本机回环地址），" % host)
        print("              但未设置访问口令 access_password。")
        print("              请在 配置.yaml 的 server.access_password 填入口令后重试，")
        print("              或将 host 改回 127.0.0.1（仅本机访问）。")
        return 1

    port = base
    while not port_free(port) and port < base + 20:
        port += 1
    if port >= base + 20:
        print("[人事工作台] 端口被占用过多，请关闭部分程序后重试。")
        return 1

    py = ROOT / "runtime" / "python" / "python.exe"
    python = str(py) if py.exists() else sys.executable

    print(f"[人事工作台] 正在启动 ... http://{host}:{port}")
    proc = subprocess.Popen(
        [python, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)],
        cwd=ROOT)

    url = f"http://{host}:{port}/api/health"
    ok = False
    for _ in range(50):
        time.sleep(0.8)
        if proc.poll() is not None:
            print("[人事工作台] 启动失败，请查看上方日志。")
            return 1
        try:
            urllib.request.urlopen(url, timeout=1)
            ok = True
            break
        except Exception:
            continue
    if not ok:
        print("[人事工作台] 服务启动超时。")
        return 1

    if auto_browser:
        webbrowser.open(f"http://{host}:{port}/")
    print("[人事工作台] 已启动，关闭本窗口即退出。")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""应用装配：建表 + 路由 + 启动扫描 + 每日自动备份。"""
import hashlib
import shutil
import sqlite3
from datetime import date

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import config
from .database import Base, engine, init_dirs, drop_legacy_fts
from . import models  # noqa: F401  确保模型注册
from .routers import pages, api

init_dirs()
Base.metadata.create_all(bind=engine)
drop_legacy_fts()

app = FastAPI(title="人事工作台", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(config.web_dir / "static")), name="static")
app.include_router(pages.router)
app.include_router(api.router)


def _pw_token():
    return hashlib.sha256(config.access_password.encode("utf-8")).hexdigest()


@app.middleware("http")
async def auth_middleware(request, call_next):
    """单口令访问控制：配置了 access_password 时，未认证请求一律拦截。"""
    pw = config.access_password
    if not pw:
        return await call_next(request)
    path = request.url.path
    if path in ("/login", "/api/login") or path.startswith("/static"):
        return await call_next(request)
    if request.cookies.get("hr_auth") == _pw_token():
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


def do_backup_if_needed():
    """每日首次启动备份 hr.db，滚动保留最近 N 份（P0-5）。"""
    src = config.data_dir / "hr.db"
    if not src.exists():
        return
    backups = config.backups_dir
    backups.mkdir(parents=True, exist_ok=True)
    tag = date.today().strftime("%Y%m%d")
    dest = backups / f"hr.db.{tag}"
    if dest.exists():
        return
    # 先 checkpoint，确保 WAL 数据落盘后再拷贝，避免备份缺数据
    try:
        con = sqlite3.connect(str(src))
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.close()
    except Exception:
        pass
    try:
        shutil.copy2(src, dest)
    except Exception:
        return
    files = sorted(backups.glob("hr.db.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[config.backup_keep:]:
        try:
            f.unlink()
        except OSError:
            pass


@app.on_event("startup")
def on_startup():
    try:
        do_backup_if_needed()
    except Exception:
        pass
    from .seed_data import seed
    try:
        seed()
    except Exception:
        pass
    from .services.reminders import sync_all_todos
    try:
        sync_all_todos()
    except Exception:
        pass
    try:
        from .abilities.scheduler import start_scheduler
        start_scheduler()
    except Exception:
        pass

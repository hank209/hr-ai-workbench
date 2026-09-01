"""全局配置加载。路径一律基于 ROOT（工作台根目录），保证绿色可搬动。"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


class Config:
    def __init__(self):
        p = ROOT / "配置.yaml"
        data = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}

        srv = data.get("server", {})
        self.host = srv.get("host", "127.0.0.1")
        self.port = int(srv.get("port", 5270))
        self.auto_open_browser = bool(srv.get("auto_open_browser", True))
        self.access_password = str(srv.get("access_password", "") or "").strip()

        db = data.get("database", {})
        db_rel = db.get("path", "data/hr.db")
        self.db_url = f"sqlite:///{(ROOT / db_rel).as_posix()}"
        self.backup_on_start = bool(db.get("backup_on_start", True))
        self.backup_keep = int(db.get("backup_keep", 7))

        self.reminder = data.get("reminder", {})
        self.knowledge = data.get("knowledge", {})

        self.data_dir = ROOT / "data"
        self.logs_dir = self.data_dir / "logs"
        self.backups_dir = self.data_dir / "backups"
        self.uploads_dir = self.data_dir / "uploads"
        self.exports_dir = self.data_dir / "exports"
        self.web_dir = ROOT / "web"


config = Config()

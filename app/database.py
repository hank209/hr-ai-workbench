"""数据库层：SQLite + WAL。主键统一用 PKBigInt（SQLite 下渲染为 INTEGER 保证自增）。"""
from sqlalchemy import create_engine, BigInteger, Integer, event
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import config

Base = declarative_base()

# 关键坑：BigInteger 主键在 SQLite 下不自增（非 rowid 别名），必须 with_variant 渲染为 INTEGER
PKBigInt = BigInteger().with_variant(Integer, "sqlite")

engine = create_engine(config.db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_fts():
    """已废弃：FTS5 检索已改用 LIKE 子串匹配（单机切片量小，性能足够）。保留空实现以兼容旧引用。"""


def init_dirs():
    for d in (config.data_dir, config.logs_dir, config.backups_dir,
              config.uploads_dir, config.exports_dir):
        d.mkdir(parents=True, exist_ok=True)


def drop_legacy_fts():
    """清理历史遗留的 chunk_fts 虚拟表及影子表（P1-7 移除 FTS 后不再使用）。"""
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE IF EXISTS chunk_fts")
    except Exception:
        pass


def migrate():
    """已废弃：新库由 create_all 建全表，无历史迁移需求。保留空实现以兼容旧引用。"""

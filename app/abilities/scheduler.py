"""APScheduler：每日 + 每 6 小时扫描提醒规则。"""
from apscheduler.schedulers.background import BackgroundScheduler

from ..services.reminders import sync_all_todos


def start_scheduler():
    sched = BackgroundScheduler()
    sched.add_job(sync_all_todos, "cron", hour=9, minute=0, id="daily_scan")
    sched.add_job(sync_all_todos, "interval", hours=6, id="interval_scan")
    sched.start()
    return sched

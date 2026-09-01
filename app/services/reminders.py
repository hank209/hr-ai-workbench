"""到期提醒规则引擎：扫描合同/面试，幂等生成待办。"""
from datetime import date, datetime

from ..config import config
from ..database import SessionLocal
from ..models import Contract, Interview, TodoItem


def _today():
    return date.today()


def _add_todo(db, title, kind, ref_id, due, level, source, note=""):
    db.add(TodoItem(title=title, kind=kind, ref_id=ref_id,
                    due_date=due, level=level, status="open",
                    source=source, note=note))


def _clear_open(db, kind, ref_id):
    db.query(TodoItem).filter(TodoItem.kind == kind,
                              TodoItem.ref_id == ref_id,
                              TodoItem.status == "open").delete()


def sync_contract_todos():
    """扫描全部合同，重新生成待办（幂等：先清旧待办再生成）。"""
    db = SessionLocal()
    try:
        today = _today()
        cfg = config.reminder
        expire_days = sorted(cfg.get("contract_expire", [60, 30, 7]), reverse=True)
        second_expire = int(cfg.get("contract_2nd_expire", 90))
        probation_days = sorted(cfg.get("probation_expire", [15, 7]), reverse=True)

        contracts = db.query(Contract).filter(
            Contract.status.in_(["履行中", "待签"])).all()
        for c in contracts:
            _clear_open(db, "contract", c.id)

            # —— 合同到期 ——
            if not c.is_indefinite and c.end_date:
                days = (c.end_date - today).days
                due = c.end_date
                if days < 0:
                    _add_todo(db, f"合同已到期：{c.personnel}《{c.name}》（{c.end_date}）",
                              "contract", c.id, due, "urgent", "合同到期扫描",
                              "请立即处理续签/终止手续，避免事实劳动关系风险。")
                else:
                    for d in expire_days:
                        if days <= d:
                            level = "urgent" if d <= 7 else ("high" if d <= 30 else "medium")
                            _add_todo(db, f"合同将于{days}天后到期：{c.personnel}《{c.name}》（{c.end_date}）",
                                      "contract", c.id, due, level, "合同到期扫描",
                                      f"到期前{d}天提醒（规则配置）。")
                            break
                # 第2次及以上合同特别预警（下次应为无固定期限）
                if c.contract_no and c.contract_no >= 2 and days <= second_expire:
                    _add_todo(db,
                              f"第{c.contract_no}次合同即将到期：{c.personnel}（{c.end_date}）——按劳动合同法第14条，本次续订时除劳动者本人提出订立固定期限外，应当订立无固定期限劳动合同",
                              "contract", c.id, due, "high", "第2次合同预警",
                              "另有第39条、第40条第1/2项情形的除外。本提示不构成法律意见。")

            # —— 试用期到期 ——
            if c.probation_end:
                pdays = (c.probation_end - today).days
                for d in probation_days:
                    if pdays <= d:
                        if pdays < 0:
                            _add_todo(db, f"试用期已结束：{c.personnel}（{c.probation_end}），转正评估待补",
                                      "contract", c.id, c.probation_end, "high", "试用期扫描")
                        else:
                            _add_todo(db, f"试用期将于{pdays}天后到期：{c.personnel}（{c.probation_end}），请发起转正评估",
                                      "contract", c.id, c.probation_end, "high", "试用期扫描")
                        break

        db.commit()
    finally:
        db.close()


def sync_interview_todos():
    """扫描待确认/已预约的面试，生成提醒（逾期/当天/次日），幂等。"""
    db = SessionLocal()
    try:
        now = datetime.now()
        today = now.date()
        ivs = db.query(Interview).filter(
            Interview.status.in_(["待确认", "已预约"])).all()
        for iv in ivs:
            _clear_open(db, "interview", iv.id)
            if not iv.start_time:
                continue
            sd = iv.start_time.date()
            days = (sd - today).days
            if days < 0:
                level, title = "urgent", f"面试已逾期：{iv.candidate_name}（{iv.position or '未标岗位'}）原定 {iv.start_time:%m-%d %H:%M}"
                due = sd
            elif days == 0:
                level, title = "high", f"今日面试：{iv.candidate_name}（{iv.position or ''}）{iv.start_time:%m-%d %H:%M}"
                due = sd
            elif days == 1:
                level, title = "medium", f"明日面试：{iv.candidate_name}（{iv.position or ''}）{iv.start_time:%m-%d %H:%M}"
                due = sd
            else:
                continue
            _add_todo(db, title, "interview", iv.id, due, level, "面试提醒",
                      f"面试官：{iv.interviewers or '未填写'}；方式：{iv.mode}")
        db.commit()
    finally:
        db.close()


def sync_all_todos():
    """合同 + 面试 全量重扫（供各处统一调用）。"""
    sync_contract_todos()
    sync_interview_todos()

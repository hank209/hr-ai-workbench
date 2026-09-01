"""页面路由（服务端渲染，Jinja2 + HTMX）。"""
import json
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import case

from ..config import config
from ..database import SessionLocal
from ..models import (Contract, QuickReply, KnowledgeDoc, Interview, TodoItem,
                      Requisition, Candidate, CandidateSection, Employee,
                      EmployeeEvent, AttendanceException, SalaryRecord,
                      DocTemplate, ChecklistItem)

router = APIRouter()
templates = Jinja2Templates(directory=str(config.web_dir / "templates"))

LEVEL_ORDER = case(
    (TodoItem.level == "urgent", 0),
    (TodoItem.level == "high", 1),
    (TodoItem.level == "medium", 2),
    else_=3,
)


@router.get("/login")
def login_page(request: Request, err: str = ""):
    return templates.TemplateResponse(request, "login.html", _ctx(request, err=err))


HELP_FILENAMES = ("使用说明-专员版.html", "使用说明.html")


def _help_file():
    """定位程序根目录的使用说明文件（按顺序找，找不到返回 None）。"""
    root = config.web_dir.parent
    for name in HELP_FILENAMES:
        p = root / name
        if p.exists():
            return p
    return None


@router.get("/help")
def help_page(request: Request):
    """右上角「查看使用帮助」入口：直接返回根目录的使用说明。

    说明文件内的截图已 base64 内联，不依赖 /static 或 docs/ 目录，
    单独拷走或双击打开也不会丢图。
    """
    p = _help_file()
    if not p:
        return HTMLResponse(
            "<meta charset='utf-8'>"
            "<body style='font-family:\"Microsoft YaHei\",sans-serif;padding:48px;"
            "color:#1f2328;line-height:1.8'>"
            "<h2>未找到使用说明文件</h2>"
            "<p>请把 <code>使用说明-专员版.html</code> 放到程序根目录下，再刷新本页。</p>"
            "<p><a href='/'>返回工作台</a></p></body>",
            status_code=404)
    return FileResponse(str(p), media_type="text/html; charset=utf-8")


def _ctx(request: Request, **kw):
    # 新签名：TemplateResponse(request, name, context) —— context 不含 request
    base = {"now": datetime.now()}
    base.update(kw)
    return base


@router.get("/")
def dashboard(request: Request):
    db = SessionLocal()
    try:
        today = date.today()
        todos = (db.query(TodoItem)
                 .filter(TodoItem.status == "open")
                 .order_by(LEVEL_ORDER, TodoItem.due_date.is_(None), TodoItem.due_date)
                 .limit(50).all())
        urgent = sum(1 for t in todos if t.level == "urgent")
        expiring = (db.query(Contract)
                    .filter(Contract.status.in_(["履行中", "待签"]),
                            Contract.is_indefinite.is_(False),
                            Contract.end_date.isnot(None),
                            Contract.end_date <= today + timedelta(days=30))
                    .count())
        today_iv = (db.query(Interview)
                    .filter(Interview.status.in_(["待确认", "已预约"]),
                            Interview.start_time >= datetime.combine(today, datetime.min.time()),
                            Interview.start_time < datetime.combine(today + timedelta(days=1), datetime.min.time()))
                    .count())
        doc_count = db.query(KnowledgeDoc).count()
        reply_count = db.query(QuickReply).filter(QuickReply.is_active.is_(True)).count()
        return templates.TemplateResponse(request, "dashboard.html", _ctx(
            request, todos=todos, urgent=urgent, expiring=expiring,
            today_iv=today_iv, doc_count=doc_count, reply_count=reply_count))
    finally:
        db.close()


@router.get("/contract")
def contract_page(request: Request):
    db = SessionLocal()
    try:
        today = date.today()
        contracts = (db.query(Contract)
                     .order_by(Contract.end_date.is_(None), Contract.end_date, Contract.id.desc())
                     .all())
        expiring_7 = [c for c in contracts
                      if c.status in ("履行中", "待签") and not c.is_indefinite
                      and c.end_date and (c.end_date - today).days <= 7]
        expiring_30 = [c for c in contracts
                       if c.status in ("履行中", "待签") and not c.is_indefinite
                       and c.end_date and 7 < (c.end_date - today).days <= 30]
        expiring_60 = [c for c in contracts
                       if c.status in ("履行中", "待签") and not c.is_indefinite
                       and c.end_date and 30 < (c.end_date - today).days <= 60]
        stats = {
            "total": len(contracts),
            "active": sum(1 for c in contracts if c.status in ("履行中", "待签")),
            "expire30": len(expiring_7) + len(expiring_30),
        }
        return templates.TemplateResponse(request, "contract.html", _ctx(
            request, contracts=contracts,
            expiring_7=expiring_7, expiring_30=expiring_30, expiring_60=expiring_60,
            stats=stats))
    finally:
        db.close()


@router.get("/contract/new")
def contract_new(request: Request):
    return templates.TemplateResponse(request, "contract_form.html", _ctx(request, c=None))


@router.get("/contract/{cid}/edit")
def contract_edit(request: Request, cid: int):
    db = SessionLocal()
    try:
        c = db.get(Contract, cid)
        if not c:
            return templates.TemplateResponse(request, "404.html", _ctx(request), status_code=404)
        return templates.TemplateResponse(request, "contract_form.html", _ctx(request, c=c))
    finally:
        db.close()


@router.get("/contract/import")
def contract_import_page(request: Request):
    return templates.TemplateResponse(request, "contract_import.html", _ctx(request))


@router.get("/replies")
def replies_page(request: Request, err: str = ""):
    db = SessionLocal()
    try:
        replies = (db.query(QuickReply)
                   .filter(QuickReply.is_active.is_(True))
                   .order_by(QuickReply.usage_count.desc(), QuickReply.id.desc())
                   .all())
        categories = ["考勤假期", "薪酬福利", "社保公积金", "入职离职", "报销差旅", "其他"]
        return templates.TemplateResponse(request, "replies.html", _ctx(
            request, replies=replies, categories=categories, err=err))
    finally:
        db.close()


@router.get("/replies/new")
def reply_new(request: Request):
    return templates.TemplateResponse(request, "reply_form.html", _ctx(request, r=None))


@router.get("/replies/{rid}/edit")
def reply_edit(request: Request, rid: int):
    db = SessionLocal()
    try:
        r = db.get(QuickReply, rid)
        if not r:
            return templates.TemplateResponse(request, "404.html", _ctx(request), status_code=404)
        return templates.TemplateResponse(request, "reply_form.html", _ctx(request, r=r))
    finally:
        db.close()


@router.get("/knowledge")
def knowledge_page(request: Request):
    db = SessionLocal()
    try:
        docs = db.query(KnowledgeDoc).order_by(KnowledgeDoc.id.desc()).limit(100).all()
        return templates.TemplateResponse(request, "knowledge.html", _ctx(request, docs=docs))
    finally:
        db.close()


@router.get("/interviews")
def interviews_page(request: Request):
    db = SessionLocal()
    try:
        interviews = (db.query(Interview)
                      .order_by(Interview.start_time.is_(None), Interview.start_time.desc())
                      .all())
        return templates.TemplateResponse(request, "interviews.html", _ctx(request, interviews=interviews))
    finally:
        db.close()


@router.get("/interviews/new")
def interview_new(request: Request):
    return templates.TemplateResponse(request, "interview_form.html", _ctx(request, iv=None))


@router.get("/interviews/{iid}/edit")
def interview_edit(request: Request, iid: int):
    db = SessionLocal()
    try:
        iv = db.get(Interview, iid)
        if not iv:
            return templates.TemplateResponse(request, "404.html", _ctx(request), status_code=404)
        return templates.TemplateResponse(request, "interview_form.html", _ctx(request, iv=iv))
    finally:
        db.close()


# ---------- 简历 ----------

DEFAULT_HARD = {"education": "不限", "min_years": 0, "city": "不限",
                "salary_max": 0, "skills": "", "skills_mode": "any"}
DEFAULT_SOFT = {"weights": {"years": 20, "school": 12, "management": 14,
                            "stability": 12, "skills": 20},
                "pass_threshold": 80, "maybe_threshold": 60}


@router.get("/resume")
def resume_page(request: Request, rid: int = 0, imported: int = 0,
                ok: int = 0, dup: int = 0, scan: int = 0, q: str = ""):
    db = SessionLocal()
    try:
        requisitions = db.query(Requisition).order_by(Requisition.id.desc()).all()
        cur = None
        if rid:
            cur = db.get(Requisition, rid)
        if not cur and requisitions:
            cur = requisitions[0]

        try:
            hard = json.loads(cur.hard_json) if cur and cur.hard_json else DEFAULT_HARD
        except Exception:
            hard = DEFAULT_HARD
        try:
            soft = json.loads(cur.soft_json) if cur and cur.soft_json else DEFAULT_SOFT
        except Exception:
            soft = DEFAULT_SOFT

        cq = db.query(Candidate)
        if cur:
            cq = cq.filter(Candidate.requisition_id == cur.id)
        if q:
            cq = cq.filter(Candidate.name.contains(q) | Candidate.phone.contains(q))
        cand_objs = cq.order_by(Candidate.bucket != "pass", Candidate.score.desc()).all()

        def _loads(s, default):
            try:
                return json.loads(s) if s else default
            except Exception:
                return default

        candidates = []
        for c in cand_objs:
            try:
                skills_list = json.loads(c.skills_json or "[]")
            except Exception:
                skills_list = []
            candidates.append({
                "id": c.id, "name": c.name or "未识别", "phone": c.phone,
                "email": c.email, "city": c.city, "education": c.education,
                "school": c.school, "work_years": c.work_years,
                "expect_salary": c.expect_salary, "source_channel": c.source_channel,
                "parse_level": c.parse_level, "bucket": c.bucket, "score": c.score,
                "skills": skills_list,
                "hard_detail": _loads(c.hard_detail_json, []),
                "score_detail": _loads(c.score_detail_json, []),
                "screened_at": c.screened_at,
            })

        counts = {"all": len(candidates),
                  "pass": sum(1 for c in candidates if c["bucket"] == "pass"),
                  "maybe": sum(1 for c in candidates if c["bucket"] == "maybe"),
                  "reject": sum(1 for c in candidates if c["bucket"] == "reject"),
                  "unscreened": sum(1 for c in candidates if not c["bucket"])}
        return templates.TemplateResponse(request, "resume.html", _ctx(
            request, requisitions=requisitions, cur=cur, hard=hard, soft=soft,
            candidates=candidates, counts=counts,
            imported=imported, ok=ok, dup=dup, scan=scan, q=q,
            candidates_len=len(candidates)))
    finally:
        db.close()


@router.get("/resume/import")
def resume_import_page(request: Request):
    db = SessionLocal()
    try:
        requisitions = db.query(Requisition).order_by(Requisition.id.desc()).all()
        return templates.TemplateResponse(request, "resume_import.html", _ctx(
            request, requisitions=requisitions))
    finally:
        db.close()


@router.get("/resume/{cid}")
def resume_detail(request: Request, cid: int):
    db = SessionLocal()
    try:
        c = db.get(Candidate, cid)
        if not c:
            return templates.TemplateResponse(request, "404.html", _ctx(request), status_code=404)
        try:
            conf = json.loads(c.confidence_json or "{}")
        except Exception:
            conf = {}
        try:
            hard_detail = json.loads(c.hard_detail_json or "[]")
        except Exception:
            hard_detail = []
        try:
            score_detail = json.loads(c.score_detail_json or "[]")
        except Exception:
            score_detail = []
        sections = (db.query(CandidateSection)
                    .filter(CandidateSection.candidate_id == cid)
                    .order_by(CandidateSection.order_no).all())
        return templates.TemplateResponse(request, "resume_detail.html", _ctx(
            request, c=c, conf=conf, hard_detail=hard_detail,
            score_detail=score_detail, sections=sections,
            field_items=[(k, getattr(c, k, "")) for k in
                         ("name", "phone", "email", "city", "education", "school",
                          "major", "work_years", "expect_salary",
                          "current_company", "current_title")]))
    finally:
        db.close()


# ---------- 员工档案 ----------

def _mask(v):
    """敏感字段 UI 掩码"""
    s = str(v or "")
    if len(s) <= 4:
        return s
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


@router.get("/employees")
def employees_page(request: Request, q: str = ""):
    db = SessionLocal()
    try:
        eq = db.query(Employee)
        if q:
            eq = eq.filter(Employee.name.contains(q) | Employee.emp_no.contains(q) | Employee.department.contains(q))
        employees = eq.order_by(Employee.department, Employee.name).all()
        stats = {
            "total": db.query(Employee).count(),
            "active": db.query(Employee).filter(Employee.status.in_(["在职", "试用"])).count(),
            "probation": db.query(Employee).filter(Employee.status == "试用").count(),
            "departments": len({e.department for e in employees if e.department}),
        }
        return templates.TemplateResponse(request, "employees.html", _ctx(
            request, employees=employees, stats=stats, q=q))
    finally:
        db.close()


@router.get("/employees/{eid}")
def employee_detail(request: Request, eid: int):
    db = SessionLocal()
    try:
        e = db.get(Employee, eid)
        if not e:
            return templates.TemplateResponse(request, "404.html", _ctx(request), status_code=404)
        events = (db.query(EmployeeEvent).filter(EmployeeEvent.emp_id == eid)
                  .order_by(EmployeeEvent.event_date.desc(), EmployeeEvent.id.desc()).all())
        return templates.TemplateResponse(request, "employee_detail.html", _ctx(
            request, e=e, events=events, mask=_mask))
    finally:
        db.close()


# ---------- 考勤 ----------

@router.get("/attendance")
def attendance_page(request: Request, month: str = ""):
    db = SessionLocal()
    try:
        months = [r[0] for r in db.query(AttendanceException.month).distinct().order_by(AttendanceException.month.desc()).all()]
        aq = db.query(AttendanceException)
        if month:
            aq = aq.filter(AttendanceException.month == month)
        items = aq.order_by(AttendanceException.exception_date.desc(), AttendanceException.id.desc()).all()
        summary = {}
        for a in items:
            summary[a.exception_type] = summary.get(a.exception_type, 0) + 1
        by_status = {"待确认": 0, "已确认": 0, "已处理": 0}
        for a in items:
            if a.status in by_status:
                by_status[a.status] += 1
        return templates.TemplateResponse(request, "attendance.html", _ctx(
            request, items=items, months=months, month=month,
            summary=summary, by_status=by_status))
    finally:
        db.close()


# ---------- 假期计算器 ----------

@router.get("/leave")
def leave_page(request: Request):
    db = SessionLocal()
    try:
        employees = (db.query(Employee)
                     .filter(Employee.status.in_(["在职", "试用"]))
                     .order_by(Employee.name).all())
        return templates.TemplateResponse(request, "leave.html", _ctx(
            request, employees=employees))
    finally:
        db.close()


# ---------- 工资答疑 ----------

@router.get("/salary")
def salary_page(request: Request, month: str = "", emp: str = ""):
    db = SessionLocal()
    try:
        months = [r[0] for r in db.query(SalaryRecord.month).distinct().order_by(SalaryRecord.month.desc()).all()]
        names = [r[0] for r in db.query(SalaryRecord.emp_name).distinct().order_by(SalaryRecord.emp_name).all()]
        sq = db.query(SalaryRecord)
        if month:
            sq = sq.filter(SalaryRecord.month == month)
        if emp:
            sq = sq.filter(SalaryRecord.emp_name == emp)
        records = sq.order_by(SalaryRecord.month.desc(), SalaryRecord.emp_name).all()
        return templates.TemplateResponse(request, "salary.html", _ctx(
            request, records=records, months=months, names=names,
            month=month, emp=emp))
    finally:
        db.close()


# ---------- 入离职清单 ----------

@router.get("/checklist")
def checklist_page(request: Request, emp: str = ""):
    db = SessionLocal()
    try:
        cq = db.query(ChecklistItem)
        if emp:
            cq = cq.filter(ChecklistItem.emp_name == emp)
        items = cq.order_by(ChecklistItem.emp_name, ChecklistItem.check_type,
                            ChecklistItem.id).all()
        # 按 员工+类型 分组
        groups = {}
        for it in items:
            key = (it.emp_name, it.check_type)
            groups.setdefault(key, []).append(it)
        people = [r[0] for r in db.query(ChecklistItem.emp_name).distinct().order_by(ChecklistItem.emp_name).all()]
        return templates.TemplateResponse(request, "checklist.html", _ctx(
            request, groups=groups, people=people, emp=emp))
    finally:
        db.close()


# ---------- 文书生成 ----------

@router.get("/docgen")
def docgen_page(request: Request, tid: int = 0, emp_id: int = 0):
    db = SessionLocal()
    try:
        doc_tpls = db.query(DocTemplate).order_by(DocTemplate.category, DocTemplate.id).all()
        cur = None
        if tid:
            cur = db.get(DocTemplate, tid)
        if not cur and doc_tpls:
            cur = doc_tpls[0]
        employees = (db.query(Employee)
                     .filter(Employee.status.in_(["在职", "试用"]))
                     .order_by(Employee.name).all())
        emp = None
        if emp_id:
            emp_obj = db.get(Employee, emp_id)
            if emp_obj:
                emp = {"name": emp_obj.name, "department": emp_obj.department,
                       "position": emp_obj.position,
                       "hire_date": str(emp_obj.hire_date) if emp_obj.hire_date else "",
                       "probation_end": str(emp_obj.probation_end) if emp_obj.probation_end else "",
                       "gender": emp_obj.gender, "id_card": emp_obj.id_card,
                       "education": emp_obj.education}
        return templates.TemplateResponse(request, "docgen.html", _ctx(
            request, templates=doc_tpls, cur=cur, employees=employees, emp=emp,
            new_mode=False, edit_id=0, edit_tpl=None))
    finally:
        db.close()


@router.get("/docgen/new")
def docgen_new(request: Request):
    return templates.TemplateResponse(request, "docgen.html", _ctx(
        request, templates=[], cur=None, employees=[], emp=None,
        new_mode=True, edit_id=0, edit_tpl=None))


@router.get("/docgen/{tid}/edit")
def docgen_edit(request: Request, tid: int):
    db = SessionLocal()
    try:
        t = db.get(DocTemplate, tid)
        if not t:
            return templates.TemplateResponse(request, "404.html", _ctx(request), status_code=404)
        return templates.TemplateResponse(request, "docgen.html", _ctx(
            request, templates=[], cur=None, employees=[], emp=None,
            new_mode=True, edit_id=tid, edit_tpl=t))
    finally:
        db.close()

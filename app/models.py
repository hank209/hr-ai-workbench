"""一期数据模型。全部业务表在此定义（保持单文件，方便核对）。"""
from datetime import datetime

from sqlalchemy import (Column, String, Text, Date, DateTime, Boolean,
                        Integer, ForeignKey)

from .database import Base, PKBigInt


class Contract(Base):
    """合同台账（轻量版，一期不做合同正文管理）"""
    __tablename__ = "contract"

    id = Column(PKBigInt, primary_key=True)
    name = Column(String(64), nullable=False, index=True)      # 合同名称：劳动合同/保密协议/竞业限制协议...
    personnel = Column(String(64), nullable=False, index=True)  # 人员
    start_date = Column(Date)
    end_date = Column(Date)
    is_indefinite = Column(Boolean, default=False)              # 无固定期限
    contract_no = Column(Integer, default=1)                    # 第几次合同（1/2/3...）
    contract_type = Column(String(32), default="固定期限")       # 固定期限/无固定期限/以完成一定工作任务为期限
    status = Column(String(16), default="履行中", index=True)   # 待签/履行中/已续签/已终止
    probation_start = Column(Date)
    probation_end = Column(Date)
    note = Column(Text, default="")
    attachment = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class QuickReply(Base):
    """常用回复（一期 ROI 最高的功能，纯规则无 AI）"""
    __tablename__ = "quick_reply"

    id = Column(PKBigInt, primary_key=True)
    category = Column(String(32), default="其他", index=True)   # 考勤假期/薪酬福利/社保公积金/入职离职/报销差旅/其他
    title = Column(String(128), nullable=False)                  # 标题
    keywords = Column(String(255), default="")                   # 搜索关键词（逗号分隔）
    content = Column(Text, nullable=False)                       # 正文，支持 {{变量}}
    usage_count = Column(Integer, default=0)                     # 使用次数（排序）
    shortcut = Column(String(16), default="")                    # 快捷编号，如 /nj
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class KnowledgeDoc(Base):
    """知识库文档"""
    __tablename__ = "knowledge_doc"

    id = Column(PKBigInt, primary_key=True)
    title = Column(String(128), nullable=False, index=True)
    category = Column(String(32), default="制度", index=True)    # 制度/流程/模板/法规
    version = Column(String(32), default="")
    effective_date = Column(Date)
    source_file = Column(String(255), default="")                # 原文件名
    file_path = Column(String(255), default="")                  # 保存路径
    status = Column(String(16), default="已入库")                # 已入库/待修订/已停用
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)


class KnowledgeChunk(Base):
    """知识库切片（按"第X条"切分）"""
    __tablename__ = "knowledge_chunk"

    id = Column(PKBigInt, primary_key=True)
    doc_id = Column(Integer, ForeignKey("knowledge_doc.id"), index=True)
    seq = Column(Integer, default=0)                              # 序号
    section_title = Column(String(128), default="")               # 条款号，如"第三条"
    content = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)


class Interview(Base):
    """面试安排"""
    __tablename__ = "interview"

    id = Column(PKBigInt, primary_key=True)
    candidate_name = Column(String(64), nullable=False, index=True)
    position = Column(String(64), default="")
    round_name = Column(String(16), default="初试")               # 初试/复试/终面/HR面
    interviewers = Column(String(255), default="")                # 面试官，逗号分隔
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime)
    mode = Column(String(16), default="现场")                     # 现场/视频/电话
    location = Column(String(128), default="")                    # 地点/会议号
    status = Column(String(16), default="待确认", index=True)     # 待确认/已预约/已完成/已评价/已取消/爽约
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class TodoItem(Base):
    """待办中心：系统自动生成 + 手动添加"""
    __tablename__ = "todo_item"

    id = Column(PKBigInt, primary_key=True)
    title = Column(String(255), nullable=False)
    kind = Column(String(16), default="system", index=True)       # contract/interview/system
    ref_id = Column(Integer, default=0)                           # 关联记录 id
    due_date = Column(Date, index=True)
    level = Column(String(16), default="medium")                  # urgent/high/medium/low
    status = Column(String(8), default="open", index=True)        # open/done
    source = Column(String(64), default="")                       # 生成来源说明
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    resolved_at = Column(DateTime)


class Requisition(Base):
    """招聘岗位（含初筛条件）"""
    __tablename__ = "requisition"

    id = Column(PKBigInt, primary_key=True)
    title = Column(String(64), nullable=False, index=True)
    department = Column(String(64), default="")
    status = Column(String(16), default="招聘中")            # 招聘中/暂停/已关闭
    hard_json = Column(Text, default="")                     # 硬条件 JSON
    soft_json = Column(Text, default="")                     # 软条件/权重 JSON
    created_at = Column(DateTime, default=datetime.now)


class Candidate(Base):
    """候选人（解析后的结构化字段 + 最近一次初筛结果快照，可回溯）"""
    __tablename__ = "candidate"

    id = Column(PKBigInt, primary_key=True)
    requisition_id = Column(Integer, default=0, index=True)  # 0 = 未关联岗位
    name = Column(String(64), default="", index=True)
    phone = Column(String(32), default="")
    email = Column(String(64), default="")
    city = Column(String(32), default="")
    education = Column(String(16), default="")
    school = Column(String(64), default="")
    major = Column(String(64), default="")
    work_years = Column(Integer, default=0)
    expect_salary = Column(Integer, default=0)
    current_company = Column(String(128), default="")
    current_title = Column(String(64), default="")
    skills_json = Column(Text, default="[]")                 # 技能命中列表
    top_school = Column(Boolean, default=False)              # 985/211 院校
    has_management = Column(Boolean, default=False)          # 管理经验
    job_changes = Column(Integer, default=0)                 # 工作经历段数（稳定性）
    source_channel = Column(String(32), default="未标注", index=True)  # BOSS/51job/其他
    file_path = Column(String(255), default="")
    file_hash = Column(String(64), default="")
    raw_text = Column(Text, default="")
    parse_level = Column(String(16), default="ok")           # ok / scan(扫描件) / failed
    confidence_json = Column(Text, default="{}")
    bucket = Column(String(8), default="", index=True)       # pass / maybe / reject（最近一次初筛）
    score = Column(Integer, default=0)
    hard_detail_json = Column(Text, default="[]")
    score_detail_json = Column(Text, default="[]")
    screened_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)


class CandidateSection(Base):
    """候选人原文板块（详情页核对用）"""
    __tablename__ = "candidate_section"

    id = Column(PKBigInt, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate.id"), index=True)
    section_type = Column(String(16), default="其他")
    content = Column(Text, default="")
    order_no = Column(Integer, default=0)


class Employee(Base):
    """员工档案（一期轻量版：敏感字段明文存储但 UI 默认掩码，见使用说明风险提示）"""
    __tablename__ = "employee"

    id = Column(PKBigInt, primary_key=True)
    emp_no = Column(String(32), default="", index=True)       # 工号
    name = Column(String(64), nullable=False, index=True)
    gender = Column(String(8), default="未知")                # 男/女/未知（仅展示）
    birth_date = Column(Date)
    phone = Column(String(32), default="")
    email = Column(String(64), default="")
    department = Column(String(64), default="", index=True)
    position = Column(String(64), default="")
    hire_date = Column(Date, index=True)
    probation_end = Column(Date)                              # 试用期到期日（提醒转正）
    status = Column(String(16), default="在职", index=True)   # 在职/试用/已离职
    education = Column(String(16), default="")
    id_card = Column(String(32), default="")                  # 敏感：UI 掩码
    bank_card = Column(String(32), default="")                # 敏感：UI 掩码
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class EmployeeEvent(Base):
    """员工异动时间轴"""
    __tablename__ = "employee_event"

    id = Column(PKBigInt, primary_key=True)
    emp_id = Column(Integer, ForeignKey("employee.id"), index=True)
    event_type = Column(String(16), default="其他")           # 入职/转正/调岗/调薪/离职/其他
    event_date = Column(Date)
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)


class AttendanceException(Base):
    """考勤异常（Excel 导入 + 批量处理）"""
    __tablename__ = "attendance_exception"

    id = Column(PKBigInt, primary_key=True)
    emp_name = Column(String(64), nullable=False, index=True)
    month = Column(String(7), default="", index=True)         # 2026-08
    exception_date = Column(Date)
    exception_type = Column(String(16), default="其他")       # 漏打卡/迟到/早退/缺卡/其他
    reason = Column(String(255), default="")
    status = Column(String(16), default="待确认", index=True) # 待确认/已确认/已处理
    handler_note = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)


class SalaryRecord(Base):
    """工资明细（Excel 导入，答疑助手数据源）"""
    __tablename__ = "salary_record"

    id = Column(PKBigInt, primary_key=True)
    emp_name = Column(String(64), nullable=False, index=True)
    month = Column(String(7), default="", index=True)         # 2026-08
    base_salary = Column(Integer, default=0)
    performance = Column(Integer, default=0)
    subsidy = Column(Integer, default=0)
    overtime_pay = Column(Integer, default=0)
    social_insurance = Column(Integer, default=0)             # 个人社保（扣项）
    housing_fund = Column(Integer, default=0)                 # 个人公积金（扣项）
    tax = Column(Integer, default=0)                          # 个税（扣项）
    other_deduct = Column(Integer, default=0)                 # 其他扣款（请假/罚款）
    net_salary = Column(Integer, default=0)                   # 实发
    note = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)


class DocTemplate(Base):
    """文书模板（JD/通知/offer/证明），变量 {{xxx}} 填充"""
    __tablename__ = "doc_template"

    id = Column(PKBigInt, primary_key=True)
    name = Column(String(64), nullable=False)
    category = Column(String(16), default="通知", index=True)  # JD/通知/offer/证明/制度
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class ChecklistItem(Base):
    """入离职清单项（内置模板生成）"""
    __tablename__ = "checklist_item"

    id = Column(PKBigInt, primary_key=True)
    emp_name = Column(String(64), nullable=False, index=True)
    check_type = Column(String(8), default="入职", index=True) # 入职/离职
    item_name = Column(String(128), nullable=False)
    done = Column(Boolean, default=False)
    done_at = Column(DateTime)
    note = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)


class AuditLog(Base):
    """审计日志：所有写操作留痕"""
    __tablename__ = "audit_log"

    id = Column(PKBigInt, primary_key=True)
    ts = Column(DateTime, default=datetime.now, index=True)
    action = Column(String(64), default="")                       # add/update/delete/import/export
    target = Column(String(64), default="")                       # contract/reply/doc/interview/todo
    detail = Column(Text, default="")

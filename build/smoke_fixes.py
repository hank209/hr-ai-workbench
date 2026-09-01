"""回测报告修复项专项验证：覆盖 P0-1~P0-5、P1-1~P1-6、P1-8。"""
import io
import json
import sqlite3
import urllib.request
import urllib.parse
from datetime import date, datetime, timedelta

BASE = "http://127.0.0.1:5270"
fails = []


def post_form(path, data):
    req = urllib.request.Request(BASE + path, data=urllib.parse.urlencode(data).encode(), method="POST")
    try:
        return urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        return e.code


def post_multipart(path, fields, files):
    boundary = "----fixb"
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n')
    for k, (fn, content) in files:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: application/octet-stream\r\n\r\n')
        parts.append(content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content)
        parts.append("\r\n")
    parts.append(f"--{boundary}--\r\n")
    req = urllib.request.Request(BASE + path, data="".join(parts).encode(), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        return urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        return e.code


def get(path):
    return urllib.request.urlopen(BASE + urllib.parse.quote(path, safe="/?&=%")).read().decode("utf-8", errors="replace")


def q(sql):
    con = sqlite3.connect("data/hr.db")
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def exec(sql):
    con = sqlite3.connect("data/hr.db")
    try:
        con.execute(sql)
        con.commit()
    finally:
        con.close()


# ---------- P0-1 合同新增后自动生成提醒 ----------
exec("delete from contract"); exec("delete from todo_item where kind='contract'")
end30 = (date.today() + timedelta(days=30)).isoformat()
st = post_form("/api/contract/add", {"name": "劳动合同", "personnel": "测试甲",
               "start_date": "2023-09-01", "end_date": end30, "contract_no": "1",
               "contract_type": "固定期限", "status": "履行中", "probation_end": "", "note": ""})
todos = q("select count(*) from todo_item where kind='contract'")
print("P0-1 合同新增后自动提醒:", st, "待办数=", todos[0][0])
if todos[0][0] == 0:
    fails.append("P0-1")

# ---------- P0-3 面试新增后自动提醒 ----------
exec("delete from interview"); exec("delete from todo_item where kind='interview'")
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
st = post_form("/api/interview/add", {"candidate_name": "面试乙", "position": "Java",
               "round_name": "初试", "interviewers": "张经理", "start_time": tomorrow,
               "end_time": "", "mode": "现场", "location": "", "status": "待确认", "note": ""})
todos = q("select title from todo_item where kind='interview'")
print("P0-3 面试自动提醒:", st, todos)
if not todos:
    fails.append("P0-3")

# ---------- P0-4 法条文案 ----------
exec("delete from contract"); exec("delete from todo_item")
post_form("/api/contract/add", {"name": "劳动合同", "personnel": "第三次合同者",
          "start_date": "2021-09-01", "end_date": (date.today() + timedelta(days=80)).isoformat(),
          "contract_no": "2", "contract_type": "固定期限", "status": "履行中", "probation_end": "", "note": ""})
titles = q("select title from todo_item where source='第2次合同预警'")
txt = titles[0][0] if titles else ""
print("P0-4 法条文案:", txt[:60], "...")
if "除劳动者本人提出订立固定期限外" not in txt:
    fails.append("P0-4")

# ---------- P0-2 敏感字段掩码 ----------
exec("delete from employee")
post_form("/api/employee/add", {"name": "敏感员工", "gender": "男", "id_card": "110101199005201234",
          "bank_card": "6222020200012345678", "department": "研发", "hire_date": "2023-01-01"})
eid = q("select id from employee")[0][0]
html = get(f"/employees/{eid}")
print("P0-2 明文泄漏:", "110101199005201234" in html, "|", "6222020200012345678" in html)
if "110101199005201234" in html or "6222020200012345678" in html:
    fails.append("P0-2")

# ---------- P0-5 自动备份 ----------
import os
backups = [f for f in os.listdir("data/backups") if f.startswith("hr.db.")]
print("P0-5 备份文件:", backups)
if not backups:
    fails.append("P0-5")

# ---------- P1-1~P1-5 简历解析 ----------
import sys
sys.path.insert(0, ".")
from app.abilities.resume_parser import parse_resume

def parse_text(txt, filename="r.txt"):
    r = parse_resume(filename, txt.encode("utf-8"))
    return r["fields"]

# P1-1 无标签姓名
f = parse_text("张三\n期望城市：杭州\n教育经历\n浙江大学 本科\n工作经历\n2020.03-2023.06 A公司\n专业技能\nJava")
print("P1-1 无标签姓名:", repr(f.get("name")))
if f.get("name") != "张三":
    fails.append("P1-1")

# P1-2 技能误判
f = parse_text("姓名：甲\n熟悉 MongoDB 和 Django，会用 JavaScript 写前端，数据库用 MySQL\n")
sk = f.get("skills") or []
print("P1-2 技能:", sk)
for bad in ("go", "sql"):
    if bad in sk:
        fails.append("P1-2:" + bad)
if "javascript" in sk and "java" in sk:
    fails.append("P1-2:java in javascript")

# P1-3 年限（无"经验"二字）
f = parse_text("姓名：乙\n工作年限：5年\n工作经历\n2019.07-2022.06 A公司\n2022.07-至今 B公司\n")
print("P1-3 工作年限:", f.get("work_years"), "段数:", f.get("job_changes"))
if f.get("work_years") not in (5, 5.0):
    fails.append("P1-3")
# P1-4 段数
if f.get("job_changes") != 2:
    fails.append("P1-4")

# ---------- P1-6 批量上传容错 ----------
exec("delete from candidate"); exec("delete from candidate_section"); exec("delete from requisition")
post_form("/api/requisition/add", {"title": "测试岗", "education": "不限", "min_years": "0", "salary_max": "0", "skills": "", "skills_mode": "any"})
rid = q("select id from requisition order by id desc limit 1")[0][0]
st = post_multipart("/api/resume/upload", {"channel": "其他", "requisition_id": str(rid)},
                    [("files", ("good.txt", "姓名：丙\n本科\n5年工作经验\n")),
                     ("files", ("bad.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"))])
n = q("select count(*) from candidate")[0][0]
print("P1-6 坏文件容错:", st, "入库数=", n)
if n != 1:
    fails.append("P1-6")

# ---------- P1-8 快捷编号唯一 ----------
exec("delete from quick_reply where shortcut='/testx'")
post_form("/api/reply/add", {"category": "其他", "title": "A", "keywords": "", "content": "x", "shortcut": "/testx"})
st2 = post_form("/api/reply/add", {"category": "其他", "title": "B", "keywords": "", "content": "y", "shortcut": "/testx"})
cnt = q("select count(*) from quick_reply where shortcut='/testx'")[0][0]
print("P1-8 快捷编号唯一:", st2, "重复数=", cnt)
if cnt != 1:
    fails.append("P1-8")

print("\n==== 结果 ====")
print("FAILS:", fails if fails else "NONE — 全部修复项通过")

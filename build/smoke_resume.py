"""简历模块端到端冒烟测试：建岗位 → 上传 4 份样本 → 筛选 → 校验三档归类与详情修正。"""
import sqlite3
import urllib.request
import urllib.parse

BASE = "http://127.0.0.1:5270"
fails = []


def post_multipart(path, fields, files):
    """files: list of (field_name, (filename, content))，支持同名多文件"""
    boundary = "----smokeb"
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


def post_form(path, data):
    req = urllib.request.Request(BASE + path, data=urllib.parse.urlencode(data).encode(), method="POST")
    try:
        return urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        return e.code


def get(path):
    return urllib.request.urlopen(BASE + path).read().decode("utf-8", errors="replace")


# 1. 先建岗位
st = post_form("/api/requisition/add", {
    "title": "Java高级开发工程师", "department": "研发中心",
    "education": "本科", "min_years": "5", "city": "不限",
    "salary_max": "25000", "skills": "Java, Spring Cloud", "skills_mode": "any"})
print("1 新建岗位:", st)
con = sqlite3.connect("data/hr.db")
rid = con.execute("select id from requisition order by id desc limit 1").fetchone()[0]
con.close()
print("   岗位 id:", rid)

# 2. 上传 4 份样本简历（归入岗位）
resumes = {
    "1_zhangsan.txt": (
        "姓名：张三\n期望城市：杭州   期望薪资：22k\n"
        "教育经历\n浙江大学 本科 计算机科学与技术 2014-2018\n"
        "工作经历\n2020.03-2023.06 杭州某科技公司 高级Java开发工程师\n负责 Spring Cloud 微服务架构，管理 5 人团队\n"
        "专业技能\nJava, Spring Cloud, MySQL, Redis, Docker\n"
        "自我评价\n6年工作经验，熟悉微服务架构"),
    "2_lisi.txt": (
        "姓名：李四\n期望城市：上海   期望薪资：24k\n"
        "教育经历\n武汉大学 硕士 软件工程 2016-2019\n"
        "工作经历\n2019.07-2022.06 某公司 Java工程师\n2022.07-至今 某公司 高级Java工程师 管理 3 人团队\n"
        "专业技能\nJava, Spring Cloud, MySQL\n"
        "自我评价\n5年以上工作经验"),
    "3_wangwu.txt": (
        "姓名：王五\n期望城市：北京   期望薪资：15k\n"
        "教育经历\n北京某职业技术学院 大专 2019-2022\n"
        "工作经历\n2022.08-2024.08 某小公司 开发工程师\n"
        "专业技能\nJavaScript\n"
        "自我评价\n2年工作经验"),
    "4_zhaoqi.txt": (
        "姓名：赵七\n期望城市：上海   期望薪资：25k\n"
        "教育经历\n西安电子科技大学 本科 2015-2019\n"
        "工作经历\n2019.07-2022.06 A公司 Java工程师\n2022.07-至今 B公司 高级工程师 管理 2 人团队\n"
        "专业技能\nJava, Redis\n"
        "自我评价\n5年工作经验"),
}
try:
    import fitz
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    resumes["5_scan.pdf"] = pdf_bytes
except Exception:
    pass

st = post_multipart("/api/resume/upload",
                    {"channel": "BOSS直聘", "requisition_id": str(rid)},
                    [("files", (fn, content)) for fn, content in resumes.items()])
print("2 批量上传(5份):", st)

# 3. 校验字段抽取
con = sqlite3.connect("data/hr.db")
cands = con.execute("select id,name,education,school,work_years,expect_salary,city,parse_level from candidate order by id").fetchall()
con.close()
print("3 入库候选人:")
for c in cands:
    print("   ", c)
assert len(cands) == 5, "应有 5 条候选人"
zhang = [c for c in cands if c[1] == "张三"][0]
assert zhang[2] == "本科" and zhang[4] == 6 and zhang[5] == 22000 and zhang[6] == "杭州", "张三字段抽取失败"
assert [c for c in cands if c[1] == "李四"][0][2] == "硕士", "李四学历抽取失败"
assert [c for c in cands if c[1] == "王五"][0][2] == "大专", "王五学历抽取失败"
assert [c for c in cands if c[1] == "赵七"][0][4] == 5, "赵七年限抽取失败"
assert any(c[7] == "scan" for c in cands), "扫描件应被识别"
print("4 字段抽取校验: 通过")

# 5. 运行初筛
st = post_form("/api/resume/screen", {
    "requisition_id": str(rid), "education": "本科", "min_years": "5",
    "city": "不限", "salary_max": "25000", "skills": "Java, Spring Cloud",
    "skills_mode": "any", "w_years": "20", "w_school": "12",
    "w_management": "14", "w_stability": "12", "w_skills": "20",
    "pass_threshold": "80", "maybe_threshold": "60"})
print("5 运行初筛:", st)

con = sqlite3.connect("data/hr.db")
buckets = con.execute("select name,bucket,score from candidate where requisition_id=? and parse_level='ok'", (rid,)).fetchall()
con.close()
print("6 初筛结果:")
for b in buckets:
    print("   ", b)
bm = {n: (bk, sc) for n, bk, sc in buckets}
assert bm.get("张三") and bm["张三"][0] == "pass", f"张三应通过, 实际{bm.get('张三')}"
assert bm.get("李四") and bm["李四"][0] == "pass", f"李四应通过, 实际{bm.get('李四')}"
assert bm.get("赵七") and bm["赵七"][0] == "maybe", f"赵七应待定, 实际{bm.get('赵七')}"
assert bm.get("王五") and bm["王五"][0] == "reject", f"王五应不通过, 实际{bm.get('王五')}"
print("7 三档归类校验: 通过")

# 8. 列表页渲染
page = get(f"/resume?rid={rid}")
for kw in ["张三", "李四", "王五", "赵七", "扫描件·待人工识别", "通过", "待定"]:
    assert kw in page, f"列表页缺 {kw}"
print("8 列表页渲染: 通过")

# 9. 详情页 + 人工修正
page = get(f"/resume/{zhang[0]}")
assert "张三" in page and "初筛理由" in page, "详情页渲染失败"
st = post_form(f"/api/resume/{zhang[0]}/patch", {"name": "张三", "phone": "13800000001",
              "email": "z@t.com", "city": "杭州", "education": "本科", "school": "浙江大学",
              "work_years": "6", "expect_salary": "22000", "current_company": "", "current_title": ""})
page = get(f"/resume/{zhang[0]}")
assert "z@t.com" in page, "修正未生效"
print("9 详情页修正: 通过")

print("FAILS:", fails if fails else "NONE — 简历模块全部通过")

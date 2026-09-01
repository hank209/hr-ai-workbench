"""端到端冒烟测试（开发用）。python build/smoke_test.py"""
import json
import urllib.request
import urllib.parse
import datetime

BASE = "http://127.0.0.1:5270"
fails = []


def post_form(path, data, expect_redirect="/"):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(BASE + path, data=body, method="POST")
    try:
        resp = urllib.request.urlopen(req)
        return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def post_multipart(path, fields, files):
    boundary = "----smokeboundary"
    parts = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n")
    for k, (fn, content, ctype) in files.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fn}\"\r\nContent-Type: {ctype}\r\n\r\n")
        parts.append(content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content)
        parts.append("\r\n")
    parts.append(f"--{boundary}--\r\n")
    body = "".join(parts).encode()
    req = urllib.request.Request(BASE + path, data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        resp = urllib.request.urlopen(req)
        return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def get(path):
    return urllib.request.urlopen(BASE + path).read().decode("utf-8", errors="replace")


# 1. 新增合同（30 天后到期 → 应生成待办）
st = post_form("/api/contract/add", {
    "name": "劳动合同", "personnel": "赵六", "start_date": "2023-09-01",
    "end_date": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
    "contract_no": "2", "contract_type": "固定期限", "status": "履行中",
    "probation_start": "", "probation_end": "", "note": "冒烟测试"})
print("1 新增合同:", st)

# 2. 模板下载
req = urllib.request.Request(BASE + "/api/contract/template")
resp = urllib.request.urlopen(req)
print("2 Excel模板下载:", resp.status, resp.headers.get("Content-Disposition", "")[:40])

# 3. 知识库上传（txt，含条款）
demo = ("考勤管理制度\n"
        "第一条 员工每天工作时间为上午9:00至下午18:00，午休1小时。\n"
        "第二条 员工累计工作已满1年不满10年的，年休假5天；满10年不满20年的，年休假10天。\n"
        "第三条 员工请病假需提供医院诊断证明，连续病假超过3天需额外提供休假建议书。\n"
        "第四条 法定节假日加班按工资的300%支付加班费。\n")
st = post_multipart("/api/knowledge/upload",
                    {"title": "考勤管理制度(测试)", "category": "制度", "version": "v1.0", "effective_date": "2026-01-01"},
                    {"file": ("kaoqin.txt", demo, "text/plain")})
print("3 知识库上传:", st)

# 4. 知识库检索（中文子串匹配）
data = urllib.parse.urlencode({"q": "休假", "limit": "5"}).encode()
resp = urllib.request.urlopen(urllib.request.Request(BASE + "/api/knowledge/search", data=data, method="POST"))
items = json.loads(resp.read().decode())["items"]
print("4 检索'休假':", len(items), "条 ->", items[0]["section"] if items else "FAIL")
if not items:
    fails.append("知识检索")

# 5. 常用回复复制计数
st = post_form("/api/reply/1/copy", {})
print("5 回复复制计数:", st)

# 6. 面试新增 + 状态变更
st = post_form("/api/interview/add", {
    "candidate_name": "王五", "position": "Java工程师", "round_name": "初试",
    "interviewers": "张经理", "start_time": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M"),
    "end_time": "", "mode": "现场", "location": "3楼A", "status": "待确认", "note": ""})
print("6 新增面试:", st)

# 7. 待办生成检查（应包含合同到期）
page = get("/")
for kw in ["赵六", "第2次合同", "30"]:
    if kw in page:
        print(f"7 待办含[{kw}]: YES")
        break
else:
    print("7 待办含合同到期: NO")
    fails.append("待办生成")

# 8. 首页统计卡
page = get("/")
import re
m = re.search(r"合同 30 天内到期</div><div class=\"num[^\"]*\">(\d+)</div>", page)
print("8 首页统计-合同30天内到期:", m.group(1) if m else "?")
page = get("/contract")
print("9 合同页含赵六:", "赵六" in page)

print("FAILS:", fails if fails else "NONE — 全部通过")

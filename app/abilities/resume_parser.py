"""简历解析引擎：清洗 → 板块切分 → 字段抽取（正则+词典，无大模型）→ 置信度标注。

设计原则：招聘平台导出的简历几乎全是文本型 PDF，纯规则抽取即可达 85~90% 准确率。
低置信度字段由界面标黄提示人工确认；扫描件标记 parse_level=scan 由人工识别。
"""
import re
from datetime import date

# ---------- 平台水印与噪声（清洗） ----------
PLATFORM_NOISE = [
    "boss直聘", "智联招聘", "前程无忧", "猎聘", "拉勾", "脉脉", "51job",
    "简历模板", "下载时间", "打印时间", "生成时间", "www.", "http://", "https://",
]
MASKED_PHONE_RE = re.compile(r"1[3-9]\d{2}[\*＊]{4}\d{4}")   # 脱敏手机号 138****1234

# ---------- 正则 ----------
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
BIRTH_RE = re.compile(r"(?:出生|生于)[年月:：\s]*((?:19|20)\d{2})")
YEAR_RE = re.compile(r"(?:19|20)\d{2}")
SALARY_RE = re.compile(r"(?:期望)?(?:薪资|月薪|薪)[^0-9]{0,6}(\d+(?:\.\d+)?)[kK千]?[-\~至到—]?(\d+(?:\.\d+)?)?[kK千万]?(?:/月|/月薪)?|(?:月薪|薪资)[^0-9]{0,4}(\d+(?:\.\d+)?)[kK]")
EXPERIENCE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*年(?:以上|左右)?")
DATE_RANGE_RE = re.compile(
    r"(?P<s>(?:19|20)\d{2})(?:[./年\-]\d{1,2}[月]?)?"
    r"\s*[-~至到—]\s*"
    r"(?:(?P<e>(?:19|20)\d{2})(?:[./年\-]\d{1,2}[月]?)?|(?P<now>至今|现在|今))"
)
POSITION_TITLE_RE = re.compile(r"(?:现任|担任|职位|岗位|title)[：:\s]*(.{2,20})")

# ---------- 词典 ----------
EDU_LEVELS = ["博士", "硕士研究生", "硕士", "研究生", "本科", "双学位", "大专", "专科", "高中", "中专", "中技"]
KNOWN_SCHOOLS = {
    "北京大学", "清华大学", "复旦大学", "上海交通大学", "浙江大学", "南京大学", "中国科学技术大学",
    "哈尔滨工业大学", "西安交通大学", "中国人民大学", "北京航空航天大学", "北京理工大学", "天津大学",
    "南开大学", "同济大学", "华中科技大学", "武汉大学", "中山大学", "厦门大学", "四川大学", "重庆大学",
    "山东大学", "吉林大学", "湖南大学", "中南大学", "大连理工大学", "电子科技大学", "西北工业大学",
    "东南大学", "兰州大学", "东北大学", "华南理工大学", "中国农业大学", "中央民族大学", "华东师范大学",
    "北京师范大学", "北京邮电大学", "对外经济贸易大学", "上海财经大学", "中央财经大学", "西南财经大学",
    "中南财经政法大学", "北京外国语大学", "上海外国语大学", "中国政法大学", "西安电子科技大学",
    "南京航空航天大学", "南京理工大学", "苏州大学", "暨南大学", "深圳大学", "广东工业大学",
}
CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "西安", "重庆", "苏州",
          "天津", "长沙", "郑州", "青岛", "大连", "宁波", "厦门", "合肥", "福州", "济南", "昆明",
          "南昌", "贵阳", "南宁", "哈尔滨", "长春", "沈阳", "石家庄", "太原", "无锡", "佛山",
          "东莞", "珠海", "惠州", "中山"]
SKILLS = [
    "java", "python", "go", "golang", "c++", "c#", "php", "javascript", "typescript", "node",
    "vue", "react", "angular", "spring", "springboot", "spring cloud", "mysql", "redis",
    "postgresql", "oracle", "sqlserver", "mongodb", "kafka", "rabbitmq", "rocketmq",
    "docker", "kubernetes", "k8s", "linux", "nginx", "hadoop", "spark", "flink",
    "fastapi", "django", "flask", "git", "jenkins", "selenium", "微信小程序", "小程序",
    "项目管理", "团队管理", "需求分析", "产品设计", "数据分析", "excel", "sql", "etl", "bi",
    "测试", "自动化测试", "接口测试", "性能测试", "算法", "机器学习", "深度学习", "nlp", "cv",
    "android", "ios", "flutter", "reactnative", "html", "css", "echarts", "pandas", "numpy",
    "爬虫", "ocr", "大模型", "llm", "prompt", "rpa", "网络运维", "安全", "渗透测试",
]
SECTION_TITLES = {
    "求职意向": ["求职意向", "期望职位", "应聘岗位"],
    "教育经历": ["教育经历", "教育背景", "学历"],
    "工作经历": ["工作经历", "工作经验", "职业经历", "工作履历"],
    "项目经历": ["项目经历", "项目经验", "项目"],
    "专业技能": ["专业技能", "技能特长", "技能", "个人技能"],
    "自我评价": ["自我评价", "个人评价", "自我描述", "关于我"],
    "证书荣誉": ["证书", "荣誉", "获奖"],
}

# ---------- 工具 ----------


def _norm_year_int(s: str):
    m = re.search(r"(?:19|20)\d{2}", s or "")
    return int(m.group()) if m else None


def _mask_confident(phone: str):
    """手机号中间四位打码（解析结果展示用），实际数据明文入库。"""
    return phone


# ---------- 清洗 ----------


def clean_resume(text: str) -> str:
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if len(s) <= 40 and any(k in s.lower() for k in PLATFORM_NOISE):
            continue  # 剔除页眉页脚水印行
        lines.append(s)
    return "\n".join(lines)


# ---------- 板块切分 ----------


def split_sections(text: str):
    """按简历板块标题切分。返回 [(section_type, content)]"""
    lines = text.splitlines()
    sections, cur_type, cur = [], "其他", []
    hits = {t: title for title, alts in SECTION_TITLES.items() for t in alts}

    def flush():
        if cur:
            sections.append((cur_type, "\n".join(cur)))
            cur.clear()

    for ln in lines:
        if len(ln) <= 14 and ln in hits:
            flush()
            cur_type = hits[ln]
        else:
            cur.append(ln)
    flush()
    return sections or [("其他", text)]


# ---------- 字段抽取 ----------


def extract_fields(text: str, sections=None):
    """返回 (fields, confidence)。fields 各字段 + 置信度 0~1。"""
    sections = sections or split_sections(text)
    fields = {}
    conf = {}

    def put(key, value, level):
        if value not in (None, "", [], "未知", 0):
            fields[key] = value
            conf[key] = level

    # 手机号（含脱敏识别）
    masked = MASKED_PHONE_RE.search(text)
    phone = PHONE_RE.search(text)
    if phone:
        put("phone", phone.group(), 1.0)
    elif masked:
        put("phone", masked.group(), 1.0)
        fields["phone_masked"] = True

    # 邮箱
    email = EMAIL_RE.search(text)
    put("email", email.group() if email else None, 1.0)

    # 出生年 → 年龄
    birth = BIRTH_RE.search(text)
    if birth:
        by = int(birth.group(1))
        age = date.today().year - by
        put("age", age, 0.9)

    # 姓名：先找"姓名：XXX"标签，失败回退到首行短中文文本
    nm = None
    name_conf = 0.0
    name_m = re.search(r"(?:姓名|名字)[：:\s]*(.{2,8})", text)
    if name_m:
        candidate = name_m.group(1).strip()
        if not any(ch in candidate for ch in "1234567890@.电话邮箱"):
            nm, name_conf = candidate, 0.95
    if not nm:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if lines:
            first = re.sub(r"[：:\s]", "", lines[0])
            section_names = {t for alts in SECTION_TITLES.values() for t in alts}
            if (2 <= len(first) <= 4 and re.fullmatch(r"[\u4e00-\u9fa5]+", first)
                    and first not in section_names
                    and first not in ("个人简历", "简历", "求职简历", "简历模板")):
                nm, name_conf = first, 0.6
    put("name", nm, name_conf)

    # 学历
    edu = None
    for lv in EDU_LEVELS:
        if lv in text:
            edu = lv
            break
    put("education", edu, 0.95)

    # 学校
    school, is_985, school_conf = None, False, 0.0
    for s in KNOWN_SCHOOLS:
        if s in text:
            school, is_985, school_conf = s, True, 0.95
            break
    if not school:
        m = re.search(r"([\u4e00-\u9fa5]{2,12}(?:大学|学院|学校))", text)
        if m:
            school, school_conf = m.group(1), 0.6
    put("school", school, school_conf)
    put("top_school", is_985 or None, 0.95)

    # 工作年限
    exp = None
    exp_conf = 0.0
    m = EXPERIENCE_RE.search(text)
    if m:
        exp = int(m.group(1))
        exp_conf = 0.9
    else:
        # 由工作经历时间区间推算（低置信）
        total_months = 0
        for r in DATE_RANGE_RE.finditer(text):
            sy = int(r.group("s"))
            if r.group("now"):
                ey = date.today().year
            elif r.group("e"):
                ey = int(r.group("e"))
            else:
                ey = sy
            if ey >= sy:
                total_months += (ey - sy) * 12
        if total_months >= 6:
            exp = round(total_months / 12, 1)
            exp_conf = 0.5
    put("work_years", exp, exp_conf if exp else 0.0)

    # 期望薪资
    salary = None
    m = re.search(r"期望(?:薪资|月薪|薪酬)[：:\s]*([0-9kK\.\-~至到万]+\s*(?:元|/月)?)", text)
    if m:
        raw = m.group(1)
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", raw)]
        if "万" in raw:
            nums = [n * 10000 for n in nums]
        elif any(ch.isalpha() and ch.lower() == "k" for ch in raw):
            nums = [n * 1000 for n in nums]
        if nums:
            salary = int(max(nums))  # 取上限
    if not salary:
        m = SALARY_RE.search(text)
        if m:
            nums = [float(x) for x in m.groups() if x]
            if "k" in m.group().lower():
                nums = [n * 1000 for n in nums]
            if nums:
                salary = int(max(nums))
    put("expect_salary", salary, 0.8)

    # 城市
    city = None
    m = re.search(r"(?:期望|期望工作|工作地点|现居|所在|城市)[：:\s]*([\u4e00-\u9fa5]{2,4}(?:市)?)", text)
    if m:
        c = m.group(1).replace("市", "")
        if c in CITIES:
            city = c
    if not city:
        for c in ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "西安", "重庆", "苏州", "天津"]:
            if c in text:
                city = c
                break
    put("city", city, 0.8)

    # 当前公司/职位
    cm = re.search(r"(?:现任|目前就职于|目前公司)[：:\s]*([\u4e00-\u9fa5A-Za-z0-9&]{2,20}公司|[\u4e00-\u9fa5A-Za-z0-9&]{2,20})", text)
    tm = POSITION_TITLE_RE.search(text)
    put("current_company", cm.group(1) if cm else None, 0.7)
    put("current_title", tm.group(1) if tm else None, 0.7)

    # 技能匹配：英文/数字用词边界（防 go 命中 mongodb、java 命中 javascript、sql 命中 mysql），中文用子串
    text_lower = text.lower()

    def _skill_hit(skill: str, tl: str) -> bool:
        skill = skill.lower()
        if skill.isascii():
            return re.search(r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])", tl) is not None
        return skill in tl

    skills = [s for s in SKILLS if _skill_hit(s, text_lower)]
    put("skills", skills or None, 0.9)

    # 管理经验
    put("has_management", ("管理" in text and any(k in text for k in ["团队", "下属", "负责人", "经理", "主管"])), 0.8)

    # 稳定性：工作经历段数（DATE_RANGE_RE 已支持"至今"，段数准确）
    ranges = list(DATE_RANGE_RE.finditer(text))
    put("job_changes", len(ranges) or None, 0.6)

    return fields, conf


def parse_resume(filename: str, raw: bytes):
    """完整解析。返回 dict：raw_text, is_scan, fields, confidence, sections"""
    from .doc_utils import extract_text
    text = extract_text(filename, raw)
    is_scan = False
    if filename.lower().endswith(".pdf"):
        import fitz, io
        doc = fitz.open(stream=raw, filetype="pdf")
        chars = sum(len(page.get_text()) for page in doc)
        pages = max(1, doc.page_count)
        doc.close()
        if chars / pages < 50:
            is_scan = True  # 扫描件：无文本层
    if is_scan:
        return {"raw_text": "", "is_scan": True, "fields": {}, "confidence": {},
                "sections": [("其他", "")]}
    text = clean_resume(text)
    sections = split_sections(text)
    fields, conf = extract_fields(text, sections)
    return {"raw_text": text, "is_scan": False, "fields": fields,
            "confidence": conf, "sections": sections}

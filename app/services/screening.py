"""简历初筛引擎：硬条件过滤 + 软条件加权评分 + 三档归类。全规则、可解释、可审计。"""
import json


def _edu_rank(edu):
    rank = {"博士": 6, "硕士": 5, "硕士研究生": 5, "研究生": 5, "本科": 4, "双学位": 4,
            "大专": 3, "专科": 3, "高中": 2, "中专": 2, "中技": 2, None: 0}
    return rank.get(edu, 0)


def _check_hard(c, cond):
    """返回 (pass_all, details)。details: [{key, label, ok, expect, actual}]"""
    details = []
    all_ok = True

    edu_req = cond.get("education") or "不限"
    if edu_req != "不限":
        ok = _edu_rank((c.get("education") or "").replace("硕士研究生", "硕士").replace("研究生", "硕士")) >= _edu_rank(edu_req)
        details.append({"key": "education", "label": "学历", "ok": ok,
                        "expect": f"{edu_req}及以上", "actual": c.get("education") or "未识别"})
        all_ok = all_ok and ok

    min_years = int(cond.get("min_years") or 0)
    if min_years > 0:
        y = c.get("work_years") or 0
        ok = y >= min_years
        details.append({"key": "years", "label": "工作年限", "ok": ok,
                        "expect": f"{min_years}年以上", "actual": f"{y}年" if y else "未识别"})
        all_ok = all_ok and ok

    city = cond.get("city") or "不限"
    if city != "不限":
        ok = c.get("city") == city
        details.append({"key": "city", "label": "现居/期望城市", "ok": ok,
                        "expect": city, "actual": c.get("city") or "未识别"})
        all_ok = all_ok and ok

    salary_max = int(cond.get("salary_max") or 0)
    if salary_max > 0:
        s = c.get("expect_salary") or 0
        ok = s <= salary_max
        details.append({"key": "salary", "label": "期望薪资上限", "ok": ok,
                        "expect": f"{salary_max}元内", "actual": f"{s}元" if s else "未识别"})
        all_ok = all_ok and ok

    skills_req = [s for s in (cond.get("skills") or "").split(",") if s.strip()]
    if skills_req:
        mode = cond.get("skills_mode") or "any"
        matched = [s for s in skills_req if s.strip().lower() in [x.lower() for x in (c.get("skills") or [])]]
        ok = (len(matched) == len(skills_req)) if mode == "all" else (len(matched) > 0)
        details.append({"key": "skills", "label": "技能关键词", "ok": ok,
                        "expect": ("全部满足" if mode == "all" else "任一满足") + "：" + ",".join(skills_req),
                        "actual": ("命中：" + ",".join(matched)) if matched else "未命中"})
        all_ok = all_ok and ok

    return all_ok, details


def _score_soft(c, cond, weights):
    """返回 (score, score_detail)。权重任意，自动归一化到 100 分制。"""
    score, detail = 0, []
    total_w = sum(weights.values()) or 1
    norm = 100.0 / total_w  # 权重之和不为 100 时归一化，保证满分恒为 100

    def add(key, label, pts, base, reason):
        nonlocal score
        w = weights.get(key, 0)
        part = round(base * w / 50 * norm, 1)   # base 为 0~50 折算分 × 权重 × 归一化
        score += part
        detail.append({"key": key, "label": label, "points": pts, "weight": w,
                       "part": part, "reason": reason})

    # 工作年限充足度（满分 50 折算）
    min_years = int(cond.get("min_years") or 0)
    y = c.get("work_years") or 0
    if min_years and y:
        ratio = min(1.0, y / (min_years + 2))
        add("years", "工作年限", 1, ratio * 50, f"{y}年 / 要求{min_years}年")
    elif min_years and not y:
        add("years", "工作年限", 0, 0, "未识别年限")

    # 知名企业/院校（仅加分，非硬性）
    if c.get("top_school"):
        add("school", "985/211 院校", 1, 45, c.get("school", ""))
    elif c.get("school"):
        add("school", "院校层次", 0, 30, c.get("school", ""))

    if c.get("has_management"):
        add("management", "团队管理经验", 1, 40, "有管理/带团队描述")

    # 稳定性：工作经历分段 ≤2 段加分
    changes = c.get("job_changes") or 0
    if changes == 0:
        add("stability", "稳定性", 0, 0, "未识别工作经历")
    elif changes <= 2:
        add("stability", "稳定性", 1, 45, f"{changes}段经历，较稳定")
    else:
        add("stability", "稳定性", 0, 15, f"{changes}段经历，跳槽较频繁")

    # 技能命中度
    req = [s for s in (cond.get("skills") or "").split(",") if s.strip()]
    skills = c.get("skills") or []
    if req:
        hit = sum(1 for s in req if s.strip().lower() in [x.lower() for x in skills])
        add("skills", "技能命中", 1, round(50 * hit / len(req)), f"{hit}/{len(req)}")

    score = round(min(100, score))
    return score, detail


def screen(candidate_fields, cond, weights=None, pass_threshold=80, maybe_threshold=60):
    """candidate_fields: 解析出的字段 dict。返回 {bucket, score, hard_detail, score_detail}"""
    weights = weights or {"years": 20, "school": 12, "management": 14,
                          "stability": 12, "skills": 20}
    hard_ok, hard_detail = _check_hard(candidate_fields, cond)
    score, score_detail = _score_soft(candidate_fields, cond, weights)

    # 硬条件不满足 → 直接"不通过"档（但保留分数与理由，方便查看差多少）
    if not hard_ok:
        bucket = "reject"
    elif score >= pass_threshold:
        bucket = "pass"
    elif score >= maybe_threshold:
        bucket = "maybe"
    else:
        bucket = "reject"

    return {"bucket": bucket, "score": score, "hard_pass": hard_ok,
            "hard_detail": hard_detail, "score_detail": score_detail}


def serialize(d):
    return json.dumps(d, ensure_ascii=False)

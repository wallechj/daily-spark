#!/usr/bin/env python3
"""Daily Spark 自动更新脚本（供 GitHub Actions 每天调用）。

只有当距离上次提交的天数 >= next_gap_days（1~3 随机）时才产生一次小改动，
否则不做任何改动（也就不会产生提交）。
改动类型在「新增灵感 / 文案微调 / 版本日志」之间轮换，避免连续重复。
"""

import datetime
import json
import os
import random
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(REPO, ".github", "spark-state.json")
MSG_PATH = "/tmp/spark-commit-msg.txt"

# 灵感句子库（与 data/quotes.json 现有内容不重复）
QUOTE_BANK = [
    {"zh": "把焦虑换成计划，把计划拆成今天。", "en": "Turn anxiety into a plan, and the plan into today."},
    {"zh": "你不需要很厉害才能开始，但要开始才能很厉害。", "en": "You don't have to be great to start, but you have to start to be great."},
    {"zh": "今天偷的懒，都会变成明天的债。", "en": "Today's laziness becomes tomorrow's debt."},
    {"zh": "先完成，再完美；先出发，再调整。", "en": "Done first, perfect later; start first, adjust later."},
    {"zh": "难走的路，都是上坡路。", "en": "The hard road is always uphill."},
    {"zh": "把时间花在值得的人和事上。", "en": "Spend your time on people and things that matter."},
    {"zh": "自律不是束缚，是自由的前提。", "en": "Discipline isn't a cage; it's the price of freedom."},
    {"zh": "每天读十页书，一年就是十几本书。", "en": "Ten pages a day is a dozen books a year."},
    {"zh": "别怕走得慢，怕的是站着不动还焦虑。", "en": "Don't fear slowness; fear standing still while anxious."},
    {"zh": "好习惯是复利，坏习惯也是。", "en": "Good habits compound. So do bad ones."},
    {"zh": "把手机放下，世界会清晰很多。", "en": "Put the phone down; the world gets clearer."},
    {"zh": "先处理情绪，再处理事情，顺序别反。", "en": "Handle emotions first, then problems — in that order."},
    {"zh": "你怎么过一天，就怎么过一生。", "en": "How you spend your days is how you spend your life."},
    {"zh": "降低期待，认真生活。", "en": "Lower expectations, live seriously."},
    {"zh": "允许一切发生，是成年人最大的松弛。", "en": "Letting things be is the deepest calm."},
    {"zh": "存钱和存健康，都是给未来的自己。", "en": "Saving money and health are both gifts to your future self."},
    {"zh": "多喝水，多走路，少生气。", "en": "Drink water, walk more, anger less."},
    {"zh": "把「等我有空」改成「就现在」。", "en": "Change \"when I'm free\" to \"right now.\""},
    {"zh": "专注三小时，胜过忙碌一整天。", "en": "Three focused hours beat a busy day."},
    {"zh": "记不住就写下来，写下来就不会忘。", "en": "Write it down and you won't forget."},
    {"zh": "和优秀的人在一起，你也会发光。", "en": "Stay close to excellent people; you'll shine too."},
    {"zh": "拒绝内耗，从放下手机开始。", "en": "Stop the mental drain; start by putting the phone down."},
    {"zh": "今天的你，正在为明天的你铺路。", "en": "Today's you is paving the road for tomorrow's you."},
    {"zh": "小事不拖，大事不慌。", "en": "Don't delay small things; don't panic over big ones."},
    {"zh": "笑一笑，没什么大不了。", "en": "Smile — it's no big deal."},
    {"zh": "健康是 1，其他都是 0。", "en": "Health is the 1; everything else is a 0."},
    {"zh": "把复杂留给自己，把简单留给别人。", "en": "Keep complexity for yourself; leave simplicity for others."},
    {"zh": "行动是治愈焦虑最好的药。", "en": "Action is the best cure for anxiety."},
    {"zh": "每天留一点时间给自己发呆。", "en": "Leave a little time each day to just stare blankly."},
    {"zh": "认真吃饭，好好睡觉，日子就不会太差。", "en": "Eat well, sleep well; life won't be too bad."},
    {"zh": "不要和昨天的人比输赢。", "en": "Don't compete with who you were yesterday."},
    {"zh": "把热爱变成习惯，把习惯变成生活。", "en": "Turn passion into habit, habit into life."},
    {"zh": "慢工出细活，心急吃不了热豆腐。", "en": "Slow work makes fine work."},
    {"zh": "给生活做减法，给热爱做加法。", "en": "Subtract from life; add to passion."},
    {"zh": "今天也是被小确幸包围的一天。", "en": "Today is another day wrapped in small joys."},
    {"zh": "未来很长，慢慢走，别着急。", "en": "The future is long; walk slowly, don't rush."},
]

BUTTON_VARIANTS = ["再来一句 ↻", "换一句看看 ↻", "下一句 ✨"]
HINT_VARIANTS = ["每一次打开，都在变好一点点。", "小步快走，每天进步一点点。", "坚持打卡，灵感自来。"]


def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(st):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_msg(msg):
    with open(MSG_PATH, "w", encoding="utf-8") as f:
        f.write(msg + "\n")


def add_quotes(st):
    path = os.path.join(REPO, "data", "quotes.json")
    with open(path, encoding="utf-8") as f:
        quotes = json.load(f)
    used = set(st.get("used_quotes", []))
    avail = [i for i in range(len(QUOTE_BANK)) if i not in used]
    if not avail:
        return None
    n = min(3, len(avail))
    pick = random.sample(avail, n)
    for i in pick:
        quotes.append(QUOTE_BANK[i])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)
        f.write("\n")
    used.update(pick)
    st["used_quotes"] = sorted(used)
    return f"✨ 新增 {n} 条每日灵感"


def tweak_copy(st):
    path = os.path.join(REPO, "index.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    for i, v in enumerate(BUTTON_VARIANTS):
        if v in html:
            nxt = BUTTON_VARIANTS[(i + 1) % len(BUTTON_VARIANTS)]
            html = html.replace(v, nxt, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            return "🎨 微调「今日灵感」换句按钮文案"
    for i, v in enumerate(HINT_VARIANTS):
        if v in html:
            nxt = HINT_VARIANTS[(i + 1) % len(HINT_VARIANTS)]
            html = html.replace(v, nxt, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            return "🎨 微调「灵感足迹」区文案"
    return None


def bump_version(st):
    html_path = os.path.join(REPO, "index.html")
    md_path = os.path.join(REPO, "README.md")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r'<span id="version">v(\d+)\.(\d+)\.(\d+)</span>', html)
    if not m:
        return None
    major, minor, patch = map(int, m.groups())
    new_ver = f"v{major}.{minor}.{patch + 1}"
    html = html.replace(m.group(0), f'<span id="version">{new_ver}</span>', 1)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    today = datetime.date.today().isoformat()
    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    entry = f"- **{new_ver}** ({today}) — 日常维护：文案与细节优化\n"
    md = md.rstrip("\n") + "\n" + entry
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    return f"📝 版本更新到 {new_ver}"


def main():
    today = datetime.date.today().isoformat()
    st = load_state()
    last = st.get("last_commit")
    gap = st.get("next_gap_days", 2)
    if last:
        days = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(last)).days
        if days < gap:
            print(f"skip: {days}d < {gap}d")
            return
    cands = {"quotes": add_quotes, "copy": tweak_copy, "version": bump_version}
    last_type = st.get("last_type")
    order = [t for t in cands if t != last_type]
    random.shuffle(order)
    if last_type in cands:
        order.append(last_type)
    msg, used_type = None, None
    for t in order:
        msg = cands[t](st)
        if msg:
            used_type = t
            break
    if not msg:
        print("no applicable update")
        return
    st["last_commit"] = today
    st["next_gap_days"] = random.randint(1, 3)
    st["last_type"] = used_type
    save_state(st)
    write_msg(msg)
    print("commit:", msg)


if __name__ == "__main__":
    main()

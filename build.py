#!/usr/bin/env python3
"""카페인영어 CafeInEnglish 사이트 빌더

content/ 의 JSON 파일을 읽어 docs/ 에 정적 사이트를 만듭니다.
GitHub Pages 는 docs/ 폴더를 그대로 서비스합니다.

    python3 build.py          # docs/ 다시 만들기
    python3 build.py --serve  # 만들고 http://localhost:8000 에서 미리보기
"""
import hashlib, html, io, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT, ASSETS, OUT = ROOT / "content", ROOT / "assets", ROOT / "docs"

SITE = json.loads((CONTENT / "site.json").read_text("utf-8"))
DOMAIN = SITE["domain"].rstrip("/")
CATS = {"video": "영상으로 배우기", "expr": "영어표현", "tip": "영어꿀팁", "think": "사유의 문장"}
CAT_LEAD = {
    "video": "카페인영어 영상 한 편에서 표현을 뽑아 정리하고, 퀴즈로 확인해요",
    "expr": "새 표현 · 비슷한 표현 · 헷갈리는 표현을 연상법과 퀴즈로",
    "tip": "회화 · 단어 · 듣기 · 발음, 바로 써먹는 영어 꿀팁",
    "think": "영상 속 곱씹을 문장을 필사하고, 빈칸으로 다시 떠올려 보세요",
}
e = lambda s: html.escape(str(s), quote=True)

try:
    import segno
except ImportError:  # QR 없이도 빌드는 됩니다
    segno = None
    print("⚠️  segno 가 없어 출력물 QR 코드를 건너뜁니다 (pip install segno)")


def qr_svg(url):
    if not segno:
        return ""
    b = io.BytesIO()
    segno.make(url, error="m").save(b, kind="svg", scale=4, border=2, xmldecl=False, svgns=True,
                                     dark="#111", light="#fff", omitsize=True)
    return b.getvalue().decode().strip()


def load(kind):
    items = [json.loads(p.read_text("utf-8")) for p in sorted((CONTENT / kind).glob("*.json"))]
    return sorted(items, key=lambda x: (x.get("date", ""), x["id"]), reverse=True)


POSTS, THINKS = load("posts"), load("think")
POST_BY_ID, THINK_BY_ID = {p["id"]: p for p in POSTS}, {t["id"]: t for t in THINKS}
post_url = lambda p: f"/p/{p['id']}/"
think_url = lambda t: f"/think/{t['id']}/"
ASSET_V = hashlib.md5(b"".join(f.read_bytes() for f in sorted(ASSETS.glob("*")))).hexdigest()[:8]


def mmss(t):
    return f"{t // 60}:{t % 60:02d}"


# ------------------------------------------------------------------ layout
def layout(title, desc, path, body, nav="", data=None, og_type="website"):
    full_title = f"{title} | 카페인영어" if path != "/" else f"{SITE['name']} — {SITE['tagline']}"
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(SITE["adsense_client"])}" crossorigin="anonymous"></script>'
           if SITE.get("adsense_client") else "")
    ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={e(SITE["ga_id"])}"></script>'
          f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{e(SITE['ga_id'])}');</script>"
          if SITE.get("ga_id") else "")
    navlinks = "".join(
        f'<a href="/category/{k}/"{" class=on" if nav == k else ""}>{v}</a>' for k, v in CATS.items())
    navlinks += f'<a href="/notes/"{" class=on" if nav == "notes" else ""}>내 오답노트<span class="badge" id="nav-badge" hidden></span></a>'
    pjson = json.dumps(data or {}, ensure_ascii=False).replace("</", "<\\/")
    pdata = '<script id="page-data" type="application/json">' + pjson + '</script>'
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{DOMAIN}{path}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{e(SITE['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{DOMAIN}{path}">
<link rel="stylesheet" href="/assets/style.css?v={ASSET_V}">
{ads}{ga}
</head>
<body>
<header class="top"><div class="top-in">
  <a class="logo" href="/">카페인영어 <span style="font-weight:600;color:var(--accent)">CafeInEnglish</span></a>
  <nav class="nav">{navlinks}</nav>
</div></header>
<main>
{body}
</main>
<footer class="foot no-print">
  <div>{e(SITE['name'])} · {e(SITE['tagline'])}</div>
  <div style="margin-top:8px"><a href="/about/">소개</a><a href="/privacy/">개인정보처리방침</a><a href="/contact/">문의</a>{f'<a href="{e(SITE["youtube"])}" target="_blank" rel="noopener">유튜브</a>' if SITE.get("youtube") else ""}</div>
</footer>
{pdata}
<script src="/assets/app.js?v={ASSET_V}" defer></script>
</body>
</html>
"""


def card(href, chips, title, sub):
    chip_html = "".join('<span class="chip %s">%s</span>' % (c, e(t)) for c, t in chips)
    return f'<a class="card" href="{href}">{chip_html}<h3>{e(title)}</h3><p>{e(sub)}</p></a>'


def post_card(p):
    return card(post_url(p), [(p["cat"], CATS[p["cat"]]), (p["cat"], p.get("sub", ""))], p["title"],
                f"{p.get('lead', '')} · 퀴즈 {len(p['quiz'])}문제")


def think_card(t):
    return card(think_url(t), [("think", "사유의 문장"), ("video", t["speaker"])], t["title"],
                f"필사할 문장 {len(t['quotes'])}개")


PRINT_BTN = """
<div class="no-print" style="margin-top:22px">
  <button class="btn ghost" id="print-btn">🖨️ 출력해서 복습하기 (PDF 저장)</button>
  <p class="lead" style="font-size:13px;text-align:center;margin-top:6px">인쇄 창에서 대상을 <b>'PDF로 저장'</b>으로 고르면 파일로 받을 수 있어요</p>
</div>"""
CIRC = ["①", "②", "③", "④", "⑤"]


def ws_head(title, sub, video, path):
    qrs = ""
    if video:
        qrs += f'<div class="ws-qr">{qr_svg("https://youtu.be/" + video)}<div>🎬 영상<br>다시 보기</div></div>'
    qrs += f'<div class="ws-qr">{qr_svg(DOMAIN + path + "?src=print")}<div>📝 퀴즈·오답노트<br>다시 풀기</div></div>'
    return (f'<div class="ws-head"><div><div class="brand">카페인영어 CafeInEnglish · 복습 노트</div>'
            f'<h1 style="margin:4px 0 0">{e(title)}</h1><div class="date">{e(sub)}</div>'
            f'<div class="date" style="margin-top:6px">공부한 날: ______ / ______</div></div>'
            f'<div class="ws-qrs">{qrs if segno else ""}</div></div>')


# ------------------------------------------------------------------ pages
def related_links(p):
    links = list(p.get("related", []))
    if p.get("think") in THINK_BY_ID:
        links.append({"label": "✍️ 이 영상 문장 필사하기", "href": think_url(THINK_BY_ID[p["think"]])})
    for cat, label in (("expr", "다른 표현 보러가기 →"), ("tip", "다른 꿀팁 보러가기 →"), ("video", "다른 영상 표현 보기 →")):
        other = next((o for o in POSTS if o["cat"] == cat and o["id"] != p["id"]), None)
        if other:
            links.append({"label": label, "href": post_url(other)})
    return links[:4]


def page_post(p):
    url = post_url(p)
    video = p.get("video")
    parts = [f'<span class="chip {p["cat"]}">{CATS[p["cat"]]}</span><span class="chip {p["cat"]}">{e(p.get("sub", ""))}</span>',
             f'<h1>{e(p["title"])}</h1><p class="lead">{e(p.get("lead", ""))}</p><p class="date-line">{e(p.get("date", ""))}</p>']
    if video:
        parts.append(f'<div class="video-embed"><iframe id="yt" src="https://www.youtube.com/embed/{video}?enablejsapi=1&rel=0&playsinline=1" '
                     f'title="{e(p["title"])}" loading="lazy" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>')
    parts.append(p.get("body_html", ""))
    if p.get("expressions"):
        parts.append(f'<h2>{e(p.get("expressions_heading", "오늘의 표현"))}</h2>')
        for x in p["expressions"]:
            ts = f'<button class="ts" data-t="{x["t"]}">▶ {mmss(x["t"])} 듣기</button>' if video and "t" in x else ""
            parts.append(f"""<div class="box xp">
  <h3>{e(x['en'])}{ts}</h3><div>{e(x['ko'])}</div>
  <div class="orig">🎙️ {e(x['orig'])}</div>
  <ul class="ex"><li><span class="en">{e(x['ex'])}</span><span class="ko">{e(x['exKo'])}</span></li></ul>
  <div class="memo" style="margin-bottom:0">🧠 <b>연상법</b> — {e(x['memo'])}</div>
</div>""")
    if p.get("think") in THINK_BY_ID:
        parts.append(f'<div class="think-box">✍️ <b>이 영상 속 마음에 남는 문장</b>은 <a href="{think_url(THINK_BY_ID[p["think"]])}">사유의 문장</a>에서 필사하고 복기할 수 있어요.</div>')
    parts.append('<h2 class="quiz-h">✅ 오늘 배운 거 확인하기</h2><div id="quiz"></div>')
    parts.append(PRINT_BTN)
    # 출력용 문제지 (화면에서는 숨김)
    qs = "".join(
        f'<div class="ws-q"><b>{i + 1}. {e(q["q"])}</b>'
        + (f'<br><span style="font-family:Georgia,serif">{e(q["sub"])}</span>' if "___" in q.get("sub", "") else "")
        + "<br>" + "".join(f'<span class="o">{CIRC[k]} {e(o)}</span>' for k, o in enumerate(q["options"])) + "</div>"
        for i, q in enumerate(p["quiz"]))
    key = "".join(f'<li><b>{CIRC[q["answer"]]} {e(q["options"][q["answer"]])}</b> — {e(q["explain"])}<br>🧠 {e(q["mnemonic"])}</li>' for q in p["quiz"])
    parts.append(f"""<div class="print-only ws"><div style="break-before:page"></div>
{ws_head("✏️ 확인 문제", p["title"], video, url)}
<p style="font-size:13px">본문을 다시 읽은 뒤, 정답에 ○ 표시해 보세요. 정답과 연상법은 맨 아래에 있어요.</p>{qs}
<h2>✍️ 오늘의 표현, 직접 써 보기</h2><div class="ws-label">오늘 배운 표현으로 나만의 문장 2개 만들기</div>
<div class="ws-line"></div><div class="ws-line"></div><div class="ws-line"></div><div class="ws-line"></div>
<div class="ws-key"><b>정답과 연상법</b><ol>{key}</ol></div>
<p style="font-size:12px;color:#555">{DOMAIN.replace("https://", "")} · 매일 표현 하나, 같이 공부해요</p></div>""")
    data = {"type": "post", "id": p["id"], "title": p["title"], "url": url, "cat": p["cat"], "catName": CATS[p["cat"]],
            "quiz": p["quiz"], "links": related_links(p), "kakao": SITE.get("kakao", "")}
    return layout(p["title"], p.get("description", p.get("lead", "")), url, "\n".join(parts), p["cat"], data, "article")


def page_think(t):
    url = think_url(t)
    cards = []
    for i, q in enumerate(t["quotes"]):
        cards.append(f"""<div class="quote no-print" data-id="{t['id']}:{i}" data-i="{i}">
  <div class="meta"><span>문장 {i + 1} / {len(t['quotes'])}</span>
    <a class="ts" href="https://www.youtube.com/watch?v={t.get('video', '')}&t={q['t']}s" target="_blank" rel="noopener" style="text-decoration:none">▶ {mmss(q['t'])} 영상에서 듣기</a></div>
  <p class="en">{e(q['en'])}</p><p class="ko">{e(q['ko'])}</p>
  <div class="think-box">💭 <b>생각해 보기</b> — {e(q['think'])}<br><br>❓ {e(q['ask'])}</div>
  <div class="tabs"><button class="on" data-mode="copy">✍️ 필사하기</button><button data-mode="blank">🧩 빈칸 복기</button></div>
  <div class="pane"></div>
  <div style="margin-top:14px;font-size:14px;font-weight:700">💬 나의 한 줄</div>
  <textarea class="note" placeholder="이 문장이 나에게 주는 의미를 한 줄로 남겨 보세요" style="min-height:60px;margin-top:6px"></textarea>
  <div class="row"><button class="btn ghost save-note">저장</button></div>
</div>""")
    ws = "".join(f"""<div class="ws-quote"><p class="en">{i + 1}. {e(q['en'])}</p><p class="ko">{e(q['ko'])}</p>
<div class="ws-label">따라 쓰기</div><div class="ws-line"></div><div class="ws-line"></div>
<div class="ws-label">❓ {e(q['ask'])}</div><div class="ws-line"></div></div>""" for i, q in enumerate(t["quotes"]))
    post = POST_BY_ID.get(t.get("post"))
    body = f"""<div class="no-print">
<span class="chip think">사유의 문장</span><span class="chip video">{e(t['speaker'])}</span>
<h1>{e(t['title'])}</h1>
<p class="lead">따라 쓰고(필사), 빈칸으로 다시 떠올리고(복기), 나의 한 줄을 남겨 보세요.</p>
{f'<a class="btn ghost" href="{post_url(post)}">🎬 이 영상의 영어표현 먼저 보기</a>' if post else ""}
</div>
{"".join(cards)}
{PRINT_BTN}
<div class="print-only ws">{ws_head("✍️ 필사 노트 — " + t["title"], t["speaker"], t.get("video"), url)}{ws}</div>
<div class="cq-cta no-print" style="margin-top:16px">
  <a class="btn primary" href="/category/think/">📓 내 필사 노트 보기</a>
  {f'<a class="btn kakao" href="{e(SITE["kakao"])}" target="_blank" rel="noopener">💬 매일 아침 문장 하나, 카톡으로 받기</a>' if SITE.get("kakao") else ""}
</div>"""
    data = {"type": "think", "id": t["id"], "title": t["title"], "speaker": t["speaker"], "url": url,
            "quotes": [{"en": q["en"], "ko": q["ko"], "blanks": q["blanks"]} for q in t["quotes"]]}
    return layout(t["title"] + " — 필사하기", t.get("description", ""), url, body, "think", data, "article")


def page_category(cat):
    url = f"/category/{cat}/"
    if cat == "think":
        cards = "".join(think_card(t) for t in THINKS)
        body = (f'<h1>✍️ {CATS[cat]}</h1><p class="lead">{CAT_LEAD[cat]}</p><div class="cards">{cards}</div>'
                '<h2>📓 내 필사 노트 (<span id="copy-count">0</span>)</h2><div id="copy-notes"></div>')
    else:
        items = [p for p in POSTS if p["cat"] == cat]
        cards = "".join(post_card(p) for p in items) or '<div class="empty"><p>곧 첫 글이 올라와요 ☕</p></div>'
        body = f'<h1>{CATS[cat]}</h1><p class="lead">{CAT_LEAD[cat]}</p><div class="cards">{cards}</div>'
    return layout(CATS[cat], CAT_LEAD[cat], url, body, cat)


def page_home():
    latest = "".join(post_card(p) for p in POSTS[:12])
    thinks = "".join(think_card(t) for t in THINKS[:4])
    body = f"""<div class="hero">
  <h1 style="margin:0">오늘도 영어 한 잔</h1>
  <p>영어를 매일 조금씩이라도 하고 싶어서 제가 쓰려고 만든 공간이에요. 셀럽 인터뷰에서 건진 표현을 정리하고, 퀴즈로 확인하고, 틀린 건 오답노트로 다시 봐요. 같이 매일 한 잔씩 해요.</p>
  <p style="font-size:13px;color:var(--muted)">— 카페인영어 CafeInEnglish</p>
</div>
<h2>새로 올라온 글</h2><div class="cards">{latest}</div>
{f'<h2>✍️ 사유의 문장</h2><div class="cards">{thinks}</div>' if thinks else ""}"""
    return layout(SITE["name"], SITE["tagline"], "/", body)


def page_notes():
    body = ('<h1>📒 내 오답노트</h1><p class="lead">틀린 문제는 다시 풀어서 맞히면 \'졸업\'해요. '
            '오답노트는 이 기기의 브라우저에만 저장돼요.</p><div id="notes-root"></div>')
    return layout("내 오답노트", "퀴즈에서 틀린 문제를 모아 다시 풀고 복기하는 나만의 오답노트", "/notes/", body, "notes",
                  {"type": "notes", "kakao": SITE.get("kakao", "")})


def page_static(slug, title, desc, inner):
    return layout(title, desc, f"/{slug}/", f'<h1>{e(title)}</h1><div class="prose">{inner}</div>')


EMAIL = SITE.get("contact_email") or ""
email_html = f'<a href="mailto:{e(EMAIL)}">{e(EMAIL)}</a>' if EMAIL else "(문의 이메일 준비 중)"
ABOUT = f"""
<p>안녕하세요, 유튜브 채널 <b>카페인영어 CafeInEnglish</b>를 운영하고 있어요.</p>
<p>이 사이트는 제가 영어를 매일 조금씩이라도 공부하고 싶어서 만든 공간이에요. 셀럽 인터뷰와 연설에서 건진 표현을 정리하고, 글 끝의 퀴즈로 확인하고, 틀린 문제는 오답노트로 다시 봐요. 마음에 남는 문장은 필사하고 복기해요.</p>
<h2>이런 걸 할 수 있어요</h2>
<ul>
<li><b>영상으로 배우기</b> — 카페인영어 영상 속 표현을 장면과 함께 정리</li>
<li><b>영어표현 · 영어꿀팁</b> — 새 표현, 헷갈리는 표현, 회화·단어·듣기 꿀팁</li>
<li><b>퀴즈와 오답노트</b> — 틀린 문제는 자동으로 모여서 다시 풀 수 있어요</li>
<li><b>사유의 문장</b> — 곱씹을 문장을 필사하고 빈칸으로 복기</li>
<li><b>출력해서 복습하기</b> — 글마다 PDF 복습지로 저장하거나 인쇄할 수 있어요</li>
</ul>
<p>인용한 인터뷰·연설 문장은 학습을 위해 짧게 인용하고 출처를 밝히고 있어요. 문제가 있다면 <a href="/contact/">문의</a>로 알려주세요.</p>
<p>같이 매일 한 잔씩 해요 ☕</p>"""
PRIVACY = f"""
<p>{e(SITE['name'])}(이하 '사이트')는 이용자의 개인정보를 소중히 여깁니다. 이 방침은 {e(DOMAIN.replace('https://', ''))} 에 적용됩니다.</p>
<h2>1. 수집하는 정보</h2>
<p>사이트는 회원가입이 없으며 이름, 연락처 등 개인정보를 직접 수집하지 않습니다.</p>
<h2>2. 브라우저 저장소 이용</h2>
<p>퀴즈 오답노트, 필사 기록, '나의 한 줄'은 이용자의 기기 브라우저(localStorage)에만 저장되며 사이트 서버로 전송되지 않습니다. 브라우저의 사이트 데이터를 삭제하면 기록도 함께 삭제됩니다.</p>
<h2>3. 광고 (Google AdSense)</h2>
<p>사이트는 Google AdSense 광고를 게재할 수 있습니다. Google을 포함한 제3자 공급업체는 쿠키를 사용하여 이용자의 이전 방문 기록을 바탕으로 광고를 게재할 수 있습니다. 이용자는 <a href="https://adssettings.google.com" target="_blank" rel="noopener">Google 광고 설정</a>에서 맞춤 광고를 해제할 수 있습니다. 자세한 내용은 <a href="https://policies.google.com/technologies/ads" target="_blank" rel="noopener">Google 광고 정책</a>을 참고하세요.</p>
<h2>4. 방문 통계</h2>
<p>사이트는 방문자 수 등 통계 확인을 위해 Google Analytics를 사용할 수 있으며, 이 과정에서 쿠키 등 비식별 정보가 수집될 수 있습니다.</p>
<h2>5. 외부 콘텐츠</h2>
<p>사이트에 삽입된 YouTube 영상은 YouTube(Google)의 개인정보처리방침이 적용됩니다.</p>
<h2>6. 문의</h2>
<p>개인정보 관련 문의: {email_html}</p>
<p>시행일: 2026년 10월 1일</p>"""
CONTACT = f"""
<p>사이트나 콘텐츠에 대한 의견, 오류 제보, 저작권 관련 요청은 아래로 보내주세요.</p>
<div class="box">📩 {email_html}</div>
{f'<p>유튜브: <a href="{e(SITE["youtube"])}" target="_blank" rel="noopener">카페인영어 CafeInEnglish</a></p>' if SITE.get("youtube") else ""}"""


def page_404():
    return layout("페이지를 찾을 수 없어요", "요청한 페이지가 없어요", "/404.html",
                  '<div class="empty"><div class="e">☕</div><p>찾으시는 페이지가 없어요.<br>주소가 바뀌었거나 삭제된 글일 수 있어요.</p></div>'
                  '<a class="btn primary" href="/">홈으로 가기</a>')


# ------------------------------------------------------------------ build
def write(path, text):
    f = OUT / path.lstrip("/")
    if path.endswith("/"):
        f = f / "index.html"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, "utf-8")


def build():
    global START
    import time
    START = time.time() - 1
    # 기존 파일은 덮어쓰기만 합니다 (삭제하지 않음). 더 이상 쓰지 않는 파일은 마지막에 알려줍니다.
    before = {f for f in OUT.rglob("*") if f.is_file()} if OUT.exists() else set()
    OUT.mkdir(exist_ok=True)
    shutil.copytree(ASSETS, OUT / "assets", dirs_exist_ok=True)
    pages = ["/"]
    write("/", page_home())
    for p in POSTS:
        write(post_url(p), page_post(p)); pages.append(post_url(p))
    for t in THINKS:
        write(think_url(t), page_think(t)); pages.append(think_url(t))
    for c in CATS:
        write(f"/category/{c}/", page_category(c)); pages.append(f"/category/{c}/")
    write("/notes/", page_notes())
    write("/about/", page_static("about", "카페인영어 소개", "제가 매일 영어 공부하려고 만든 공간, 카페인영어를 소개해요", ABOUT)); pages.append("/about/")
    write("/privacy/", page_static("privacy", "개인정보처리방침", "카페인영어 개인정보처리방침", PRIVACY)); pages.append("/privacy/")
    write("/contact/", page_static("contact", "문의", "카페인영어 문의하기", CONTACT)); pages.append("/contact/")
    (OUT / "404.html").write_text(page_404(), "utf-8")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{DOMAIN}{u}</loc></url>\n" for u in pages) + "</urlset>\n", "utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n", "utf-8")
    (OUT / "CNAME").write_text(DOMAIN.replace("https://", "") + "\n", "utf-8")
    (OUT / ".nojekyll").write_text("", "utf-8")
    if SITE.get("adsense_client"):
        pub = SITE["adsense_client"].replace("ca-", "")
        (OUT / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", "utf-8")
    after = {f for f in OUT.rglob("*") if f.is_file()}
    written = {OUT / "assets" / f.name for f in ASSETS.glob("*")} | {f for f in after if f.stat().st_mtime >= START}
    stale = sorted(str(f.relative_to(OUT)) for f in before - written if f.name != ".DS_Store")
    if stale:
        print("🧹 더 이상 쓰지 않는 파일 (지워도 됨):", ", ".join(stale))
    print(f"✅ docs/ 생성 완료 — 글 {len(POSTS)}개, 사유의 문장 {len(THINKS)}개, 페이지 {len(pages)}개")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import http.server, functools, socketserver
        h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        with socketserver.TCPServer(("", 8000), h) as s:
            print("미리보기: http://localhost:8000"); s.serve_forever()

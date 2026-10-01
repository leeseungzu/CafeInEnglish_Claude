#!/usr/bin/env python3
"""카페인영어 CafeInEnglish 사이트 빌더

content/ 의 JSON 파일을 읽어 docs/ 에 정적 사이트를 만듭니다.
GitHub Pages 는 docs/ 폴더를 그대로 서비스합니다.

    python3 build.py          # docs/ 다시 만들기
    python3 build.py --serve  # 만들고 http://localhost:8000 에서 미리보기
"""
import hashlib, html, io, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT, ASSETS, OUT = ROOT / "content", ROOT / "assets", ROOT / "docs"

SITE = json.loads((CONTENT / "site.json").read_text("utf-8"))
DOMAIN = SITE["domain"].rstrip("/")
CATS = {"video": "영상으로 배우기", "expr": "영어표현", "tip": "영어꿀팁", "think": "사유의 문장"}
TILE_SUB = {"video": "카영 영상 속 표현을 장면과 함께", "expr": "새 표현 · 비슷한 표현 · 헷갈리는 표현",
            "tip": "회화 · 단어 · 듣기 · 발음", "think": "필사하고 빈칸으로 복기"}
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


try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # 공유 이미지 없이도 빌드는 됩니다
    Image = None
FONT = ROOT / "fonts" / "PretendardVariable.ttf"


def _font(size, weight):
    f = ImageFont.truetype(str(FONT), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def og_image(name, chip, big, small, foot="읽고 · 듣고 · 퀴즈로 확인"):
    """글마다 카톡·SNS 미리보기 이미지(1200×630)를 만들고 주소를 돌려줍니다."""
    if not (Image and FONT.exists()):
        return "/assets/og.png"
    W, H, PAD = 1200, 630, 80
    BG, INK, LIME, MUTED = "#F4EEE4", "#2A1A12", "#CDEB5B", "#7A6A5E"
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # 상단: C. 배지 + 브랜드
    d.rounded_rectangle((PAD, 62, PAD + 64, 126), 16, fill=INK)
    d.text((PAD + 15, 94), "C", font=_font(44, 800), fill=BG, anchor="lm")
    d.ellipse((PAD + 43, 102, PAD + 53, 112), fill=LIME)
    d.text((PAD + 84, 94), "카페인영어 CafeInEnglish", font=_font(30, 700), fill=INK, anchor="lm")
    # 카테고리 칩
    cf = _font(26, 700)
    cw = d.textlength(chip, font=cf)
    d.rounded_rectangle((PAD, 168, PAD + cw + 40, 214), 23, fill=INK)
    d.text((PAD + 20, 191), chip, font=cf, fill=BG, anchor="lm")
    # 큰 영어 표현: 폭에 맞춰 글자 크기 자동 조절, 최대 2줄
    maxw = W - PAD * 2
    for size in range(124, 54, -4):
        bf = _font(size, 800)
        words, lines, cur = big.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=bf) <= maxw or not cur:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
        if (len(lines) <= 2 and len(lines) * size * 1.12 <= 230
                and all(d.textlength(l, font=bf) <= maxw for l in lines)):
            break
    lh = int(size * 1.12)
    y = 246 + (230 - len(lines) * lh) // 2 - int(size * .08)
    for l in lines:
        lw = d.textlength(l, font=bf)
        d.rectangle((PAD - 6, y + int(size * .62), PAD + lw + 6, y + int(size * .98)), fill=LIME)
        d.text((PAD, y), l, font=bf, fill=INK)
        y += lh
    # 한국어 설명 + 하단 주소
    sf = _font(38, 600)
    while d.textlength(small, font=sf) > maxw and len(small) > 4:
        small = small[:-2].rstrip() + "…"
    d.text((PAD, 492), small, font=sf, fill=INK)
    d.text((PAD, 566), "cafeinenglish.com", font=_font(26, 600), fill=MUTED)
    d.text((W - PAD, 566), foot, font=_font(26, 600), fill=MUTED, anchor="ra")
    out = OUT / "og" / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)
    return f"/og/{name}.png"


ORG = {"@type": "Organization", "name": "카페인영어 CafeInEnglish", "url": DOMAIN + "/",
       "logo": {"@type": "ImageObject", "url": DOMAIN + "/assets/icon-512.png"}}


def ld_html(objs):
    """구글 구조화 데이터 (JSON-LD)"""
    if not objs:
        return ""
    j = json.dumps({"@context": "https://schema.org", "@graph": objs}, ensure_ascii=False).replace("</", "<\\/")
    return '<script type="application/ld+json">' + j + "</script>"


def ld_article(title, desc, url, img, date, mod, section, crumbs):
    art = {"@type": "Article", "headline": title[:110], "description": desc, "image": DOMAIN + img,
           "datePublished": date, "dateModified": mod, "inLanguage": "ko", "articleSection": section,
           "author": ORG, "publisher": ORG, "mainEntityOfPage": DOMAIN + url}
    bc = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(crumbs)]}
    return [art, bc]


SNS_ICON = {
    "kakao": '<svg width="26" height="24" viewBox="0 0 30 28" aria-hidden="true"><path d="M15 2C7.8 2 2 6.6 2 12.3c0 3.7 2.4 6.9 6.1 8.7l-1.3 4.8c-.1.4.4.7.7.5l5.7-3.8c.6.1 1.2.1 1.8.1 7.2 0 13-4.6 13-10.3S22.2 2 15 2z" fill="#3A1D1D"/></svg>',
    "youtube": '<svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true"><path d="M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .5 12 31 31 0 0 0 1 16.8a3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-4.8 31 31 0 0 0-.5-4.8z" fill="#fff"/><path d="M9.8 15.1V8.9l5.4 3.1z" fill="#FF0033"/></svg>',
    "instagram": '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5.5"/><circle cx="12" cy="12" r="4.2"/><circle cx="17.3" cy="6.7" r="1.1" fill="#fff" stroke="none"/></svg>',
}


def sns_fab():
    """우측 하단 버튼 하나 → 누르면 SNS 목록이 펼쳐짐 (주소가 있는 채널만)"""
    items = [("youtube", "유튜브", SITE.get("youtube")), ("instagram", "인스타그램", SITE.get("instagram")),
             ("kakao", "카카오톡 채널", SITE.get("kakao"))]
    # 카카오는 채널 주소가 비어 있어도 보여 주고, 누르면 '곧 열려요' 안내 (site.json에 주소만 넣으면 바로 연결)
    links = "".join(
        (f'<a class="fab-item {k}" href="{e(u)}" target="_blank" rel="noopener" aria-label="{n}" title="{n}">' if u else f'<a class="fab-item {k} pending" href="#" aria-label="{n}" title="{n}">')
        + f'<span class="fab-ic">{SNS_ICON[k]}</span></a>'
        for k, n, u in items if u or k == "kakao")
    if not links:
        return ""
    return ('<div class="fab no-print" id="fab"><div class="fab-menu" id="fab-menu">' + links + '</div>'
            '<button class="fab-main" type="button" aria-expanded="false" aria-controls="fab-menu" aria-label="카페인영어 SNS 채널 보기">'
            '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>'
            '</button></div>')


def video_block(video, title, hint):
    """썸네일만 먼저 보여주고, 누르면 그때 유튜브 플레이어를 불러옵니다 (페이지 속도 ↑)."""
    return (f'<div class="video-slot no-print"><div class="video-embed" data-vid="{video}">'
            f'<button class="v-facade" type="button" aria-label="{e(title)} 영상 재생">'
            f'<img src="https://i.ytimg.com/vi/{video}/hqdefault.jpg" alt="" width="480" height="360">'
            '<span class="v-play"><svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></span></button>'
            '<div id="yt"></div>'
            '<button class="v-close" aria-label="작은 화면 닫기"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg></button></div></div>'
            '<div class="vbar no-print"><span class="vbar-k">재생 속도</span><button class="spd" data-r="0.75">0.75x</button><button class="spd on" data-r="1">1x</button>'
            f'<span class="vbar-hint">{hint}</span></div>')


ICON_PLAY = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M7 4l13 8-13 8z"/></svg>'
ICON_LOOP = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/></svg>')


def seg_buttons(t, end):
    return (f'<div class="sh-btns"><button class="sh-play" data-t="{t}" data-end="{end}" data-n="1">{ICON_PLAY}{mmss(t)} 듣기</button>'
            f'<button class="sh-play" data-t="{t}" data-end="{end}" data-n="3">{ICON_LOOP}3번 반복</button></div>')


def share_block(label):
    return ('<div class="share no-print">'
            f'<div class="share-t">{label}</div>'
            '<div class="share-b"><button class="btn ghost js-share" type="button">'
            '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7"/><path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/></svg>공유하기</button>'
            '<button class="btn ghost js-copylink" type="button">'
            '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>링크 복사</button></div></div>')


def load(kind):
    import datetime
    items = []
    for f in sorted((CONTENT / kind).glob("*.json")):
        it = json.loads(f.read_text("utf-8"))
        mod = datetime.date.fromtimestamp(f.stat().st_mtime).isoformat()
        it["_mod"] = max(mod, it.get("date", mod))   # 수정일 (사이트맵 · 구조화 데이터용)
        items.append(it)
    return sorted(items, key=lambda x: (x.get("date", ""), x["id"]), reverse=True)


POSTS, THINKS = load("posts"), load("think")
AUDIO_DIR = ROOT / "audio"
AUDIO = json.loads((AUDIO_DIR / "index.json").read_text("utf-8")) if (AUDIO_DIR / "index.json").exists() else {}


def audio_map(*htmls):
    """이 페이지 예문 중 원어민 음성(mp3)이 있는 것만 {문장: 주소}"""
    found = {}
    for h in htmls:
        for m in re.findall(r'<span class="en">(.*?)</span>', h, re.S):
            t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m))).strip()
            if t in AUDIO:
                found[t] = "/audio/" + AUDIO[t]
    return found
POST_BY_ID, THINK_BY_ID = {p["id"]: p for p in POSTS}, {t["id"]: t for t in THINKS}
post_url = lambda p: f"/p/{p['id']}/"
think_url = lambda t: f"/think/{t['id']}/"
ASSET_V = hashlib.md5(b"".join(f.read_bytes() for f in sorted(ASSETS.glob("*")))).hexdigest()[:8]


def mmss(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


# ------------------------------------------------------------------ layout
def layout(title, desc, path, body, nav="", data=None, og_type="website", aside="", wide=False, og_img="/assets/og.png", seo_title=None, ld=None):
    full_title = f"{seo_title or title} | 카페인영어" if path != "/" else f"카페인영어 — {SITE['tagline']}"
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(SITE["adsense_client"])}" crossorigin="anonymous"></script>'
           if SITE.get("adsense_client") else "")
    ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={e(SITE["ga_id"])}"></script>'
          f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{e(SITE['ga_id'])}');</script>"
          if SITE.get("ga_id") else "")
    navlinks = "".join(
        f'<a href="/category/{k}/"{" class=on" if nav == k else ""}>{v}</a>' for k, v in CATS.items())
    room = f'<a class="room{" on" if nav == "notes" else ""}" href="/notes/">내 공부방<span class="badge" id="nav-badge" hidden></span></a>'
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
<meta property="og:image" content="{DOMAIN}{og_img}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{DOMAIN}{og_img}">
<link rel="preconnect" href="https://i.ytimg.com">
{ld_html(ld)}
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="icon" href="/assets/icon-192.png" sizes="192x192" type="image/png">
<meta name="theme-color" content="#F4EEE4">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="/assets/style.css?v={ASSET_V}">
{ads}{ga}
</head>
<body>
<header class="top"><div class="top-in">
  <a class="logo" href="/"><img class="logo-mark" src="/assets/icon-192.png" alt="" width="30" height="30">카페인영어 <i>CafeInEnglish</i></a>
  <nav class="nav">{navlinks}</nav>
  {room}
</div></header>
<div class="wrap{" has-side" if aside else ""}{" wide" if wide else ""}">
<main>
{body}
</main>
{f'<aside class="side no-print"><div class="side-in">{aside}</div></aside>' if aside else ""}
</div>
<footer class="foot no-print">
  <div>{e(SITE['tagline'])}</div>
  <div style="margin-top:8px"><a href="/about/">소개</a><a href="/privacy/">개인정보처리방침</a><a href="/contact/">문의</a>{f'<a href="{e(SITE["youtube"])}" target="_blank" rel="noopener">유튜브</a>' if SITE.get("youtube") else ""}{f'<a href="{e(SITE["instagram"])}" target="_blank" rel="noopener">인스타그램</a>' if SITE.get("instagram") else ""}</div>
</footer>
{sns_fab()}
{pdata}
<script src="/assets/app.js?v={ASSET_V}" defer></script>
</body>
</html>
"""


def card(href, chips, title, sub):
    chip_html = "".join('<span class="chip %s">%s</span>' % (c, e(t)) for c, t in chips)
    return f'<a class="card" href="{href}"><div class="chips">{chip_html}</div><h3>{e(title)}</h3><p>{e(sub)}</p></a>'


def post_card(p):
    return card(post_url(p), [(p["cat"], CATS[p["cat"]]), (p["cat"], p.get("sub", ""))], p["title"],
                f"{p.get('lead', '')} · 퀴즈 {len(p['quiz'])}문제")


def think_card(t):
    return card(think_url(t), [("think", "사유의 문장"), ("video", t["speaker"])], t["title"],
                f"필사할 문장 {len(t['quotes'])}개")


PRINT_BTN = """
<div class="no-print" style="margin-top:22px">
  <button class="btn ghost js-print" id="print-btn">출력해서 복습하기 (PDF 저장)</button>
  <p class="lead" style="font-size:13px;text-align:center;margin-top:6px">인쇄 창에서 대상을 <b>'PDF로 저장'</b>으로 고르면 파일로 받을 수 있어요</p>
</div>"""
CIRC = ["①", "②", "③", "④", "⑤"]


def ws_head(title, sub, video, path):
    qrs = ""
    if video:
        qrs += f'<div class="ws-qr">{qr_svg("https://youtu.be/" + video)}<div>영상<br>다시 보기</div></div>'
    qrs += f'<div class="ws-qr">{qr_svg(DOMAIN + path + "?src=print")}<div>퀴즈·오답노트<br>다시 풀기</div></div>'
    return (f'<div class="ws-head"><div><div class="brand">카페인영어 CafeInEnglish · 복습 노트</div>'
            f'<h1 style="margin:4px 0 0">{e(title)}</h1><div class="date">{e(sub)}</div>'
            f'<div class="date" style="margin-top:6px">공부한 날: ______ / ______</div></div>'
            f'<div class="ws-qrs">{qrs if segno else ""}</div></div>')


# ------------------------------------------------------------------ pages
def similar_posts(p, n=4):
    """같은 카테고리·세부 분류 우선, 최신 순으로 관련 글 고르기"""
    def score(o):
        return (2 if o["cat"] == p["cat"] else 0) + (1 if o.get("sub") == p.get("sub") else 0)
    others = [o for o in POSTS if o["id"] != p["id"]]
    others.sort(key=lambda o: (score(o), o.get("date", ""), o["id"]), reverse=True)
    return others[:n]


def related_links(p):
    links = list(p.get("related", []))
    if p.get("think") in THINK_BY_ID:
        links.append({"label": "이 영상 문장 필사하기", "href": think_url(THINK_BY_ID[p["think"]])})
    for o in similar_posts(p, 4):
        links.append({"label": o["title"], "href": post_url(o)})
    return links[:4]


def add_heading_ids(body_html, toc):
    """본문 <h2>에 id를 붙이고 목차(toc)에 추가"""
    def sub(m):
        n = len(toc) + 1
        text = re.sub(r"<[^>]+>", "", m.group(2))
        toc.append((f"s{n}", text))
        return f'<h2{m.group(1)} id="s{n}">{m.group(2)}</h2>'
    return re.sub(r"<h2([^>]*)>(.*?)</h2>", sub, body_html)


def toc_html(toc, quiz_label="퀴즈 풀기"):
    items = "".join(f'<li><a href="#{i}">{e(t)}</a></li>' for i, t in toc)
    return f'<ol class="toc">{items}<li class="q"><a href="#quiz-sec">{quiz_label}</a></li></ol>'


def side_common():
    yt = (f'<div class="side-box"><h4>카페인영어 유튜브</h4><a class="btn ghost" href="{e(SITE["youtube"])}" target="_blank" rel="noopener">▶ 채널 구경하기</a></div>'
          if SITE.get("youtube") else "")
    kk = (f'<div class="side-box"><h4>매일 한 잔</h4><a class="btn kakao" href="{e(SITE["kakao"])}" target="_blank" rel="noopener">카톡으로 매일 받기</a></div>'
          if SITE.get("kakao") else "")
    return kk + yt


def page_post(p):
    url = post_url(p)
    video = p.get("video")
    parts = [f'<span class="chip {p["cat"]}">{CATS[p["cat"]]}</span><span class="chip {p["cat"]}">{e(p.get("sub", ""))}</span>',
             f'<h1>{e(p["title"])}</h1><p class="lead">{e(p.get("lead", ""))}</p><p class="date-line">{e(p.get("date", ""))}</p>']
    toc_slot = len(parts)
    if video:
        parts.append(video_block(video, p["title"], "표현의 <b>듣기</b>·<b>3번 반복</b>으로 따라 말해 보세요"))
    toc = []
    parts.append(add_heading_ids(p.get("body_html", ""), toc))
    if p.get("expressions"):
        toc.append(("expr", p.get("expressions_heading", "오늘의 표현")))
        parts.append(f'<h2 id="expr">{e(p.get("expressions_heading", "오늘의 표현"))}</h2>')
        for xi, x in enumerate(p["expressions"]):
            ts = ""
            shadow = ""
            if video and "t" in x:
                end = x.get("end", x["t"] + 4)
                say = f'<div class="sh-say"><span class="lbl">따라 말하기</span><b>{e(x["say"])}</b></div>' if x.get("say") else ""
                tips = "".join(f"<li>{e(tp)}</li>" for tp in x.get("tips", []))
                shadow = (f'<div class="shadow">{seg_buttons(x["t"], end)}'
                          f'{say}{f"<ul class=sh-tips>{tips}</ul>" if tips else ""}</div>')
            toc.append((f"x{xi + 1}", x["en"]))
            parts.append(f"""<div class="box xp" id="x{xi + 1}">
  <h3>{e(x['en'])}{ts}</h3><div>{e(x['ko'])}</div>
  <div class="orig">{e(x['orig'])}</div>
  {shadow}
  <ul class="ex"><li><span class="en">{e(x['ex'])}</span><span class="ko">{e(x['exKo'])}</span></li></ul>
  <div class="memo" style="margin-bottom:0"><b class="lbl">연상법</b> {e(x['memo'])}</div>
</div>""")
    if p.get("think") in THINK_BY_ID:
        parts.append(f'<div class="think-box"><b>이 영상 속 마음에 남는 문장</b>은 <a href="{think_url(THINK_BY_ID[p["think"]])}">사유의 문장</a>에서 필사하고 복기할 수 있어요.</div>')
    parts.append('<h2 class="quiz-h" id="quiz-sec">오늘 배운 거 확인하기</h2><div id="quiz"></div>')
    parts.append(share_block("같이 공부할 친구에게 이 글 보내기"))
    parts.append(PRINT_BTN)
    # 출력용 문제지 (화면에서는 숨김)
    qs = "".join(
        f'<div class="ws-q"><b>{i + 1}. {e(q["q"])}</b>'
        + (f'<br><span>{e(q["sub"])}</span>' if "___" in q.get("sub", "") else "")
        + "<br>" + "".join(f'<span class="o">{CIRC[k]} {e(o)}</span>' for k, o in enumerate(q["options"])) + "</div>"
        for i, q in enumerate(p["quiz"]))
    key = "".join(f'<li><b>{CIRC[q["answer"]]} {e(q["options"][q["answer"]])}</b> — {e(q["explain"])}<br>연상법 · {e(q["mnemonic"])}</li>' for q in p["quiz"])
    parts.append(f"""<div class="print-only ws"><div style="break-before:page"></div>
{ws_head("확인 문제", p["title"], video, url)}
<p style="font-size:13px">본문을 다시 읽은 뒤, 정답에 ○ 표시해 보세요. 정답과 연상법은 맨 아래에 있어요.</p>{qs}
<h2>오늘의 표현, 직접 써 보기</h2><div class="ws-label">오늘 배운 표현으로 나만의 문장 2개 만들기</div>
<div class="ws-line"></div><div class="ws-line"></div><div class="ws-line"></div><div class="ws-line"></div>
<div class="ws-key"><b>정답과 연상법</b><ol>{key}</ol></div>
<p style="font-size:12px;color:#555">{DOMAIN.replace("https://", "")} · 매일 표현 하나, 같이 공부해요</p></div>""")
    parts.append('<h2 class="rel-h no-print">같이 보면 좋은 글</h2><div class="cards rel no-print">'
                 + "".join(post_card(o) for o in similar_posts(p, 4)) + "</div>")
    parts.insert(toc_slot, f'<details class="toc-m no-print"><summary>목차 · 퀴즈 바로가기</summary>{toc_html(toc)}</details>')
    links = related_links(p)
    link_items = "".join('<li><a href="%s">%s</a></li>' % (l["href"], e(l["label"])) for l in links)
    aside = (f'<div class="side-box"><h4>이 글의 목차</h4>{toc_html(toc)}</div>'
             f'<div class="side-box"><h4>복습하기</h4><a class="btn ghost" href="#quiz-sec">퀴즈 풀기</a>'
             f'<a class="btn ghost" href="/notes/">내 공부방<span class="n-pill js-notes-count"></span></a>'
             f'<button class="btn ghost js-print">출력 · PDF 저장</button></div>'
             + (f'<div class="side-box"><h4>이어서 보기</h4><ul class="side-links">{link_items}</ul></div>' if links else "")
             + side_common())
    data = {"type": "post", "id": p["id"], "title": p["title"], "url": url, "cat": p["cat"], "catName": CATS[p["cat"]],
            "quiz": p["quiz"], "links": links, "kakao": SITE.get("kakao", ""), "audio": audio_map("\n".join(parts))}
    og = p.get("og") or {}
    xs = p.get("expressions") or [{}]
    data["share"] = og.get("en") or xs[0].get("en") or ""
    img = og_image("p-" + p["id"], CATS[p["cat"]], og.get("en") or xs[0].get("en") or p["title"],
                   og.get("ko") or p.get("lead", ""))
    desc = p.get("description", p.get("lead", ""))
    ld = ld_article(p["title"], desc, url, img, p.get("date", ""), p["_mod"], CATS[p["cat"]],
                    [("홈", "/"), (CATS[p["cat"]], f"/category/{p['cat']}/"), (p["title"], url)])
    return layout(p["title"], desc, url, "\n".join(parts), p["cat"], data, "article", aside, og_img=img,
                  seo_title=p.get("seo_title"), ld=ld)


def q_end(q):
    """끝 시간이 없으면 단어 수로 대략 계산 (초당 2.4단어 + 여유 1.2초)"""
    return q.get("end") or round(q["t"] + len(q["en"].split()) / 2.4 + 1.2, 1)


def page_think(t):
    url = think_url(t)
    cards = []
    for i, q in enumerate(t["quotes"]):
        cards.append(f"""<div class="quote no-print" id="q{i + 1}" data-id="{t['id']}:{i}" data-i="{i}">
  <div class="meta"><span>문장 {i + 1} / {len(t['quotes'])}</span></div>
  <p class="en">{e(q['en'])}</p><p class="ko">{e(q['ko'])}</p>
  {seg_buttons(q['t'], q_end(q)) if t.get('video') else ''}
  <div class="think-box"><b class="lbl">생각해 보기</b> {e(q['think'])}<span class="ask">{e(q['ask'])}</span></div>
  <div class="tabs"><button class="on" data-mode="copy">필사하기</button><button data-mode="blank">빈칸 복기</button></div>
  <div class="pane"></div>
  <div style="margin-top:14px;font-size:14px;font-weight:700">나의 한 줄</div>
  <textarea class="note" placeholder="이 문장이 나에게 주는 의미를 한 줄로 남겨 보세요" style="min-height:60px;margin-top:6px"></textarea>
  <div class="row"><button class="btn ghost save-note">저장</button></div>
</div>""")
    ws = "".join(f"""<div class="ws-quote"><p class="en">{i + 1}. {e(q['en'])}</p><p class="ko">{e(q['ko'])}</p>
<div class="ws-label">따라 쓰기</div><div class="ws-line"></div><div class="ws-line"></div>
<div class="ws-label">Q. {e(q['ask'])}</div><div class="ws-line"></div></div>""" for i, q in enumerate(t["quotes"]))
    post = POST_BY_ID.get(t.get("post"))
    body = f"""<div class="no-print">
<span class="chip think">사유의 문장</span><span class="chip video">{e(t['speaker'])}</span>
<h1>{e(t['title'])}</h1>
<p class="lead">따라 쓰고(필사), 빈칸으로 다시 떠올리고(복기), 나의 한 줄을 남겨 보세요.</p>
</div>
{video_block(t["video"], t["title"], "문장마다 <b>듣기</b>·<b>3번 반복</b>으로 소리까지 익혀요") if t.get("video") else ""}
{f'<a class="btn ghost no-print" href="{post_url(post)}">이 영상의 영어표현 먼저 보기</a>' if post else ""}
{"".join(cards)}
{share_block("마음에 남는 문장, 친구와 같이 필사해요")}
{PRINT_BTN}
<div class="print-only ws">{ws_head("필사 노트 — " + t["title"], t["speaker"], t.get("video"), url)}{ws}</div>
<div class="cq-cta no-print" style="margin-top:16px">
  <a class="btn primary" href="/notes/#copy">내 공부방에서 필사 노트 보기</a>
  {f'<a class="btn kakao" href="{e(SITE["kakao"])}" target="_blank" rel="noopener">매일 아침 문장 하나, 카톡으로 받기</a>' if SITE.get("kakao") else ""}
</div>"""
    data = {"type": "think", "id": t["id"], "title": t["title"], "speaker": t["speaker"], "url": url,
            "quotes": [{"en": q["en"], "ko": q["ko"], "blanks": q["blanks"]} for q in t["quotes"]]}
    qlist = "".join(f'<li><a href="#q{i + 1}">{e(q["en"][:42] + ("…" if len(q["en"]) > 42 else ""))}</a></li>' for i, q in enumerate(t["quotes"]))
    aside = (f'<div class="side-box"><h4>문장 목록</h4><ol class="toc">{qlist}</ol></div>'
             f'<div class="side-box"><h4>복습하기</h4><a class="btn ghost" href="/notes/#copy">내 필사 노트</a>'
             f'<button class="btn ghost js-print">필사 노트 출력</button>'
             + (f'<a class="btn ghost" href="{post_url(post)}">영상 표현 보기</a>' if post else "") + '</div>' + side_common())
    og = t.get("og") or {}
    shortest = min(t["quotes"], key=lambda q: len(q["en"]))["en"]
    data["share"] = og.get("en") or shortest
    img = og_image("t-" + t["id"], "사유의 문장 · 필사", og.get("en") or shortest, og.get("ko") or t["title"], "듣고 · 따라 쓰고 · 빈칸으로 복기")
    ld = ld_article(t["title"], t.get("description", ""), url, img, t.get("date", ""), t["_mod"], "사유의 문장",
                    [("홈", "/"), ("사유의 문장", "/category/think/"), (t["title"], url)])
    return layout(t["title"] + " — 필사하기", t.get("description", ""), url, body, "think", data, "article", aside, og_img=img,
                  seo_title=t.get("seo_title"), ld=ld)


def page_category(cat):
    url = f"/category/{cat}/"
    if cat == "think":
        cards = "".join(think_card(t) for t in THINKS)
        body = (f'<h1>{CATS[cat]}</h1><p class="lead">{CAT_LEAD[cat]}</p><div class="cards">{cards}</div>'
                '<p class="a-intro">필사한 문장은 <a href="/notes/#copy">내 공부방</a>에 모여요.</p>')
    else:
        items = [p for p in POSTS if p["cat"] == cat]
        cards = "".join(post_card(p) for p in items) or '<div class="empty"><p>곧 첫 글이 올라와요.</p></div>'
        body = f'<h1>{CATS[cat]}</h1><p class="lead">{CAT_LEAD[cat]}</p><div class="cards">{cards}</div>'
    return layout(CATS[cat], CAT_LEAD[cat], url, body, cat, wide=True)


def page_home():
    today = SITE.get("today") or {}
    tp = POST_BY_ID.get(today.get("post")) or next((p for p in POSTS if p["cat"] == "expr"), POSTS[0])
    t_en = today.get("en") or tp["title"]
    t_ko = today.get("ko") or tp.get("lead", "")
    t_desc = today.get("desc") or ""
    words = t_en.split(" ")
    phrase = e(" ".join(words[:-1])) + (" " if len(words) > 1 else "") + f'<span class="hl">{e(words[-1])}</span>'
    vp = next((p for p in POSTS if p["cat"] == "video"), None)
    feature = ""
    if vp:
        pills = "".join(f"<span>{e(x['en'])}</span>" for x in vp.get("expressions", [])[:3])
        thumb = f'<img src="https://i.ytimg.com/vi/{vp["video"]}/hqdefault.jpg" alt="" loading="lazy">' if vp.get("video") else ""
        feature = (f'<a class="a-feature" href="{post_url(vp)}"><div class="a-thumb">{thumb}<span class="a-play">'
                   '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2A1A12" stroke-width="2.4" stroke-linejoin="round"><path d="M8 5l11 7-11 7z"/></svg></span></div>'
                   f'<div class="k">영상으로 배우기</div><h3>{e(vp["title"])}</h3><div class="a-pills">{pills}</div></a>')
    tiles = "".join(f'<a class="a-tile" href="/category/{k}/"><span class="n">0{n}</span><b>{v}</b><span>{TILE_SUB[k]}</span></a>'
                    for n, (k, v) in enumerate(CATS.items(), 1))
    shown = {tp["id"]} | ({vp["id"]} if vp else set())
    latest = "".join(post_card(p) for p in [p for p in POSTS if p["id"] not in shown][:6])
    thinks = "".join(think_card(t) for t in THINKS[:3])
    body = f"""<section class="a-hero">
  <div>
    <div class="a-kicker">오늘의 한 잔 · {CATS[tp["cat"]]}</div>
    <h1 class="a-phrase">{phrase}</h1>
    <p class="a-mean">{e(t_ko)}</p>
    {f'<p class="a-desc">{e(t_desc)}</p>' if t_desc else ""}
    <div class="a-btns"><a class="btn primary" href="{post_url(tp)}">글 읽고 퀴즈 풀기</a><a class="btn ghost" href="/notes/">내 공부방</a></div>
  </div>
  {feature}
</section>
<nav class="a-tiles" aria-label="카테고리">{tiles}</nav>
{f'<div class="a-head"><h2>새로 올라온 글</h2></div><div class="cards">{latest}</div>' if latest else ""}
{f'<div class="a-head" style="margin-top:36px"><h2>사유의 문장</h2><a href="/category/think/">전체 보기</a></div><div class="cards">{thinks}</div>' if thinks else ""}
"""
    ld = [{"@type": "WebSite", "name": "카페인영어 CafeInEnglish", "alternateName": "카페인영어", "url": DOMAIN + "/", "inLanguage": "ko"}, ORG]
    return layout(SITE["name"], SITE["tagline"], "/", body, wide=True, ld=ld)


def page_notes():
    body = ('<h1>내 공부방</h1><p class="lead">틀린 문제와 필사한 문장이 여기에 모여요. '
            '기록은 이 기기의 브라우저에만 저장돼요.</p>'
            '<h2 id="wrong">오답노트</h2><p class="lead" style="font-size:15px">다시 풀어서 맞히면 \'졸업\'해요.</p><div id="notes-root"></div>'
            '<h2 id="copy">필사 노트 (<span id="copy-count">0</span>)</h2><div id="copy-notes"></div>')
    return layout("내 공부방", "퀴즈 오답노트와 필사 노트를 모아 다시 복습하는 나만의 공부방", "/notes/", body, "notes",
                  {"type": "notes", "kakao": SITE.get("kakao", "")}, wide=True)


def page_static(slug, title, desc, inner):
    return layout(title, desc, f"/{slug}/", f'<h1>{e(title)}</h1><div class="prose">{inner}</div>')


EMAIL = SITE.get("contact_email") or ""
email_html = f'<a href="mailto:{e(EMAIL)}">{e(EMAIL)}</a>' if EMAIL else "(문의 이메일 준비 중)"
def _about_card():
    today = SITE.get("today") or {}
    tp = POST_BY_ID.get(today.get("post")) or next((p for p in POSTS if p["cat"] == "expr"), POSTS[0])
    en = today.get("en") or tp["title"]
    words = en.split(" ")
    phrase = e(" ".join(words[:-1])) + (" " if len(words) > 1 else "") + f'<span class="hl">{e(words[-1])}</span>'
    return (f'<a class="today-card" href="{post_url(tp)}"><div><div class="tc-k">오늘의 한 잔 · {CATS[tp["cat"]]}</div>'
            f'<div class="tc-en">{phrase}</div><div class="tc-ko">{e(today.get("ko") or tp.get("lead", ""))}</div></div>'
            '<span class="tc-go" aria-hidden="true"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span></a>'
            '<p class="tc-note">거창한 계획 말고,<br class="m-br"> 커피 한 잔 마시는 마음으로 시작해보세요!</p>')


ABOUT_CARD = _about_card()
ABOUT = f"""
<p class="about-tag">매일 조금씩, 깊게 스며드는 CafeInEnglish</p>
<p>안녕하세요, 유튜브 <b>카페인영어 CafeInEnglish</b>예요.</p>
<p>저도 한국에서 영어를 배운 평범한 학생이었어요. 외우고, 시험 보고, 취업을 위해 점수를 만들고. 그렇게 오랫동안 영어를 '공부'해 왔는데, 어느 날 돌아보니 제게 남은 건 점수였지 언어가 아니더라고요.</p>
<p>그때부터 진짜 영어를 하고 싶어졌어요. 문법 문제가 아니라, 사람들이 실제로 쓰는 말로 생각하고 이야기하는 영어요.</p>
<p>저는 지금 영주권을 받고 미국 이민을 앞두고 있어요. 낯선 곳에서의 새로운 도전을 준비하면서 느끼는 건, 영어는 결국 <b>생각을 넓혀주는 도구</b>라는 거예요. 새로운 언어로 세상을 보면, 보이는 것도 달라지니까요.</p>
<p>카페인영어는 그 여정을 기록하고 나누는 공간이에요. 셀럽 인터뷰와 연설 속 살아있는 표현으로 매일 조금씩, 하지만 깊게. 영어라는 언어로 생각을 넓히면서 같이 성장해요. <b>재미있게, 그리고 쉽게!</b></p>
<div class="brand-c"><img src="/assets/icon-192.png" alt="" width="64" height="64"><div><b>C.</b> 매일 한 잔의 커피처럼, 대화 속 진짜 영어를 꾸준히.<br><span>오늘의 한 문장에 마침표를 찍는 곳, CafeInEnglish.</span></div></div>
<h2>이런 걸 할 수 있어요</h2>
<div class="feats"><div class="feat"><span class="feat-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 5l11 7-11 7z"/></svg></span><div><b>영상으로 배우기</b><p>카페인영어 영상 속 표현을 실제 장면과 함께 익혀요.</p></div></div><div class="feat"><span class="feat-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16M4 12h11M4 18h7"/></svg></span><div><b>영어표현 · 영어꿀팁</b><p>새 표현과 헷갈리는 표현부터 회화, 단어, 듣기 요령까지 담았어요.</p></div></div><div class="feat"><span class="feat-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3 8-8"/><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"/></svg></span><div><b>퀴즈와 오답노트</b><p>글 끝 퀴즈로 확인하고, 틀린 문제는 내 공부방에 자동으로 모여요.</p></div></div><div class="feat"><span class="feat-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg></span><div><b>사유의 문장</b><p>마음에 남는 문장을 따라 쓰고, 빈칸으로 다시 떠올려요.</p></div></div><div class="feat"><span class="feat-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V3h12v6"/><rect x="6" y="14" width="12" height="7" rx="1"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/></svg></span><div><b>출력해서 복습하기</b><p>글마다 PDF 복습지로 저장하거나 인쇄해서 볼 수 있어요.</p></div></div></div>
{ABOUT_CARD}
"""
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
def _contact():
    from urllib.parse import quote
    icons = {
        "bulb": '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9V16h7v-2.1A6 6 0 0 0 12 3z"/>',
        "bug": '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
        "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
        "hand": '<path d="M17 11V6a2 2 0 0 0-4 0v5M13 10V4a2 2 0 0 0-4 0v7M9 10.5V6a2 2 0 0 0-4 0v8a8 8 0 0 0 16 0v-3a2 2 0 0 0-4 0"/>',
    }
    svg = lambda d, n=22: f'<svg width="{n}" height="{n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{d}</svg>'
    arrow = svg('<path d="M5 12h14M13 6l6 6-6 6"/>', 18)
    kinds = [("bulb", "표현·콘텐츠 제안", "궁금한 표현, 다뤄줬으면 하는 영상"),
             ("bug", "오류 제보", "틀린 해설, 화면·기능 오류"),
             ("shield", "저작권 요청", "인용된 콘텐츠의 수정·삭제 요청"),
             ("hand", "협업·제휴", "콘텐츠 협업, 광고, 강의 제안")]
    tiles = "".join(
        f'<a class="ct-tile" href="mailto:{e(EMAIL)}?subject={quote("[" + t + "] ")}"><span class="ct-i">{svg(icons[i])}</span>'
        f'<span class="ct-t"><b>{t}</b><span>{d}</span></span><span class="ct-go">{arrow}</span></a>' for i, t, d in kinds)
    copy_icon = svg('<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>', 16)
    return (f'<p class="lead">어떤 이야기든 편하게 보내주세요.</p><div class="ct-grid">{tiles}</div>'
            f'<div class="ct-mail"><span class="ct-k">이메일</span><span class="ct-addr">{e(EMAIL)}</span>'
            f'<button class="ct-copy" data-copy="{e(EMAIL)}">{copy_icon}<span>주소 복사</span></button></div>')


CONTACT = _contact() if EMAIL else "<p>(문의 이메일 준비 중)</p>"


def page_404():
    return layout("페이지를 찾을 수 없어요", "요청한 페이지가 없어요", "/404.html",
                  '<div class="empty"><p>찾으시는 페이지가 없어요.<br>주소가 바뀌었거나 삭제된 글일 수 있어요.</p></div>'
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
    if (ROOT / "images").exists():
        shutil.copytree(ROOT / "images", OUT / "images", dirs_exist_ok=True)
    if AUDIO_DIR.exists():
        shutil.copytree(AUDIO_DIR, OUT / "audio", dirs_exist_ok=True, ignore=shutil.ignore_patterns("index.json"))
    global LASTMOD
    LASTMOD = {post_url(p): p["_mod"] for p in POSTS}
    LASTMOD.update({think_url(t): t["_mod"] for t in THINKS})
    newest = max(LASTMOD.values()) if LASTMOD else None
    if newest:
        LASTMOD["/"] = newest
        for c in CATS:
            LASTMOD[f"/category/{c}/"] = max([v for p in POSTS if p["cat"] == c for v in [p["_mod"]]] or [newest]) if c != "think" else max(t["_mod"] for t in THINKS)
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
        + "".join(f"  <url><loc>{DOMAIN}{u}</loc>" + (f"<lastmod>{LASTMOD[u]}</lastmod>" if u in LASTMOD else "") + "</url>\n" for u in pages)
        + "</urlset>\n", "utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n", "utf-8")
    (OUT / "CNAME").write_text(DOMAIN.replace("https://", "") + "\n", "utf-8")
    (OUT / ".nojekyll").write_text("", "utf-8")
    if SITE.get("adsense_client"):
        pub = SITE["adsense_client"].replace("ca-", "")
        (OUT / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", "utf-8")
    after = {f for f in OUT.rglob("*") if f.is_file()}
    written = {OUT / "assets" / f.name for f in ASSETS.glob("*")} | {OUT / "audio" / f.name for f in AUDIO_DIR.glob("*.mp3")} | {OUT / "images" / f.name for f in (ROOT / "images").glob("*")} | {f for f in after if f.stat().st_mtime >= START}
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

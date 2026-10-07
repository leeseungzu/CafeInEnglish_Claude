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
CAT_SEO = {  # 카테고리 페이지 검색용 제목 · 설명
    "video": ("영상으로 배우는 영어 - 카페인영어 영상 속 표현 정리와 퀴즈",
              "카페인영어 유튜브 영상 한 편에서 실제로 쓰는 영어 표현을 뽑아 뜻, 예문, 발음과 함께 정리하고 퀴즈로 확인해요."),
    "expr": ("원어민 영어표현 - 뜻, 예문, 비슷한 표현, 헷갈리는 표현 정리",
             "Sounds good, My bad, I'm on it처럼 원어민이 매일 쓰는 영어표현을 뜻, 예문, 비슷한 표현, 자주 하는 실수와 연상법, 퀴즈로 정리했어요."),
    "tip": ("영어꿀팁 - 회화, 발음, 듣기, 콩글리시까지 바로 써먹는 영어 팁",
            "한국인이 자주 틀리는 영어 회화, 발음, 듣기, 콩글리시를 쉽게 풀어 정리했어요. 식당, 카페, 병원, 화상회의에서 바로 쓰는 문장과 퀴즈까지."),
    "think": ("영어 명언 필사 - 사유의 문장, 연설과 인터뷰 속 영어 문장",
              "손흥민, 젠슨 황, 순다르 피차이의 영어 연설과 인터뷰 속 곱씹을 문장을 영상으로 듣고, 따라 쓰고, 빈칸으로 다시 떠올려 보세요."),
}
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


EN_FONT = ROOT / "fonts" / "PlusJakartaSans-Bold.ttf"
OG_BG = [("#FFF3EC", "#FFE0CF"), ("#EEF5FF", "#D6E6FF"), ("#F4F0FF", "#E2D8FF"), ("#EFFAF3", "#D2F0DE"), ("#FFF9E9", "#FCEBB6")]


def og_chat(name, chip, en, ko, chat, icon, key_id):
    """C안 공유 이미지(1200×630): 왼쪽 표현 + 오른쪽 실제 대화 카드 + 3D 아이콘. 카톡·SNS 미리보기용."""
    if not (Image and FONT.exists()):
        return "/assets/og.png"
    from PIL import ImageFilter
    W, H, PAD = 1200, 630, 72
    INK, BODY, MUTED, LIME = "#191F28", "#333D4B", "#6B7684", "#CDEB5B"
    c1, c2 = OG_BG[int(hashlib.md5(key_id.encode()).hexdigest(), 16) % len(OG_BG)]
    hx = lambda c: tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    g = Image.new("RGB", (2, 2)); g.putdata([hx(c1), hx(c1), hx(c1), hx(c2)])
    im = g.resize((W, H), Image.BILINEAR).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    ImageDraw.Draw(glow).ellipse((560, -220, 1260, 380), fill=(255, 255, 255, 170))
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(im)
    enf = lambda sz: ImageFont.truetype(str(EN_FONT), sz) if EN_FONT.exists() else _font(sz, 800)
    # 브랜드 + 칩
    d.rounded_rectangle((PAD, 56, PAD + 52, 108), 14, fill=INK)
    d.text((PAD + 12, 82), "C", font=_font(36, 800), fill="#FFFFFF", anchor="lm")
    d.ellipse((PAD + 35, 88, PAD + 43, 96), fill=LIME)
    d.text((PAD + 68, 82), "카페인영어 CafeInEnglish", font=_font(26, 700), fill=INK, anchor="lm")
    cf = _font(22, 700); cw = d.textlength(chip, font=cf)
    d.rounded_rectangle((PAD, 150, PAD + cw + 32, 190), 20, fill=(255, 255, 255, 200))
    d.text((PAD + 16, 170), chip, font=cf, fill=BODY, anchor="lm")
    # 큰 영어 표현 (왼쪽 칸, 최대 3줄)
    maxw = 470
    for size in range(84, 40, -4):
        bf = enf(size); lines = _wrap(d, en, bf, maxw)
        if len(lines) <= 3 and all(d.textlength(l, font=bf) <= maxw for l in lines) and len(lines) * size * 1.15 <= 250:
            break
    lh = int(size * 1.15); y = 222 + (250 - len(lines) * lh) // 2
    for i, l in enumerate(lines):
        lw = d.textlength(l, font=bf)
        if i == len(lines) - 1:
            d.rectangle((PAD - 4, y + int(size * .78), PAD + lw + 4, y + int(size * 1.02)), fill=LIME)
        d.text((PAD, y), l, font=bf, fill=INK)
        y += lh
    kf = _font(32, 700)
    while d.textlength(ko, font=kf) > maxw and len(ko) > 4:
        ko = ko[:-2].rstrip() + "…"
    d.text((PAD, 492), ko, font=kf, fill=BODY)
    d.text((PAD, 560), "cafeinenglish.com", font=_font(24, 600), fill=MUTED)
    # 오른쪽 대화 카드 (그림자 → 카드)
    cx0, cx1, cy0 = 600, 1140, 130
    qf, af, lf = _font(27, 500), _font(31, 700), _font(20, 600)
    bw = cx1 - cx0 - 72
    ql = _wrap(d, chat.get("q", ""), qf, bw - 40) if chat.get("q") else []
    # 내 대답: 단어마다 색 (핵심 표현은 라임)
    a, key = chat["a"], chat.get("key", "")
    i0 = a.find(key) if key else -1
    words = []
    pos = 0
    for w in a.split(" "):
        st = a.find(w, pos); pos = st + len(w)
        words.append((w, i0 >= 0 and st < i0 + len(key) and pos > i0))
    alines, cur = [], []
    for w in words:
        t = " ".join(x for x, _ in cur + [w])
        if cur and d.textlength(t, font=af) > bw - 44:
            alines.append(cur); cur = [w]
        else:
            cur.append(w)
    alines.append(cur)
    qh = len(ql) * 38 + 30 if ql else 0
    ah = len(alines) * 42 + 30
    ch = 46 + 30 + qh + (18 if ql else 0) + ah + 26 + 34
    cy1 = cy0 + ch
    sh = Image.new("RGBA", (W, H), (30, 40, 70, 0))
    ImageDraw.Draw(sh).rounded_rectangle((cx0 + 24, cy0 + 40, cx1 - 24, cy1 + 24), 36, fill=(30, 40, 70, 30))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(22)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((cx0, cy0, cx1, cy1), 36, fill=(255, 255, 255, 235))
    y = cy0 + 36
    d.text((cx0 + 36, y), "실제 대화에선 이렇게", font=lf, fill="#8B95A1")
    y += 46
    if ql:
        qw = max(d.textlength(l, font=qf) for l in ql) + 40
        d.rounded_rectangle((cx0 + 36, y, cx0 + 36 + qw, y + qh), 24, fill="#F2F4F6")
        for k, l in enumerate(ql):
            d.text((cx0 + 56, y + 15 + k * 38), l, font=qf, fill=BODY)
        y += qh + 18
    aw = max(d.textlength(" ".join(x for x, _ in ln), font=af) for ln in alines) + 44
    d.rounded_rectangle((cx1 - 36 - aw, y, cx1 - 36, y + ah), 26, fill=INK)
    for k, ln in enumerate(alines):
        x = cx1 - 36 - aw + 22
        for w, hit in ln:
            d.text((x, y + 13 + k * 42), w, font=af, fill=LIME if hit else "#FFFFFF")
            x += d.textlength(w + " ", font=af)
    y += ah + 14
    d.text((cx1 - 40, y), ko, font=lf, fill="#8B95A1", anchor="ra")
    # 3D 아이콘 (카드 왼쪽 아래에 걸치게)
    ip = ASSETS / "icons" / f"{icon}.webp"
    if icon and ip.exists():
        ic = Image.open(ip).convert("RGBA").resize((150, 150), Image.LANCZOS)
        shd = Image.new("RGBA", (W, H), (30, 40, 60, 0))
        alpha = ic.split()[3].point(lambda v: v * .28)
        shd.paste((30, 40, 60, 255), (cx0 - 30, cy1 - 70 + 14), alpha)
        im = Image.alpha_composite(im, shd.filter(ImageFilter.GaussianBlur(10)))
        im.alpha_composite(ic, (cx0 - 36, min(cy1 - 70, H - 160)))
    out = OUT / "og" / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(out, optimize=True)
    return f"/og/{name}.png"


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


SERIF_I = ROOT / "fonts" / "LiberationSerif-BoldItalic.ttf"


def _wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def _spaced(d, xy, text, font, fill, spacing, anchor_right=False):
    """글자 사이를 띄워서 쓰기 (라벨용)"""
    w = sum(d.textlength(c, font=font) for c in text) + spacing * (len(text) - 1)
    x, y = xy
    if anchor_right:
        x -= w
    for c in text:
        d.text((x, y), c, font=font, fill=fill)
        x += d.textlength(c, font=font) + spacing


THEMES = {  # 배경, 글자, 핵심 단어 스타일
    "dark": ("#2A1A12", "#F4EEE4", "lime"),
    "lime": ("#CDEB5B", "#2A1A12", "underline"),
    "cream": ("#EFE7DA", "#2A1A12", "marker"),
    "olive": ("#3B4430", "#F4EEE4", "lime"),
}


def thumb_image(name, theme, ko, text, key):
    """목록 카드용 썸네일 (1안 · 빅 타이포): 색 블록 + 아주 큰 표현 + 핵심 단어 강조"""
    if not (Image and FONT.exists()):
        return None
    W, H, PAD = 960, 504, 56
    bg, fg, style = THEMES[theme]
    LIME, INK = "#CDEB5B", "#2A1A12"
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    kf = _font(44, 700)
    words = text.split()
    kw = key.split()
    keyidx = set()
    for i in range(len(words) - len(kw) + 1):
        if words[i:i + len(kw)] == kw:
            keyidx = set(range(i, i + len(kw)))
            break
    maxw = W - PAD * 2 - (20 if style == "pill" else 0)
    for size in range(132, 50, -4):
        f = _font(size, 900)
        lines = _wrap(d, text, f, maxw)
        if len(lines) <= 3 and len(lines) * size * 0.98 <= H - 200 and all(d.textlength(l, font=f) <= maxw for l in lines):
            break
    lh = int(size * 0.98)
    block = 44 * 1.2 + 18 + lh * len(lines)
    y0 = int((H - block) / 2) + 6
    d.text((PAD, y0), ko, font=kf, fill=fg if theme != "dark" else "#D9CDBE")
    y = int(y0 + 44 * 1.2 + 18 - size * .04)
    wi = 0
    for ln in lines:
        x = PAD
        lw = ln.split()
        # 같은 줄의 핵심 단어 구간
        span = [j for j in range(len(lw)) if wi + j in keyidx]
        if span and style == "marker":
            xs = x + d.textlength(" ".join(lw[:span[0]]) + (" " if span[0] else ""), font=f)
            xe = x + d.textlength(" ".join(lw[:span[-1] + 1]), font=f)
            d.rectangle((xs - 8, y + int(size * .44), xe + 8, y + int(size * .84)), fill=LIME)
        if span and style == "pill":
            xs = x + d.textlength(" ".join(lw[:span[0]]) + (" " if span[0] else ""), font=f)
            xe = x + d.textlength(" ".join(lw[:span[-1] + 1]), font=f)
            d.rounded_rectangle((xs - 14, y + int(size * .04), xe + 14, y + int(size * 1.1)), int(size * .18), fill=INK)
        for j, w in enumerate(lw):
            iskey = wi + j in keyidx
            col = fg
            if iskey and style == "lime":
                col = LIME
            if iskey and style == "pill":
                col = LIME
            d.text((x, y - int(size * .06)), w, font=f, fill=col)
            ww = d.textlength(w, font=f)
            if iskey and style == "underline":
                nxt = d.textlength(" ", font=f) if (j + 1 < len(lw) and wi + j + 1 in keyidx) else 0
                d.rectangle((x, y + int(size * .97), x + ww + nxt, y + int(size * .97) + max(5, size // 16)), fill=INK)
            x += ww + d.textlength(" ", font=f)
        wi += len(lw)
        y += lh
    out = OUT / "og" / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.convert("P", palette=Image.ADAPTIVE, colors=64).save(out, optimize=True)
    # 목록 카드용 작은 WebP (카드 폭 325px 기준, 2배 해상도 대비 480px)
    im.resize((480, round(480 * H / W)), Image.LANCZOS).save(out.with_suffix(".webp"), "WEBP", quality=82)
    return f"/og/{name}.png"


def thumb_theme(p):
    """카테고리별 고정 색: 영어표현=에스프레소, 영어꿀팁=크림, 사유의 문장=올리브 (라임은 핵심 단어에만)"""
    return {"expr": "dark", "tip": "cream"}.get(p["cat"], "dark")


def thumb_num(p):
    order = [o["id"] for o in sorted(POSTS, key=lambda o: (o.get("date", ""), o["id"])) if o["cat"] == p["cat"]]
    return f"No.{order.index(p['id']) + 1:02d}"


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
             ("kakao", "카카오톡 오픈채팅", SITE.get("kakao"))]
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



def yt_thumb(video):
    """유튜브 썸네일을 사이트 안에 16:9 WebP(640x360, 20KB 안팎)로 저장해 써요.
    images/yt/<id>.webp 가 없으면 빌드할 때 한 번 내려받아 만들고, 실패하면 유튜브 주소를 그대로 써요."""
    f = ROOT / "images" / "yt" / f"{video}.webp"
    if not f.exists():
        try:
            import urllib.request, io
            from PIL import Image
            data = None
            for q in ("maxresdefault", "hqdefault"):
                try:
                    data = urllib.request.urlopen(f"https://i.ytimg.com/vi/{video}/{q}.jpg", timeout=10).read()
                    break
                except Exception:
                    continue
            im = Image.open(io.BytesIO(data)).convert("RGB")
            w, h = im.size
            ch = round(w * 9 / 16)
            im = im.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch)).resize((640, 360), Image.LANCZOS)
            f.parent.mkdir(parents=True, exist_ok=True)
            im.save(f, "WEBP", quality=80)
        except Exception:
            return f"https://i.ytimg.com/vi/{video}/hqdefault.jpg"
    small = f.with_name(f"{video}-400.webp")
    if not small.exists():
        try:
            from PIL import Image
            Image.open(f).resize((400, 225), Image.LANCZOS).save(small, "WEBP", quality=78)
        except Exception:
            pass
    return f"/images/yt/{video}.webp"


def yt_ver(video, suf=""):
    f = ROOT / "images" / "yt" / f"{video}{suf}.webp"
    return hashlib.md5(f.read_bytes()).hexdigest()[:8] if f.exists() else "0"


def yt_img(video, attrs):
    """휴대폰엔 400px, 큰 화면엔 640px 썸네일을 보내요"""
    src = yt_thumb(video)
    if src.startswith("/images/yt/") and (ROOT / "images" / "yt" / f"{video}-400.webp").exists():
        # 파일 내용이 바뀌면 주소(?v=)도 바뀌어서 브라우저·카톡이 옛 이미지를 쓰지 않아요
        v1, v4 = yt_ver(video), yt_ver(video, "-400")
        return (f'<img src="/images/yt/{video}-400.webp?v={v4}" srcset="/images/yt/{video}-400.webp?v={v4} 400w, {src}?v={v1} 640w" '
                f'sizes="(max-width:600px) 92vw, 480px" alt="" width="640" height="360" {attrs}>')
    return f'<img src="{src}" alt="" width="640" height="360" {attrs}>'

def video_block(video, title, hint):
    """썸네일만 먼저 보여주고, 누르면 그때 유튜브 플레이어를 불러옵니다 (페이지 속도 ↑)."""
    return (f'<div class="video-slot no-print"><div class="video-embed" data-vid="{video}">'
            f'<button class="v-facade" type="button" aria-label="{e(title)} 영상 재생">'
            + yt_img(video, 'fetchpriority="high"') +
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
# ------------------------------------------------------------------ font (속도)
FONT_FILE = ASSETS / "pretendard-subset.woff2"
FONT_CHARS = ASSETS / "pretendard-subset.chars"


def site_font():
    """사이트에 실제로 쓰인 글자만 담은 Pretendard 글꼴 1개(woff2, 120KB 안팎)를 만들어요.
    외부 CDN 글꼴(조각 파일 14개, 350KB)을 대신해서 첫 화면이 빨리 떠요.
    글자 목록이 바뀌었을 때만 다시 만들고, fontTools·brotli가 없으면 기존 파일을 그대로 써요."""
    chars = set()
    for f in list(CONTENT.rglob("*.json")) + [ROOT / "build.py", ASSETS / "app.js"]:
        chars |= set(f.read_text("utf-8"))
    chars |= {chr(c) for c in range(0x20, 0x7F)}
    text = "".join(sorted(c for c in chars if ord(c) >= 0x20))
    old = FONT_CHARS.read_text("utf-8") if FONT_CHARS.exists() else ""
    if FONT_FILE.exists() and set(text) <= set(old):
        return
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
        from fontTools import subset
        import brotli  # noqa: F401  (woff2 저장에 필요)
    except ImportError:
        if FONT_FILE.exists():
            print("⚠️  새 글자가 생겼지만 fontTools/brotli가 없어 글꼴을 다시 만들지 못했어요 (pip install fonttools brotli)")
        return
    font = instancer.instantiateVariableFont(TTFont(ROOT / "fonts" / "PretendardVariable.ttf"), {"wght": (400, 800)})
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt"]
    sub = subset.Subsetter(opts)
    sub.populate(text=text, unicodes=list(range(0xA0, 0x100)) + list(range(0x2010, 0x2028)) + list(range(0x2190, 0x2194)))
    sub.subset(font)
    font.flavor = "woff2"
    font.save(FONT_FILE)
    FONT_CHARS.write_text(text, "utf-8")
    print(f"🔤 글꼴 다시 만듦: {len(text)}자, {FONT_FILE.stat().st_size // 1024}KB")


site_font()

ASSET_V = hashlib.md5(b"".join(f.read_bytes() for f in sorted(ASSETS.rglob("*")) if f.is_file())).hexdigest()[:8]
FONT_V = hashlib.md5(FONT_FILE.read_bytes()).hexdigest()[:8] if FONT_FILE.exists() else ""
STYLE_CSS = (ASSETS / "style.css").read_text("utf-8")


def mmss(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


# ------------------------------------------------------------------ layout
def layout(title, desc, path, body, nav="", data=None, og_type="website", aside="", wide=False, og_img="/assets/og.png", seo_title=None, ld=None, preload="", robots=""):
    full_title = f"{seo_title or title} | 카페인영어" if path != "/" else f"카페인영어 - {SITE['tagline']}"
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(SITE["adsense_client"])}" crossorigin="anonymous"></script>'
           if SITE.get("adsense_client") else "")
    # 방문 통계(GA)는 페이지가 다 뜬 뒤에 불러와요 (첫 화면 속도 ↑, 방문 기록은 그대로 남아요)
    ga = (f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{e(SITE['ga_id'])}');"
          f"addEventListener('load',function(){{setTimeout(function(){{var s=document.createElement('script');s.async=1;s.src='https://www.googletagmanager.com/gtag/js?id={e(SITE['ga_id'])}';document.head.appendChild(s)}},1500)}});</script>"
          if SITE.get("ga_id") else "")
    # 첫 화면 큰 이미지를 head에서 가장 먼저 요청 (그다음 글꼴)
    font_head = (preload + f'<link rel="preload" href="/assets/pretendard-subset.woff2?v={FONT_V}" as="font" type="font/woff2" crossorigin>'
                 f"<style>@font-face{{font-family:'Pretendard Variable';font-weight:400 800;font-style:normal;font-display:swap;"
                 f"src:url('/assets/pretendard-subset.woff2?v={FONT_V}') format('woff2-variations'),url('/assets/pretendard-subset.woff2?v={FONT_V}') format('woff2')}}</style>"
                 if FONT_V else '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">')
    navlinks = f'<a href="/"{" class=on" if path == "/" else ""}>홈</a>' + "".join(
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
<link rel="canonical" href="{DOMAIN}{path}">{f'<meta name="robots" content="{robots}">' if robots else ""}
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{e(SITE['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{DOMAIN}{path}">
<meta property="og:image" content="{DOMAIN}{og_img}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{DOMAIN}{og_img}">
{f'<meta name="google-site-verification" content="{e(SITE["google_verify"])}">' if SITE.get("google_verify") else ""}{f'<meta name="naver-site-verification" content="{e(SITE["naver_verify"])}">' if SITE.get("naver_verify") else ""}
{ld_html(ld)}
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="icon" href="/assets/icon-192.png" sizes="192x192" type="image/png">
<meta name="theme-color" content="#FFFFFF">
{font_head}
<style>{STYLE_CSS}</style>
{ads}{ga}
</head>
<body>
<header class="top"><div class="top-in">
  <a class="logo" href="/"><img class="logo-mark" src="/assets/logo-mark.png" alt="" width="30" height="30">카페인영어 <i>CafeInEnglish</i></a>
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


def card(href, chips, title, sub, thumb=None, play=False, alt="", hl=3, data_sub=""):
    chip_html = "".join('<span class="chip %s">%s</span>' % (c, e(t)) for c, t in chips)
    th = ""
    if thumb:
        badge = ('<span class="th-play"><svg width="16" height="16" viewBox="0 0 24 24"><path d="M8 5l11 7-11 7z" fill="#2A1A12"/></svg></span>'
                 if play else "")
        if thumb.startswith("<"):
            th = f'<div class="thumb cthumb">{thumb}</div>'
        elif thumb.startswith("icon:"):
            name = thumb[5:]
            img = f'<img src="/assets/icons/{name}.webp?v={ASSET_V}" alt="{e(alt)}" loading="lazy" width="96" height="96">'
            th = f'<div class="thumb ic ic-{chips[0][0]}">{img}</div>'
        elif thumb.startswith("/images/yt/"):
            vid = thumb.rsplit("/", 1)[1].replace(".webp", "")
            img = yt_img(vid, 'loading="lazy"').replace('sizes="(max-width:600px) 92vw, 480px"', 'sizes="(max-width:600px) 92vw, 340px"')
        else:
            img = f'<img src="{thumb.replace(".png?", ".webp?")}" alt="{e(alt)}" loading="lazy" width="960" height="504">'
        if not thumb.startswith(("icon:", "<")):
            th = f'<div class="thumb">{img}{badge}</div>'
    ds = f' data-sub="{e(data_sub)}"' if data_sub else ""
    return f'<a class="card{" has-th" if thumb else ""}" href="{href}"{ds}>{th}<div class="chips">{chip_html}</div><h{hl}>{e(title)}</h{hl}><p>{e(sub)}</p></a>'


def thumb_ver(th, theme):
    """썸네일 내용이 바뀌면 주소 꼬리표도 바뀌어서, 브라우저·서버에 남은 옛 이미지 대신 새 이미지를 바로 불러와요"""
    raw = json.dumps([th, theme, THEMES.get(theme)], ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:8]


CHAT_BG = ["linear-gradient(150deg,#FFF3EC,#FFE0CF)", "linear-gradient(150deg,#EEF5FF,#D6E6FF)",
           "linear-gradient(150deg,#F4F0FF,#E2D8FF)", "linear-gradient(150deg,#EFFAF3,#D2F0DE)",
           "linear-gradient(150deg,#FFF9E9,#FCEBB6)"]


def chat_bg(key):
    return CHAT_BG[int(hashlib.md5(key.encode()).hexdigest(), 16) % len(CHAT_BG)]


def chat_html(q, a, key, ko, art="", bg="", big=False):
    """실제 대화 카드 (C안): 상대 말풍선 + 내 말풍선(핵심 표현 라임) + 작은 3D 아이콘"""
    ah = e(a)
    if key and e(key) in ah:
        ah = ah.replace(e(key), f"<b>{e(key)}</b>", 1)
    qh = f'<div class="cv-q">{e(q)}</div>' if q else ""
    lbl = '<div class="cv-lbl">실제 대화에선 이렇게</div>' if big else ""
    koh = f'<div class="cv-ko">{e(ko)}</div>' if (big and ko) else ""
    return (f'<div class="chatv{" big" if big else ""}" style="background:{bg}" aria-hidden="true"><div class="cv-card">{lbl}{qh}'
            f'<div class="cv-a"><span>{ah}</span></div>{koh}</div>{art}</div>')


def icon_img(name, cls="cv-ic", lazy=True):
    lz = ' loading="lazy"' if lazy else ""
    return f'<img class="{cls}" src="/assets/icons/{name}.webp?v={ASSET_V}" alt=""{lz} width="96" height="96">'


def post_thumb(p):
    """영상 글은 유튜브 썸네일, 나머지는 공유 이미지(og)를 썸네일로"""
    if p.get("video"):
        return yt_thumb(p["video"]), True
    if p.get("chat"):
        c = p["chat"]
        art = icon_img(p["icon"]) if p.get("icon") else ""
        return chat_html(c["q"], c["a"], c.get("key", ""), c.get("ko", ""), art, chat_bg(p["id"])), False
    if p.get("icon") and (ASSETS / "icons" / f"{p['icon']}.webp").exists():
        return "icon:" + p["icon"], False
    return f"/og/th-p-{p['id']}.png?v={thumb_ver(p.get('thumb'), thumb_theme(p))}", False


def thumb_alt(th):
    return f"{th.get('text', '')} - {th.get('ko', '')}".strip(" -") if th else ""


def post_card(p, hl=3):
    th, play = post_thumb(p)
    return card(post_url(p), [(p["cat"], CATS[p["cat"]]), (p["cat"], p.get("sub", ""))], p["title"],
                f"{p.get('lead', '')} · 퀴즈 {len(p['quiz'])}문제", th, play, thumb_alt(p.get("thumb")), hl, p.get("sub", ""))


def think_card(t, hl=3):
    return card(think_url(t), [("think", "사유의 문장"), ("speaker", t["speaker"])], t["title"],
                f"필사할 문장 {len(t['quotes'])}개", yt_thumb(t["video"]) if t.get("video") else f"/og/th-t-{t['id']}.png?v={thumb_ver(t.get('thumb'), 'olive')}",
                alt=thumb_alt(t.get("thumb")), hl=hl)


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
            f'<h2 class="ws-title">{e(title)}</h2><div class="date">{e(sub)}</div>'
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


def short_pair(o):
    """퀴즈 결과 '이어서 배우기' 한 줄용 (굵은 영어, 짧은 뜻)"""
    th = o.get("thumb") or {}
    if th.get("text"):
        return th["text"], th.get("ko", "")
    og = o.get("og") or {}
    return og.get("en") or o["title"], og.get("ko", "")


def related_links(p):
    links = [dict(l, en=l["label"], ko="") for l in p.get("related", [])]
    if p.get("think") in THINK_BY_ID:
        links.append({"label": "이 영상 문장 필사하기", "en": "사유의 문장", "ko": "이 영상 문장 필사하기", "href": think_url(THINK_BY_ID[p["think"]])})
    for o in similar_posts(p, 4):
        en, ko = short_pair(o)
        links.append({"label": o["title"], "en": en, "ko": ko, "href": post_url(o)})
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
    yt = (f'<div class="side-box"><h4>카페인영어 유튜브</h4><a class="btn ghost" href="{e(SITE["youtube"])}" target="_blank" rel="noopener">채널 구경하기</a></div>'
          if SITE.get("youtube") else "")
    kk = (f'<div class="side-box"><h4>카페인영어 카카오톡</h4><a class="btn kakao" href="{e(SITE["kakao"])}" target="_blank" rel="noopener">카톡 받아보기</a></div>'
          if SITE.get("kakao") else "")
    return ""  # 사이드바 홍보 버튼(카톡·유튜브)은 쓰지 않음 — 너무 홍보 느낌이라 우측 하단 + 버튼으로만 안내


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
  <div class="orig">{e(x['orig'])}{f'<span class="orig-ko">{e(x["origKo"])}</span>' if x.get("origKo") else ""}</div>
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
    parts.append('<h2 class="rel-h no-print">같이 보면 좋은 글</h2><div class="cards rel list no-print">'
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
    if p.get("thumb") and not p.get("video") and not p.get("chat"):
        thumb_image("th-p-" + p["id"], thumb_theme(p), p["thumb"].get("ko", ""), p["thumb"]["text"], p["thumb"]["key"])
    if p.get("chat"):
        c = p["chat"]
        en = (p.get("thumb") or {}).get("text") or og.get("en") or p["title"]
        ver = hashlib.md5(json.dumps([c, en, p.get("icon"), "og2"], ensure_ascii=False).encode()).hexdigest()[:6]
        img = og_chat(f"p-{p['id']}-{ver}", CATS[p["cat"]] + " · " + p.get("sub", ""), en, c.get("ko", ""), c, p.get("icon", ""), p["id"])
    else:
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
<span class="chip think">사유의 문장</span><span class="chip speaker">{e(t['speaker'])}</span>
<h1>{e(t['title'])}</h1>
<p class="lead">따라 쓰고(필사), 빈칸으로 다시 떠올리고(복기), 나의 한 줄을 남겨 보세요.</p>
</div>
{video_block(t["video"], t["title"], "문장마다 <b>듣기</b>·<b>3번 반복</b>으로 소리까지 익혀요") if t.get("video") else ""}
{f'<a class="btn ghost no-print" href="{post_url(post)}">이 영상의 영어표현 먼저 보기</a>' if post else ""}
{"".join(cards)}
{share_block("마음에 남는 문장, 친구와 같이 필사해요")}
{PRINT_BTN}
<div class="print-only ws">{ws_head("필사 노트 - " + t["title"], t["speaker"], t.get("video"), url)}{ws}</div>
<div class="cq-cta no-print" style="margin-top:16px">
  <a class="btn primary" href="/notes/#copy">내 공부방에서 필사 노트 보기</a>
  {f'<a class="btn kakao" href="{e(SITE["kakao"])}" target="_blank" rel="noopener">매일 아침 문장 하나, 카톡으로 받기<img class="kk-ic" src="/assets/kakao-talk.png" alt="" width="24" height="22"></a>' if SITE.get("kakao") else ""}
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
    tq = t.get("thumb") or {"text": og.get("en") or shortest, "key": ""}
    thumb_image("th-t-" + t["id"], "olive", tq.get("ko", ""), tq["text"], tq["key"])
    img = og_image("t-" + t["id"], "사유의 문장 · 필사", og.get("en") or shortest, og.get("ko") or t["title"], "듣고 · 따라 쓰고 · 빈칸으로 복기")
    ld = ld_article(t["title"], t.get("description", ""), url, img, t.get("date", ""), t["_mod"], "사유의 문장",
                    [("홈", "/"), ("사유의 문장", "/category/think/"), (t["title"], url)])
    return layout(t["title"] + " - 필사하기", t.get("description", ""), url, body, "think", data, "article", aside, og_img=img,
                  seo_title=t.get("seo_title"), ld=ld)


def page_category(cat):
    url = f"/category/{cat}/"
    if cat == "think":
        items = THINKS
        cards = "".join(think_card(t, 2) for t in THINKS)
        body = (f'<h1>{CATS[cat]}</h1><p class="lead">{CAT_LEAD[cat]}</p><div class="cards list">{cards}</div>'
                '<p class="a-intro">필사한 문장은 <a href="/notes/#copy">내 공부방</a>에 모여요.</p>')
    else:
        items = [p for p in POSTS if p["cat"] == cat]
        cards = "".join(post_card(p, 2) for p in items) or '<div class="empty"><p>곧 첫 글이 올라와요.</p></div>'
        subs = [x for x in dict.fromkeys(p.get("sub", "") for p in items) if x]
        filt = ""
        if cat != "video" and len(subs) > 1:
            btn = lambda v, n, lbl, on="": f'<button type="button" class="sf-b{on}" data-sub="{e(v)}"><span>{e(lbl)}</span><em>{n}</em></button>'
            filt = ('<aside class="subfilter" aria-label="분류"><div class="sf-h">분류</div>'
                    + btn("", len(items), "전체", " on")
                    + "".join(btn(x, sum(1 for p in items if p.get("sub") == x), x) for x in subs) + "</aside>")
        body = (f'<h1>{CATS[cat]}</h1><p class="lead">{CAT_LEAD[cat]}</p>'
                f'<div class="cat-grid{" has-filter" if filt else ""}"><div class="cards list">{cards}</div>{filt}</div>')
    seo_t, seo_d = CAT_SEO[cat]
    links = [think_url(t) for t in items] if cat == "think" else [post_url(p) for p in items]
    ld = [{"@type": "CollectionPage", "name": CATS[cat], "description": seo_d, "url": DOMAIN + url, "inLanguage": "ko",
           "isPartOf": {"@type": "WebSite", "name": SITE["name"], "url": DOMAIN + "/"},
           "mainEntity": {"@type": "ItemList", "itemListElement": [
               {"@type": "ListItem", "position": i + 1, "url": DOMAIN + u} for i, u in enumerate(links)]}},
          {"@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"},
              {"@type": "ListItem", "position": 2, "name": CATS[cat], "item": DOMAIN + url}]}]
    img = og_image("c-" + cat, "카테고리", CATS[cat], CAT_LEAD[cat], "읽고 · 듣고 · 퀴즈로 확인")
    return layout(CATS[cat], seo_d, url, body, cat, wide=True, seo_title=seo_t, ld=ld, og_img=img)


SERIES = json.loads((CONTENT / "series.json").read_text("utf-8")) if (CONTENT / "series.json").exists() else []


def page_series(sr):
    url = f"/series/{sr['id']}/"
    items = [POST_BY_ID[i] for i in sr["posts"] if i in POST_BY_ID]
    cards = "".join(post_card(p, 2) for p in items) + "".join(think_card(THINK_BY_ID[i], 2) for i in sr.get("thinks", []) if i in THINK_BY_ID)
    body = (f'<div class="chips"><span class="chip">아티클 시리즈</span></div><h1>{e(sr["title"])}</h1><p class="lead">{e(sr["desc"])}</p>'
            f'<div class="cat-grid"><div class="cards list">{cards}</div></div>')
    ld = [{"@type": "CollectionPage", "name": sr["title"], "description": sr["desc"], "url": DOMAIN + url, "inLanguage": "ko"},
          {"@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"},
              {"@type": "ListItem", "position": 2, "name": sr["title"], "item": DOMAIN + url}]}]
    img = og_image("s-" + sr["id"], "아티클 시리즈", sr["title"], sr["desc"], "읽고 · 듣고 · 퀴즈로 확인")
    return layout(sr["title"], sr["desc"], url, body, wide=True, seo_title=f'{sr["title"]} - 영어 공부 시리즈', ld=ld, og_img=img)


def daily_index(n):
    """한국 날짜 기준으로 매일 하나씩 돌아가며 (app.js와 같은 계산)"""
    import time
    return int((time.time() + 9 * 3600) // 86400) % n



def notice_html():
    """홈 공지 배너 — site.json 의 notice {label, title, sub, href} 가 있을 때만 보여요."""
    n = SITE.get("notice")
    if not n:
        return ""
    return (f'<a class="notice" href="{e(n["href"])}"><span class="lbl">{e(n.get("label", "공지"))}</span>'
            f'<span class="nt-body"><b>{e(n["title"])}</b><span>{e(n.get("sub", ""))}</span></span>'
            f'<span class="nt-go" aria-hidden="true">›</span></a>')

def page_home():
    daily = []
    if (CONTENT / "daily.json").exists():
        for it in json.loads((CONTENT / "daily.json").read_text("utf-8")):
            p = POST_BY_ID.get(it["post"])
            if p:
                daily.append({**it, "url": post_url(p), "cat": CATS[p["cat"]]})
    # 카톡 '오늘의 한 잔' 예약 작업이 읽는 공개 목록 (홈과 같은 순서·같은 날짜 계산)
    (OUT / "daily.json").write_text(json.dumps(
        [{"en": d["en"], "ko": d["ko"], "desc": d.get("desc", ""), "url": DOMAIN + d["url"]} for d in daily],
        ensure_ascii=False, indent=1), "utf-8")
    today = daily[daily_index(len(daily))] if daily else (SITE.get("today") or {})
    tp = POST_BY_ID.get(today.get("post")) or next((p for p in POSTS if p["cat"] == "expr"), POSTS[0])
    t_en = today.get("en") or tp["title"]
    t_ko = today.get("ko") or tp.get("lead", "")
    t_desc = today.get("desc") or ""
    words = t_en.split(" ")
    phrase = e(" ".join(words[:-1])) + (" " if len(words) > 1 else "") + f'<span class="hl">{e(words[-1])}</span>'
    # ── 1. 오늘의 한 잔 슬라이드 (오늘 · 어제 · 그 전 날들, 옆으로 넘겨 보기) ──
    def vis(p, d, n):
        bg = CHAT_BG[n % len(CHAT_BG)]
        if p and p.get("chat") and p["cat"] != "video":
            c = p["chat"]
            return chat_html(c["q"], c["a"], c.get("key", ""), c.get("ko", ""), icon_img(p["icon"], "cv-ic", False) if p.get("icon") else "", bg, True)
        # 영상 글: 그 표현의 예문으로 대화 만들기 + 영상 썸네일
        norm = lambda t: re.sub(r"[^a-z' ]", "", t.lower()).strip()
        x = next((x for x in (p or {}).get("expressions", []) if norm(x["en"]) == norm(d["en"])), None)
        q, a = "", d["en"]
        if x:
            parts = re.split(r"(?<=[.!?])\s+", x["ex"].strip())
            q, a = (" ".join(parts[:-1]), parts[-1]) if len(parts) > 1 else ("", parts[0])
        key = d["en"].replace("~", "").strip()
        key = next((m.group(0) for m in [re.search(re.escape(key), a, re.I)] if m), key)
        art = f'<div class="cv-yt">{yt_img(p["video"], "loading=lazy")}</div>' if p and p.get("video") else ""
        return chat_html(q, a, key, d.get("ko", ""), art, bg, True)
    slides_data = [{"en": d["en"], "ko": d["ko"], "desc": d.get("desc", ""), "cat": d["cat"], "url": d["url"],
                    "vis": vis(POST_BY_ID.get(d.get("post")), d, n)} for n, d in enumerate(daily)]
    N_SLIDES = min(5, len(slides_data))
    def slide_html(it, label):
        w = it["en"].split(" ")
        ph = e(" ".join(w[:-1])) + (" " if len(w) > 1 else "") + f'<span class="hl">{e(w[-1])}</span>'
        return (f'<article class="hs-slide"><div class="hs-txt"><div class="a-kicker">{e(label)} · {e(it["cat"])}</div>'
                f'<p class="a-phrase{" long" if len(it["en"]) > 16 else ""}">{ph}</p><p class="a-mean">{e(it["ko"])}</p>'
                f'<p class="a-desc">{e(it["desc"])}</p><a class="btn ghost" href="{it["url"]}">글 읽고 퀴즈 풀기</a></div>'
                f'<a class="hs-art" href="{it["url"]}" tabindex="-1" aria-hidden="true">{it["vis"]}</a></article>')
    import time as _t
    kst = _t.gmtime(_t.time() + 9 * 3600)
    def label(k, day_secs):
        if k == 0: return "오늘의 한 잔"
        if k == 1: return "어제의 한 잔"
        g = _t.gmtime(day_secs - k * 86400)
        return f"{g.tm_mon}월 {g.tm_mday}일의 한 잔"
    i0 = daily_index(len(slides_data)) if slides_data else 0
    now_k = _t.time() + 9 * 3600
    slides = "".join(slide_html(slides_data[(i0 - k) % len(slides_data)], label(k, now_k)) for k in range(N_SLIDES))
    hero = f"""<section class="hs" aria-label="오늘의 한 잔">
  <div class="hs-track" id="hs-track">{slides}</div>
  <div class="hs-ctl"><button type="button" class="hs-btn" id="hs-prev" aria-label="이전 표현"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M15 6l-6 6 6 6"/></svg></button><button type="button" class="hs-btn" id="hs-next" aria-label="다음 표현"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M9 6l6 6-6 6"/></svg></button><span class="hs-dots" id="hs-dots"></span></div>
</section>"""
    slides_js = json.dumps(slides_data, ensure_ascii=False).replace("</", "<\\/")
    hero_js = """<script>(function(){var L=%s,n=Math.min(5,L.length);if(!n)return;var day=Math.floor((Date.now()/1000+9*3600)/86400),i0=day%%L.length,tr=document.getElementById("hs-track");
if(i0!==%d){var x=function(t){return String(t).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})};
var lab=function(k){if(!k)return"오늘의 한 잔";if(k===1)return"어제의 한 잔";var d=new Date((day-k)*86400000);return(d.getUTCMonth()+1)+"월 "+d.getUTCDate()+"일의 한 잔"};
tr.innerHTML=Array.from({length:n},function(_,k){var it=L[((i0-k)%%L.length+L.length)%%L.length],w=it.en.split(" "),last=w.pop();
return '<article class="hs-slide"><div class="hs-txt"><div class="a-kicker">'+lab(k)+' · '+x(it.cat)+'</div><p class="a-phrase'+(it.en.length>16?' long':'')+'">'+(w.length?x(w.join(" "))+" ":"")+'<span class="hl">'+x(last)+'</span></p><p class="a-mean">'+x(it.ko)+'</p><p class="a-desc">'+x(it.desc||"")+'</p><a class="btn ghost" href="'+it.url+'">글 읽고 퀴즈 풀기</a></div><a class="hs-art" href="'+it.url+'" tabindex="-1" aria-hidden="true">'+it.vis+'</a></article>'}).join("")}
var dots=document.getElementById("hs-dots");dots.innerHTML=Array.from({length:n},function(){return"<i></i>"}).join("");
var cur=function(){return Math.round(tr.scrollLeft/tr.clientWidth)},paint=function(){var c=cur();[].forEach.call(dots.children,function(d,j){d.className=j===c?"on":""});document.getElementById("hs-prev").disabled=c<=0;document.getElementById("hs-next").disabled=c>=n-1};
var go=function(d){tr.scrollTo({left:(cur()+d)*tr.clientWidth,behavior:"smooth"})};
document.getElementById("hs-prev").onclick=function(){go(-1)};document.getElementById("hs-next").onclick=function(){go(1)};
tr.addEventListener("scroll",function(){clearTimeout(tr._t);tr._t=setTimeout(paint,60)},{passive:true});paint()})();</script>""" % (slides_js, i0)

    # ── 2. 전체 아티클 (8개씩 페이지) + 인기 있는 글 ──
    PER = 8
    allitems = sorted([("p", p) for p in POSTS] + [("t", t) for t in THINKS],
                      key=lambda x: (x[1].get("date", ""), x[1]["id"]), reverse=True)
    arts = "".join((post_card(o) if k == "p" else think_card(o)).replace('<a class="card', f'<a data-pg="{n // PER + 1}" class="card' + (" pg-hide" if n >= PER else ""), 1)
                   for n, (k, o) in enumerate(allitems))
    pages_n = (len(allitems) + PER - 1) // PER
    pager = ('<nav class="pager" id="pager" aria-label="페이지">'
             + "".join(f'<button type="button" class="{"on" if i == 1 else ""}" data-pg="{i}">{i}</button>' for i in range(1, pages_n + 1))
             + "</nav>") if pages_n > 1 else ""
    pop_ids = SITE.get("popular") or [p["id"] for p in POSTS[:5]]
    pop = []
    for pid in pop_ids:
        o = POST_BY_ID.get(pid)
        if o:
            pop.append((post_url(o), o["title"], CATS[o["cat"]]))
        elif pid in THINK_BY_ID:
            t = THINK_BY_ID[pid]; pop.append((think_url(t), t["title"], "사유의 문장"))
    pop_html = "".join(f'<li><a href="{u}"><span class="pop-n">{i}</span><span><b>{e(tt)}</b><small>{e(c)}</small></span></a></li>'
                       for i, (u, tt, c) in enumerate(pop[:5], 1))

    # ── 3. 아티클 시리즈 ──
    series_html = ""
    for sr in SERIES:
        sp = [POST_BY_ID[i] for i in sr["posts"] if i in POST_BY_ID]
        icons = [o["icon"] for o in sp if o.get("icon")][:3]
        if icons:
            cover = f'<div class="sr-cover ic-{sp[0]["cat"]}">' + "".join(f'<img src="/assets/icons/{ic}.webp?v={ASSET_V}" alt="" loading="lazy" width="96" height="96">' for ic in icons) + "</div>"
        else:
            vids = [o for o in sp if o.get("video")]
            lazy = 'loading="lazy"'
            cover = ('<div class="sr-cover yt">' + yt_img(vids[0]["video"], lazy) + '</div>') if vids else '<div class="sr-cover"></div>'
        series_html += (f'<a class="sr-card" href="/series/{sr["id"]}/">{cover}<h3>{e(sr["title"])}</h3>'
                        f'<p>{e(sr["desc"])}</p><span class="sr-n">글 {len(sp) + len(sr.get("thinks", []))}개</span></a>')

    body = f"""<h1 class="sr-only">카페인영어 CafeInEnglish - 매일 조금씩, 깊게 스며드는 영어 공부</h1>
{hero}{hero_js}
{notice_html()}
<div class="home-grid">
  <section><h2 class="home-h">전체 아티클</h2><div class="cards list" id="all-arts">{arts}</div>{pager}</section>
  <aside class="pop"><h2 class="pop-h">인기 있는 글</h2><ol>{pop_html}</ol></aside>
</div>
<section class="series"><h2 class="home-h">아티클 시리즈</h2><div class="sr-grid">{series_html}</div></section>
"""
    vp = None
    ld = [{"@type": "WebSite", "name": "카페인영어 CafeInEnglish", "alternateName": "카페인영어", "url": DOMAIN + "/", "inLanguage": "ko"}, ORG]
    pre = ""
    p0 = POST_BY_ID.get(daily[i0]["post"]) if daily else None
    if p0 and p0.get("icon"):
        pre = f'<link rel="preload" as="image" href="/assets/icons/{p0["icon"]}.webp?v={ASSET_V}" fetchpriority="high">'
    if vp and vp.get("video") and (ROOT / "images" / "yt" / f'{vp["video"]}-400.webp').exists():
        v = vp["video"]
        pre = (f'<link rel="preload" as="image" href="/images/yt/{v}-400.webp?v={yt_ver(v, "-400")}" imagesrcset="/images/yt/{v}-400.webp?v={yt_ver(v, "-400")} 400w, /images/yt/{v}.webp?v={yt_ver(v)} 640w" '
               'imagesizes="(max-width:600px) 92vw, 480px" fetchpriority="high">')
    return layout(SITE["name"], SITE["tagline"], "/", body, wide=True, ld=ld, data={"type": "home", "daily": daily}, preload=pre)


def page_notes():
    body = ('<h1>내 공부방</h1><p class="lead">틀린 문제와 필사한 문장이 여기에 모여요. '
            '기록은 이 기기의 브라우저에만 저장돼요.</p>'
            '<h2 id="wrong">오답노트</h2><p class="lead" style="font-size:15px">다시 풀어서 맞히면 \'졸업\'해요.</p><div id="notes-root"></div>'
            '<h2 id="copy">필사 노트 (<span id="copy-count">0</span>)</h2><div id="copy-notes"></div>')
    return layout("내 공부방", "퀴즈 오답노트와 필사 노트를 모아 다시 복습하는 나만의 공부방", "/notes/", body, "notes",
                  {"type": "notes", "kakao": SITE.get("kakao", "")}, wide=True, robots="noindex,follow")


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
    """문의 폼 (A안): 유형 → 내용 → 답장 이메일 → 보내기.
    서버가 없어서 FormSubmit(formsubmit.co)으로 승주 메일함에 바로 보내요.
    처음 한 번은 FormSubmit이 보내는 '확인(Activate)' 메일을 눌러야 이후 문의가 들어와요."""
    kinds = ["표현·콘텐츠 제안", "오류 제보", "저작권 요청", "협업·제휴", "기타"]
    chips = "".join(f'<button type="button" class="cf-chip{" on" if n == 0 else ""}" data-kind="{e(k)}" aria-pressed="{"true" if n == 0 else "false"}">{e(k)}</button>'
                    for n, k in enumerate(kinds))
    return (f'<p class="lead">어떤 이야기든 편하게 남겨 주세요. 보통 1~2일 안에 답장드려요.</p>'
            f'<form class="cf" id="contact-form" data-to="{e(SITE.get("formsubmit_id") or EMAIL)}" novalidate>'
            f'<div class="cf-step" id="cf-kind-l">어떤 문의인가요?</div>'
            f'<div class="cf-chips" role="group" aria-labelledby="cf-kind-l">{chips}</div>'
            '<label class="cf-l" for="cf-msg">궁금한 내용</label>'
            '<textarea class="cf-in" id="cf-msg" name="message" rows="6" maxlength="3000" required '
            'placeholder="예) \'I\'m down\'처럼 헷갈리는 표현을 더 다뤄 주세요"></textarea>'
            '<label class="cf-l" for="cf-mail">답장 받을 이메일</label>'
            '<input class="cf-in" id="cf-mail" name="email" type="email" inputmode="email" autocomplete="email" required placeholder="name@example.com">'
            '<input type="text" name="_honey" class="cf-hp" tabindex="-1" autocomplete="off" aria-hidden="true">'
            '<p class="cf-err" id="cf-err" role="alert" hidden></p>'
            '<button class="cf-send" type="submit">문의 보내기</button>'
            '<p class="cf-note">보내 주신 이메일은 답장에만 사용해요</p></form>'
            '<div class="cf-done" id="cf-done" hidden><b>문의가 잘 전달됐어요</b><span>1~2일 안에 남겨 주신 이메일로 답장드릴게요.</span>'
            '<a class="btn ghost" href="/">홈으로</a></div>')


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



# ── 여행영어 무료 자료 안내 페이지 (/travel/) ──────────────────────────────
# PDF는 files/travel-english.pdf 에 넣으면 다운로드 버튼이 자동으로 켜져요 (없으면 '준비 중' 안내).
# 인스타 DM 링크와 PDF 속 QR이 이 주소를 가리키니, 주소(/travel/)와 상황 글 id는 바꾸지 않아요.
TRAVEL_PDF = "files/travel-english.pdf"
TRAVEL_SITUATIONS = [("기내", "airplane", "in-flight"), ("입국심사", "passport-control", "immigration"), ("수하물·세관", "luggage", "baggage-customs"),
                     ("교통", "taxi", "transportation"), ("호텔", "hotel", "hotel-check-in"), ("카페", "hot-beverage", "travel-cafe"), ("식당", "fork-knife-plate", "travel-restaurant"),
                     ("쇼핑·계산", "shopping-bags", "shopping-checkout"), ("길 찾기", "world-map", "asking-directions"), ("문제 상황", "pill", "travel-trouble")]
TRAVEL_PLAN = ["살아남는 문장 + 기내", "입국심사 + 수하물", "교통", "호텔", "카페 + 식당", "쇼핑 + 길 찾기", "문제 상황 + 복습"]

def page_travel():
    pdf_ok = (ROOT / TRAVEL_PDF).exists()
    dl = (f'<a class="btn primary tv-dl" href="/{TRAVEL_PDF}" download>여행영어 PDF 내려받기</a>' if pdf_ok
          else '<div class="tv-soon">PDF를 마무리하고 있어요. 곧 여기서 내려받을 수 있어요.</div>')
    steps = [("page", "PDF 받기", "출력하거나 폰에 저장해요"),
             ("mobile-phone", "QR 찍기", "페이지마다 QR로 발음을 들어요"),
             ("speech-balloon", "따라 말하기", "느리게 한 번, 보통 속도로 한 번"),
             ("check", "써 본 문장 체크", "여행 중에 써 본 문장에 표시해요")]
    steps_html = "".join(f'<div class="tv-step">{icon_img(ic, "tv-ic")}<div><span class="tv-n">STEP {i + 1}</span>'
                         f'<b>{e(t)}</b><span>{e(d)}</span></div></div>' for i, (ic, t, d) in enumerate(steps))
    tiles = ""
    for name, ic, pid in TRAVEL_SITUATIONS:
        inner = f'{icon_img(ic, "tv-ic")}<b>{e(name)}</b>'
        if pid in POST_BY_ID:
            tiles += f'<a class="tv-tile on" href="{post_url(POST_BY_ID[pid])}">{inner}<span class="tv-go">지금 공부하기 ›</span></a>'
        else:
            tiles += f'<div class="tv-tile">{inner}<span class="tv-wait">곧 열려요</span></div>'
    # 숫자는 상황 글에서 직접 세요: 질문 = .ex.hear 항목, 대답 = .ex.ans 항목
    n_q = n_a = 0
    for _, _, pid in TRAVEL_SITUATIONS:
        bh = POST_BY_ID[pid].get("body_html", "") if pid in POST_BY_ID else ""
        n_q += bh.count('<span class="hn">')
        n_a += sum(blk.count("<li") for blk in re.findall(r'<ul class="ex ans">(.*?)</ul>', bh, re.S))
    plan = "".join(f'<div class="tv-day"><span>Day {i + 1}</span><b>{e(t)}</b></div>' for i, t in enumerate(TRAVEL_PLAN))
    faq = [("정말 무료인가요?", "네, 무료예요. 제가 공부하면서 정리한 걸 필요한 분과 같이 쓰고 싶어서 만들었어요."),
           ("어느 나라에서 쓸 수 있나요?", "미국 영어 기준이에요. 영국에서 다르게 쓰는 표현은 따로 표시했고, 영어를 쓰는 대부분의 국제공항과 관광지에서 그대로 통해요."),
           ("출력해서 봐도 되나요?", "네, A4로 출력하기 좋게 만들었어요. 폰에 저장해 두고 공항에서 꺼내 봐도 좋아요.")]
    faq_html = "".join(f'<details class="tv-faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faq)
    kakao = SITE.get("kakao", "")
    body = f"""<div class="tv">
<section class="tv-hero">
  {icon_img("passport-control", "tv-hero-ic", lazy=False)}
  <span class="lbl">무료 자료</span>
  <h1>여행영어,<br>공항부터 호텔까지</h1>
  <p>현지에서 <b>실제로 들리는 영어</b>를 상황별로 정리했어요.</p>
  <div class="tv-stats"><div><b>{len(TRAVEL_SITUATIONS)}</b><span>상황</span></div><div><b>{n_q}</b><span>직원 질문</span></div><div><b>{n_a}</b><span>바로 쓰는 대답</span></div></div>
  {dl}
</section>
<h2>이런 걸 배워요</h2>
<div class="tv-demo">
  <div class="tv-row"><span class="tv-who">직원</span><span class="tv-bub">What brings you here?</span></div>
  <div class="tv-hear"><span class="lbl">이렇게 들려요</span><b>왓 브링쥬 히어?</b></div>
  <div class="tv-row me"><span class="tv-bub me">I'm here on vacation.</span></div>
  <div class="tv-ko">여행 왔어요</div>
</div>
<p class="tv-cap">문장을 몰라서가 아니라, 소리가 낯설어서 막히는 거예요.<br>직원 질문이 실제로 어떻게 들리는지부터 익혀요.</p>
<h2>이렇게 쓰면 돼요</h2>
<div class="tv-steps">{steps_html}</div>
<h2>상황별로 바로 공부하기</h2>
<div class="tv-grid">{tiles}</div>
<h2>출발 전 7일 플랜</h2>
<div class="tv-plan">{plan}</div>
<p class="tv-cap">하루 10~15분이면 충분해요.</p>
<h2>자주 묻는 질문</h2>
{faq_html}
<div class="tv-cta">{icon_img("alarm-clock", "tv-ic")}<b>여행 끝나고도 이어가고 싶다면</b><span>매일 아침 7시, 실제로 쓰이는 영어 표현 하나를 카톡으로 보내드려요.</span>
{f'<a class="btn kakao" href="{e(kakao)}" target="_blank" rel="noopener">매일 아침 1일 1영 받아보기</a>' if kakao else ""}</div>
</div>"""
    return layout("여행영어 무료 PDF, 공항부터 호텔까지", "입국심사, 호텔, 카페, 식당에서 직원이 실제로 하는 말과 바로 쓰는 대답을 상황별로 정리한 여행영어 무료 자료예요. 원어민 발음 듣기와 출력용 PDF를 함께 드려요.",
                  "/travel/", body, seo_title="여행영어 무료 PDF - 공항부터 호텔까지, 현지에서 들리는 영어")

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
    for sr in SERIES:
        write(f"/series/{sr['id']}/", page_series(sr)); pages.append(f"/series/{sr['id']}/")
    write("/notes/", page_notes())
    if (ROOT / "images").exists():  # 빌드 중 새로 만든 유튜브 썸네일까지 다시 복사
        shutil.copytree(ROOT / "images", OUT / "images", dirs_exist_ok=True)
    write("/about/", page_static("about", "카페인영어 소개", "제가 매일 영어 공부하려고 만든 공간, 카페인영어를 소개해요", ABOUT)); pages.append("/about/")
    write("/privacy/", page_static("privacy", "개인정보처리방침", "카페인영어 개인정보처리방침", PRIVACY)); pages.append("/privacy/")
    write("/contact/", page_static("contact", "문의", "카페인영어 문의하기", CONTACT)); pages.append("/contact/")
    if (ROOT / "files").exists():
        shutil.copytree(ROOT / "files", OUT / "files", dirs_exist_ok=True)
    write("/travel/", page_travel()); pages.append("/travel/")
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
    written = {OUT / "assets" / f.relative_to(ASSETS) for f in ASSETS.rglob("*") if f.is_file()} | {OUT / "audio" / f.name for f in AUDIO_DIR.glob("*.mp3")} | {OUT / "images" / f.relative_to(ROOT / "images") for f in (ROOT / "images").rglob("*") if f.is_file()} | {f for f in after if f.stat().st_mtime >= START}
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

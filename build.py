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
CATS = {"video": "영상으로 배우기", "expr": "영어표현", "tip": "영어꿀팁", "story": "영어 이야기", "think": "사유의 문장"}
NAV_CATS = ("video", "expr", "tip", "story")  # 위쪽 메뉴 (사유의 문장은 '영상' 칸 안 전환으로)
TILE_SUB = {"video": "카영 영상 속 표현을 장면과 함께", "expr": "새 표현 · 비슷한 표현 · 헷갈리는 표현",
            "tip": "여행 · 회화 · 단어 · 듣기 · 발음", "story": "매일 쓰는 단어에 숨은 역사", "think": "필사하고 빈칸으로 복기"}
CAT_SEO = {  # 카테고리 페이지 검색용 제목 · 설명
    "video": ("영상으로 배우는 영어 - 카페인영어 영상 속 표현 정리와 퀴즈",
              "카페인영어 유튜브 영상 한 편에서 실제로 쓰는 영어 표현을 뽑아 뜻, 예문, 발음과 함께 정리하고 퀴즈로 확인해요."),
    "expr": ("원어민 영어표현 - 뜻, 예문, 비슷한 표현, 헷갈리는 표현 정리",
             "Sounds good, My bad, I'm on it처럼 원어민이 매일 쓰는 영어표현을 뜻, 예문, 비슷한 표현, 자주 하는 실수와 연상법, 퀴즈로 정리했어요."),
    "tip": ("영어꿀팁 - 회화, 발음, 듣기, 콩글리시까지 바로 써먹는 영어 팁",
            "한국인이 자주 틀리는 영어 회화, 발음, 듣기, 콩글리시를 쉽게 풀어 정리했어요. 식당, 카페, 병원, 화상회의에서 바로 쓰는 문장과 퀴즈까지."),
    "story": ("영어 이야기 - 영어 단어 어원과 유래, 실제 기록과 사진으로 보는 영어의 역사",
              "hello, OK, deadline, bug처럼 매일 쓰는 영어 단어가 어디서 왔는지 실제 기록과 사진으로 따라가고, 지금 쓰는 법과 퀴즈까지 정리했어요."),
    "think": ("영어 명언 필사 - 사유의 문장, 연설과 인터뷰 속 영어 문장",
              "손흥민, 젠슨 황, 순다르 피차이의 영어 연설과 인터뷰 속 곱씹을 문장을 영상으로 듣고, 따라 쓰고, 빈칸으로 다시 떠올려 보세요."),
}
CAT_LEAD = {  # 휴대폰(360px)에서도 한 줄에 들어가게 짧게
    "video": "영상 속 표현을 장면과 함께 배워요",
    "expr": "원어민이 매일 쓰는 표현, 뉘앙스까지",
    "tip": "여행·발음·듣기, 바로 써먹는 영어 팁",
    "story": "매일 쓰는 단어에 숨은 역사",
    "think": "곱씹을 문장을 듣고, 쓰고, 떠올려요",
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
        return "/assets/og-home-2.png"
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
    d.rounded_rectangle((PAD, 56, PAD + 52, 108), 14, fill="#2A1A12")
    d.text((PAD + 12, 82), "C", font=_font(36, 800), fill="#F4EEE4", anchor="lm")
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
        return "/assets/og-home-2.png"
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


AUTHOR_NAME = "카영 스터디언"
AUTHOR_BIO = "미국 이민을 앞두고 온 가족이 영어를 공부하고 있습니다. 직접 공부하며 이해한 것들을 하나씩 정리해 나누고 있어요. 저도 여전히 배우는 중이라 부족한 부분이 있을 수 있습니다. 틀린 내용은 편하게 짚어주시고, 궁금한 점도 함께 나눠주세요. 혼자 공부할 때보다 함께할 때 더 멀리 갈 수 있다고 믿습니다."
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
           "author": {"@type": "Person", "name": AUTHOR_NAME, "url": DOMAIN + "/about/"}, "publisher": ORG, "mainEntityOfPage": DOMAIN + url}
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


SVG_PRINT = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V3h12v6"/><rect x="6" y="14" width="12" height="7" rx="1"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/></svg>'
SVG_QUIZ = '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3 8-8"/><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"/></svg>'
SVG_BOOK = '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/></svg>'
SVG_PEN = '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>'
SVG_PLAY = '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 5l11 7-11 7z"/></svg>'


def act_row(icon, title, sub="", href=None, cls="", right=""):
    """아이콘 + 제목/설명 + 화살표로 된 목록형 버튼 (출력·복습하기·내 공부방 등 공통)"""
    inner = (f'<span class="act-ic">{icon}</span><span class="act-t"><b>{title}</b>'
             + (f'<small>{sub}</small>' if sub else "") + f'</span><span class="act-r">{right}<i class="chev">›</i></span>')
    if href:
        return f'<a class="act {cls}" href="{href}">{inner}</a>'
    return f'<button class="act {cls}" type="button">{inner}</button>'


APP_ROW = ('<div class="app-cta js-appcta"><a class="act app-row" href="/app/"><span class="act-ic"><img src="/assets/icon-192.png?v=3" alt="" width="40" height="40" loading="lazy"></span>'
           '<span class="act-t"><b>앱으로 매일 5분</b><small>홈 화면에 추가하면 오늘의 한 잔부터 바로 열려요 · 무료</small></span>'
           '<span class="act-r"><span class="app-btn">설치</span></span></a></div>')
NB_APP = ('<div class="app-cta js-appcta" data-k="nbAppX"><div class="nb-app"><img src="/assets/icon-192.png?v=3" alt="" width="52" height="52">'
          '<div class="t"><b>앱으로 쓰면 더 편해요</b><small class="js-appsub" data-and="홈 화면에서 바로 열고, 오늘의 5분부터 시작해요.">아이폰은 Safari와 앱 기록이 따로 저장돼요. 앱에서 시작하면 기록이 한곳에 모여요.</small></div>'
          '<a href="/app/">설치</a></div><button class="nb-app-x js-appx" type="button">다음에 할게요 ✕</button></div>')
# 휴대폰 + 아직 앱이 아닐 때만 보여 줘요. 내 공부방 카드는 '다음에 할게요'를 누르면 1주 동안 숨김.
APP_CTA_JS = ("<script>(function(){var u=navigator.userAgent,s=(window.matchMedia&&matchMedia('(display-mode: standalone)').matches)||navigator.standalone,"
              "ios=/iPhone|iPad|iPod/i.test(u)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1),mob=ios||/Android/i.test(u);"
              "document.querySelectorAll('.js-appcta').forEach(function(el){if(s||!mob)return;var k=el.dataset.k;"
              "if(k){try{if(Date.now()-(+localStorage.getItem(k)||0)<6048e5)return}catch(e){}"
              "var x=el.querySelector('.js-appx');x&&x.addEventListener('click',function(){try{localStorage.setItem(k,Date.now())}catch(e){}el.remove()})}"
              "var sb=el.querySelector('.js-appsub');if(sb&&!ios)sb.textContent=sb.dataset.and;el.classList.add('on')})})();</script>")


END_CTA = ('<div class="end-cta no-print js-keep" hidden><small>다 읽었다면, 마지막 한 걸음</small>'
           '<b class="ec-t">오늘 배운 표현, 내일 다시 꺼내기</b><span class="ec-s">이 글의 핵심 문장을 복습에 담으면 1일 · 3일 · 7일 뒤에 다시 꺼내 줘요</span>'
           '<div class="ec-a"><button class="ec-b" type="button">복습에 담기</button><a class="ec-l" href="/notes/#review" hidden>내 공부방에서 보기 ›</a></div></div>')
SVG_SH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
END_APP = ('<div class="app-cta js-appcta no-print"><a class="end-app" href="/app/"><img src="/assets/icon-192.png?v=3" alt="" width="26" height="26" loading="lazy">'
           '<span><b>앱으로 매일 5분</b> · 홈 화면에서 바로 열기</span><em>설치 ›</em></a></div>')


def share_block(label, print_label="출력"):
    """글 끝: 출력 · 공유 · 링크 복사를 작은 버튼 한 줄로 + (모바일 웹만) 앱 한 줄"""
    return (f'<div class="end-row no-print" role="group" aria-label="{label}">'
            f'<button class="js-print" type="button">{SVG_SH}<path d="M6 9V3h12v6"/><rect x="6" y="14" width="12" height="7" rx="1"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/></svg>{print_label}</button>'
            f'<button class="js-share" type="button">{SVG_SH}<path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7"/><path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/></svg>공유</button>'
            f'<button class="js-copylink" type="button">{SVG_SH}<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>링크 복사</button></div>'
            + END_APP)


AUTHOR_SIG = (f'<div class="au-s no-print"><img src="/assets/logo-mark.png?v=3" alt="" width="40" height="40" loading="lazy">'
              f'<div><b>{AUTHOR_NAME}</b><span>직접 공부하며 정리한 영어를 나눠요 · <a href="/contact/">의견 남기기</a> · <a href="/about/">소개</a></span></div></div>')


def alt_chips(html_text):
    """대답 카드의 '바꿔 쓰기' 문구(on business 출장 · to visit family 가족 방문)를 칩으로 바꿔요"""
    def conv(m):
        out = []
        for part in [x.strip() for x in m.group(1).split(" · ") if x.strip()]:
            mm = re.match(r"^([A-Za-z0-9][^가-힣]*?)\s+([가-힣].*)$", part)
            if mm:
                out.append(f'<span class="c">{mm.group(1)}<i>{mm.group(2)}</i></span>')
            elif not re.search(r"[가-힣]", part):
                out.append(f'<span class="c">{part}</span>')
            else:
                out.append(f'<span class="t">{part}</span>')
        return '<span class="alt"><small>이렇게 바꿔 말해도 돼요</small>' + "".join(out) + "</span>"
    return re.sub(r'<span class="alt"><small>바꿔 쓰기</small>(.*?)</span>', conv, html_text, flags=re.S)


def load(kind):
    import datetime
    items = []
    for f in sorted((CONTENT / kind).glob("*.json")):
        it = json.loads(f.read_text("utf-8"))
        mod = datetime.date.fromtimestamp(f.stat().st_mtime).isoformat()
        it["_mod"] = max(mod, it.get("date", mod), it.get("updated", ""))   # 수정일 (사이트맵 · 구조화 데이터용)
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
    for f in list(CONTENT.rglob("*.json")) + [ROOT / "build.py", ASSETS / "app.js", ASSETS / "tools.js"]:
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
def _min_css(c):
    """페이지에 넣을 때만 가볍게: 주석·줄바꿈·불필요한 빈칸 빼기 (원본 style.css는 그대로)"""
    c = re.sub(r"/\*.*?\*/", "", c, flags=re.S)
    c = re.sub(r"\s*\n\s*", "", c)
    c = re.sub(r"\s*([{};])\s*", r"\1", c)
    return c.replace(";}", "}")
STYLE_CSS = _min_css((ASSETS / "style.css").read_text("utf-8"))
CSS_V = hashlib.md5(STYLE_CSS.encode()).hexdigest()[:8]  # 디자인 파일은 /assets/site.css 로 따로 (페이지마다 넣지 않아 가볍고, 한 번 받으면 저장)


def mmss(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


# ------------------------------------------------------------------ layout
SW_JS = """// 카페인영어 홈 화면 앱: 페이지는 항상 서버에 새로 확인(브라우저 10분 캐시도 건너뜀), 끊기면 저장본. 글꼴·음성·이미지는 저장해 빠르게
const C = "ky-v2";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  if (u.pathname.startsWith("/assets/") || u.pathname.startsWith("/audio/")) {
    e.respondWith(caches.open(C).then(c => c.match(e.request).then(r => r || fetch(e.request).then(n => { if (n.ok) c.put(e.request, n.clone()); return n; }))));
  } else if (e.request.mode === "navigate") {
    e.respondWith(fetch(u.href, { cache: "no-cache", credentials: "same-origin" }).then(n => {
      if (n.redirected) return Response.redirect(n.url, 302);
      const cp = n.clone(); caches.open(C).then(c => c.put(e.request, cp)); return n;
    }).catch(() => caches.match(e.request)));
  }
});
"""


# ── 홈 화면 앱으로 열었을 때만 보이는 아래쪽 탭 바 ─────────────────────
# 웹 브라우저에서는 숨김(검색·광고 영향 없음). 주소 끝에 ?app=1 을 붙이면 웹에서도 미리 볼 수 있어요.
_TI = lambda d: f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{d}</svg>'
TABS = [("home", "/", "홈", _TI('<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>')),
        ("video", "/category/video/", "영상", _TI('<rect x="2.5" y="5" width="19" height="14" rx="4"/><path d="M10 9.5v5l4.5-2.5z" fill="currentColor"/>')),
        ("expr", "/category/expr/", "표현", _TI('<path d="M21 12a8 8 0 0 1-11.5 7.2L4 20.5l1.4-4.6A8 8 0 1 1 21 12z"/>')),
        ("tip", "/category/tip/", "꿀팁", _TI('<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z"/>')),
        ("story", "/category/story/", "이야기", _TI('<path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5z"/><path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z"/>'))]
APP_HEAD_JS = ("<script>(function(){try{var q=/[?&]app=1/.test(location.search);if(q)sessionStorage.setItem('appPreview','1');"
               "if(q||sessionStorage.getItem('appPreview')||(window.matchMedia&&matchMedia('(display-mode: standalone)').matches)||navigator.standalone)"
               "document.documentElement.classList.add('is-app')}catch(e){}})();</script>")


def tabbar(nav):
    on = ' class="on" aria-current="page"'
    return ('<nav class="tabbar no-print" aria-label="앱 메뉴">' + "".join(
        f'<a href="{h}"{on if nav == k or (k == "video" and nav == "think") else ""}>{ic}<span>{t}</span></a>' for k, h, t, ic in TABS) + '</nav>')


# '영상' 칸 안에서 영상으로 배우기 ↔ 사유의 문장 전환 (웹·앱 모두)
APP_SEG = lambda cat: ('<div class="app-seg no-print" role="tablist" aria-label="영상·문장">'
                       + "".join(f'<a role="tab" href="/category/{k}/"{" class=on aria-selected=true" if k == cat else ""}>{CATS[k]}</a>' for k in ("video", "think")) + '</div>')
# 앱에서는 두 카테고리가 '영상·문장' 탭 하나이므로 제목·설명도 묶음 이름으로 (웹·검색엔진에는 원래 제목 그대로)
APP_HEAD = lambda cat: (f'<h1 data-app="영상·문장"><span class="wt">{CATS[cat]}</span></h1>'
                        f'<p class="lead" data-app="영상 속 표현과 곱씹을 문장을 한곳에"><span class="wt">{CAT_LEAD[cat]}</span></p>')
NAV_SHORT = {"video": "영상", "expr": "표현", "tip": "꿀팁", "story": "이야기", "think": "문장"}  # 휴대폰 위쪽 메뉴는 짧은 이름 (앱 탭과 같게)


def layout(title, desc, path, body, nav="", data=None, og_type="website", aside="", wide=False, og_img="/assets/og-home-2.png", seo_title=None, ld=None, preload="", robots=""):
    full_title = f"{seo_title or title} | 카페인영어" if path != "/" else f"카페인영어 | {SITE.get('home_title') or SITE['tagline']}"
    full_title = full_title.replace(" - ", " | ")  # 브라우저 탭·검색 제목 구분은 하이픈 대신 세로 바로 통일
    # 애드센스: 소유 확인은 meta 태그로, 광고 스크립트(약 200KB)는 첫 스크롤·터치 때(또는 로드 7초 뒤) 불러와요 → 첫 화면 속도 ↑
    ads = (f'<meta name="google-adsense-account" content="{e(SITE["adsense_client"])}">'
           f"<script>(function(){{var d=0;function L(){{if(d)return;d=1;var s=document.createElement('script');s.async=1;s.crossOrigin='anonymous';"
           f"s.src='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(SITE['adsense_client'])}';document.head.appendChild(s)}};"
           f"['scroll','touchstart','mousemove','keydown','click'].forEach(function(t){{addEventListener(t,L,{{once:true,passive:true}})}});"
           f"addEventListener('load',function(){{setTimeout(L,7000)}})}})();</script>"
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
        f'<a href="/category/{k}/"{" class=on" if nav == k or (k == "video" and nav == "think") else ""}><span class="nl-l">{CATS[k]}</span><span class="nl-s">{NAV_SHORT[k]}</span></a>' for k in NAV_CATS) + \
        f'<a href="/tools/"{" class=on" if nav == "tools" else ""}><span class="nl-l">영어 도구</span><span class="nl-s">도구</span></a>'
    room = f'<a class="room{" on" if nav == "notes" else ""}" href="/notes/">내 공부방<span class="badge" id="nav-badge" hidden></span></a>'
    room = ('<button class="srch-btn" type="button" aria-label="표현 검색" title="표현 검색"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></button>' + room)
    pjson = json.dumps(data or {}, ensure_ascii=False).replace("</", "<\\/")
    pdata = '<script id="page-data" type="application/json">' + pjson + '</script>'
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">{APP_HEAD_JS}
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
<link rel="icon" href="/assets/favicon.svg?v=3" type="image/svg+xml">
<link rel="icon" href="/assets/favicon-32.png?v=3" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png?v=3">
<link rel="icon" href="/assets/icon-192.png" sizes="192x192" type="image/png">
<meta name="theme-color" content="#FFFFFF">
<link rel="manifest" href="/manifest.webmanifest"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="카페인영어"><meta name="apple-mobile-web-app-status-bar-style" content="default">
{font_head}
<link rel="stylesheet" href="/assets/site.css?v={CSS_V}">
{ads}{ga}
</head>
<body>
<header class="top"><div class="top-in">
  <a class="logo" href="/"><img class="logo-mark" src="/assets/logo-mark.png?v=3" alt="" width="30" height="30">카페인영어 <i>CafeInEnglish</i></a>
  <nav class="nav">{navlinks}<button class="srch-btn nav-srch" type="button" aria-label="표현 검색"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></button></nav>
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
  <div style="margin-top:8px"><a href="/tools/">영어 도구</a><a href="/about/">소개</a><a href="/privacy/">개인정보처리방침</a><a href="/contact/">문의</a>{f'<a href="{e(SITE["youtube"])}" target="_blank" rel="noopener">유튜브</a>' if SITE.get("youtube") else ""}{f'<a href="{e(SITE["instagram"])}" target="_blank" rel="noopener">인스타그램</a>' if SITE.get("instagram") else ""}</div>
</footer>
{sns_fab()}
{tabbar("home" if path == "/" else nav)}
{pdata}
<script src="/assets/app.js?v={ASSET_V}" defer></script>
{APP_CTA_JS if 'js-appcta' in body else ''}
</body>
</html>
"""


def card(href, chips, title, sub, thumb=None, play=False, alt="", hl=3, data_sub=""):
    chip_html = "".join('<span class="chip %s">%s</span>' % (c, e(t)) for c, t in chips[:1])
    src = " · ".join(t for c, t in chips[1:] if t and t != (chips[0][1] if chips else ""))
    src_html = f'<span class="src">{e(src)}</span> · ' if src else ""
    th = ""
    if thumb:
        badge = ('<span class="th-play"><svg width="16" height="16" viewBox="0 0 24 24"><path d="M8 5l11 7-11 7z" fill="#fff"/></svg></span>'
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
            vt = thumb.startswith("/images/yt/")
            bg = img.replace("<img ", '<img aria-hidden="true" class="th-bg" ', 1).replace(f'alt="{e(alt)}"', 'alt=""') if vt else ""
            th = f'<div class="thumb{" vthumb" if vt else ""}">{bg}{img}{badge}</div>'
    ds = f' data-sub="{e(data_sub)}"' if data_sub else ""
    return f'<a class="card{" has-th" if thumb else ""}" href="{href}"{ds}>{th}<div class="chips">{chip_html}</div><h{hl}>{e(title)}</h{hl}><p>{src_html}{e(sub)}</p></a>'


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


# 난이도: 기초(처음 보는 사람도 바로 쓰는 생활 표현) / 실전(일·뉴스·연설, 뉘앙스까지). 글 JSON "level"이 있으면 그걸 씀.
LEVEL_PRO = {"email-phrases", "video-call", "keep-me-posted", "walk-me-through", "swamped", "im-on-it", "linking",
             "negative-question", "would-you-mind", "make-sense", "this-vs-next"}
def level(p):
    return p.get("level") or ("실전" if p["cat"] == "video" or p["id"] in LEVEL_PRO else "기초")


def post_card(p, hl=3):
    th, play = post_thumb(p)
    lv = level(p)
    return card(post_url(p), [(p["cat"], CATS[p["cat"]]), (p["cat"], p.get("sub", ""))], p["title"],
                f"{p.get('lead', '')} · 퀴즈 {len(p['quiz'])}문제", th, play, thumb_alt(p.get("thumb")), hl, p.get("sub", "")).replace(
                    '</div><h', f'<span class="lv lv-{"pro" if lv == "실전" else "base"}">{lv}</span></div><h', 1).replace(' href=', f' data-lv="{lv}" href=', 1)


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


# 글 본문 꾸미기: '뜻' 강조 카드(글마다 파스텔), 섹션 제목 앞 작은 3D 아이콘
H2_ICON = [("뜻", "light-bulb"), ("예문", "speech-balloon"), ("실제로는", "waving-hand"), ("실제 대화", "waving-hand"), ("헷갈", "question-mark"),
           ("비슷한 표현", "thumbs-up"), ("자주 하는 실수", "grimacing-face")]
def mean_card(m, tint):
    """'뜻' 카드: 대표 표현을 크게, 뜻, 같은 뜻의 다른 표현은 작은 칩으로"""
    exprs = [x.strip() for x in re.split(r"</b>\s*/\s*<b>", m.group(2)) if x.strip()]
    alt = ('<span class="alt"><i>같은 뜻</i>' + "".join(f"<em>{x}</em>" for x in exprs[1:]) + "</span>") if len(exprs) > 1 else ""
    return f'{m.group(1)}<div class="box mean-hi" style="background:{tint}"><b>{exprs[0]}</b><span class="m">{m.group(3)}</span>{alt}</div>'


def post_dress(html, tint):
    html = re.sub(r'(<h2[^>]*>뜻</h2>\s*)<div class="box"><b>(.*?)</b>\s*=\s*(.*?)</div>',
                  lambda m: mean_card(m, tint), html, count=1, flags=re.S)
    def ic(m):
        txt = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        name = next((n for k, n in H2_ICON if txt == k or txt.startswith(k)), None)
        if not name:
            return m.group(0)
        return f'<h2{m.group(1)} class="h-ic"><img src="/assets/icons/{name}.webp?v={ASSET_V}" alt="" width="28" height="28" loading="lazy">{m.group(2)}</h2>'
    return re.sub(r"<h2([^>]*)>(.*?)</h2>", ic, html)


# 영상 글: 본문 인용 상자를 '장면 카드'로 (SCENE 번호 + 아는 구간이면 '이 장면 듣기' + 핵심 표현 라임 밑줄)
IRREG = {"take": "took|taken|takes|taking", "have": "has|had|having", "be": "is|are|was|were|been|being|am", "go": "went|gone|goes|going",
         "get": "got|gotten|gets|getting", "make": "made|makes|making", "come": "came|comes|coming", "give": "gave|given|gives|giving",
         "find": "found|finds|finding", "run": "ran|runs|running", "put": "puts|putting", "let": "lets|letting", "end": "ended|ends|ending",
         "jump": "jumped|jumps|jumping", "figure": "figured|figures|figuring", "break": "broke|broken|breaks|breaking", "keep": "kept|keeps|keeping"}
POSS = "my|your|his|her|our|their|its"


def expr_regex(en):
    """표현 목록의 'take my breath away', 'I have to admit ~' → 본문에서 찾을 정규식 (가장 긴 조각, 동사 변화·소유격 허용)"""
    frags = [f.strip(" .?!,") for f in re.split(r"~|…|\.\.\.|\+|\(|\)", en)]
    frags = [f for f in frags if len(f) >= 6 and not re.search(r"[가-힣]", f)]
    if not frags:
        return None
    words = max(frags, key=len).split()
    pats = []
    for k, w in enumerate(words):
        lw = w.lower()
        if lw in ("one's", "my") and k > 0:
            pats.append(f"(?:{POSS}|one's)")
        elif k == 0 and lw in IRREG:
            pats.append(f"(?:{re.escape(w)}|{IRREG[lw]})")
        else:
            pats.append(re.escape(w))
    return re.compile(r"(?<![A-Za-z])" + r"\s+".join(pats) + r"(?![A-Za-z])", re.I)


def _nz(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]", " ", html.unescape(re.sub(r"<[^>]+>", "", t)).lower().replace("’", "'"))).strip()


SAY_V = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
         '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/></svg>')


def scene_dress(body, p):
    """본문 인용 상자 중 '영상 속 실제 장면'만 장면 카드로. 시간 출처: line_times(롱폼 클립) · 표현 orig · 사유의 문장 (지어내지 않음)"""
    timed = [(_nz(t), a, b) for t, a, b in p.get("line_times", [])]
    for x in p.get("expressions", []):
        if x.get("orig") and x.get("t") is not None:
            timed.append((_nz(x["orig"]), x["t"], x.get("end") or round(x["t"] + 4, 1)))
    th = THINK_BY_ID.get(p.get("think"))
    for q in (th or {}).get("quotes", []):
        if q.get("t") is not None:
            timed.append((_nz(q["en"]), q["t"], q_end(q)))

    def when(txt):
        n = re.sub(r"^(and|well|so) ", "", _nz(txt))
        if len(n) < 12:
            return None
        strip = lambda k: re.sub(r"^(and|well|so) ", "", k)
        inside = [(len(k), a, b) for k, a, b in timed if n in strip(k)]
        if inside:  # 이 줄을 통째로 담은 구간 중 가장 짧은 것
            _, a, b = min(inside)
            return (a, b)
        parts = [(a, b) for k, a, b in timed if len(strip(k)) >= 12 and strip(k) in n]
        return (min(x[0] for x in parts), max(x[1] for x in parts)) if parts else None  # 여러 구간에 걸친 줄
    rx = [r for r in (expr_regex(x.get("en", "")) for x in p.get("expressions", [])) if r]
    n = [0]

    def box(m):
        inner = m.group(1)
        spans = re.findall(r'<span class="en">(.*?)</span>', inner)
        hits = [when(t) for t in spans]
        if not any(hits):
            return m.group(0)  # 영상 속 장면이 아니면(예문·공식 등) 그대로
        n[0] += 1
        for t in spans:
            p.setdefault("_scene_of", {})[re.sub(r"^(and|well|so) ", "", _nz(t))] = n[0]
        st = min(h[0] for h in hits if h); en = max(h[1] for h in hits if h)
        btn = f'<button class="sh-play sc-play" type="button" data-t="{st}" data-end="{en}" data-n="1">{ICON_PLAY}{mmss(st)} 이 장면 듣기</button>'
        it = iter(hits)

        def line(mm):
            txt, h = mm.group(1), next(it)
            for r in rx:
                f = r.search(txt)
                if f and "<mark" not in txt:
                    txt = txt[:f.start()] + '<mark class="xhl">' + f.group(0) + "</mark>" + txt[f.end():]
            if h:  # 이 줄도 원본 영상으로 듣기
                txt += f'<button class="sh-play say-v" type="button" data-t="{h[0]}" data-end="{h[1]}" data-n="1" aria-label="영상에서 듣기">{SAY_V}</button>'
            return f'<span class="en">{txt}</span>'
        inner = re.sub(r'<span class="en">(.*?)</span>', line, inner)
        return f'<div class="box scene" id="sc{n[0]}"><div class="sc-h"><span class="sc-n">SCENE {n[0]:02d}</span>{btn}</div><ul class="ex">{inner}</ul></div>'
    return re.sub(r'<div class="box"><ul class="ex">(.*?)</ul></div>', box, body, flags=re.S)


def expr_strip(p):
    xs = p.get("expressions") or []
    if not xs:
        return ""
    return (f'<nav class="xstrip no-print" aria-label="이 영상에서 건질 표현"><b>이 영상에서 건질 표현 {len(xs)}개</b><div>'
            + "".join(f'<a href="#x{i + 1}">{e(x["en"])}</a>' for i, x in enumerate(xs)) + "</div></nav>")


def page_post(p):
    url = post_url(p)
    video = p.get("video")
    _lv = level(p)
    parts = [f'<span class="chip {p["cat"]}">{CATS[p["cat"]]}</span><span class="chip {p["cat"]}">{e(p.get("sub", ""))}</span><span class="lv lv-{"pro" if _lv == "실전" else "base"}" title="{"일·뉴스·연설, 뉘앙스까지" if _lv == "실전" else "처음 봐도 바로 쓰는 생활 표현"}">{_lv}</span>',
             f'<h1>{e(p["title"])}</h1><p class="lead">{e(p.get("lead", ""))}</p><p class="date-line">{e(p.get("date", ""))}{(" · " + e(p["updated"]) + " 수정") if p.get("updated") and p["updated"] != p.get("date") else ""}</p>']
    tint = re.search(r"#[0-9A-Fa-f]{6}", chat_bg(p["id"])).group(0)
    if not video and p.get("chat"):
        c = p["chat"]
        art = icon_img(p["icon"], lazy=False) if p.get("icon") else ""
        parts.append('<div class="post-hero">' + chat_html(c["q"], c["a"], c.get("key", ""), c.get("ko", ""), art, chat_bg(p["id"]), big=True) + '</div>')
    toc_slot = len(parts)
    if video:
        parts.append(video_block(video, p["title"], "표현의 <b>듣기</b>·<b>3번 반복</b>으로 따라 말해 보세요"))
        parts.append(expr_strip(p))
    toc = []
    _body = post_dress(add_heading_ids(alt_chips(p.get("body_html", "")), toc), tint)
    if video:
        _body = scene_dress(_body, p)
    parts.append('<div class="pb">' + _body + '</div>')
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
            orig_html = f'<div class="orig">{e(x["orig"])}' + (f'<span class="orig-ko">{e(x["origKo"])}</span>' if x.get("origKo") else "") + '</div>'
            on = re.sub(r"^(and|well|so) ", "", _nz(x.get("orig", "")))
            scn = next((v for k, v in p.get("_scene_of", {}).items() if on and len(k) >= 12 and (k in on or on in k)), None)
            if scn:  # 원문은 위 장면 카드에 이미 있으니, 여기선 장면으로 돌아가는 링크만 (중복 없이)
                orig_html = f'<a class="xp-from" href="#sc{scn}"><span>SCENE {scn:02d}</span>에서 나온 표현 · 장면 다시 보기 ↑</a>'

            parts.append(f"""<div class="box xp" id="x{xi + 1}">
  <h3>{e(x['en'])}{ts}</h3><div>{e(x['ko'])}</div>
  {orig_html}
  {shadow}
  <ul class="ex"><li><span class="en">{e(x['ex'])}</span><span class="ko">{e(x['exKo'])}</span></li></ul>
  <div class="memo" style="margin-bottom:0"><b class="lbl">연상법</b> {e(x['memo'])}</div>
</div>""")
    if p.get("think") in THINK_BY_ID:
        parts.append(f'<div class="think-box"><b>이 영상 속 마음에 남는 문장</b>은 <a href="{think_url(THINK_BY_ID[p["think"]])}">사유의 문장</a>에서 필사하고 복기할 수 있어요.</div>')
    parts.append(post_say_block(p))
    parts.append('<h2 class="quiz-h" id="quiz-sec">오늘 배운 거 확인하기</h2><div id="quiz"></div>')
    if p.get("note"):
        parts.append(f'<div class="study-note"><b class="lbl">스터디 노트</b> {p["note"]}</div>')
    parts.append(END_CTA)
    parts.append(share_block("이 글 출력 · 공유"))
    tv_ids = [pid for _, _, pid in TRAVEL_SITUATIONS if pid in POST_BY_ID]
    if p["id"] in tv_ids:
        k = tv_ids.index(p["id"])
        name_of = {pid: (nm, ic) for nm, ic, pid in TRAVEL_SITUATIONS}
        if k + 1 < len(tv_ids):
            nx = POST_BY_ID[tv_ids[k + 1]]; nm, ic = name_of[nx["id"]]
            parts.append(f'<div class="tv-next no-print"><span class="tv-next-h">여행영어 {k + 1}/{len(tv_ids)} · 다음 상황</span>'
                         + act_row(icon_img(ic, "act-img"), e(nm) + " 영어", e(nx["title"]), href=post_url(nx)) + '</div>')
        else:
            parts.append('<div class="tv-next no-print"><span class="tv-next-h">여행영어 10가지 상황을 다 봤어요</span>'
                         + act_row(icon_img("passport-control", "act-img"), "처음부터 복습하기", "7일 플랜과 무료 PDF 보러 가기", href="/travel/") + '</div>')
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
    parts.append(AUTHOR_SIG)
    parts.insert(toc_slot, f'<details class="toc-m no-print"><summary>목차 · 퀴즈 바로가기</summary>{toc_html(toc)}</details>')
    links = related_links(p)
    link_items = "".join('<li><a href="%s">%s</a></li>' % (l["href"], e(l["label"])) for l in links)
    aside = (f'<div class="side-box"><h4>이 글의 목차</h4>{toc_html(toc)}</div>'
             f'<div class="side-box"><h4>복습하기</h4><div class="acts">'
             + act_row(SVG_QUIZ, "퀴즈 풀기", f"{len(p['quiz'])}문제 · 1분", href="#quiz-sec")
             + act_row(SVG_BOOK, "내 공부방", "틀린 문제 다시 보기", href="/notes/#wrong", right='<span class="n-pill js-notes-count"></span>')
             + act_row(SVG_PRINT, "출력 · PDF 저장", "A4 복습지", cls="js-print") + '</div></div>'
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
        cards.append(f"""<div class="quote qc no-print" id="q{i + 1}" data-id="{t['id']}:{i}" data-i="{i}">
  <div class="qtop"><span class="qn">SENTENCE {i + 1:02d} / {len(t['quotes']):02d}</span><span class="qm" aria-hidden="true">”</span>
  <p class="en">{e(q['en'])}</p><p class="ko">{e(q['ko'])}</p>
  {seg_buttons(q['t'], q_end(q)) if t.get('video') else ''}</div>
  <div class="qbot"><div class="think-box"><b class="lbl">생각해 보기</b> {e(q['think'])}<span class="ask">{e(q['ask'])}</span></div>
  <button type="button" class="qwr" aria-expanded="false"><span>✍️ 직접 써 보기<small>필사 · 빈칸 복기 · 나의 한 줄</small></span><i>›</i></button>
  <div class="qwr-b" hidden>
  <div class="tabs"><button class="on" data-mode="copy">필사하기</button><button data-mode="blank">빈칸 복기</button></div>
  <div class="pane"></div>
  <div style="margin-top:14px;font-size:14px;font-weight:700">나의 한 줄</div>
  <textarea class="note" placeholder="이 문장이 나에게 주는 의미를 한 줄로 남겨 보세요" style="min-height:60px;margin-top:6px"></textarea>
  <div class="row"><button class="btn ghost save-note">저장</button></div>
  </div></div>
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
<div class="end-cta no-print"><small>다 따라 썼다면, 마지막 한 걸음</small><b class="ec-t">오늘 쓴 문장, 내 필사 노트에 모여요</b>
<span class="ec-s">필사한 문장과 나의 한 줄은 내 공부방에서 언제든 다시 볼 수 있어요</span><div class="ec-a"><a class="ec-l" href="/notes/#copy">필사 노트 보기 ›</a></div></div>
{share_block("필사 노트 출력 · 공유", "필사 출력")}
{f'<a class="end-app end-kk no-print" href="{e(SITE["kakao"])}" target="_blank" rel="noopener"><img src="/assets/kakao-talk.png" alt="" width="26" height="24" loading="lazy"><span><b>매일 아침 문장 하나</b> · 카톡으로 받기</span><em>받기 ›</em></a>' if SITE.get("kakao") else ""}
<div class="print-only ws">{ws_head("필사 노트 - " + t["title"], t["speaker"], t.get("video"), url)}{ws}</div>"""
    data = {"type": "think", "id": t["id"], "title": t["title"], "speaker": t["speaker"], "url": url,
            "quotes": [{"en": q["en"], "ko": q["ko"], "blanks": q["blanks"]} for q in t["quotes"]]}
    qlist = "".join(f'<li><a href="#q{i + 1}">{e(q["en"][:42] + ("…" if len(q["en"]) > 42 else ""))}</a></li>' for i, q in enumerate(t["quotes"]))
    aside = (f'<div class="side-box"><h4>문장 목록</h4><ol class="toc">{qlist}</ol></div>'
             f'<div class="side-box"><h4>복습하기</h4><div class="acts">'
             + act_row(SVG_PEN, "내 필사 노트", "써 둔 문장 다시 보기", href="/notes/#copy")
             + act_row(SVG_PRINT, "필사 노트 출력", "A4로 따라 쓰기", cls="js-print")
             + (act_row(SVG_PLAY, "영상 표현 보기", "이 영상의 영어표현", href=post_url(post)) if post else "") + '</div></div>' + side_common())
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



# 목록 페이지 소개글 (페이지마다 다르게 — 같은 문장 복사 금지). 설명 1문단 + 길이 맞춘 팁 3개(아이콘 카드)
def _about_box(title, para, items):
    tips = "".join(f'<li><img src="/assets/icons/{ic}.webp?v={ASSET_V}" alt="" width="28" height="28" loading="lazy"><span><b>{a}</b>{b}</span></li>' for ic, a, b in items)
    return f'<section class="cat-about"><h2>{title}</h2><p>{para}</p><ul class="ca-tips">{tips}</ul></section>'
CAT_ABOUT = {
    "expr": _about_box("영어표현은 이렇게 정리해요",
        "원어민이 매일 쓰는 짧은 표현을 골라, 뉘앙스 → 비슷한 표현 비교 → 자주 하는 실수 → 퀴즈 순서로 정리해요.",
        [("speech-balloon", "처음이라면", "'기초'부터 보세요"), ("laptop", "회사·메일이라면", "'실전'을 골라요"), ("check", "복습은", "내 공부방에 모여요")]),
    "tip": _about_box("영어꿀팁에서는 이런 걸 다뤄요",
        "여행 문장, 생활 회화, 연음과 발음, 콩글리시까지. '왜 그런지'를 먼저 설명하고 바로 쓸 문장을 보여 줘요.",
        [("airplane", "여행 전이라면", "여행 시리즈부터"), ("ear", "듣기가 막히면", "연음 글부터"), ("mobile-phone", "말하기 전에", "콩글리시 점검")]),
    "story": _about_box("영어 이야기는 이렇게 읽어요",
        "매일 쓰는 단어가 어디서 왔는지 옛 신문, 편지, 사진 같은 실제 기록으로 따라가요. 출처가 확인된 이야기만 쓰고, 잘못 알려진 설은 따로 구분해요.",
        [("light-bulb", "가볍게 읽고", "단어의 숨은 사연"), ("speech-balloon", "바로 써 보기", "지금 쓰는 예문"), ("check", "기억하기", "퀴즈 3문제")]),
    "video": _about_box("영상으로 배우기는 이렇게 봐요",
        "인터뷰와 연설을 장면 단위로 나눠, 짧게 인용하고 길게 해설해요. '이 장면 듣기'로 원본 목소리를 바로 들을 수 있어요.",
        [("headphone", "먼저", "자막 없이 듣기"), ("page", "그다음", "장면 해설 읽기"), ("check", "마지막", "표현 5개와 퀴즈")]),
    "think": _about_box("사유의 문장은 이렇게 써요",
        "영상 속 곱씹을 문장을 따라 쓰고(필사), 빈칸으로 다시 떠올리고(복기), 나의 한 줄을 남기는 공간이에요.",
        [("page", "한 문장씩", "필사부터 시작"), ("light-bulb", "생각해 보기", "나의 한 줄 남기기"), ("check", "모아 보기", "필사 노트에 쌓여요")]),
}
SERIES_ABOUT = {
    "travel": _about_box("이 시리즈를 이렇게 활용하세요",
        "기내부터 입국, 호텔, 식당, 문제 상황까지 여행 순서대로 묶었어요. 직원이 하는 말을 먼저 듣고, 내 대답을 짧게 익혀요.",
        [("calendar", "출발 일주일 전", "하루 1~2편씩"), ("passport-control", "공항 가는 길", "PDF로 마지막 복습"), ("ear", "현지에서", "QR로 발음 듣기")]),
    "work": _about_box("이 시리즈를 이렇게 활용하세요",
        "회의, 메일, 메신저에서 원어민 동료가 매일 쓰는 짧은 표현이에요. 상사·동료·고객에 따라 말투를 맞추는 법도 함께 담았어요.",
        [("laptop", "메일 쓰기 전", "메일 표현부터"), ("speech-balloon", "회의 중에는", "walk me through"), ("check", "답장할 때", "I'm on it")]),
    "mistakes": _about_box("이 시리즈를 이렇게 활용하세요",
        "문법은 맞는데 뜻이 반대로 전해지는 영어를 모았어요. 한국어 습관 때문에 틀리는 이유를 먼저 짚고 바로잡아요.",
        [("question-mark", "가장 많이 틀리는", "부정 의문문 대답"), ("grimacing-face", "의외의 함정", "would you mind"), ("mobile-phone", "말하기 전에", "콩글리시 점검")]),
    "leaders": _about_box("이 시리즈를 이렇게 활용하세요",
        "세계 무대에 선 리더들의 실제 연설과 인터뷰예요. 어떤 구조로 말했고 어떤 표현이 청중을 움직였는지 해설해요.",
        [("headphone", "듣기 연습", "이 장면 듣기"), ("studio-microphone", "발표 준비", "연설 구조 따라 하기"), ("page", "말하기 연습", "사유의 문장 필사")]),
}

def page_category(cat):
    url = f"/category/{cat}/"
    def one_filter(title, keys):  # 한 그룹 필터 (영상: 종류, 사유의 문장: 인물)
        ks = [k for k in dict.fromkeys(keys) if k]
        b = lambda v, n, lbl, on="": f'<button type="button" class="sf-b{on}" data-sub="{e(v)}"><span>{e(lbl)}</span><em>{n}</em></button>'
        view = ""
        if cat in ("video", "think"):  # PC 오른쪽: 영상으로 배우기 ↔ 사유의 문장 (휴대폰에서는 숨기고 위쪽 전환 사용)
            n = {"video": sum(1 for p in POSTS if p["cat"] == "video"), "think": len(THINKS)}
            view = ('<div class="sf-g sf-view" role="group" aria-label="보기"><div class="sf-h">보기</div>'
                    + "".join(f'<a class="sf-a{" on" if k == cat else ""}" href="/category/{k}/"><span>{CATS[k]}</span><em>{n[k]}</em></a>' for k in ("video", "think")) + '</div>')
        return (f'<aside class="subfilter sf-one" aria-label="{title}"><div class="sf-g" role="group" aria-label="{title}"><div class="sf-h">{title}</div>'
                + b("", len(keys), "전체", " on") + "".join(b(k, keys.count(k), k) for k in ks) + f'</div>{view}<p class="sf-empty" hidden>이 조합의 글은 아직 없어요</p></aside>')
    if cat == "think":
        items = THINKS
        who = [t.get("theme") or "기타" for t in THINKS]  # 주제(겸손·관계·흔들릴 때 …) — 새 글마다 content/think/*.json 의 "theme"
        cards = "".join(think_card(t, 2).replace(' href=', f' data-sub="{e(w)}" href=', 1) for t, w in zip(THINKS, who))
        filt = one_filter("주제", sorted(who, key=["겸손", "관계", "흔들릴 때"].index if all(w in ["겸손", "관계", "흔들릴 때"] for w in who) else None))
        body = (APP_HEAD(cat) + APP_SEG(cat) +
                f'<div class="cat-grid has-filter"><div class="cards list">{cards}</div>{filt}</div>' + CAT_ABOUT.get(cat, ""))
    elif cat == "video":
        items = [p for p in POSTS if p["cat"] == cat]
        kind = lambda sub: "강의" if "강의" in sub else "인터뷰" if "인터뷰" in sub else "대담" if "대담" in sub else "연설"
        kinds = [kind(p.get("sub", "")) for p in items]
        cards = "".join(re.sub(r' data-sub="[^"]*"', "", post_card(p, 2), 1).replace(' href=', f' data-sub="{k}" href=', 1) for p, k in zip(items, kinds))
        order = [k for k in ["연설", "인터뷰", "대담", "강의"] if k in kinds]
        filt = one_filter("종류", sorted(kinds, key=order.index))
        body = (APP_HEAD(cat) + APP_SEG(cat) +
                f'<div class="cat-grid has-filter"><div class="cards list">{cards}</div>{filt}</div>' + CAT_ABOUT.get(cat, ""))
    elif cat == "story":
        items = [p for p in POSTS if p["cat"] == cat]
        cards = "".join(post_card(p, 2) for p in items)
        subs = [p.get("sub", "") for p in items]
        filt = one_filter("분류", subs) if len(set(subs)) > 1 else ""
        body = (f'<h1>{CATS[cat]}</h1><p class="lead">{CAT_LEAD[cat]}</p>'
                f'<div class="cat-grid{" has-filter" if filt else ""}"><div class="cards list">{cards}</div>{filt}</div>' + CAT_ABOUT.get(cat, ""))
    else:
        items = [p for p in POSTS if p["cat"] == cat]
        cards = "".join(post_card(p, 2) for p in items) or '<div class="empty"><p>곧 첫 글이 올라와요.</p></div>'
        subs = [x for x in dict.fromkeys(p.get("sub", "") for p in items) if x]
        filt = ""
        if cat != "video" and items:
            btn = lambda v, n, lbl, on="": f'<button type="button" class="sf-b{on}" data-sub="{e(v)}"><span>{e(lbl)}</span><em>{n}</em></button>'
            lvb = lambda v, n, lbl, on="": f'<button type="button" class="sf-b sf-lv{on}" data-lv="{v}"><span>{lbl}</span><em>{n}</em></button>'
            lvs = [level(p) for p in items]
            g_lv = ('<div class="sf-g" role="group" aria-label="난이도"><div class="sf-h">난이도</div>' + lvb("", len(items), "전체", " on")
                    + lvb("기초", lvs.count("기초"), "기초") + lvb("실전", lvs.count("실전"), "실전") + "</div>")
            g_sub = ('<div class="sf-g" role="group" aria-label="분류"><div class="sf-h">분류</div>' + btn("", len(items), "전체", " on")
                     + "".join(btn(x, sum(1 for p in items if p.get("sub") == x), x) for x in subs) + "</div>") if len(subs) > 1 else ""
            filt = f'<aside class="subfilter" aria-label="글 고르기">{g_lv}{g_sub}<p class="sf-empty" hidden>이 조합의 글은 아직 없어요</p></aside>'
        body = (f'<h1>{CATS[cat]}</h1><p class="lead">{CAT_LEAD[cat]}</p>'
                f'<div class="cat-grid{" has-filter" if filt else ""}"><div class="cards list">{cards}</div>{filt}</div>' + CAT_ABOUT.get(cat, ""))
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
    sn = sr.get("notice") or (TRAVEL_NOTICE if sr["id"] == "travel" else None)
    body = (f'<div class="chips"><span class="chip">아티클 시리즈</span></div><h1>{e(sr["title"])}</h1><p class="lead">{e(sr.get("lead") or sr["desc"])}</p>'
            + (notice_html(sn) if sn else "") +
            f'<div class="cat-grid"><div class="cards list">{cards}</div></div>' + SERIES_ABOUT.get(sr["id"], ""))
    ld = [{"@type": "CollectionPage", "name": sr["title"], "description": sr["desc"], "url": DOMAIN + url, "inLanguage": "ko"},
          {"@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"},
              {"@type": "ListItem", "position": 2, "name": sr["title"], "item": DOMAIN + url}]}]
    img = og_image("s-" + sr["id"], "아티클 시리즈", sr["title"], sr["desc"], "읽고 · 듣고 · 퀴즈로 확인")
    return layout(sr["title"], sr["desc"] + ". 예문과 원어민 발음 듣기, 퀴즈로 함께 복습해요.", url, body, wide=True, seo_title=f'{sr["title"]} - 영어 공부 시리즈', ld=ld, og_img=img)


def daily_index(n):
    """한국 날짜 기준으로 매일 하나씩 돌아가며 (app.js와 같은 계산)"""
    import time
    return int((time.time() + 9 * 3600) // 86400) % n



def notice_html(n=None):
    """홈 공지 배너 — site.json 의 notice {label, title, sub, href} 가 있을 때만 보여요. n을 주면 그 내용으로 그려요."""
    n = n or SITE.get("notice")
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
    def mq_data(d):
        """폰 첫 화면 퀴즈: 상대 말 → (가려진) 내 대답 → 원어민 발음"""
        p = POST_BY_ID.get(d.get("post")) or {}
        norm = lambda t: re.sub(r"[^a-z' ]", "", t.lower()).strip()
        en = d["en"]; k = norm(en.replace("~", ""))
        q, a, ako = "", en, ""
        c = p.get("chat")
        if c and k and k[:12] in norm(c["a"]):
            q, a, ako = c["q"], c["a"], c.get("ko", "")
        else:
            x = next((x for x in p.get("expressions", []) if norm(x["en"]) == k), None)
            if x:
                parts = re.split(r"(?<=[.!?])\s+", x["ex"].strip())
                if len(parts) > 1:
                    q, a = " ".join(parts[:-1]), parts[-1]
        ic = f'/assets/icons/{p["icon"]}.webp?v={ASSET_V}' if p.get("icon") else ""
        return {"q": q, "qa": a, "qk": ako, "au": ("/audio/" + AUDIO[en]) if en in AUDIO else "", "ic": ic}
    slides_data = [{"en": d["en"], "ko": d["ko"], "desc": d.get("desc", ""), "cat": d["cat"], "url": d["url"],
                    "vis": vis(POST_BY_ID.get(d.get("post")), d, n), **mq_data(d)} for n, d in enumerate(daily)]
    N_SLIDES = min(7, len(slides_data))
    def slide_html(it, label):
        w = it["en"].split(" ")
        ph = e(" ".join(w[:-1])) + (" " if len(w) > 1 else "") + f'<span class="hl">{e(w[-1])}</span>'
        return (f'<article class="hs-slide"><div class="hs-txt"><div class="a-kicker">{e(label)} · {e(it["cat"])}</div>'
                f'<p class="a-phrase{" long" if len(it["en"]) > 16 else ""}">{ph}</p><p class="a-mean">{e(it["ko"])}</p>'
                f'<p class="a-desc">{e(it["desc"])}</p><div class="hs-btns">' + ('<a class="btn hs-rt" href="/notes/#routine">5분 루틴으로 내 것 만들기 →</a>' if label == "오늘의 한 잔" else "") + f'<a class="btn ghost" href="{it["url"]}">글 읽고 퀴즈 풀기 →</a></div></div>'
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
    _pool = today_pool()
    _gp = [(g["id"], g["icon"], g["short"], g["desc"]) for g in TODAY_GOALS]
    picker = ('<section class="gp" id="gp" aria-label="지금 필요한 영어 고르기"><p class="gp-q">지금 어떤 영어가 필요하세요? <small>가입 없이 · 무료 · 하루 5분</small></p><div class="gp-row">'
              + "".join(f'<a class="gp-c" href="/notes/?goal={g}#routine" data-goal="{g}"><img src="/assets/icons/{icn}.webp?v={ASSET_V}" alt="" width="40" height="40"><b>{t}</b>'
                        f'<small>{d}</small></a>' for g, icn, t, d in _gp)
              + '</div></section>')
    SPK = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>'
    PLAY = '<svg class="mq-pl" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M7 4.5v15l13-7.5z" fill="currentColor"/></svg>'
    def mq_card(it, lab, md):
        q = f'<span class="mq-q">{e(it["q"])}</span>' if it["q"] else ""
        qa = f'<span class="mq-a">{e(it["qa"])}</span>' if it["q"] else ""
        w = it["en"].split(" ")
        en_h = e(" ".join(w[:-1])) + (" " if len(w) > 1 else "") + f'<span class="hl">{e(w[-1])}</span>'
        ic = f'<img class="mq-ic" src="{it["ic"]}" alt="" width="56" height="56" loading="lazy">' if it["ic"] else ""
        return (f'<article class="mq" data-a="{it["au"]}">{ic}<p class="mq-k"><span>{e(lab)}</span><span>{md}</span></p>'
                f'<h2 class="mq-h">"{e(it["ko"])}"<br>영어로 하면?</h2>'
                f'<div class="mq-ans"><span class="mq-en">{en_h}</span><button type="button" class="mq-sp" aria-label="발음 다시 듣기">{SPK}</button></div>'
                f'<div class="mq-chat">{q}<button type="button" class="mq-me">{PLAY}눌러서 정답 듣기</button>{qa}</div>'
                f'<a class="mq-btn" href="/notes/#routine">5분 루틴으로 내 것 만들기</a>'
                f'<a class="mq-link" href="{it["url"]}">왜 이렇게 말할까? 글 읽고 퀴즈 풀기 ›</a></article>')
    def mq_md(k):
        g = _t.gmtime(now_k - k * 86400)
        return f"{g.tm_mon}월 {g.tm_mday}일"
    mq = ('<section class="mqs" id="mqs" aria-label="최근 일주일 한 잔 퀴즈"><div class="mq-tr" id="mq-tr">'
          + "".join(mq_card(slides_data[(i0 - k) % len(slides_data)], label(k, now_k), mq_md(k)) for k in range(N_SLIDES))
          + '</div><div class="mq-dots" id="mq-dots"></div></section>') if slides_data else ""
    kk = SITE.get("kakao", "")
    intro = ('<section class="hi" aria-label="카페인영어 소개"><div class="hi-t"><span class="hi-k">CafeInEnglish</span>'
             '<p class="hi-h">영상으로 배우는 <em>진짜 영어표현</em></p><span class="hi-s">하루 5분 · 가입 없이 무료</span></div>'
             + (f'<a class="hi-btn" href="{e(kk)}" target="_blank" rel="noopener"><img src="/assets/kakao-talk.png" alt="" width="24" height="22">매일 아침 1일 1영 받기<i>›</i></a>' if kk else "")
             + '</section>')
    hero = '<div class="m-home">' + intro + picker + mq + notice_html().replace('class="notice"', 'class="notice m-nt"', 1) + '</div>' + f"""<section class="hs" aria-label="오늘의 한 잔">
  <div class="hs-track" id="hs-track">{slides}</div>
  <div class="hs-ctl"><button type="button" class="hs-btn" id="hs-prev" aria-label="이전 표현"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M15 6l-6 6 6 6"/></svg></button><button type="button" class="hs-btn" id="hs-next" aria-label="다음 표현"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M9 6l6 6-6 6"/></svg></button><span class="hs-dots" id="hs-dots"></span></div>
</section>"""
    slides_js = json.dumps(slides_data, ensure_ascii=False).replace("</", "<\\/")
    hero_js = """<script>(function(){var L=%s,n=Math.min(7,L.length);if(!n)return;var day=Math.floor((Date.now()/1000+9*3600)/86400),i0=day%%L.length,tr=document.getElementById("hs-track");
if(i0!==%d){var x=function(t){return String(t).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})};
var lab=function(k){if(!k)return"오늘의 한 잔";if(k===1)return"어제의 한 잔";var d=new Date((day-k)*86400000);return(d.getUTCMonth()+1)+"월 "+d.getUTCDate()+"일의 한 잔"};
tr.innerHTML=Array.from({length:n},function(_,k){var it=L[((i0-k)%%L.length+L.length)%%L.length],w=it.en.split(" "),last=w.pop();
return '<article class="hs-slide"><div class="hs-txt"><div class="a-kicker">'+lab(k)+' · '+x(it.cat)+'</div><p class="a-phrase'+(it.en.length>16?' long':'')+'">'+(w.length?x(w.join(" "))+" ":"")+'<span class="hl">'+x(last)+'</span></p><p class="a-mean">'+x(it.ko)+'</p><p class="a-desc">'+x(it.desc||"")+'</p><div class="hs-btns">'+(k?'':'<a class="btn hs-rt" href="/notes/#routine">5분 루틴으로 내 것 만들기 →</a>')+'<a class="btn ghost" href="'+it.url+'">글 읽고 퀴즈 풀기 →</a></div></div><a class="hs-art" href="'+it.url+'" tabindex="-1" aria-hidden="true">'+it.vis+'</a></article>'}).join("")}
window.KY_W={L:L,i0:i0,day:day,n:n};var mt=document.getElementById("mq-tr");if(mt){var X=function(t){return String(t).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})},
SPK=mt.querySelector(".mq-sp").innerHTML,PL=mt.querySelector(".mq-pl").outerHTML,
lb=function(k){if(!k)return"오늘의 한 잔";if(k===1)return"어제의 한 잔";var d=new Date((day-k)*86400000);return(d.getUTCMonth()+1)+"월 "+d.getUTCDate()+"일의 한 잔"},
md=function(k){var d=new Date((day-k)*86400000);return(d.getUTCMonth()+1)+"월 "+d.getUTCDate()+"일"},
seen=[];try{seen=JSON.parse(localStorage.getItem("ky_mq_seen")||"[]")}catch(e){}
mt.innerHTML=Array.from({length:n},function(_,k){var T=L[((i0-k)%%L.length+L.length)%%L.length],w=T.en.split(" "),wl=w.pop(),dk=day-k;
return '<article class="mq'+(seen.indexOf(dk)>-1?' seen':'')+'" data-a="'+(T.au||"")+'" data-d="'+dk+'" data-k="'+k+'">'+(T.ic?'<img class="mq-ic" src="'+T.ic+'" alt="" width="56" height="56"'+(k?' loading="lazy"':'')+'>':'')
+'<p class="mq-k"><span>'+lb(k)+'</span><span>'+md(k)+'</span></p><h2 class="mq-h">"'+X(T.ko)+'"<br>영어로 하면?</h2>'
+'<div class="mq-ans"><span class="mq-en">'+(w.length?X(w.join(" "))+" ":"")+'<span class="hl">'+X(wl)+'</span></span><button type="button" class="mq-sp" aria-label="발음 다시 듣기">'+SPK+'</button></div>'
+'<div class="mq-chat">'+(T.q?'<span class="mq-q">'+X(T.q)+'</span>':'')+'<button type="button" class="mq-me">'+PL+'눌러서 정답 듣기</button>'+(T.q?'<span class="mq-a">'+X(T.qa)+'</span>':'')+'</div>'
+'<a class="mq-btn" href="/notes/#routine">5분 루틴으로 내 것 만들기</a><a class="mq-link" href="'+T.url+'">왜 이렇게 말할까? 글 읽고 퀴즈 풀기 ›</a></article>'}).join("");
var au=new Audio(),say=function(c){var a=c.getAttribute("data-a");if(!a)return;try{if(au.src.indexOf(a)<0)au.src=a;au.currentTime=0;au.play().catch(function(){})}catch(e){}};
mt.addEventListener("click",function(ev){var c=ev.target.closest(".mq");if(!c)return;if(ev.target.closest(".mq-me")){c.classList.add("on");say(c);var dk=+c.getAttribute("data-d");if(seen.indexOf(dk)<0){seen.push(dk);seen=seen.slice(-14);try{localStorage.setItem("ky_mq_seen",JSON.stringify(seen))}catch(e){}}
mp();if(window.gtag)gtag("event","quiz_reveal",{days_ago:+c.getAttribute("data-k")})}else if(ev.target.closest(".mq-sp"))say(c)});
var md2=document.getElementById("mq-dots");md2.innerHTML=Array.from({length:n},function(){return"<i></i>"}).join("");
var mp=function(){var w=mt.firstElementChild?mt.firstElementChild.offsetWidth+10:1,c=Math.round(mt.scrollLeft/w);[].forEach.call(md2.children,function(d,j){d.className=j===c?"on":""});var cc=mt.children[c];if(cc)mt.style.height=cc.offsetHeight+"px"};
mt.addEventListener("scroll",function(){clearTimeout(mt._t);mt._t=setTimeout(mp,50)},{passive:true});mp();addEventListener("resize",mp);KY_W.fit=mp;if(window.ResizeObserver){var ro=new ResizeObserver(function(){mp()});[].forEach.call(mt.children,function(c){ro.observe(c)})}}
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
        icons = sr.get("icons") or [o["icon"] for o in sp if o.get("icon")][:3]
        if icons:
            cover = f'<div class="sr-cover ic-{sr.get("bg") or sp[0]["cat"]}">' + "".join(f'<img src="/assets/icons/{ic}.webp?v={ASSET_V}" alt="" loading="lazy" width="96" height="96">' for ic in icons) + "</div>"
        else:
            vids = [o for o in sp if o.get("video")]
            lazy = 'loading="lazy"'
            cover = ('<div class="sr-cover yt">' + yt_img(vids[0]["video"], lazy).replace("<img ", '<img aria-hidden="true" class="yt-bg" ', 1) + yt_img(vids[0]["video"], lazy).replace("<img ", '<img class="yt-fg" ', 1) + '</div>') if vids else '<div class="sr-cover"></div>'
        series_html += (f'<a class="sr-card" href="/series/{sr["id"]}/">{cover}<h3>{e(sr["title"])}</h3>'
                        f'<p>{e(sr["desc"])}</p><span class="sr-n">글 {len(sp) + len(sr.get("thinks", []))}개</span></a>')

    body = f"""<h1 class="sr-only">카페인영어 CafeInEnglish - 매일 조금씩, 깊게 스며드는 영어 공부</h1>
<div class="pc-band">{hero}{hero_js}
{notice_html()}</div>
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
    return layout(SITE["name"], SITE.get("description") or SITE["tagline"], "/", body, wide=True, ld=ld, data={"type": "home", "daily": daily}, preload=pre)


TODAY_CTA = ('<div class="acts rt-cta no-print"><a class="act" href="/notes/#routine"><span class="act-ic"><img src="/assets/icons/hot-beverage.webp" alt="" width="22" height="22"></span>'
             '<span class="act-t"><b>오늘의 한 잔 5분 루틴</b><small>듣기 · 말하기 · 복습하고, 내 공부방에서 도장 찍기</small></span><span class="act-r"><i class="chev">›</i></span></a></div>')
TODAY_GOALS = [
    {"id": "talk", "short": "일상 대화", "name": "일상 대화 영어", "desc": "인사·스몰톡", "icon": "speech-balloon",
     "posts": ["how-are-you", "excuse-me-sorry", "ask-to-repeat", "sounds-good", "im-down", "im-good", "craving", "its-on-me", "my-bad",
               "looking-forward-to", "sorry-to-hear", "negative-question", "would-you-mind", "what-do-you-call", "in-vs-after", "konglish", "make-sense"]},
    {"id": "travel", "short": "여행", "name": "해외여행 영어", "desc": "공항·호텔", "icon": "airplane", "series": "travel"},
    {"id": "work", "short": "회사", "name": "회사 영어", "desc": "메일·회의", "icon": "laptop", "series": "work"},
    {"id": "life", "short": "해외 생활", "name": "해외 생활 영어", "desc": "이민·유학", "icon": "world-map",
     "posts": ["ask-to-repeat", "what-do-you-call", "id-like-to", "asking-directions", "shopping-checkout", "doctor", "this-vs-next",
               "email-phrases", "would-you-mind", "travel-trouble", "video-call"]},
]


def _say_clean(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip()


def post_say_items(p, limit=None):
    """글 속 내가 말할 문장(원어민 음성 있는 짧은 문장)을 글 순서대로"""
    body = p.get("body_html", "")
    pairs = []
    for m in re.finditer(r'<ul class="ex( ans| talk)?">(.*?)</ul>', body, re.S):
        ul, talk = m.group(2), m.group(1) == " talk"
        for li in re.finditer(r'<li( class="[^"]*")?>(.*?)</li>', ul, re.S):
            if talk and li.group(1) != ' class="me"':
                continue
            k = re.search(r'<span class="en">(.*?)</span><span class="ko">(.*?)</span>', li.group(2), re.S)
            if k:
                pairs.append((m.start() + li.start(), k.group(1), k.group(2)))
    for m in re.finditer(r'<div class="rep-a"><span class="en">(.*?)</span><span class="ko">(.*?)</span>', body, re.S):
        pairs.append((m.start(), m.group(1), m.group(2)))
    n = len(body)
    for i, x in enumerate(p.get("expressions", [])):
        for en, ko in ((x.get("orig", ""), x.get("origKo", "")), (x.get("ex", ""), x.get("exKo", ""))):
            if en and ko:
                pairs.append((n + i * 2, e(en), e(ko)))
    items, seen = [], set()
    for _, en, ko in sorted(pairs, key=lambda t: t[0]):
        en, ko = _say_clean(en), _say_clean(ko)
        ko = re.sub(r"\s*\([^)]*\)\s*$", "", ko).strip()
        if en in seen or en not in AUDIO or not ko or not 8 <= len(en) <= 60 or any(c in en for c in "→/…") or "..." in en:
            continue
        seen.add(en)
        items.append({"en": en, "ko": ko, "a": "/audio/" + AUDIO[en], "p": post_url(p)})
    return items[:limit] if limit else items


def post_say_block(p):
    """글 끝 '입으로 마무리하기': 핵심 문장 3개를 한국어만 보고 말해 보기"""
    items = post_say_items(p)
    if not items:
        return ""
    # 오늘의 한 잔에 쓰인 대표 문장이 있으면 맨 앞으로
    top = [d["en"] for d in json.loads((CONTENT / "daily.json").read_text("utf-8")) if d.get("post") == p["id"]] if (CONTENT / "daily.json").exists() else []
    items.sort(key=lambda x: 0 if x["en"] in top else 1)
    picks, step = [], max(1, len(items) // 3)
    for i in range(0, len(items), step):
        picks.append(items[i])
        if len(picks) == 3:
            break
    data = json.dumps(picks, ensure_ascii=False).replace("</", "<\\/")
    return (f'<section class="ps no-print" id="say-end" aria-label="입으로 마무리하기"><p class="ps-k">입으로 마무리하기</p>'
            f'<h3>방금 배운 문장, 소리 내어 말해 볼까요?</h3><div class="ps-body"></div>'
            f'<script type="application/json" class="ps-data">{data}</script></section>')


def today_pool():
    """목표별 '오늘의 5분' 문장 목록: 시리즈 글 예문 중 원어민 음성이 있는 짧은 문장"""
    pool = {}
    sr_posts = {sr["id"]: sr["posts"] for sr in SERIES}
    for g in TODAY_GOALS:
        ids = g.get("posts") or sr_posts.get(g.get("series"), [])
        items, seen = [], set()
        for pid in ids:
            p = POST_BY_ID.get(pid)
            if not p:
                continue
            body = p.get("body_html", "")
            pairs = []  # (위치, en, ko) — 내가 말할 문장만: 일반 예문, '이렇게 대답해요', 대화 속 '나', 바로 쓰는 문장
            for m in re.finditer(r'<ul class="ex( ans| talk)?">(.*?)</ul>', body, re.S):
                ul, talk = m.group(2), m.group(1) == " talk"
                for li in re.finditer(r'<li( class="[^"]*")?>(.*?)</li>', ul, re.S):
                    if talk and li.group(1) != ' class="me"':
                        continue
                    k = re.search(r'<span class="en">(.*?)</span><span class="ko">(.*?)</span>', li.group(2), re.S)
                    if k:
                        pairs.append((m.start() + li.start(), k.group(1), k.group(2)))
            for m in re.finditer(r'<div class="rep-a"><span class="en">(.*?)</span><span class="ko">(.*?)</span>', body, re.S):
                pairs.append((m.start(), m.group(1), m.group(2)))
            for _, en, ko in sorted(pairs):
                    en = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", en))).strip()
                    ko = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", ko))).strip()
                    ko = re.sub(r"\s*\([^)]*\)\s*$", "", ko).strip()  # 끝의 (정중)·(격식 있는 메일) 같은 메모는 빼고
                    if en in seen or en not in AUDIO or not ko or not 8 <= len(en) <= 60 or any(c in en for c in "→/…") or "..." in en:
                        continue
                    seen.add(en)
                    items.append({"en": en, "ko": ko, "a": "/audio/" + AUDIO[en], "p": post_url(p)})
        # 시리즈 글 순서 = 실제 상황 순서 (여행: 기내 → 입국 → 이동 → 호텔 → 카페·식당 → 쇼핑 → 문제 상황)
        pool[g["id"]] = items
    return pool


def page_today():
    """예전 주소 /today/ → 내 공부방 루틴으로 이동"""
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="robots" content="noindex">'
            f'<link rel="canonical" href="{DOMAIN}/notes/"><meta http-equiv="refresh" content="0;url=/notes/#routine">'
            '<title>내 공부방 | 카페인영어</title></head><body><a href="/notes/#routine">내 공부방으로 이동</a></body></html>')


def daily_routine():
    """오늘의 한 잔 목록 (홈과 같은 순서) + 음성"""
    out = []
    if (CONTENT / "daily.json").exists():
        for d in json.loads((CONTENT / "daily.json").read_text("utf-8")):
            p = POST_BY_ID.get(d["post"])
            if p and d["en"] in AUDIO:
                out.append({"en": d["en"], "ko": d["ko"], "a": "/audio/" + AUDIO[d["en"]], "p": post_url(p)})
    return out


SVG_DL = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 19h16"/></svg>'
SVG_UL = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15V3"/><path d="M7 8l5-5 5 5"/><path d="M4 19h16"/></svg>'
BACKUP_HTML = ('<section class="bk no-print" id="backup"><h2 class="nb-h">기록 백업 <small>폰을 바꾸거나 앱으로 옮길 때</small></h2><div class="acts bk-acts">'
               + act_row(SVG_DL, "내 기록 내보내기", "오답노트 · 필사 · 연속 기록을 파일 하나로 저장", cls="js-bk-out")
               + act_row(SVG_UL, "기록 가져오기", "저장한 파일을 불러와 지금 기록에 합쳐요", cls="js-bk-in")
               + '</div><input type="file" accept="application/json,.json" class="js-bk-file" hidden>'
               '<p class="bk-note">기록은 이 기기에만 저장돼요. 내보낸 파일을 새 폰이나 앱에서 가져오면 그대로 이어져요.</p></section>')


def page_notes():
    pool = today_pool()
    goals = [{**{k: g[k] for k in ("id", "name", "short")}, "icon": f'/assets/icons/{g["icon"]}.webp?v={ASSET_V}'} for g in TODAY_GOALS if pool.get(g["id"])]
    ON = ' class="on"'
    tabs = [("today", "오늘", ""), ("wrong", "오답노트", '<i class="nbt-n js-tn-w" hidden></i>'), ("copy", "필사 노트", ""), ("log", "기록", "")]
    body = ('<h1>내 공부방</h1>'
            '<div class="nb-band"><div class="nbt no-print" role="tablist" aria-label="내 공부방">'
            + "".join(f'<button type="button" role="tab" data-tab="{k}" aria-selected="{"true" if k == "today" else "false"}"{ON if k == "today" else ""}>{t}{c}</button>' for k, t, c in tabs)
            + '</div>'
            '<div class="nbp" data-p="today"><div id="today-app"></div></div>'
            '<div class="nbp" data-p="wrong" id="wrong" hidden><div id="notes-root"></div></div>'
            '<div class="nbp" data-p="copy" id="copy" hidden><span id="copy-count" hidden>0</span><div id="copy-notes"></div></div>'
            '<div class="nbp" data-p="log" id="log" hidden>' + NB_APP + '<div id="log-app"></div>'
            + BACKUP_HTML + '</div></div>'
            f'<script src="/assets/today.js?v={ASSET_V}" defer></script>')
    norm_t = lambda t: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip()
    qa = {norm_t(q["en"]): "/audio/" + AUDIO[norm_t(q["en"])] for t in THINKS for q in t.get("quotes", []) if norm_t(q.get("en", "")) in AUDIO}
    data = {"type": "notes", "kakao": SITE.get("kakao", ""), "daily": daily_routine(), "pool": pool, "goals": goals, "qa": qa,
            "cup": f"/assets/icons/hot-beverage.webp?v={ASSET_V}", "phone": f"/assets/icons/mobile-phone.webp?v={ASSET_V}"}
    return layout("내 공부방", "오늘의 한 잔 5분 루틴과 이번 주 도장, 말해 본 문장, 퀴즈 오답노트와 필사 노트를 모아 복습하는 나만의 공부방",
                  "/notes/", body, "notes", data, wide=True, robots="noindex,follow")


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



def _about_acts():
    items = [("headphone", "영상으로 배우기", "셀럽 인터뷰·연설 장면을 구간별로 듣고 3번 반복", "/category/video/"),
             ("speech-balloon", "영어표현 · 영어꿀팁", "새 표현, 헷갈리는 표현, 생활 회화 요령", "/category/expr/"),
             ("world-map", "여행영어 무료 PDF", "공항부터 호텔까지 10가지 상황 · 7일 플랜", "/travel/"),
             ("check", "퀴즈와 내 공부방", "틀린 문제는 모였다가, 다시 맞히면 졸업", "/notes/")]
    out = ""
    for ic, t, sub, href in items:
        out += act_row(icon_img(ic, "act-img"), e(t), e(sub), href=href, cls="about-act") if href else (
            f'<div class="act about-act"><span class="act-ic">{icon_img(ic, "act-img")}</span><span class="act-t"><b>{e(t)}</b><small>{e(sub)}</small></span><span class="act-r"></span></div>')
    return out


def _about_series():
    html = ""
    for sr in SERIES:
        sp = [POST_BY_ID[i] for i in sr["posts"] if i in POST_BY_ID]
        icons = sr.get("icons") or [o["icon"] for o in sp if o.get("icon")][:3]
        if icons:
            cover = f'<div class="sr-cover ic-{sr.get("bg") or sp[0]["cat"]}">' + "".join(f'<img src="/assets/icons/{ic}.webp?v={ASSET_V}" alt="" loading="lazy" width="96" height="96">' for ic in icons) + "</div>"
        else:
            vids = [o for o in sp if o.get("video")]
            cover = ('<div class="sr-cover yt">' + yt_img(vids[0]["video"], 'loading="lazy"').replace("<img ", '<img aria-hidden="true" class="yt-bg" ', 1) + yt_img(vids[0]["video"], 'loading="lazy"').replace("<img ", '<img class="yt-fg" ', 1) + '</div>') if vids else '<div class="sr-cover"></div>'
        html += (f'<a class="sr-card" href="/series/{sr["id"]}/">{cover}<h3>{e(sr["title"])}</h3>'
                 f'<p>{e(sr["desc"])}</p><span class="sr-n">글 {len(sp) + len(sr.get("thinks", []))}개</span></a>')
    return html


def _about_kakao():
    kakao = SITE.get("kakao")
    yt = SITE.get("youtube")
    btn = (f'<a class="btn kakao tv-kk-btn" href="{e(kakao)}" target="_blank" rel="noopener"><i class="kk-dot"><svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true"><path fill="#191919" d="M12 3C6.5 3 2 6.6 2 11c0 2.8 1.9 5.3 4.7 6.7L5.8 21l4-2.6c.7.1 1.4.2 2.2.2 5.5 0 10-3.6 10-8S17.5 3 12 3z"/></svg></i>1일 1영 받아보기</a>' if kakao else "")
    ytb = (f'<a class="about-yt" href="{e(yt)}" target="_blank" rel="noopener">유튜브 채널 보기 ›</a>' if yt else "")
    return (f'<div class="tv-kk about-kk"><div class="tv-kk-l"><span class="lbl">매일 한 잔</span><b>매일 아침 7시, 표현 하나씩 카톡으로</b>'
            f'<span>거창한 계획 말고, 커피 한 잔 마시는 마음으로. 무료예요.</span><div class="about-kk-btns">{btn}{ytb}</div></div>'
            '<div class="tv-kk-msg" aria-hidden="true"><div class="tv-kk-top"><span>카페인영어</span><span>오전 7:00</span></div>'
            '<div class="tv-kk-bub">오늘의 한 잔<b>I\'m on it.</b>바로 할게요</div></div></div>')

ABOUT_CARD = _about_card()
def _audio_n():
    try:
        return len(json.loads((Path(__file__).resolve().parent / "audio" / "index.json").read_text("utf-8")))
    except Exception:
        return 0
_ig = SITE.get("instagram"); _yt = SITE.get("youtube")
ABOUT = f"""
<div class="abh"><span class="k">ABOUT CAFEINENGLISH</span><h2>영상으로 배우는 <em>진짜 영어표현</em>,<br>하루 5분</h2>
<p>인터뷰와 연설 속 원어민의 말을 장면으로 듣고, 뜻과 뉘앙스를 해설하고, 퀴즈와 복습으로 내 것으로 만드는 곳이에요. 가입 없이 무료예요.</p>
<div class="abs"><div><b>1만+</b><span>유튜브 구독자</span></div><div><b>{len(POSTS)}편</b><span>해설 글</span></div><div><b>{_audio_n()}개</b><span>예문 음성</span></div></div></div>
<h2>카페인영어를 만든 이유</h2>
<p>안녕하세요. 카페인영어 운영자입니다.</p>
<p>저는 한국에서 영어를 배운 평범한 사람입니다. 외우고, 시험 보고, 취업을 위해 점수를 만들고. 그렇게 오랫동안 영어를 '공부'해 왔는데, 어느 날 돌아보니 제게 남은 건 점수였지 언어가 아니더라고요.</p>
<p>'점수를 위한 영어'가 아니라 '생각을 넓히는 영어'를 하자는 마음에서 시작했습니다.</p>
<p>영어는 <b>생각을 넓혀 주는 도구</b>입니다. 새로운 언어로 세상을 보면 만나는 사람과 이야기가 달라지고, 생각의 폭도 그만큼 넓어진다고 생각해요. 그래서 이 영어라는 언어를 <b>쉽고 재미있게</b>, 함께 공부하며 성장하고 싶은 사람들을 위한 마음으로 카페인영어를 만들었습니다. 매일 조금씩, 하지만 깊게. 영어로 함께 성장했으면 좋겠습니다.</p>
<div class="abq"><img src="/assets/icon-192.png" alt="" width="52" height="52"><div><b>매일 한 잔의 커피처럼, 대화 속 진짜 영어를 꾸준히.</b><span>오늘의 한 문장에 마침표를 찍는 곳, CafeInEnglish.</span></div></div>
<h2>이런 걸 할 수 있어요</h2>
<div class="about-acts">{_about_acts()}</div>
<h2>아티클 시리즈</h2>
<p class="about-sub">상황별로 모아 두었어요. 필요한 곳부터 골라 보세요.</p>
<div class="sr-grid about-sr">{_about_series()}</div>
<h2>콘텐츠는 이렇게 만들어요</h2>
<p class="about-sub">믿고 공부할 수 있도록, 글을 만들 때 지키는 원칙이에요.</p>
<div class="ab-prin">
<div><b>실제로 쓰이는 표현만</b><span>영상·인터뷰·사전에서 실제로 쓰인 표현만 골라요.</span></div>
<div><b>인용은 짧게, 해설은 길게</b><span>원문은 짧게 인용하고, 쓰임과 팁은 직접 풀어 써요.</span></div>
<div><b>예문과 음성</b><span>예문은 직접 쓰고, 음성은 원어민 억양의 AI 음성이에요.</span></div>
<div><b>틀리면 고쳐요</b><span>오류는 <a href="/contact/">문의</a>로 알려 주세요. 고친 글엔 수정일을 남겨요.</span></div>
</div>
<h2>운영자</h2>
<div class="abo"><img src="/assets/icon-192.png" alt="" width="56" height="56"><div><b>카영 스터디언</b><small>유튜브 카페인영어 운영 · 2026년 9월부터 사이트 운영<br>오류 제보와 제안은 언제든 환영해요.</small>
<div class="lk"><a href="/contact/">문의하기</a>{f'<a href="{e(_yt)}" target="_blank" rel="noopener">유튜브</a>' if _yt else ""}{f'<a href="{e(_ig)}" target="_blank" rel="noopener">인스타그램</a>' if _ig else ""}</div></div></div>
{_about_kakao()}
"""
PRIVACY = f"""
<div class="pv-sum">
<div class="pv-item">{icon_img("raised-hand", "pv-ic")}<b>회원가입 없음</b><span>이름·연락처를 묻지 않아요</span></div>
<div class="pv-item">{icon_img("mobile-phone", "pv-ic")}<b>기록은 내 기기에만</b><span>오답노트·필사는 브라우저에 저장</span></div>
<div class="pv-item">{icon_img("speech-balloon", "pv-ic")}<b>문의 이메일은 답장에만</b><span>답변 후 1년 보관, 요청 시 즉시 삭제</span></div>
</div>
<p>{e(SITE['name'])}(이하 '사이트')는 이용자의 개인정보를 소중히 여기며, 「개인정보 보호법」 등 관련 법령을 지킵니다. 이 방침은 {e(DOMAIN.replace('https://', ''))} 에 적용됩니다.</p>
<h2>1. 수집하는 정보와 목적</h2>
<p>사이트는 회원가입 없이 이용할 수 있으며, 이름·연락처 같은 개인정보를 따로 요구하지 않습니다. 다만 아래의 경우에 한해 최소한의 정보를 처리합니다.</p>
<ul>
<li><b>문의하기</b>: 답장 받을 이메일 주소와 문의 내용 — 문의에 답변하기 위해서만 사용합니다.</li>
<li><b>방문 통계</b>: 방문 페이지, 이용 시간, 기기·브라우저 종류, 대략적인 지역 등 개인을 알아볼 수 없는 정보 — 사이트 개선을 위해 사용합니다.</li>
</ul>
<h2>2. 보유 기간과 파기</h2>
<p>문의 내용과 이메일은 답변을 마친 뒤 1년간 보관했다가 삭제합니다. 이용자가 삭제를 요청하면 바로 삭제합니다. 방문 통계는 Google Analytics 설정에 따라 보관 기간이 지나면 자동으로 삭제됩니다.</p>
<h2>3. 처리를 맡기는 곳 (위탁·국외 이전)</h2>
<ul>
<li><b>FormSubmit</b> (formsubmit.co, 미국): 문의 양식의 내용을 운영자 메일함으로 전달합니다.</li>
<li><b>Google</b> (미국): 방문 통계(Google Analytics), 광고(Google AdSense), 영상(YouTube) 서비스를 제공합니다.</li>
</ul>
<p>위 경우 외에는 이용자의 정보를 제3자에게 제공하지 않습니다.</p>
<h2>4. 브라우저에만 저장되는 기록</h2>
<p>오답노트, 필사 기록, '나의 한 줄', 학습 진도는 이용자 기기의 브라우저(localStorage)에만 저장되며 사이트 서버로 전송되지 않습니다. 브라우저의 사이트 데이터를 삭제하면 기록도 함께 삭제됩니다.</p>
<h2>5. 쿠키와 광고</h2>
<p>사이트는 방문 통계와 광고를 위해 쿠키를 사용합니다. Google을 포함한 제3자 공급업체는 쿠키를 사용해 이용자의 이전 방문 기록을 바탕으로 광고를 게재할 수 있습니다.</p>
<ul>
<li>맞춤 광고 해제: <a href="https://adssettings.google.com" target="_blank" rel="noopener">Google 광고 설정</a> · 자세한 내용은 <a href="https://policies.google.com/technologies/ads" target="_blank" rel="noopener">Google 광고 정책</a></li>
<li>방문 통계 거부: <a href="https://tools.google.com/dlpage/gaoptout" target="_blank" rel="noopener">Google Analytics 차단 부가기능</a></li>
<li>쿠키 거부: 브라우저 설정에서 쿠키 저장을 막을 수 있어요. 이 경우에도 사이트 이용에는 문제가 없습니다.</li>
</ul>
<h2>6. 외부 서비스</h2>
<p>사이트에 삽입된 YouTube 영상, 그리고 연결된 카카오톡 오픈채팅·인스타그램·유튜브 채널은 각 서비스의 개인정보처리방침이 적용됩니다.</p>
<h2>7. 이용자의 권리</h2>
<p>이용자는 언제든 자신의 정보에 대해 열람, 정정, 삭제, 처리 정지를 요청할 수 있습니다. 아래 이메일로 요청하시면 지체 없이 처리합니다.</p>
<h2>8. 개인정보 보호책임자</h2>
<p>카페인영어 운영자 · {email_html}</p>
<h2>9. 방침의 변경</h2>
<p>이 방침이 바뀌면 이 페이지에서 알려드립니다.</p>
<p>시행일: 2026년 10월 8일 (이전 버전: 2026년 10월 1일)</p>"""
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


# ── 앱 설치 안내 (/app/) ──────────────────────────────────────────────
# 리틀리·인스타의 '앱 설치' 버튼이 가리키는 주소. 들어온 곳(인스타·카톡 앱 안, 아이폰 Safari, 안드로이드, PC)에 따라 안내가 바뀌어요.
# 사이트 다른 페이지는 인앱 브라우저에서도 그대로 보이게 두고, 이 페이지에서만 외부 브라우저로 안내해요.
APP_CSS = """
.ap{max-width:560px;margin:0 auto}
.ap-hero{text-align:center;padding:8px 0 4px}
.ap-hero img.ap-icon{width:96px;height:96px;border-radius:22px;box-shadow:0 10px 28px rgba(25,31,40,.18)}
.ap-hero h1{font-size:28px;margin:18px 0 8px;line-height:1.35}
.ap-hero p{color:#4E5968;margin:0;font-size:16px}
.ap-ben{display:grid;gap:10px;margin:26px 0 22px}
.ap-cmp{margin:0 0 22px;background:#F7F8FA;border-radius:22px;padding:14px 10px 12px;text-align:center}
.ap-cmp img{width:100%;height:auto;display:block}
.ap-cmp figcaption{font-size:14px;color:#6B7684;margin-top:6px}
.ap-ben div{display:flex;gap:14px;align-items:center;background:#F2F4F6;border-radius:18px;padding:14px 16px}
.ap-ben img{width:44px;height:44px;flex:none}
.ap-ben b{display:block;font-size:16px;color:#191F28}
.ap-ben small{display:block;color:#6B7684;font-size:14px;margin-top:2px}
.ap-box{border:1px solid #E5E8EB;border-radius:22px;padding:22px 20px;background:#fff}
.ap-box h2{font-size:20px;margin:0 0 6px}
.ap-box>p{color:#4E5968;margin:0 0 16px;font-size:15px}
.ap-steps{list-style:none;padding:0;margin:0 0 16px;display:grid;gap:10px}
.ap-steps li{display:flex;gap:12px;align-items:flex-start;font-size:16px;color:#191F28;line-height:1.5}
.ap-steps li i{flex:none;width:26px;height:26px;border-radius:50%;background:#191F28;color:#fff;font-style:normal;font-size:14px;font-weight:700;display:flex;align-items:center;justify-content:center;margin-top:1px}
.ap-steps .k{display:inline-flex;align-items:center;gap:4px;background:#F2F4F6;border-radius:8px;padding:1px 8px;font-weight:700;white-space:nowrap}
.ap-btn{display:flex;width:100%;align-items:center;justify-content:center;gap:8px;border:0;border-radius:14px;padding:16px;font-size:17px;font-weight:700;cursor:pointer;text-decoration:none;font-family:inherit}
.ap-btn.pri{background:#3182F6;color:#fff}
.ap-btn.sub{background:#fff;color:#191F28;border:1px solid #E5E8EB;margin-top:10px}
.ap-note{font-size:13px;color:#8B95A1;margin:14px 0 0;line-height:1.6}
.ap-qr{display:flex;gap:20px;align-items:center}
.ap-qr .q{flex:none;width:150px;height:150px;border:1px solid #E5E8EB;border-radius:16px;padding:8px;background:#fff}
.ap-qr .q svg{width:100%;height:100%;display:block}
.ap-pane{display:none}.ap-pane.on{display:block}
.ap-toast{position:fixed;left:50%;bottom:32px;transform:translateX(-50%);background:#191F28;color:#fff;padding:12px 18px;border-radius:12px;font-size:15px;opacity:0;transition:opacity .2s;pointer-events:none;z-index:99}
.ap-toast.on{opacity:1}
.ap-more{text-align:center;margin:22px 0 0;font-size:15px}
.ap-more a{color:#4E5968}
@media (max-width:599px){.ap-qr{flex-direction:column;text-align:center}}
.ap-guide{margin-top:16px}
.ap-tabs{display:flex;gap:6px;background:#F2F4F6;border-radius:14px;padding:4px;margin:0 0 16px}
.ap-tabs button{flex:1;border:0;background:transparent;border-radius:11px;padding:10px;font-size:15px;font-weight:700;color:#6B7684;cursor:pointer;font-family:inherit}
.ap-tabs button.on{background:#fff;color:#191F28;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.ap-tp{display:none}.ap-tp.on{display:block}
.ap-tp h3{font-size:16px;margin:14px 0 8px;color:#191F28}
.ap-tp h3:first-child{margin-top:0}
"""

SHARE_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7"/><path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/></svg>'
PLUS_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="4"/><path d="M12 8v8M8 12h8"/></svg>'


def page_app():
    url = DOMAIN + "/app/"
    ben = [("hot-beverage", "앱을 열면 바로 오늘의 5분", "오늘의 한 잔 · 이번 주 도장이 첫 화면"),
           ("mobile-phone", "주소창 없이 넓게, 아래 탭으로 이동", "영상 · 표현 · 꿀팁 · 내 공부방이 손가락 하나로"),
           ("check", "오답노트 · 필사가 한곳에", "틀린 문제와 따라 쓴 문장이 차곡차곡"),
           ("rocket", "앱스토어 없이 1초 설치", "가입 없이 무료 · 휴대폰 용량도 거의 안 써요")]
    bh = "".join(f'<div>{icon_img(i, "", False)}<span><b>{e(t)}</b><small>{e(s)}</small></span></div>' for i, t, s in ben)
    copy_btn = '<button class="ap-btn sub js-ap-copy" type="button">주소 복사하기</button>'
    body = f"""<style>{APP_CSS}</style>
<div class="ap">
<div class="ap-hero"><img class="ap-icon" src="/assets/icon-192.png?v=3" alt="카페인영어 앱 아이콘" width="96" height="96">
<h1>카페인영어를 앱으로</h1><p>홈 화면에서 한 번에, 매일 5분 영어</p></div>
<div class="ap-ben">{bh}</div>
<figure class="ap-cmp"><img src="/assets/app-compare.webp?v={ASSET_V}" alt="웹 브라우저 화면과 카영 앱 화면 비교: 앱은 주소창 없이 전체 화면이고 아래 탭으로 이동해요" width="1064" height="1186" loading="lazy"><figcaption>같은 카영이라도, 앱으로 열면 이렇게 달라요</figcaption></figure>

<div class="ap-box ap-pane" id="ap-inapp-ios"><h2>Safari에서 열어 주세요</h2>
<p>인스타·스레드 같은 앱 안에서는 홈 화면에 추가할 수 없어요. 딱 한 번만 Safari로 열면 돼요.</p>
<ol class="ap-steps"><li><i>1</i><span>화면의 <span class="k">···</span> 버튼을 눌러요</span></li>
<li><i>2</i><span><span class="k">외부 브라우저에서 열기</span>를 눌러요</span></li>
<li><i>3</i><span>Safari에서 이 페이지가 다시 열리면 안내대로 추가해요</span></li></ol>
{copy_btn}<p class="ap-note">메뉴가 안 보이면 주소를 복사해 Safari 주소창에 붙여 넣어 주세요.</p></div>

<div class="ap-box ap-pane" id="ap-inapp-and"><h2>크롬에서 열어 주세요</h2>
<p>앱 안의 브라우저에서는 설치가 안 돼요. 버튼을 누르면 크롬으로 열려요.</p>
<a class="ap-btn pri js-ap-chrome" href="#">크롬으로 열기</a>{copy_btn}
<p class="ap-note">안 열리면 오른쪽 위 ⋮ 메뉴에서 '다른 브라우저로 열기'를 눌러 주세요.</p></div>

<div class="ap-box ap-pane" id="ap-kakao"><h2>브라우저로 여는 중이에요</h2>
<p>카카오톡 안에서는 설치가 안 돼서, 외부 브라우저로 바로 넘겨 드릴게요.</p>
<a class="ap-btn pri js-ap-kakao" href="#">브라우저로 열기</a>{copy_btn}</div>

<div class="ap-box ap-pane" id="ap-ios"><h2>홈 화면에 추가하기</h2>
<p>세 번만 누르면 끝나요.</p>
<ol class="ap-steps"><li><i>1</i><span>아래쪽 <span class="k">{SHARE_SVG} 공유</span> 버튼을 눌러요 <small style="color:#8B95A1">(안 보이면 ··· 버튼 안에 있어요)</small></span></li>
<li><i>2</i><span>목록을 올려 <span class="k">{PLUS_SVG} 홈 화면에 추가</span>를 눌러요</span></li>
<li><i>3</i><span>오른쪽 위 <span class="k">추가</span>를 누르면 끝!</span></li></ol>
<p class="ap-note">아이폰은 Safari와 홈 화면 앱이 기록을 따로 저장해요. 오답노트·필사는 앱에서 시작하는 걸 추천해요.</p></div>

<div class="ap-box ap-pane" id="ap-and"><h2>앱 설치하기</h2>
<p>버튼 한 번이면 홈 화면에 카페인영어가 생겨요.</p>
<button class="ap-btn pri js-ap-install" type="button">카페인영어 앱 설치</button>
<ol class="ap-steps js-ap-manual" style="display:none;margin-top:16px"><li><i>1</i><span>오른쪽 위 <span class="k">⋮</span> 메뉴를 눌러요</span></li>
<li><i>2</i><span><span class="k">홈 화면에 추가</span> 또는 <span class="k">앱 설치</span>를 눌러요</span></li></ol></div>

<div class="ap-box ap-pane" id="ap-pc"><h2>휴대폰으로 설치하기</h2>
<div class="ap-qr"><div class="q">{qr_svg(url)}</div>
<div><p style="margin:0 0 8px;color:#4E5968">휴대폰 카메라로 QR을 비추면 이 페이지가 열려요. 안내대로 홈 화면에 추가하면 끝이에요.</p>
<button class="ap-btn sub js-ap-install" type="button" style="display:none">이 PC에 앱으로 설치</button></div></div></div>

<div class="ap-box ap-pane" id="ap-done"><h2>이미 앱으로 보고 있어요</h2>
<p>오늘의 5분부터 시작해 볼까요?</p><a class="ap-btn pri" href="/notes/?src=app">오늘의 한 잔 열기</a></div>

<div class="ap-box ap-guide" id="ap-guide"><h2>휴대폰별 설치 방법</h2>
<p>쓰는 휴대폰을 골라 보세요.</p>
<div class="ap-tabs"><button type="button" data-t="ios">아이폰</button><button type="button" data-t="and">안드로이드</button></div>
<div class="ap-tp" data-t="ios"><h3>Safari에서</h3>
<ol class="ap-steps"><li><i>1</i><span>Safari로 cafeinenglish.com/app 을 열어요</span></li>
<li><i>2</i><span>아래쪽 <span class="k">{SHARE_SVG} 공유</span> 버튼을 눌러요 <small style="color:#8B95A1">(안 보이면 ··· 버튼 안)</small></span></li>
<li><i>3</i><span><span class="k">{PLUS_SVG} 홈 화면에 추가</span> → 오른쪽 위 <span class="k">추가</span></span></li></ol>
<p class="ap-note" style="margin-top:0">인스타·카톡 안에서 열었다면 먼저 Safari로 열어 주세요.</p></div>
<div class="ap-tp" data-t="and"><h3>크롬에서</h3>
<ol class="ap-steps"><li><i>1</i><span>크롬으로 cafeinenglish.com/app 을 열어요</span></li>
<li><i>2</i><span><span class="k">카페인영어 앱 설치</span> 버튼을 눌러요. 버튼이 없으면 오른쪽 위 <span class="k">⋮</span> 메뉴를 눌러요</span></li>
<li><i>3</i><span><span class="k">홈 화면에 추가</span> 또는 <span class="k">앱 설치</span> → <span class="k">설치</span></span></li></ol>
<h3>삼성 인터넷에서</h3>
<ol class="ap-steps"><li><i>1</i><span>아래쪽 <span class="k">≡</span> 메뉴를 눌러요</span></li>
<li><i>2</i><span><span class="k">현재 페이지 추가</span> → <span class="k">홈 화면</span>을 눌러요</span></li></ol>
<p class="ap-note" style="margin-top:0">인스타·카톡 안에서 열었다면 먼저 크롬이나 삼성 인터넷으로 열어 주세요.</p></div>
</div>

<p class="ap-more"><a href="/">앱 없이 사이트로 둘러보기 ›</a></p>
</div>
<div class="ap-toast" id="ap-toast">주소를 복사했어요</div>
<script>
(function(){{
var U="{url}",ua=navigator.userAgent||"",$=function(s){{return document.querySelector(s)}},$$=function(s){{return document.querySelectorAll(s)}};
var ios=/iPhone|iPad|iPod/i.test(ua)||(navigator.platform==="MacIntel"&&navigator.maxTouchPoints>1),and=/Android/i.test(ua);
var kakao=/KAKAOTALK/i.test(ua),inapp=kakao||/Instagram|FBAN|FBAV|FB_IAB|Barcelona|Threads|NAVER|Line\\/|DaumApps|everytimeApp|BAND|wv\\)/i.test(ua);
var standalone=(window.matchMedia&&matchMedia("(display-mode: standalone)").matches)||navigator.standalone;
function show(id){{var p=$("#"+id);if(p)p.classList.add("on")}}
function toast(t){{var el=$("#ap-toast");el.textContent=t;el.classList.add("on");setTimeout(function(){{el.classList.remove("on")}},1800)}}
function copy(){{(navigator.clipboard?navigator.clipboard.writeText(U):Promise.reject()).then(function(){{toast("주소를 복사했어요")}},function(){{var t=document.createElement("textarea");t.value=U;document.body.appendChild(t);t.select();try{{document.execCommand("copy");toast("주소를 복사했어요")}}catch(e){{prompt("주소를 복사해 주세요",U)}}t.remove()}})}}
$$(".js-ap-copy").forEach(function(b){{b.addEventListener("click",copy)}});
var kk="kakaotalk://web/openExternal?url="+encodeURIComponent(U),ch="intent://"+U.replace(/^https?:\\/\\//,"")+"#Intent;scheme=https;package=com.android.chrome;end";
var a1=$(".js-ap-kakao");if(a1)a1.href=kk;var a2=$(".js-ap-chrome");if(a2)a2.href=ch;
var dp=null;
window.addEventListener("beforeinstallprompt",function(ev){{ev.preventDefault();dp=ev;$$(".js-ap-install").forEach(function(b){{b.style.display=""}})}});
window.addEventListener("appinstalled",function(){{toast("설치됐어요! 홈 화면을 확인해 보세요")}});
$$(".js-ap-install").forEach(function(b){{b.addEventListener("click",function(){{if(dp){{dp.prompt();dp.userChoice.then(function(c){{try{{window.gtag&&gtag("event","app_install_choice",{{outcome:c&&c.outcome}})}}catch(e){{}}dp=null}})}}else{{var m=$(".js-ap-manual");if(m)m.style.display="";b.style.display="none"}}}})}});
function tab(t){{$$(".ap-tabs button").forEach(function(b){{b.classList.toggle("on",b.dataset.t===t)}});$$(".ap-tp").forEach(function(p){{p.classList.toggle("on",p.dataset.t===t)}})}}
$$(".ap-tabs button").forEach(function(b){{b.addEventListener("click",function(){{tab(b.dataset.t)}})}});
tab(and?"and":"ios");
try{{window.gtag&&gtag("event","app_page_view",{{env:standalone?"app":kakao?"kakao":(inapp&&ios)?"inapp_ios":(inapp&&and)?"inapp_and":ios?"ios":and?"android":"pc"}})}}catch(e){{}}
if(standalone){{show("ap-done");var g=$("#ap-guide");if(g)g.style.display="none"}}
else if(kakao){{show("ap-kakao");setTimeout(function(){{location.href=kk}},400)}}
else if(inapp&&ios)show("ap-inapp-ios");
else if(inapp&&and)show("ap-inapp-and");
else if(ios)show("ap-ios");
else if(and){{show("ap-and");setTimeout(function(){{if(!dp){{var m=$(".js-ap-manual");if(m)m.style.display=""}}}},2500)}}
else show("ap-pc");
}})();
</script>"""
    return layout("카페인영어 앱 설치", "카페인영어를 홈 화면 앱으로 설치하세요. 앱을 열면 오늘의 5분 루틴부터, 오답노트·필사도 한곳에. 가입 없이 무료.",
                  "/app/", body, "", None, robots="noindex,follow")



def search_index():
    """사이트 안 검색용 색인 (/search.json) — 제목·설명·표현(영어/한국어)·예문"""
    def strip(h):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()
    out = []
    for p in POSTS:
        terms = []
        for x in p.get("expressions") or []:
            terms.append([x.get("en", ""), x.get("ko", "")])
        for en, ko in re.findall(r'<span class="en">(.*?)</span>\s*<span class="ko">(.*?)</span>', p.get("body_html", ""), re.S)[:14]:
            terms.append([strip(en), strip(ko)])
        ch = p.get("chat") or {}
        if ch.get("a"):
            terms.append([ch["a"], ch.get("ko", "")])
        seen, tt = set(), []
        for en, ko in terms:
            k = en.lower()
            if en and k not in seen:
                seen.add(k); tt.append([en, ko])
        out.append({"u": post_url(p), "t": p["title"], "c": CATS.get(p["cat"], ""), "s": p.get("sub", ""),
                    "d": p.get("description") or p.get("lead", ""), "x": tt[:16]})
    for t in THINKS:
        out.append({"u": think_url(t), "t": t["title"], "c": "사유의 문장", "s": t.get("speaker", ""),
                    "d": t.get("description", ""), "x": [[q["en"], q["ko"]] for q in t.get("quotes", [])]})
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


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
TRAVEL_NOTICE = {"label": "무료 자료", "title": "여행영어 PDF, 공항부터 호텔까지", "sub": "10가지 상황 · 7일 플랜 · 원어민 발음 QR", "href": "/travel/"}
TRAVEL_SITUATIONS = [("기내", "airplane", "in-flight"), ("입국심사", "passport-control", "immigration"), ("수하물·세관", "luggage", "baggage-customs"),
                     ("교통", "taxi", "transportation"), ("호텔", "hotel", "hotel-check-in"), ("카페", "hot-beverage", "travel-cafe"), ("식당", "fork-knife-plate", "travel-restaurant"),
                     ("쇼핑·계산", "shopping-bags", "shopping-checkout"), ("길 찾기", "world-map", "asking-directions"), ("문제 상황", "pill", "travel-trouble")]
# 출발 전 7일 플랜: (제목, [글 id], 설명) — 설명의 {0},{1}은 그 글의 질문 수로 자동 채워져요. 줄을 누르면 첫 번째 글로 가요.
TRAVEL_PLAN = [("기내 + 살아남는 문장", ["in-flight"], "승무원 질문 {0}개 · 되묻는 한 문장"),
               ("입국심사 + 수하물·세관", ["immigration", "baggage-customs"], "심사관 질문 {0}개 · 세관 질문 {1}개"),
               ("교통", ["transportation"], "택시·버스·지하철에서 들리는 말 {0}개"),
               ("호텔", ["hotel-check-in"], "체크인 질문 {0}개 · 요청 문장"),
               ("카페 + 식당", ["travel-cafe", "travel-restaurant"], "카페 질문 {0}개 · 서버 질문 {1}개"),
               ("쇼핑 + 길 찾기", ["shopping-checkout", "asking-directions"], "계산대 질문 {0}개 · 길 안내 {1}개"),
               ("문제 상황 + 전체 복습", ["travel-trouble"], "분실·결항·아플 때 · 퀴즈로 마무리")]

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
        n_q += bh.count('<span class="hn">Q')
        ans_en = set(re.findall(r'<div class="rep-a"><span class="en">(.*?)</span>', bh))
        for blk in re.findall(r'<ul class="ex ans">(.*?)</ul>', bh, re.S):
            ans_en |= set(re.findall(r'<span class="en">(.*?)</span>', blk))
        n_a += len(ans_en)
    icon_of = {pid: ic for _, ic, pid in TRAVEL_SITUATIONS}
    def qn(pid):
        return POST_BY_ID[pid].get("body_html", "").count('<span class="hn">Q') if pid in POST_BY_ID else 0
    plan = ""
    for i, (title, pids, sub) in enumerate(TRAVEL_PLAN):
        d = len(TRAVEL_PLAN) - i
        ics = "".join(icon_img(icon_of[x], "tv-pi") for x in pids if x in icon_of)
        href = post_url(POST_BY_ID[pids[0]]) if pids[0] in POST_BY_ID else "/travel/"
        plan += (f'<a class="tv-pr{" last" if d == 1 else ""}" href="{href}"><span class="tv-dd"><small>D-</small><b>{d}</b></span>'
                 f'<span class="tv-pt"><b>{e(title)}</b><span>{e(sub.format(*[qn(x) for x in pids]))}</span></span>'
                 f'<span class="tv-pic">{ics}<i class="chev">›</i></span></a>')
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
<div class="tv-plan2">{plan}</div>
<div class="tv-plan-foot"><b>하루 10~15분</b>이면 충분해요. 출발 날짜에 맞춰 D-7부터 시작해 보세요.</div>
<h2>자주 묻는 질문</h2>
{faq_html}
<div class="tv-kk"><div class="tv-kk-l"><span class="lbl">여행 끝나고도</span><b>매일 아침 7시, 표현 하나씩 카톡으로</b>
<span>여행에서 들었던 그 영어, 잊기 전에 하루 한 문장씩 이어가요. 무료예요.</span>
{f'<a class="btn kakao tv-kk-btn" href="{e(kakao)}" target="_blank" rel="noopener"><i class="kk-dot"><svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true"><path fill="#191919" d="M12 3C6.5 3 2 6.6 2 11c0 2.8 1.9 5.3 4.7 6.7L5.8 21l4-2.6c.7.1 1.4.2 2.2.2 5.5 0 10-3.6 10-8S17.5 3 12 3z"/></svg></i>1일 1영 받아보기</a>' if kakao else ""}</div>
<div class="tv-kk-msg" aria-hidden="true"><div class="tv-kk-top"><span>카페인영어</span><span>오전 7:00</span></div><div class="tv-kk-bub">오늘의 한 잔<b>You can't miss it.</b>금방 찾으실 거예요</div></div></div>
</div>"""
    return layout("여행영어 무료 PDF, 공항부터 호텔까지", "입국심사, 호텔, 카페, 식당에서 직원이 실제로 하는 말과 바로 쓰는 대답을 상황별로 정리한 여행영어 무료 자료예요. 원어민 발음 듣기와 출력용 PDF를 함께 드려요.",
                  "/travel/", body, seo_title="여행영어 무료 PDF - 공항부터 호텔까지, 현지에서 들리는 영어")

# ── 영어 생활 도구 (/tools/) ──────────────────────────────────────────────
# 근거: 네이버 월간 검색량 (2026-10-23 조회, 프로젝트 문서 claude/영어도구_검색량_근거.md)
#   영어이름변환기 32,540 · 영어이름 15,470 · 영문이름 14,500 · 한글이름영문변환 12,090 · 여권이름영문변환 7,350
#   영문주소변환 76,300 · 영문주소검색변환 6,210 · 한국주소영문변환 4,070 · 영문주소동호수 1,540
# 영문 주소는 행정안전부 도로명주소 '영문주소 검색 API' 승인키가 있어야 켜져요 → site.json 의 "juso_eng_key"
# 키가 없으면 주소 도구 페이지는 만들되 검색엔진에 안 보이게(noindex) 하고 메뉴·사이트맵에서 빼요.
JUSO_KEY = SITE.get("juso_eng_key", "")
_CHO = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
_JUNG = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]
_JONG = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"]


def rr_word(w):
    """국어의 로마자 표기법 (인명: 음절마다, 음운 변화 미반영 · ㄹㄹ은 ll)"""
    out, prev_l = "", False
    for ch in w:
        c = ord(ch) - 0xAC00
        i, v, f = c // 588, (c % 588) // 28, c % 28
        out += ("l" if i == 5 and prev_l else _CHO[i]) + _JUNG[v] + _JONG[f]
        prev_l = f == 8
    return out[:1].upper() + out[1:]


# 성씨: 자주 보이는 표기 순서 (첫 번째가 추천). 표에는 앞쪽 40개만 보여 주고, 변환기는 전부 써요.
SURNAMES = [
    ("김", ["Kim", "Gim"]), ("이", ["Lee", "Yi", "Rhee"]), ("박", ["Park", "Pak", "Bak"]), ("최", ["Choi", "Choe"]),
    ("정", ["Jung", "Jeong", "Chung"]), ("강", ["Kang", "Gang"]), ("조", ["Cho", "Jo"]), ("윤", ["Yoon", "Yun"]),
    ("장", ["Jang", "Chang"]), ("임", ["Lim", "Im", "Yim"]), ("한", ["Han"]), ("오", ["Oh", "O"]), ("서", ["Seo", "Suh"]),
    ("신", ["Shin", "Sin"]), ("권", ["Kwon", "Gwon"]), ("황", ["Hwang"]), ("안", ["Ahn", "An"]), ("송", ["Song"]),
    ("전", ["Jeon", "Jun", "Chun"]), ("홍", ["Hong"]), ("유", ["Yoo", "Yu", "You"]), ("고", ["Ko", "Go"]), ("문", ["Moon", "Mun"]),
    ("양", ["Yang"]), ("손", ["Son", "Sohn"]), ("배", ["Bae"]), ("백", ["Baek", "Paik", "Baik"]), ("허", ["Heo", "Huh", "Hur"]),
    ("남", ["Nam"]), ("심", ["Shim", "Sim"]), ("노", ["Noh", "Roh", "No"]), ("하", ["Ha"]), ("곽", ["Kwak", "Gwak"]),
    ("성", ["Sung", "Seong"]), ("차", ["Cha"]), ("주", ["Joo", "Ju", "Chu"]), ("우", ["Woo", "U"]), ("구", ["Koo", "Gu", "Ku"]),
    ("민", ["Min"]), ("류", ["Ryu", "Yoo"]), ("나", ["Na", "Ra"]), ("진", ["Jin", "Chin"]), ("지", ["Ji", "Jee"]),
    ("엄", ["Eom", "Um", "Uhm"]), ("채", ["Chae"]), ("원", ["Won"]), ("천", ["Cheon", "Chun"]), ("방", ["Bang"]),
    ("공", ["Kong", "Gong"]), ("현", ["Hyun", "Hyeon"]), ("변", ["Byun", "Byeon"]), ("염", ["Yeom", "Yum"]), ("여", ["Yeo", "Yuh"]),
    ("추", ["Choo", "Chu"]), ("도", ["Do", "Doh"]), ("소", ["So"]), ("석", ["Seok", "Suk"]), ("선", ["Sun", "Seon"]),
    ("설", ["Seol", "Sul"]), ("마", ["Ma"]), ("길", ["Gil", "Kil"]), ("연", ["Yeon", "Youn"]), ("위", ["Wi", "Wee"]),
    ("표", ["Pyo"]), ("명", ["Myung", "Myeong"]), ("기", ["Ki", "Gi"]), ("반", ["Ban", "Bahn"]), ("왕", ["Wang"]),
    ("금", ["Keum", "Geum"]), ("옥", ["Ok"]), ("육", ["Yook", "Yuk"]), ("인", ["In"]), ("맹", ["Maeng"]), ("제", ["Je"]),
    ("모", ["Mo"]), ("탁", ["Tak"]), ("국", ["Kook", "Guk"]), ("어", ["Eo", "Uh"]), ("은", ["Eun"]), ("편", ["Pyun", "Pyeon"]),
    ("용", ["Yong"]), ("예", ["Ye"]), ("경", ["Kyung", "Gyeong"]), ("봉", ["Bong"]), ("사", ["Sa"]), ("부", ["Boo", "Bu"]),
    ("가", ["Ka", "Ga"]), ("복", ["Bok"]), ("태", ["Tae"]), ("목", ["Mok"]), ("형", ["Hyung", "Hyeong"]), ("피", ["Pi"]),
    ("두", ["Doo", "Du"]), ("감", ["Kam", "Gam"]), ("호", ["Ho"]), ("음", ["Eum"]), ("빈", ["Bin"]), ("동", ["Dong"]),
    ("시", ["Si", "Shi"]), ("범", ["Beom", "Bum"]), ("승", ["Seung"]), ("상", ["Sang"]), ("라", ["Ra", "La"]),
    ("남궁", ["Namgung", "Namkung"]), ("황보", ["Hwangbo"]), ("제갈", ["Jegal"]), ("선우", ["Sunwoo", "Seonu"]),
    ("독고", ["Dokgo", "Dokko"]), ("사공", ["Sagong"]), ("서문", ["Seomun"]), ("동방", ["Dongbang"]),
]
COMPOUND_SUR = [s for s, _ in SURNAMES if len(s) == 2]


def tool_ld(name, desc, url, faq):
    app = {"@type": "WebApplication", "name": name, "url": DOMAIN + url, "description": desc, "inLanguage": "ko",
           "applicationCategory": "UtilitiesApplication", "operatingSystem": "All", "isAccessibleForFree": True,
           "offers": {"@type": "Offer", "price": "0", "priceCurrency": "KRW"}, "publisher": ORG}
    bc = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "홈", "item": DOMAIN + "/"},
        {"@type": "ListItem", "position": 2, "name": "영어 도구", "item": DOMAIN + "/tools/"},
        {"@type": "ListItem", "position": 3, "name": name, "item": DOMAIN + url}]}
    fq = {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}} for q, a in faq]}
    return [app, bc, fq]


def tool_faq(faq):
    return '<div class="tl-faq">' + "".join(f"<details><summary>{e(q)}</summary><p>{a}</p></details>" for q, a in faq) + "</div>"


def tool_kakao():
    k = SITE.get("kakao")
    return (f'<a class="tl-kk" href="{e(k)}" target="_blank" rel="noopener"><span><b>매일 아침 7시, 영어 표현 하나</b>'
            f'<span>카톡으로 받는 1일 1영, 무료예요</span></span><em>받아보기</em></a>') if k else ""


TOOL_JS = lambda: f'<script src="/assets/tools.js?v={ASSET_V}" defer></script>'


def page_tool_name():
    url = "/tools/english-name/"
    top = "".join(f"<tr><td>{e(s)}</td><td>{e(rr_word(s))}</td><td><b>{e(v[0])}</b>{(' <span class=mt>· ' + e(', '.join(v[1:])) + '</span>') if len(v) > 1 else ''}</td></tr>"
                  for s, v in SURNAMES[:40])
    comp = " · ".join(f"{s} <b>{e(v[0])}</b>" for s, v in SURNAMES if len(s) == 2)
    faq = [
        ("로마자 표기법과 다르게 써도 되나요?",
         "이미 여권이나 카드에 쓰고 있는 표기가 있다면 그 표기를 그대로 쓰는 게 좋아요. 처음 정한다면 국립국어원 「국어의 로마자 표기법」을 기준으로 하는 게 가장 무난해요. 이 변환기의 첫 번째 표기가 그 기준이에요."),
        ("이름을 띄어 써도 되나요? (Seung Ju)",
         "띄어 쓰지 않는 걸 권해요. 영어권에서는 띄어 쓴 두 번째 단어를 미들네임으로 보는 경우가 많아서, 이름이 Seung으로만 처리될 수 있어요. 붙여 쓰거나(Seungju) 붙임표를 넣어(Seung-ju) 주세요."),
        ("여권 영문 이름은 대문자로 써야 하나요?",
         "여권에는 대문자로 인쇄돼요. 해외 사이트나 항공권 예약에서는 대문자든 소문자든 철자만 같으면 돼요."),
        ("영어 이름(예: Ethan)과 영문 이름은 다른가요?",
         "달라요. 영문 이름은 한글 이름을 로마자로 옮긴 공식 표기라 여권, 비자, 항공권에 써요. Ethan 같은 영어 이름은 회사나 모임에서 부르는 별칭이라 공식 서류에는 쓰지 않아요."),
        ("성이 두 글자예요. (남궁, 황보, 제갈, 선우)",
         "남궁, 황보처럼 두 글자 성은 자동으로 알아봐요. 자동으로 안 될 때는 입력창 아래 '성이 두 글자예요'를 켜 주세요. 두 글자 성은 붙여서 한 단어로 써요(Namgung)."),
    ]
    body = f"""<div class="tl">
<div class="tl-head"><span class="lbl">영어 도구</span><h1>한글 이름 영문 변환기</h1>
<p>이름을 넣으면 로마자 표기법에 맞는 영문 이름과 자주 쓰는 표기를 함께 보여 드려요. 여권, 항공권, 해외 사이트 가입에 바로 쓰세요.</p></div>
<div class="tl-card">
<form class="tl-form" id="nm-form" autocomplete="off"><input id="nm-in" type="text" inputmode="text" placeholder="예) 홍길동" aria-label="한글 이름" maxlength="8" enterkeyhint="go"><button type="submit">변환</button></form>
<div class="tl-opt"><div class="tl-ex">예시 <button type="button" data-ex="이승주">이승주</button><button type="button" data-ex="김지현">김지현</button><button type="button" data-ex="남궁민">남궁민</button></div>
<label class="tl-chk"><input type="checkbox" id="nm-two">성이 두 글자예요</label></div>
<div class="tl-out" id="nm-out" hidden aria-live="polite"></div>
</div>
<div class="tl-doc">
<h2>영문 이름, 이렇게 만들어요</h2>
<div class="tl-steps">
<div class="tl-step"><i>1</i><div><b>성은 많이 쓰는 표기에서 골라요</b><span>로마자 표기법대로라면 이(李)는 <code>I</code>지만, 실제로는 <code>Lee</code>처럼 오래 써 온 표기를 더 많이 써요. 가족이 이미 쓰는 철자가 있다면 같게 맞추세요.</span></div></div>
<div class="tl-step"><i>2</i><div><b>이름은 소리가 아니라 글자대로</b><span>사람 이름은 발음이 바뀌어도 글자대로 적어요. 한복남은 소리 나는 대로 쓴 Bongnam이 아니라 <code>Han Boknam</code>이에요.</span></div></div>
<div class="tl-step"><i>3</i><div><b>이름은 붙여 쓰고, 필요하면 붙임표</b><span>홍빛나는 <code>Hong Bitna</code>로 붙여 써요. 음절이 헷갈릴 때만 <code>Bit-na</code>처럼 붙임표를 넣어요.</span></div></div>
</div>
<h2>많이 쓰는 성씨 영문 표기</h2>
<p>왼쪽은 로마자 표기법대로 쓴 표기, 오른쪽은 여권과 명함에서 자주 보이는 표기예요. 굵은 글씨가 가장 흔한 표기예요.</p>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>성</th><th>로마자 표기법</th><th>자주 보이는 표기</th></tr></thead><tbody>{top}</tbody></table></div>
<p>두 글자 성: {comp}</p>
<h2>헷갈리는 글자, 이렇게 써요</h2>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>한글</th><th>로마자 표기법</th><th>예</th></tr></thead><tbody>
<tr><td>ㅓ</td><td><b>eo</b></td><td>서 Seo, 현 Hyeon <span class="mt">· 자주 보이는 표기 Hyun</span></td></tr>
<tr><td>ㅡ</td><td><b>eu</b></td><td>은 Eun, 근 Geun</td></tr>
<tr><td>ㅢ</td><td><b>ui</b></td><td>희 Hui <span class="mt">· 자주 보이는 표기 Hee</span></td></tr>
<tr><td>ㅜ</td><td><b>u</b></td><td>주 Ju, 수 Su <span class="mt">· 자주 보이는 표기 Joo, Soo</span></td></tr>
<tr><td>ㄱ (첫소리)</td><td><b>g</b></td><td>경 Gyeong, 기 Gi <span class="mt">· 자주 보이는 표기 Kyung, Ki</span></td></tr>
<tr><td>ㅅ</td><td><b>s</b></td><td>신 Sin, 시 Si <span class="mt">· 자주 보이는 표기 Shin, Shi</span></td></tr>
<tr><td>ㄹ</td><td><b>r / l</b></td><td>첫소리는 r(리 Ri), 받침은 l(길 Gil)</td></tr>
</tbody></table></div>
<p>Hyun, Joo, Kyung 같은 표기는 2000년에 지금의 로마자 표기법이 정해지기 전에 널리 쓰던 방식과 영어식 철자 습관에서 왔어요. 틀린 표기는 아니지만, 처음 정한다면 로마자 표기법을 기준으로 하는 게 좋아요.</p>
<h2>여권 영문 이름, 정하기 전에 확인하세요</h2>
<div class="tl-note"><b>한 번 정하면 바꾸기 어려워요</b>여권의 로마자 성명은 여권법 시행령에서 정한 경우에만 바꿀 수 있어요. 신청서에 쓰기 전에 철자를 한 번 더 확인하세요.</div>
<ul>
<li><b>항공권, 해외 호텔, 해외 결제 이름은 여권과 똑같이</b> 써요. 철자가 한 글자만 달라도 탑승이나 체크인에서 문제가 생길 수 있어요.</li>
<li><b>이름은 띄어 쓰지 마세요.</b> Seung Ju처럼 띄우면 Ju를 미들네임으로 볼 수 있어요.</li>
<li><b>가족의 성 철자를 맞추세요.</b> 부모와 자녀의 성 철자가 다르면 해외에서 가족 관계를 설명해야 할 때가 있어요.</li>
</ul>
<p>여권 발급과 로마자 성명 변경 절차는 <a href="https://www.passport.go.kr" target="_blank" rel="noopener">외교부 여권안내</a>에서 확인할 수 있어요.</p>
<h2>자주 묻는 질문</h2>
{tool_faq(faq)}
<h2>다른 영어 도구</h2>
{tool_cards("name")}
{tool_kakao()}
</div></div>{TOOL_JS()}"""
    desc = "한글 이름을 입력하면 로마자 표기법에 맞는 영문 이름과 자주 쓰는 표기를 함께 보여 줘요. 여권 영문 이름 형식, 성씨별 영문 표기(김 Kim, 이 Lee, 박 Park)까지 한 번에 확인하세요."
    data = {"tool": "english_name", "surnames": [[s, v] for s, v in SURNAMES], "compound": COMPOUND_SUR}
    return layout("한글 이름 영문 변환기", desc, url, body, nav="tools", data=data,
                  seo_title="영문 이름 변환기 - 한글 이름 영어로, 여권 영문 이름 표기법",
                  ld=tool_ld("한글 이름 영문 변환기", desc, url, faq))


def page_tool_address():
    url = "/tools/english-address/"
    faq = [
        ("국가는 Republic of Korea와 South Korea 중 뭘 고르나요?",
         "둘 다 같은 나라예요. 목록에서 고르는 칸이면 South Korea나 Korea, Republic of를 고르면 되고, 직접 쓰는 칸이면 Republic of Korea라고 쓰면 돼요."),
        ("검색 결과가 안 나와요.",
         "도로명과 건물번호를 함께 넣어 보세요. 예) 테헤란로 152. 건물 이름이나 지번 주소(예: 역삼동 737)로도 찾을 수 있어요. 시·도 이름만으로는 찾을 수 없어요."),
        ("아파트 이름도 써야 하나요?",
         "도로명주소와 동·호수만 있으면 집이 정확히 정해져서 아파트 이름은 넣지 않아도 돼요. 넣고 싶다면 Address Line 2 끝에 영어로 붙이세요."),
        ("입력한 주소가 저장되나요?",
         "이 페이지는 입력한 주소를 저장하지 않아요. 검색어는 주소를 찾기 위해 행정안전부 도로명주소 API로만 보내요."),
        ("해외직구할 때 더 필요한 건 없나요?",
         "해외직구로 물건을 받으려면 개인통관고유부호가 필요해요. 관세청 개인통관고유부호 사이트에서 무료로 바로 발급받을 수 있어요."),
    ]
    body = f"""<div class="tl">
<div class="tl-head"><span class="lbl">영어 도구</span><h1>영문 주소 변환기</h1>
<p>도로명주소를 검색하면 영문 주소와 우편번호를 알려 드려요. 해외직구 사이트 칸에 맞게 나눠서 바로 복사할 수 있어요.</p></div>
<div class="tl-card">
<form class="tl-form" id="ad-form" autocomplete="off"><input id="ad-in" type="search" placeholder="도로명, 건물 이름, 지번" aria-label="한글 주소" maxlength="80" enterkeyhint="search"><button type="submit">검색</button></form>
<div class="tl-opt"><div class="tl-ex">예시 <button type="button" data-ex="테헤란로 152">테헤란로 152</button><button type="button" data-ex="세종대로 175">세종대로 175</button></div></div>
<div class="tl-out" id="ad-list" hidden aria-live="polite"></div>
<div class="tl-out" id="ad-out" hidden>
<p class="tl-sec">동·호수 넣기 <span style="font-weight:500;color:var(--faint);font-size:13px">(아파트·오피스텔)</span></p>
<div class="tl-det"><label>동<input id="ad-dong" inputmode="numeric" placeholder="101" maxlength="6"></label><label>호<input id="ad-ho" inputmode="numeric" placeholder="1004" maxlength="6"></label><label>층<input id="ad-floor" inputmode="text" placeholder="3" maxlength="4"></label></div>
<div class="tl-seg" id="ad-style" role="group" aria-label="동·호수 표기 방식"><button type="button" class="on" data-v="long">101-dong 1004-ho</button><button type="button" data-v="short">#101-1004</button></div>
<div id="ad-res" aria-live="polite"></div>
</div>
</div>
<div class="tl-doc">
<h2>영문 주소는 작은 단위부터 써요</h2>
<p>한국 주소는 큰 단위(시·도)부터 쓰지만, 영문 주소는 반대로 가장 작은 단위인 동·호수부터 써요.</p>
<div class="tl-flow"><span class="hl">동·호수</span><em>›</em><span>건물번호</span><em>›</em><span>도로명</span><em>›</em><span>구</span><em>›</em><span>시·도</span><em>›</em><span>우편번호</span><em>›</em><span>나라</span></div>
<div class="tl-tbl-w"><table class="tl-tbl"><tbody>
<tr><td>한글</td><td>서울특별시 서초구 강남대로12길 6, 101동 1004호</td></tr>
<tr><td>영문</td><td><b>101-dong 1004-ho, 6 Gangnam-daero 12-gil, Seocho-gu, Seoul 06779, Republic of Korea</b></td></tr>
</tbody></table></div>
<h2>동·호수, 층은 이렇게 써요</h2>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>한글</th><th>영문</th><th>짧게 쓸 때</th></tr></thead><tbody>
<tr><td>101동 1004호</td><td><b>101-dong 1004-ho</b></td><td>#101-1004</td></tr>
<tr><td>1004호</td><td><b>1004-ho</b></td><td>#1004</td></tr>
<tr><td>3층</td><td><b>3F</b></td><td>3rd Floor</td></tr>
<tr><td>지하 1층</td><td><b>B1</b></td><td>Basement 1</td></tr>
</tbody></table></div>
<p>어느 방식이든 국내 택배 기사님이 알아볼 수 있으면 돼요. 칸 길이가 짧은 사이트에서는 #101-1004처럼 짧게 쓰세요.</p>
<h2>해외 쇼핑몰 칸 채우는 법</h2>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>칸 이름</th><th>넣을 내용</th></tr></thead><tbody>
<tr><td>Address Line 1</td><td>건물번호 + 도로명 + 구 <span class="mt">· 예) 6 Gangnam-daero 12-gil, Seocho-gu</span></td></tr>
<tr><td>Address Line 2</td><td>동·호수 <span class="mt">· 예) 101-dong 1004-ho</span></td></tr>
<tr><td>City</td><td>시 <span class="mt">· 서울은 Seoul, 경기도는 Hwaseong-si처럼 시 이름</span></td></tr>
<tr><td>State / Province</td><td>시·도 <span class="mt">· Seoul, Gyeonggi-do</span></td></tr>
<tr><td>ZIP / Postal Code</td><td>우편번호 5자리</td></tr>
<tr><td>Phone</td><td>+82 뒤에 맨 앞 0을 빼고 <span class="mt">· 010-1234-5678 → +82 10-1234-5678</span></td></tr>
</tbody></table></div>
<h2>자주 하는 실수</h2>
<ul>
<li><b>우편번호를 6자리로 쓰기.</b> 지금 우편번호는 5자리예요. 예전 6자리 번호를 쓰면 배송이 늦어질 수 있어요.</li>
<li><b>도로명주소와 지번 주소 섞기.</b> 한 주소 안에서는 한 가지 방식만 써요. 이 변환기는 도로명주소로 알려 드려요.</li>
<li><b>Seoul-si, Seoul Special City 같은 긴 이름 쓰기.</b> 해외 사이트에서는 Seoul이면 충분해요.</li>
<li><b>한글을 섞어 쓰기.</b> 해외 쇼핑몰은 한글을 저장하지 못해서 주소가 깨질 수 있어요.</li>
</ul>
<h2>자주 묻는 질문</h2>
{tool_faq(faq)}
<p class="tl-src">주소 정보: 행정안전부 도로명주소 영문 검색 API</p>
<h2>다른 영어 도구</h2>
{tool_cards("address")}
{tool_kakao()}
</div></div>{TOOL_JS()}"""
    desc = "한글 도로명주소를 검색하면 영문 주소와 우편번호를 바로 알려 줘요. 아파트 동·호수 영문 표기, 해외직구 사이트 칸별(Address Line 1, City, State, ZIP) 입력법까지 정리했어요."
    return layout("영문 주소 변환기", desc, url, body, nav="tools", data={"tool": "english_address", "jusoKey": JUSO_KEY},
                  seo_title="영문 주소 변환기 - 도로명주소 영어로, 동 호수 영문 표기, 해외직구 주소",
                  ld=tool_ld("영문 주소 변환기", desc, url, faq), robots="" if JUSO_KEY else "noindex")



# ── 점수·시험 도구 (2026-10-23) ─────────────────────────────────────────────
# 근거(네이버 월간 검색량): 토익점수 12,950 · 오픽등급 6,950 · 토익만점점수 5,590 · 오픽등급표 5,320 · 토익점수환산기 4,030
# 출처: 한국토익위원회 토익스토리(2025 정기시험 성적 분석 /2556, 토익스피킹 안내 /2567), OPIc 공식 사이트 등급체계,
#       인크루트 어학변환기(lab.incruit.com/editor/score), 링커리어(토익 점수 환산표·채용 예시, 2025)
TOOL_LIST = [  # (key, 주소, 아이콘, 이름, 설명, 묶음)
    ("toeic", "/tools/toeic-score/", "990", "토익 점수 계산기", "맞힌 개수로 예상 점수, 평균과 비교", "score"),
    ("opic", "/tools/opic-level/", "IH", "오픽 등급표", "NL부터 AL까지 등급별 수준, 자가 진단", "score"),
    ("tos", "/tools/toeic-speaking-level/", "200", "토익스피킹 레벨표", "점수별 등급과 시험 구성", "score"),
    ("compare", "/tools/english-score-compare/", "⇄", "영어 시험 점수 비교", "토익·오픽·토익스피킹을 한눈에", "score"),
    ("name", "/tools/english-name/", "Aa", "영문 이름 변환기", "한글 이름을 여권·해외 사이트용 영문 이름으로", "life"),
    ("address", "/tools/english-address/", "#", "영문 주소 변환기", "도로명주소를 영어로, 해외직구 칸별로 나눠서", "life"),
]


def tool_cards(skip="", group=None):
    items = [t for t in TOOL_LIST if t[0] != skip and (group is None or t[5] == group) and (t[0] != "address" or JUSO_KEY)]
    return '<div class="tl-more-tools">' + "".join(
        f'<a class="tl-tool" href="{h}"><span class="ic">{e(ic)}</span><span><b>{e(t)}</b><span>{e(d)}</span></span><i>›</i></a>'
        for k, h, ic, t, d, g in items) + "</div>"


def tool_reads(title, picks):
    """도구 끝 '카영 글' 연결: picks = [(뱃지, 글 id 또는 None, 대체 조건 함수)]"""
    seen, rows = set(), []
    for badge, pid, cond in picks:
        p = POST_BY_ID.get(pid) if pid else next((x for x in POSTS if cond(x) and x["id"] not in seen), None)
        if p and p["id"] not in seen:
            seen.add(p["id"])
            rows.append(f'<a class="tl-read" href="{post_url(p)}"><i>{e(badge)}</i><span><b>{e(p["title"])}</b><span>{e(p.get("lead", ""))}</span></span></a>')
    return f"<h2>{e(title)}</h2>" + "".join(rows) if rows else ""


def tool_src(items):
    out = []
    for n, u in items:
        link = f' · <a href="{e(u)}" target="_blank" rel="noopener nofollow">원문</a>' if u else ""
        out.append(f"<span>{e(n)}{link}</span>")
    return '<div class="tl-srcs"><b>출처</b>' + "".join(out) + "</div>"


# 토익: 맞힌 개수 → 예상 점수 (공식 환산표는 없음. 링커리어 2025 추정표를 범위로 사용, LC·RC 같은 표)
TOEIC_EST = [(0, 5, 5), (40, 150, 200), (50, 220, 250), (60, 270, 300), (70, 320, 350), (80, 380, 400), (85, 410, 430), (90, 440, 460), (95, 470, 480), (100, 495, 495)]
TOEIC_AVG = {"total": 686, "lc": 378.7, "rc": 307.5}
TOEIC_AGE = [("20세 이하", 598), ("21~25세", 670), ("26~30세", 711), ("31~35세", 728), ("36~40세", 714), ("41~45세", 685), ("46~50세", 664), ("51세 이상", 639)]
HIRE = [("아시아나항공", "550점 이상", "IM1 이상"), ("현대건설", "700점 이상", "IM2 이상"), ("LS엠트론 (인문계)", "700점 이상", "IM2 이상"),
        ("한국장학재단", "800점 이상", "IM3 이상"), ("GS글로벌", "800점 이상", "IH 이상")]
SRC_TOEICSTORY = ("한국토익위원회 토익스토리, 2025년 토익 정기시험 성적 분석 (2026.03)", "https://www.toeicstory.co.kr/2556")
SRC_TOS = ("한국토익위원회 토익스토리, 토익스피킹 시험 안내 (2026.03)", "https://www.toeicstory.co.kr/2567")
SRC_OPIC = ("OPIc 공식 사이트, 시험소개·등급체계", "https://www.opic.or.kr")
SRC_LINK = ("링커리어, 2025 토익 점수 환산표·채용 기준 예시", "https://community.linkareer.com/employment_data/4104106")
SRC_INCRUIT = ("인크루트 어학변환기 (참고용 환산 기준)", "https://lab.incruit.com/editor/score/")

# 오픽 등급 (OPIc 공식 등급체계 요약을 쉬운 말로) — (등급, 이름, 한 줄, 공식 요약, 다음 등급으로 가려면)
OPIC = [
    ("AL", "Advanced Low", "의견을 말하고, 복잡한 상황도 설명하고 해결해요",
     "사건을 말할 때 시제를 일관되게 지키고, 접속사로 문장을 묶어 문단처럼 말해요. 익숙하지 않은 복잡한 상황에서도 문제를 설명하고 해결할 수 있어요.",
     "오픽의 가장 높은 등급이에요. 이제는 말하기 시험보다 실제 회의·발표 영어로 넓혀 가세요."),
    ("IH", "Intermediate High", "예상 못 한 질문에도 상황을 설명해요",
     "익숙하지 않거나 예측하지 못한 상황에서도 대부분 사건을 설명하고 문제를 해결해요. 말하는 양이 많고 어휘가 다양해요.",
     "AL은 '문단'이 갈려요. 처음-예시-정리 순서로 말하고, 과거·현재·미래 시제를 섞어도 흔들리지 않게 연습하세요."),
    ("IM3", "Intermediate Mid 3", "문장을 길게 이어 말해요 (IM 중 가장 높음)",
     "익숙한 상황에서 문장을 이어 가며 자연스럽게 말해요. 다양한 문장과 어휘를 시도해요.",
     "IH는 '돌발 질문'이 갈려요. 처음 받는 질문에도 경험 하나를 떠올려 이야기로 풀어내는 연습을 하세요."),
    ("IM2", "Intermediate Mid 2", "익숙한 주제는 문장을 이어 가며 말해요",
     "일상적인 소재와 익숙한 상황에서 문장을 나열하며 자연스럽게 말해요. 상대가 조금 배려해 주면 오래 대화할 수 있어요.",
     "말하는 양을 늘리세요. 한 질문에 문장 2~3개가 아니라, 이유와 예시를 붙여 1분 이상 말하는 연습이 좋아요."),
    ("IM1", "Intermediate Mid 1", "일상 주제를 문장으로 이어 말하기 시작해요",
     "일상적인 소재에서 문장을 이어 말해요. IM 등급 안에서는 가장 낮아요.",
     "and, so, because로 문장을 이어 붙이세요. 짧은 문장 여러 개를 한 흐름으로 묶는 것부터 시작해요."),
    ("IL", "Intermediate Low", "일상 주제는 문장으로 말해요",
     "일상적인 소재에서는 문장으로 말할 수 있어요. 좋아하는 주제에서는 자신 있게 대화에 참여해요.",
     "문장 하나로 끝내지 말고, 바로 뒤에 이유 한 문장을 붙이는 습관을 들이세요."),
    ("NH", "Novice High", "자기소개와 개인 정보는 문장으로 말해요",
     "일상적인 대부분의 소재를 문장으로 말하고, 개인 정보를 묻고 답할 수 있어요.",
     "주어와 동사를 갖춘 문장으로 끝까지 말하는 연습을 하세요. 집, 하루, 취미처럼 자주 나오는 주제부터요."),
    ("NM", "Novice Mid", "외운 단어와 문장으로 말해요",
     "이미 외운 단어나 문장으로 말할 수 있어요.",
     "자기소개 문장 10개를 소리 내어 외우고, 단어 대신 문장으로 답해 보세요."),
    ("NL", "Novice Low", "영어 단어를 나열해 말해요",
     "제한적이지만 영어 단어를 나열하며 말할 수 있어요.",
     "매일 쓰는 짧은 문장(I'm ~, I like ~, I usually ~)을 소리 내어 따라 말하는 것부터 시작해요."),
]
# 오픽 자가 진단 문장 (낮은 것부터) — 공식 등급 요약을 바탕으로
OPIC_QUIZ = [("NL", "영어 단어를 나열해서 말할 수 있어요"), ("NM", "외운 단어나 문장으로 말할 수 있어요"),
             ("NH", "자기소개처럼 내 정보는 문장으로 말할 수 있어요"), ("IL", "익숙한 일상 주제는 문장으로 말할 수 있어요"),
             ("IM", "익숙한 주제는 문장을 여러 개 이어서 말할 수 있어요"), ("IH", "처음 받는 질문에도 상황을 설명하고 풀어 갈 수 있어요"),
             ("AL", "시제를 지키며 문단처럼 짜임새 있게 말하고, 복잡한 문제도 설명할 수 있어요")]
# 토익스피킹 (토익스토리 공식 안내: 200점 만점, ACTFL 등급 매핑)
TOS = [("AH", "Advanced High", "200"), ("AM", "Advanced Mid", "180~190"), ("AL", "Advanced Low", "160~170"),
       ("IH", "Intermediate High", "140~150"), ("IM", "Intermediate Mid (IM1·IM2·IM3)", "110~130"),
       ("IL", "Intermediate Low", "90~100"), ("NH", "Novice High", "60~80"), ("NM·NL", "Novice Mid / Low", "0~50")]
TOS_PARTS = [("1~2", "문장 읽기 (Read a text aloud)", "45초", "45초"), ("3~4", "사진 묘사 (Describe a picture)", "45초", "30초"),
             ("5~7", "질문에 답하기 (Respond to questions)", "3초", "15~30초"), ("8~10", "정보 보고 답하기 (Using information)", "지문 45초 + 3초", "15~30초"),
             ("11", "의견 말하기 (Express an opinion)", "45초", "60초")]
# 비교 사다리: 같은 ACTFL 등급 이름끼리 나란히 (토익 칸은 인크루트 어학변환기의 오픽 ↔ 토익 기준)
LADDER = [("최상급", "-", "AM·AH 180~200", "-"),
          ("상급", "AL", "AL 160~170", "950~990"),
          ("중상급", "IH", "IH 140~150", "900~945"),
          ("중급 상", "IM3", "IM3 (흔히 130)", "850~895"),
          ("중급", "IM2", "IM2 (흔히 120)", "800~845"),
          ("중급 하", "IM1", "IM1 (흔히 110)", "700~795"),
          ("초중급", "IL", "IL 90~100", "600~695"),
          ("초급 상", "NH", "NH 60~80", "500~595"),
          ("초급", "NM · NL", "NM·NL 0~50", "400~495")]


def page_tool_toeic():
    url = "/tools/toeic-score/"
    est = "".join(f"<tr><td>{n}개</td><td>{lo if lo == hi else f'{lo}~{hi}'}점</td></tr>" for n, lo, hi in reversed(TOEIC_EST) if n >= 40)
    age = "".join(f"<tr><td>{a}</td><td><b>{s}점</b></td></tr>" for a, s in TOEIC_AGE)
    hire = "".join(f"<tr><td>{c}</td><td>{t}</td><td>{s}</td></tr>" for c, t, s in HIRE)
    faq = [
        ("공식 토익 점수 환산표가 있나요?",
         "없어요. ETS는 회차마다 문제 난이도를 반영해 점수를 정하기 때문에, 같은 개수를 맞혀도 회차에 따라 점수가 달라질 수 있어요. 그래서 이 계산기는 한 점수가 아니라 범위로 보여 드려요."),
        ("토익 만점은 몇 점인가요?",
         "990점이에요. LC(듣기) 495점, RC(읽기) 495점이고, 각 파트 최저 점수는 5점이라 전체 점수는 10~990점이에요."),
        ("토익 성적은 언제 나오나요?",
         "2025년 일정을 보면 일요일 시험 성적이 9일 뒤 화요일 정오에 발표됐어요. 정확한 발표일은 회차마다 토익 공식 사이트에서 확인하세요."),
        ("토익 성적 유효기간은요?",
         "시험일로부터 2년이에요. 기업이나 학교에 낼 때는 제출일 기준으로 2년이 지나지 않았는지 확인하세요."),
        ("RC 점수가 LC보다 낮게 나와요.",
         "흔한 일이에요. 2025년 정기시험 평균도 LC 378.7점, RC 307.5점으로 RC가 70점 넘게 낮았어요. RC는 시간이 부족해서 점수가 깎이는 경우가 많아요."),
    ]
    body = f"""<div class="tl">
<div class="tl-head"><span class="lbl">점수 도구</span><h1>토익 점수 계산기</h1>
<p>LC와 RC에서 맞힌 개수를 넣으면 예상 점수를 범위로 알려 드려요. 2025년 평균 점수와도 바로 비교해요.</p></div>
<div class="tl-card" id="tc">
<div class="tl-sl"><label for="tc-lc"><b>LC 맞힌 개수</b><small>듣기 100문항</small></label><div class="tl-sl-v"><input type="number" id="tc-lc-n" min="0" max="100" value="80" inputmode="numeric" aria-label="LC 맞힌 개수"><span>/ 100</span></div><input type="range" id="tc-lc" min="0" max="100" value="80"></div>
<div class="tl-sl"><label for="tc-rc"><b>RC 맞힌 개수</b><small>읽기 100문항</small></label><div class="tl-sl-v"><input type="number" id="tc-rc-n" min="0" max="100" value="70" inputmode="numeric" aria-label="RC 맞힌 개수"><span>/ 100</span></div><input type="range" id="tc-rc" min="0" max="100" value="70"></div>
<div class="tl-hero-res" aria-live="polite"><span class="tl-tag">예상 점수</span>
<p class="tl-big" id="tc-tot">—</p><p class="tl-big-sub" id="tc-part"></p>
<div class="tl-scale"><i id="tc-bar"></i><em style="left:{TOEIC_AVG['total'] / 990 * 100:.1f}%"><span>2025 평균 {TOEIC_AVG['total']}</span></em></div>
<div class="tl-pills" id="tc-pills"></div></div>
<p class="tl-note2">공식 환산표가 없어서 공개된 추정치를 범위로 보여 드려요. 실제 점수는 회차 난이도에 따라 달라져요.</p>
</div>
<div class="tl-doc">
<h2>맞힌 개수별 예상 점수표</h2>
<p>LC와 RC 모두 같은 기준으로 계산해요. 회차마다 점수가 달라질 수 있어서 범위로 정리했어요.</p>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>맞힌 개수</th><th>예상 점수 (LC 또는 RC)</th></tr></thead><tbody>{est}<tr><td>40개 미만</td><td>150점 미만</td></tr></tbody></table></div>
<h2>토익 점수, 이렇게 정해져요</h2>
<div class="tl-steps">
<div class="tl-step"><i>1</i><div><b>LC 100문항 + RC 100문항</b><span>듣기 45분, 읽기 75분 동안 모두 200문항을 풀어요.</span></div></div>
<div class="tl-step"><i>2</i><div><b>파트마다 5~495점</b><span>맞힌 개수를 점수로 바꾸고 5점 단위로 매겨요. 두 점수를 더한 10~990점이 토익 점수예요.</span></div></div>
<div class="tl-step"><i>3</i><div><b>회차마다 난이도를 반영</b><span>어려운 회차는 같은 개수를 맞혀도 점수가 조금 높게, 쉬운 회차는 조금 낮게 나올 수 있어요.</span></div></div>
</div>
<h2>2025년 토익 평균 점수</h2>
<p>2025년 정기시험 평균은 <b>{TOEIC_AVG['total']}점</b>이에요. LC 평균은 {TOEIC_AVG['lc']}점, RC 평균은 {TOEIC_AVG['rc']}점이에요. 응시 목적은 취업이 41.9%로 가장 많았어요.</p>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>나이</th><th>평균 점수</th></tr></thead><tbody>{age}</tbody></table></div>
<h2>채용 공고에서 보는 토익 기준</h2>
<p>회사마다 기준이 달라요. 공개된 채용 공고 예시를 보면 이렇게 요구했어요. 지원할 회사의 최신 공고를 꼭 확인하세요.</p>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>기업</th><th>토익</th><th>토익스피킹</th></tr></thead><tbody>{hire}</tbody></table></div>
<h2>자주 묻는 질문</h2>
{tool_faq(faq)}
{tool_reads("점수 올리는 데 도움 되는 카영 글", [("LC", None, lambda p: p.get("sub") == "듣기"), ("LC", None, lambda p: p.get("sub") == "발음"), ("LC", None, lambda p: p.get("sub") == "듣기"), ("RC", None, lambda p: p["id"] in next((s["posts"] for s in SERIES if s["id"] == "work"), []))])}
{tool_src([SRC_TOEICSTORY, SRC_LINK])}
<h2>다른 점수 도구</h2>
{tool_cards("toeic", "score")}
{tool_kakao()}
</div></div>{TOOL_JS()}"""
    desc = "토익 LC, RC 맞힌 개수를 넣으면 예상 점수를 범위로 알려 줘요. 맞힌 개수별 토익 점수 환산표, 2025년 평균 686점과 비교, 성적 발표일과 유효기간까지 정리했어요."
    data = {"tool": "toeic_score", "est": TOEIC_EST, "avg": TOEIC_AVG}
    return layout("토익 점수 계산기", desc, url, body, nav="tools", data=data,
                  seo_title="토익 점수 계산기 - 맞힌 개수로 예상 점수, 토익 점수 환산표",
                  ld=tool_ld("토익 점수 계산기", desc, url, faq))


def page_tool_opic():
    url = "/tools/opic-level/"
    rows = "".join(f'<div class="tl-grade" id="g-{g.lower()}"><b>{g}</b><div><span class="en">{e(n)}</span><p>{e(d)}</p></div></div>' for g, n, s, d, t in OPIC)
    quiz = "".join(f'<button type="button" class="tl-can" data-g="{g}"><span>{e(q)}</span><i>›</i></button>' for g, q in reversed(OPIC_QUIZ))
    faq = [
        ("오픽 등급은 몇 개인가요?", "NL, NM, NH, IL, IM1, IM2, IM3, IH, AL의 9개예요. Intermediate Mid는 IM1 < IM2 < IM3로 나눠서 줘요. 가장 높은 등급은 AL이에요."),
        ("IM2와 IH는 무엇이 다른가요?", "IM2는 익숙한 주제에서 문장을 이어 말하는 수준이고, IH는 처음 받는 질문이나 예상 못 한 상황에서도 사건을 설명하고 문제를 풀어 가는 수준이에요. 말하는 양과 어휘의 폭도 차이가 나요."),
        ("오픽은 상대평가인가요?", "아니에요. ACTFL 말하기 기준(ACTFL Proficiency Guidelines Speaking)에 따라 ACTFL 공인 평가자가 절대평가해요."),
        ("시험은 어떻게 보나요?", "컴퓨터로 보는 말하기 시험이에요. 40분 동안 12~15문항에 답하고, 처음에 고른 관심사(Background Survey)에 맞춰 질문이 나와요."),
        ("오픽과 토익스피킹 중 뭘 봐야 하나요?", "회사가 인정하는 시험이 먼저예요. 둘 다 인정하면, 내 경험을 자유롭게 말하는 게 편하면 오픽, 정해진 유형을 연습하는 게 편하면 토익스피킹이 잘 맞는 편이에요."),
    ]
    body = f"""<div class="tl">
<div class="tl-head"><span class="lbl">점수 도구</span><h1>오픽 등급표</h1>
<p>NL부터 AL까지, 오픽 등급마다 어느 정도로 말하는지 공식 기준을 쉬운 말로 정리했어요. 내 등급도 간단히 짐작해 보세요.</p></div>
<div class="tl-card">
<p class="tl-sec" style="margin-top:0">나는 어느 등급쯤일까? <span class="tl-sec-s">할 수 있는 것 중 가장 높은 것을 골라요</span></p>
<div class="tl-cans" id="oq">{quiz}</div>
<div class="tl-out" id="oq-out" hidden aria-live="polite"></div>
</div>
<div class="tl-doc">
<h2>오픽 등급 한눈에 보기</h2>
<div class="tl-ladder-s">{"".join(f'<span class="{ "hl" if g in ("IH", "IM2") else "" }">{g}</span>' for g, *_ in reversed(OPIC))}</div>
<p>왼쪽부터 낮은 등급이에요. 취업에서 많이 요구하는 등급은 회사마다 다르지만, IM2와 IH가 자주 기준으로 쓰여요.</p>
<h2>등급별로 이렇게 말해요</h2>
<div class="tl-grades">{rows}</div>
<h2>오픽 시험은 이렇게 봐요</h2>
<div class="tl-tbl-w"><table class="tl-tbl"><tbody>
<tr><td>시험 방식</td><td>컴퓨터로 보는 말하기 시험 (iBT)</td></tr>
<tr><td>시험 시간</td><td>40분</td></tr>
<tr><td>문항 수</td><td>12~15문항 (사람마다 다름)</td></tr>
<tr><td>평가</td><td>ACTFL 공인 평가자가 절대평가</td></tr>
<tr><td>등급</td><td>9개 (NL ~ AL)</td></tr>
<tr><td>응시료</td><td>84,000원 (VAT 포함)</td></tr>
</tbody></table></div>
<h2>자주 묻는 질문</h2>
{tool_faq(faq)}
{tool_reads("말하기 등급 올리는 카영 글", [("말", None, lambda p: p.get("sub") == "회화"), ("말", None, lambda p: p.get("sub") == "회화"), ("말", None, lambda p: p.get("sub") == "발음")])}
{tool_src([SRC_OPIC])}
<h2>다른 점수 도구</h2>
{tool_cards("opic", "score")}
{tool_kakao()}
</div></div>{TOOL_JS()}"""
    desc = "오픽 등급표를 NL, NM, NH, IL, IM1, IM2, IM3, IH, AL 순서로 정리하고 등급별로 어느 정도 말하는지 쉬운 말로 풀었어요. IM2와 IH 차이, 다음 등급으로 가는 방법, 내 등급 자가 진단까지."
    data = {"tool": "opic_level", "opic": [[g, n, s, t] for g, n, s, d, t in OPIC]}
    return layout("오픽 등급표", desc, url, body, nav="tools", data=data,
                  seo_title="오픽 등급표 - NL부터 AL까지 등급별 수준, IM2 IH 차이",
                  ld=tool_ld("오픽 등급표", desc, url, faq))


def page_tool_tos():
    url = "/tools/toeic-speaking-level/"
    lv = "".join(f'<tr><td>{g}</td><td>{e(n)}</td><td><b>{s}</b></td></tr>' for g, n, s in TOS)
    parts = "".join(f"<tr><td>{a}</td><td>{e(b)}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in TOS_PARTS)
    hire = "".join(f"<tr><td>{c}</td><td>{s}</td></tr>" for c, t, s in HIRE)
    faq = [
        ("토익스피킹 만점은 몇 점인가요?", "200점이에요. 200점이면 가장 높은 등급인 Advanced High(AH)예요."),
        ("IM1, IM2, IM3는 몇 점인가요?", "공식 안내에서는 Intermediate Mid를 110~130점으로 묶고 Mid1 < Mid2 < Mid3로 나눠요. 채용 공고에서는 흔히 IM1을 110점, IM2를 120점, IM3를 130점으로 봐요."),
        ("성적은 언제 나오나요?", "공식 안내 기준으로 응시일로부터 약 5일 뒤 낮 12시에 발표돼요."),
        ("시험은 몇 문항, 몇 분인가요?", "11문항이고 약 20분 동안 봐요. 문장 읽기, 사진 묘사, 질문에 답하기, 정보 보고 답하기, 의견 말하기로 나뉘어요."),
        ("토익스피킹 등급과 오픽 등급은 같은가요?", "둘 다 ACTFL 등급 이름을 쓰지만 시험 방식이 달라서 똑같다고 볼 수는 없어요. 두 시험을 공식으로 바꿔 주는 환산표도 없어요. 비교가 필요하면 영어 시험 점수 비교표를 참고하세요."),
    ]
    body = f"""<div class="tl">
<div class="tl-head"><span class="lbl">점수 도구</span><h1>토익스피킹 레벨표</h1>
<p>토익스피킹 점수를 넣으면 등급을 바로 알려 드려요. 점수별 등급표와 시험 구성도 함께 정리했어요.</p></div>
<div class="tl-card">
<div class="tl-sl"><label for="ts"><b>토익스피킹 점수</b><small>0~200점, 10점 단위</small></label><div class="tl-sl-v"><input type="number" id="ts-n" min="0" max="200" step="10" value="130" inputmode="numeric" aria-label="토익스피킹 점수"><span>/ 200</span></div><input type="range" id="ts" min="0" max="200" step="10" value="130"></div>
<div class="tl-hero-res" aria-live="polite"><span class="tl-tag">내 등급</span><p class="tl-big" id="ts-g">—</p><p class="tl-big-sub" id="ts-s"></p>
<div class="tl-scale"><i id="ts-bar"></i></div><div class="tl-pills" id="ts-p"></div></div>
</div>
<div class="tl-doc">
<h2>토익스피킹 점수별 등급표</h2>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>등급</th><th>ACTFL 등급</th><th>점수</th></tr></thead><tbody>{lv}</tbody></table></div>
<p>Intermediate Mid(110~130점)는 IM1 &lt; IM2 &lt; IM3로 나눠요. 채용 공고에서는 흔히 IM1 110점, IM2 120점, IM3 130점으로 봐요.</p>
<h2>시험 구성</h2>
<p>11문항, 약 20분 동안 봐요. 컴퓨터로 녹음한 답변을 ETS 평가자가 채점해요.</p>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>문항</th><th>유형</th><th>준비</th><th>답변</th></tr></thead><tbody>{parts}</tbody></table></div>
<h2>채용 공고에서 보는 토익스피킹 기준</h2>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>기업</th><th>토익스피킹</th></tr></thead><tbody>{hire}</tbody></table></div>
<p>회사마다, 공고마다 기준이 달라요. 지원할 회사의 최신 공고를 꼭 확인하세요.</p>
<h2>자주 묻는 질문</h2>
{tool_faq(faq)}
{tool_reads("말하기 점수 올리는 카영 글", [("말", None, lambda p: p.get("sub") == "회화"), ("말", None, lambda p: p.get("sub") == "발음"), ("말", None, lambda p: p.get("sub") == "회화")])}
{tool_src([SRC_TOS, SRC_LINK])}
<h2>다른 점수 도구</h2>
{tool_cards("tos", "score")}
{tool_kakao()}
</div></div>{TOOL_JS()}"""
    desc = "토익스피킹 점수를 넣으면 등급(AH, AM, AL, IH, IM, IL, NH)을 바로 알려 줘요. 점수별 레벨표, IM1·IM2·IM3 점수, 11문항 시험 구성, 채용 기준 예시까지 정리했어요."
    data = {"tool": "toeic_speaking"}
    return layout("토익스피킹 레벨표", desc, url, body, nav="tools", data=data,
                  seo_title="토익스피킹 레벨 점수표 - 점수별 등급 AL IH IM3, 시험 구성",
                  ld=tool_ld("토익스피킹 레벨표", desc, url, faq))


def page_tool_compare():
    url = "/tools/english-score-compare/"
    rows = "".join(f"<tr><td>{a}</td><td><b>{b}</b></td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in LADDER)
    faq = [
        ("공식 환산표인가요?", "아니에요. ETS(토익·토익스피킹)와 ACTFL(오픽)은 시험끼리 바꿔 주는 공식 환산표를 내지 않아요. 이 표는 참고용이고, 회사가 인정하는 기준을 꼭 확인하세요."),
        ("오픽과 토익스피킹은 어떻게 나란히 놓았나요?", "두 시험 모두 ACTFL 등급 이름(AL, IH, IM 등)으로 결과를 알려 줘요. 그래서 같은 등급 이름끼리 나란히 놓았어요. 시험 방식은 달라서 같은 등급이라도 체감 난이도는 다를 수 있어요."),
        ("토익 점수는 어디서 가져왔나요?", "인크루트 어학변환기가 공개한 오픽 ↔ 토익 기준을 썼어요. 토익은 듣기·읽기 시험이라 말하기 실력과 바로 같다고 볼 수는 없어요."),
        ("다른 사이트와 숫자가 달라요.", "기관마다 기준이 달라서 그래요. 예를 들어 인크루트는 예전 토익스피킹 레벨(Lv1~Lv8) 기준으로 비교해서 이 표의 토익스피킹 칸과 다를 수 있어요."),
    ]
    body = f"""<div class="tl">
<div class="tl-head"><span class="lbl">점수 도구</span><h1>영어 시험 점수 비교</h1>
<p>토익, 오픽, 토익스피킹 점수를 하나의 사다리에 놓고 비교해요. 내 점수가 어디쯤인지, 다음 목표는 무엇인지 확인하세요.</p></div>
<div class="tl-card">
<div class="tl-seg" id="cp-t" role="group" aria-label="시험 선택"><button type="button" class="on" data-t="opic">오픽</button><button type="button" data-t="tos">토익스피킹</button><button type="button" data-t="toeic">토익</button></div>
<div class="tl-picks" id="cp-p"></div>
<div class="tl-lad" id="cp-l"></div>
<p class="tl-you" id="cp-y" aria-live="polite"></p>
<p class="tl-note2">시험끼리의 공식 환산표는 없어요. 아래 기준으로 만든 참고용 비교예요.</p>
</div>
<div class="tl-doc">
<h2>영어 시험 점수 비교표</h2>
<div class="tl-tbl-w"><table class="tl-tbl"><thead><tr><th>수준</th><th>오픽</th><th>토익스피킹</th><th>토익</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>이렇게 만들었어요</h2>
<ul>
<li><b>오픽과 토익스피킹</b>은 둘 다 ACTFL 등급 이름으로 결과를 줘서, 같은 이름끼리 나란히 놓았어요. 토익스피킹 점수 범위는 한국토익위원회 공식 안내를 따랐어요.</li>
<li><b>토익</b>은 인크루트 어학변환기의 오픽 ↔ 토익 기준을 썼어요.</li>
<li>오픽의 가장 높은 등급은 AL이라, 토익스피킹 AM·AH에 해당하는 오픽 등급은 없어요.</li>
</ul>
<div class="tl-note"><b>회사가 인정하는 기준이 먼저예요</b>채용 공고는 시험마다 기준을 따로 적는 경우가 많아요. 예를 들어 현대건설은 토익 700점 이상 또는 토익스피킹 IM2 이상, GS글로벌은 토익 800점 이상 또는 토익스피킹 IH 이상을 요구했어요.</div>
<h2>자주 묻는 질문</h2>
{tool_faq(faq)}
{tool_src([SRC_OPIC, SRC_TOS, SRC_INCRUIT, SRC_LINK])}
<h2>다른 점수 도구</h2>
{tool_cards("compare", "score")}
{tool_kakao()}
</div></div>{TOOL_JS()}"""
    desc = "토익, 오픽, 토익스피킹 점수를 한 표에서 비교해요. 오픽 IH는 토익 몇 점, 토익스피킹 IM3는 오픽 어느 등급인지 참고용 기준과 출처를 함께 정리했어요."
    data = {"tool": "score_compare", "ladder": LADDER}
    return layout("영어 시험 점수 비교", desc, url, body, nav="tools", data=data,
                  seo_title="토익 오픽 토익스피킹 점수 비교표 - 영어 시험 점수 환산, 내 등급 위치",
                  ld=tool_ld("영어 시험 점수 비교", desc, url, faq))


def page_tools():
    body = f"""<div class="tl">
<div class="tl-head"><span class="lbl">무료</span><h1>영어 도구</h1>
<p>시험 점수 확인부터 여권 영문 이름까지, 영어로 확인하고 바꿔야 할 때 바로 쓰는 도구예요. 가입 없이 무료예요.</p></div>
<h2 class="tl-gh">점수·시험</h2>
{tool_cards(group="score")}
<h2 class="tl-gh">생활 영어</h2>
{tool_cards(group="life")}
<div class="tl-doc">
<h2>이런 때 쓰세요</h2>
<ul>
<li><b>토익 시험을 본 날</b> 맞힌 개수로 예상 점수를 확인하세요.</li>
<li><b>취업 준비할 때</b> 오픽, 토익스피킹, 토익 점수를 한 표에서 비교하세요.</li>
<li><b>여권을 처음 만들 때</b> 영문 이름 철자를 미리 정해 두세요.</li>
{"<li><b>해외직구를 할 때</b> 영문 주소를 쇼핑몰 칸에 맞게 나눠서 복사하세요.</li>" if JUSO_KEY else ""}
</ul>
{tool_kakao()}
</div></div>"""
    desc = "토익 점수 계산기, 오픽 등급표, 토익스피킹 레벨표, 영어 시험 점수 비교, 영문 이름 변환기까지 영어 공부와 생활에 필요한 도구를 무료로 쓸 수 있어요."
    return layout("영어 도구", desc, "/tools/", body, nav="tools", seo_title="영어 도구 - 토익 점수 계산기, 오픽 등급표, 영문 이름 변환기")


def build():
    global START
    import time
    START = time.time() - 1
    # 기존 파일은 덮어쓰기만 합니다 (삭제하지 않음). 더 이상 쓰지 않는 파일은 마지막에 알려줍니다.
    before = {f for f in OUT.rglob("*") if f.is_file()} if OUT.exists() else set()
    OUT.mkdir(exist_ok=True)
    shutil.copytree(ASSETS, OUT / "assets", dirs_exist_ok=True)
    (OUT / "assets" / "site.css").write_text(STYLE_CSS, "utf-8")
    (OUT / "search.json").write_text(search_index(), "utf-8")
    if (ROOT / "images").exists():
        shutil.copytree(ROOT / "images", OUT / "images", dirs_exist_ok=True)
    if AUDIO_DIR.exists():
        shutil.copytree(AUDIO_DIR, OUT / "audio", dirs_exist_ok=True, ignore=shutil.ignore_patterns("index.json"))
        # 오답노트 정답 문장 듣기용: {문장: 음성 주소} (내 공부방에서 필요할 때만 불러와요)
        (OUT / "assets").mkdir(exist_ok=True)
        (OUT / "assets" / "amap.json").write_text(json.dumps({t: "/audio/" + f for t, f in AUDIO.items()}, ensure_ascii=False, separators=(",", ":")), "utf-8")
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
    write("/today/", page_today())
    (OUT / "manifest.webmanifest").write_text(json.dumps({
        "name": "카페인영어 - 오늘의 5분", "short_name": "카페인영어", "lang": "ko", "start_url": "/notes/?src=app", "scope": "/",
        "display": "standalone", "background_color": "#FFFFFF", "theme_color": "#FFFFFF",
        "description": "하루 5분, 듣고 말하고 복습하는 영어 루틴",
        "icons": [{"src": "/assets/icon-192.png?v=3", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                  {"src": "/assets/icon-512.png?v=3", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}, ensure_ascii=False, indent=1), "utf-8")
    (OUT / "sw.js").write_text(SW_JS, "utf-8")
    if (ROOT / "images").exists():  # 빌드 중 새로 만든 유튜브 썸네일까지 다시 복사
        shutil.copytree(ROOT / "images", OUT / "images", dirs_exist_ok=True)
    write("/about/", page_static("about", "카페인영어 소개", "유튜브 카페인영어를 운영하는 제가 직접 공부하며 정리한 영어표현 사이트예요. 영상 복습, 원어민 발음 듣기, 퀴즈와 오답노트, 여행·회사 영어 시리즈를 소개해요.", ABOUT)); pages.append("/about/")
    write("/privacy/", page_static("privacy", "개인정보처리방침", "카페인영어(cafeinenglish.com) 개인정보처리방침. 회원가입 없이 이용하는 사이트의 수집 항목과 보유 기간, 쿠키와 광고(Google 애드센스), 이용자 권리와 문의 방법을 안내해요.", PRIVACY)); pages.append("/privacy/")
    write("/contact/", page_static("contact", "문의", "카페인영어에 콘텐츠 제안, 표현 오류 신고, 제휴 문의를 남겨 주세요. 남겨 주신 메시지는 확인한 뒤 이메일로 답장드려요.", CONTACT)); pages.append("/contact/")
    if (ROOT / "files").exists():
        shutil.copytree(ROOT / "files", OUT / "files", dirs_exist_ok=True)
    write("/travel/", page_travel()); pages.append("/travel/")
    write("/tools/", page_tools()); pages.append("/tools/")
    write("/tools/english-name/", page_tool_name()); pages.append("/tools/english-name/")
    for u, fn in (("/tools/toeic-score/", page_tool_toeic), ("/tools/opic-level/", page_tool_opic),
                  ("/tools/toeic-speaking-level/", page_tool_tos), ("/tools/english-score-compare/", page_tool_compare)):
        write(u, fn()); pages.append(u)
    write("/tools/english-address/", page_tool_address())
    if JUSO_KEY:
        pages.append("/tools/english-address/")
    write("/app/", page_app())
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

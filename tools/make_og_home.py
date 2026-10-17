"""홈(및 기본) 공유 미리보기 이미지 1200×630 — 토스 톤, 글 공유 이미지(C안)와 같은 디자인 언어.
실행: python3 tools/make_og_home.py → assets/og-home.png (build.py가 기본 og 이미지로 사용)"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "fonts" / "PretendardVariable.ttf"
ICON = ROOT / "assets" / "icons"
W, H, PAD = 1200, 630, 72
INK, BODY, MUTED, LIME, BLUE = "#191F28", "#333D4B", "#6B7684", "#CDEB5B", "#3182F6"


def F(size, weight):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_axes([weight]); return f


def hx(c): return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


# 배경: 아주 옅은 블루 그라데이션 + 오른쪽 위 흰 빛
g = Image.new("RGB", (2, 2)); g.putdata([hx("#F7FAFF"), hx("#EEF4FF"), hx("#EEF4FF"), hx("#DCE8FF")])
im = g.resize((W, H), Image.BILINEAR).convert("RGBA")
glow = Image.new("RGBA", (W, H), (255, 255, 255, 0))
ImageDraw.Draw(glow).ellipse((520, -260, 1300, 360), fill=(255, 255, 255, 190))
im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(90)))
d = ImageDraw.Draw(im)

# 로고 + 브랜드
d.rounded_rectangle((PAD, 60, PAD + 56, 116), 15, fill=INK)
d.text((PAD + 13, 88), "C", font=F(39, 800), fill="#FFFFFF", anchor="lm")
d.ellipse((PAD + 38, 95, PAD + 47, 104), fill=LIME)
d.text((PAD + 72, 88), "카페인영어 CafeInEnglish", font=F(28, 700), fill=INK, anchor="lm")

# 큰 제목 (2줄) — '스며드는'에 라임 밑줄
hf = F(76, 800)
y = 180
d.text((PAD, y), "매일 조금씩,", font=hf, fill=INK)
y += 98
w1 = d.textlength("깊게 ", font=hf); w2 = d.textlength("스며드는", font=hf)
d.rectangle((PAD + w1 - 4, y + 56, PAD + w1 + w2 + 4, y + 82), fill=LIME)
d.text((PAD, y), "깊게 스며드는 영어", font=hf, fill=INK)

# 설명 + 칩
d.text((PAD, 404), "실제 영상과 대화로 배우는 영어표현", font=F(32, 600), fill=BODY)
cx = PAD
for t in ["가입 없이", "무료", "하루 5분"]:
    cf = F(24, 700); cw = d.textlength(t, font=cf)
    d.rounded_rectangle((cx, 470, cx + cw + 36, 516), 23, fill=(255, 255, 255, 230), outline=(222, 228, 238), width=2)
    d.text((cx + 18, 493), t, font=cf, fill=BODY, anchor="lm"); cx += cw + 48
d.text((PAD, 560), "cafeinenglish.com", font=F(26, 700), fill=BLUE)

# 오른쪽: 사이트 메뉴 4칸 (3D 아이콘 타일)
tiles = [("headphone", "영상으로 배우기", "장면 듣기·따라 말하기"), ("speech-balloon", "영어표현", "실제 대화 카드"),
         ("light-bulb", "영어꿀팁", "헷갈리는 영어 정리"), ("page", "사유의 문장", "필사·빈칸 복기")]
x0, y0, tw, th, gap = 668, 96, 230, 192, 20
sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
for i in range(4):
    x = x0 + (i % 2) * (tw + gap); yy = y0 + (i // 2) * (th + gap)
    sd.rounded_rectangle((x + 10, yy + 22, x + tw - 10, yy + th + 10), 30, fill=(40, 60, 110, 34))
im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(16)))
d = ImageDraw.Draw(im)
for i, (ic, name, sub) in enumerate(tiles):
    x = x0 + (i % 2) * (tw + gap); yy = y0 + (i // 2) * (th + gap)
    d.rounded_rectangle((x, yy, x + tw, yy + th), 30, fill="#FFFFFF")
    icn = Image.open(ICON / f"{ic}.webp").convert("RGBA").resize((76, 76), Image.LANCZOS)
    im.alpha_composite(icn, (x + 28, yy + 26))
    d = ImageDraw.Draw(im)
    d.text((x + 28, yy + 118), name, font=F(28, 800), fill=INK)
    d.text((x + 28, yy + 156), sub, font=F(20, 600), fill="#8B95A1")

# 아래: 카톡 1일 1영 안내 띠
by = 556
bf = F(22, 700); txt = "매일 아침 7시, 카톡으로 받는 1일 1영"
bw = d.textlength(txt, font=bf) + 64
bx = x0 + (2 * tw + gap - bw) / 2
d.rounded_rectangle((bx, by - 26, bx + bw, by + 22), 24, fill=INK)
d.ellipse((bx + 22, by - 6, bx + 32, by + 4), fill=LIME)
d.text((bx + 44, by - 2), txt, font=bf, fill="#FFFFFF", anchor="lm")

out = ROOT / "assets" / "og-home.png"
im.convert("RGB").save(out, optimize=True)
print("saved", out)

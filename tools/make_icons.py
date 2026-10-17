"""앱 아이콘·파비콘·로고 마크: 에스프레소 #2A1A12 바탕 + 크림 C + 라임 점 (로고는 어디서나 이 모양 하나).
실행: python3 tools/make_icons.py → assets/ 아래 icon-512/192, apple-touch-icon, favicon-32, favicon.svg, logo-mark.png"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
FONT = ROOT / "fonts" / "PretendardVariable.ttf"
INK, CREAM, LIME = (42, 26, 18), (244, 238, 228), (205, 235, 91)


def mark(size, radius=0.0, scale=4):
    """radius: 모서리 둥글기(크기 대비). 0이면 꽉 찬 정사각형(아이폰·안드로이드가 알아서 잘라 줌)"""
    S = size * scale
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, S - 1, S - 1), int(S * radius), fill=INK)
    k = S / 420
    f = ImageFont.truetype(str(FONT), int(300 * k)); f.set_variation_by_axes([800])
    d.text((S / 2 - 34 * k, S / 2 + 6 * k), "C", font=f, fill=CREAM, anchor="mm")
    d.ellipse((S / 2 + 76 * k, S / 2 + 56 * k, S / 2 + 124 * k, S / 2 + 104 * k), fill=LIME)
    return im.resize((size, size), Image.LANCZOS)


mark(512).save(A / "icon-512.png", optimize=True)
mark(192).save(A / "icon-192.png", optimize=True)
mark(180).convert("RGB").save(A / "apple-touch-icon.png", optimize=True)
mark(32, .22).save(A / "favicon-32.png", optimize=True)
mark(120, .24).save(A / "logo-mark.png", optimize=True)
(A / "favicon.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#2A1A12"/>'
    '<text x="27" y="33" font-family="Pretendard,Apple SD Gothic Neo,Arial,sans-serif" font-weight="800" font-size="46" '
    'fill="#F4EEE4" text-anchor="middle" dominant-baseline="central">C</text><circle cx="47.6" cy="44.2" r="3.7" fill="#CDEB5B"/></svg>', "utf-8")
print("icons ok")

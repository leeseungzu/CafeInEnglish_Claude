#!/usr/bin/env python3
"""글 속 도식 이미지 만들기 — 모바일에서 잘 보이는 세로형 (폭 1080px)
사이트 디자인: 크림 · 에스프레소 · 라임 / Pretendard

    python3 tools/make_diagrams.py   → images/*.png (build.py가 docs/images/ 로 복사)

모바일 화면 폭(약 360px)에서 1/3로 줄어 보이므로, 가장 작은 글자도 38px 이상으로 만든다.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images"
FONT = ROOT / "fonts" / "PretendardVariable.ttf"
BG, CARD, INK, LIME, MUTED, LINE, SOFT = "#F4EEE4", "#FFFDF8", "#2A1A12", "#CDEB5B", "#7A6A5E", "#E3D9CB", "#D9CDBE"
W, M = 1080, 64
_fc = {}


def F(size, weight=700):
    k = (size, weight)
    if k not in _fc:
        f = ImageFont.truetype(str(FONT), size)
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
        _fc[k] = f
    return _fc[k]


class Canvas:
    def __init__(self, title, sub=None):
        self.im = Image.new("RGB", (W, 4000), BG)
        self.d = ImageDraw.Draw(self.im)
        self.y = 72
        for line in self.wrap(title, F(66, 800), W - 2 * M):
            self.text(M, line, F(66, 800), INK, 1.25)
        self.y += 14
        if sub:
            for line in self.wrap(sub, F(40, 600), W - 2 * M):
                self.text(M, line, F(40, 600), MUTED)
        self.y += 34

    # ---- 기본 도구
    def wrap(self, s, font, maxw):
        out, cur = [], ""
        for w in s.split(" "):
            t = (cur + " " + w).strip()
            if self.d.textlength(t, font=font) <= maxw or not cur:
                cur = t
            else:
                out.append(cur); cur = w
        out.append(cur)
        return out

    def text(self, x, s, font, fill=INK, gap=1.32):
        self.d.text((x, self.y), s, font=font, fill=fill)
        self.y += int(font.size * gap)

    def hl(self, x, y, s, font, fill=INK):
        w = self.d.textlength(s, font=font)
        self.d.rectangle((x - 6, y + int(font.size * .58), x + w + 6, y + int(font.size * .98)), fill=LIME)
        self.d.text((x, y), s, font=font, fill=fill)
        return w

    def pill(self, x, y, s, font=None, bg=INK, fg=BG):
        font = font or F(38, 700)
        w = self.d.textlength(s, font=font)
        h = int(font.size * 1.55)
        self.d.rounded_rectangle((x, y, x + w + 44, y + h), h // 2, fill=bg)
        self.d.text((x + 22, y + h / 2), s, font=font, fill=fg, anchor="lm")
        return w + 44, h

    def dark(self, lines, size=56, sub=None):
        """에스프레소 말풍선 (질문 등)"""
        h = int(size * 1.35) * len(lines) + (int(46 * 1.4) if sub else 0) + 64
        self.d.rounded_rectangle((M, self.y, W - M, self.y + h), 34, fill=INK)
        y = self.y + 32
        for ln in lines:
            self.d.text((M + 44, y), ln, font=F(size, 800), fill=BG); y += int(size * 1.35)
        if sub:
            self.d.text((M + 44, y), sub, font=F(42, 600), fill=SOFT)
        self.y += h + 28

    def card(self, draw_fn, pad=44):
        """카드 안을 그린 뒤 높이를 맞춰 테두리를 그림"""
        top = self.y
        self.y += pad
        draw_fn(M + pad, W - M - pad)
        self.y += pad - 10
        layer = Image.new("RGB", (W, self.y - top), BG)
        ImageDraw.Draw(layer).rounded_rectangle((M, 0, W - M, self.y - top - 1), 34, fill=CARD, outline=LINE, width=3)
        content = self.im.crop((0, top, W, self.y))
        # 카드 배경을 깔고 내용을 다시 올림 (배경색 BG 위 그림만 유지)
        mask = Image.eval(content.convert("L"), lambda v: 0)
        diff = Image.new("L", content.size, 0)
        px, bgc = content.load(), (244, 238, 228)
        dpx = diff.load()
        for yy in range(content.size[1]):
            for xx in range(content.size[0]):
                if px[xx, yy] != bgc:
                    dpx[xx, yy] = 255
        layer.paste(content, (0, 0), diff)
        self.im.paste(layer, (0, top))
        self.y += 26

    def note(self, s, size=42):
        lines = self.wrap(s, F(size, 700), W - 2 * M - 80)
        h = int(size * 1.45) * len(lines) + 60
        self.d.rounded_rectangle((M, self.y, W - M, self.y + h), 30, fill=LIME)
        y = self.y + 30
        for ln in lines:
            self.d.text((M + 40, y), ln, font=F(size, 700), fill=INK); y += int(size * 1.45)
        self.y += h + 28

    def save(self, name):
        y = self.y + 20
        d = self.d
        d.rounded_rectangle((M, y, M + 54, y + 54), 13, fill=INK)
        d.text((M + 13, y + 27), "C", font=F(38, 800), fill=BG, anchor="lm")
        d.ellipse((M + 35, y + 33, M + 44, y + 42), fill=LIME)
        d.text((M + 72, y + 27), "카페인영어 CafeInEnglish", font=F(36, 700), fill=INK, anchor="lm")
        d.text((W - M, y + 27), "cafeinenglish.com", font=F(32, 600), fill=MUTED, anchor="rm")
        im = self.im.crop((0, 0, W, y + 54 + 56))
        OUT.mkdir(exist_ok=True)
        im.convert("P", palette=Image.ADAPTIVE, colors=64).save(OUT / name, optimize=True)
        print("🖼 ", name, im.size)


def label(c, x, s):
    c.text(x, s, F(38, 700), MUTED, 1.3)


# ---------------------------------------------------------------- 도식들
def negative_question():
    c = Canvas("부정 질문, 이렇게 대답해요")
    c.dark(["Don't you like coffee?"], 60, "커피 안 좋아해?")
    for head, ko, en, tag in (("커피를 좋아한다면", "아니, 좋아해", "Yes, I do.", "긍정이면 Yes"),
                              ("커피를 안 좋아한다면", "응, 안 좋아해", "No, I don't.", "부정이면 No")):
        def body(x, r, head=head, ko=ko, en=en, tag=tag):
            c.text(x, head, F(46, 800)); c.y += 6
            label(c, x, "한국어"); c.text(x, ko, F(54, 700)); c.y += 8
            label(c, x, "영어"); c.hl(x, c.y, en, F(78, 800)); c.y += int(78 * 1.3)
            c.pill(x, c.y, tag); c.y += 66
        c.card(body)
    c.note("영어는 질문 모양과 상관없이, 내 대답이 긍정이면 Yes · 부정이면 No")
    c.save("negative-question-answer-yes-no.png")


def timeline(c, x, r, kind):
    """시간 막대: now 기준"""
    y = c.y + 40
    d = c.d
    d.line((x, y, r, y), fill=LINE, width=10)
    d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=INK)
    d.text((x, y + 30), "지금", font=F(36, 700), fill=MUTED, anchor="ma")
    mid = x + (r - x) * 0.62
    if kind == "in":
        d.line((x, y, mid, y), fill=INK, width=10)
        d.ellipse((mid - 22, y - 22, mid + 22, y + 22), fill=LIME, outline=INK, width=6)
        d.text((mid, y + 30), "10분 뒤 딱 이때", font=F(36, 700), fill=INK, anchor="ma")
    elif kind == "within":
        d.rectangle((x, y - 12, mid, y + 12), fill=LIME)
        d.line((mid, y - 30, mid, y + 30), fill=INK, width=6)
        d.text(((x + mid) / 2, y + 30), "이 안이면 언제든 OK", font=F(36, 700), fill=INK, anchor="ma")
    else:  # after
        ev = x + (r - x) * 0.3
        d.rounded_rectangle((ev - 70, y - 30, ev + 70, y + 30), 16, fill=INK)
        d.text((ev, y), "점심", font=F(34, 700), fill=BG, anchor="mm")
        d.ellipse((mid - 22, y - 22, mid + 22, y + 22), fill=LIME, outline=INK, width=6)
        d.text((mid, y + 30), "그다음", font=F(36, 700), fill=INK, anchor="ma")
    c.y += 140


def in_after_within():
    c = Canvas("in · after · within, 언제를 말할까?")
    rows = [("in", "in 10 minutes", "지금부터 10분 뒤", "I'll be there in ten minutes."),
            ("after", "after lunch", "어떤 일 다음에", "Let's take a walk after lunch."),
            ("within", "within 24 hours", "24시간 이내에", "Please reply within 24 hours.")]
    for kind, en, ko, ex in rows:
        def body(x, r, kind=kind, en=en, ko=ko, ex=ex):
            c.hl(x, c.y, en, F(64, 800)); c.y += int(64 * 1.3)
            c.text(x, ko, F(46, 700))
            timeline(c, x + 40, r - 40, kind)
            for ln in c.wrap(ex, F(40, 600), r - x):
                c.text(x, ln, F(40, 600), MUTED)
        c.card(body)
    c.note("'10분 후에 갈게'는 after가 아니라 in 10 minutes!")
    c.save("in-after-within-timeline.png")


def excuse_sorry():
    c = Canvas("Excuse me · Sorry · Pardon", "상황에 따라 이렇게 골라 써요")
    rows = [("실수하기 전 · 양해 구할 때", "지나갈 때, 사람 부를 때", "Excuse me."),
            ("실수한 뒤 · 사과할 때", "부딪혔을 때, 발 밟았을 때", "Sorry!"),
            ("못 알아들었을 때 (끝을 올려서)", "네? 뭐라고요?", "Sorry? / Pardon?")]
    for i, (when, eg, en) in enumerate(rows):
        def body(x, r, i=i, when=when, eg=eg, en=en):
            c.pill(x, c.y, f"{i + 1}"); c.d.text((x + 100, c.y + 6), when, font=F(44, 800), fill=INK); c.y += 78
            c.text(x, eg, F(40, 600), MUTED); c.y += 4
            c.hl(x, c.y, en, F(70, 800)); c.y += int(70 * 1.25)
        c.card(body)
    c.note("부딪히기 전엔 Excuse me, 부딪힌 후엔 Sorry! (영국·캐나다에선 지나갈 때도 Sorry를 많이 써요)", 40)
    c.save("excuse-me-sorry-pardon.png")


def would_you_mind():
    c = Canvas("부탁의 정중함 계단")
    steps = [("Can you ~?", "편한 사이"), ("Could you ~?", "정중하게"), ("Would you mind ~ing?", "아주 정중하게")]
    base = c.y
    sw = (W - 2 * M) // 3
    hs = [210, 310, 410]
    for i, (en, ko) in enumerate(steps):
        x0 = M + i * sw
        top = base + 410 - hs[i]
        c.d.rounded_rectangle((x0 + 6, top, x0 + sw - 6, base + 410), 22, fill=[CARD, SOFT, LIME][i], outline=LINE, width=3)
        lines = c.wrap(en, F(40, 800), sw - 40)
        yy = top + 24
        for ln in lines:
            c.d.text((x0 + 26, yy), ln, font=F(40, 800), fill=INK); yy += 52
        c.d.text((x0 + 26, yy + 6), ko, font=F(36, 700), fill=MUTED)
    c.y = base + 440
    c.text(M, "대답할 때 함정!", F(52, 800)); c.y += 6
    c.dark(["Would you mind", "closing the door?"], 54, "(문 닫는 거) 꺼리세요?")

    def body(x, r):
        label(c, x, "해 줄게요 (OK)")
        c.hl(x, c.y, "Not at all.", F(66, 800)); c.y += int(66 * 1.3)
        c.text(x, "No, go ahead. / Sure, no problem.", F(42, 700)); c.y += 12
        label(c, x, "주의")
        for ln in c.wrap("Yes만 단독으로 하면 '네, 꺼려요(싫어요)'로 들릴 수 있어요", F(42, 700), r - x):
            c.text(x, ln, F(42, 700))
    c.card(body)
    c.note("mind = 꺼리다 → '꺼리세요?' '아뇨(No), 전혀요!' = 해 줄게요")
    c.save("would-you-mind-politeness.png")


def doctor():
    c = Canvas("아픈 곳 + ache", "어디가 아픈지 이렇게 말해요")
    rows = [("머리", "head", "headache"), ("이", "tooth", "toothache"), ("귀", "ear", "earache"),
            ("배", "stomach", "stomachache"), ("허리 · 등", "back", "backache")]

    def body(x, r):
        for i, (ko, part, en) in enumerate(rows):
            c.d.text((x, c.y), ko, font=F(46, 800), fill=INK)
            c.d.text((x + 230, c.y + 4), part + " +ache", font=F(40, 600), fill=MUTED)
            c.y += 62
            c.hl(x, c.y, "I have a " + en + ".", F(52, 800)); c.y += 78
            if i < len(rows) - 1:
                c.d.line((x, c.y, r, c.y), fill=LINE, width=3); c.y += 26
    c.card(body)

    def throat(x, r):
        c.text(x, "목 (throat)만 예외!", F(46, 800)); c.y += 4
        c.d.text((x, c.y), "throatache", font=F(48, 700), fill=MUTED)
        w = c.d.textlength("throatache", font=F(48, 700))
        c.d.line((x, c.y + 32, x + w, c.y + 32), fill="#B23A2B", width=6)
        c.y += 76
        c.hl(x, c.y, "I have a sore throat.", F(56, 800)); c.y += 80
    c.card(throat)
    c.note("응급 상황(가슴 통증·호흡 곤란)은 바로 911 / ER로!")
    c.save("doctor-ache-body-parts.png")


def im_good():
    c = Canvas("I'm good, 뜻이 두 개예요")
    for q, qko, meaning, tip in (("How are you?", "잘 지내?", "잘 지내 (안부 대답)", None),
                                  ("Do you need a bag?", "봉투 필요하세요?", "괜찮아요, 됐어요 (거절)", "받고 싶다면 → Yes, please.")):
        c.dark([q], 56, qko)

        def body(x, r, meaning=meaning, tip=tip):
            c.hl(x, c.y, "I'm good.", F(66, 800)); c.y += int(66 * 1.3)
            c.text(x, "= " + meaning, F(48, 800))
            if tip:
                c.y += 6; c.text(x, tip, F(42, 700), MUTED)
        c.card(body)
    c.note("뭔가를 권할 때 나온 I'm good은 '필요 없어요'라는 정중한 거절!")
    c.save("im-good-two-meanings.png")


def keep_posted():
    c = Canvas("한 번? 계속? 알려 달라는 말")

    def dots(x, r, n):
        y = c.y + 34
        c.d.line((x, y, r, y), fill=LINE, width=8)
        for i in range(n):
            px = x + (r - x) * ((i + 1) / (n + 1)) if n > 1 else r - 60
            c.d.ellipse((px - 22, y - 22, px + 22, y + 22), fill=LIME, outline=INK, width=6)
        c.y += 90
    for en, ko, n, ex in (("Let me know.", "결과를 한 번 알려줘", 1, "Let me know when you get home."),
                          ("Keep me posted.", "진행될 때마다 계속 알려줘", 4, "Keep me posted on the interview!")):
        def body(x, r, en=en, ko=ko, n=n, ex=ex):
            c.hl(x, c.y, en, F(66, 800)); c.y += int(66 * 1.3)
            c.text(x, ko, F(48, 800))
            dots(x + 20, r - 20, n)
            for ln in c.wrap(ex, F(40, 600), r - x):
                c.text(x, ln, F(40, 600), MUTED)
        c.card(body)
    c.note("한 번이면 Let me know, 계속이면 Keep me posted!")
    c.save("let-me-know-vs-keep-me-posted.png")


def konglish():
    c = Canvas("콩글리시 → 이렇게 말해요")
    rows = [("핸드폰", "cell phone"), ("노트북", "laptop"), ("화이팅!", "You got this!"),
            ("아이쇼핑", "window shopping"), ("아르바이트", "part-time job"), ("원룸", "studio apartment")]

    def body(x, r):
        for i, (ko, en) in enumerate(rows):
            c.d.text((x, c.y), ko, font=F(46, 700), fill=MUTED)
            c.d.text((x + 300, c.y - 2), "→", font=F(50, 800), fill=INK)
            c.hl(x + 380, c.y - 4, en, F(50, 800))
            c.y += 80
            if i < len(rows) - 1:
                c.d.line((x, c.y, r, c.y), fill=LINE, width=3); c.y += 26
    c.card(body)
    c.note("미국·영국 기준이에요. (영국은 cell phone 대신 mobile, studio apartment 대신 studio flat)", 38)
    c.save("konglish-to-english.png")


def linking():
    c = Canvas("원어민은 이렇게 줄여 말해요")
    rows = [("going to", "gonna", "거나"), ("want to", "wanna", "워너"), ("(have) got to", "gotta", "가러")]
    for full, short, ko in rows:
        def body(x, r, full=full, short=short, ko=ko):
            c.text(x, full, F(52, 700), MUTED)
            c.d.text((x, c.y - 6), "↓  빨리 말하면", font=F(40, 700), fill=MUTED); c.y += 62
            c.hl(x, c.y, short, F(80, 800))
            c.d.text((x + c.d.textlength(short, font=F(80, 800)) + 40, c.y + 20), f"'{ko}'처럼 들려요", font=F(44, 700), fill=INK)
            c.y += int(80 * 1.25)
        c.card(body)
    c.note("말할 땐 써도 되지만, 시험·공식 문서에는 going to / want to로 써요", 40)
    c.save("gonna-wanna-gotta.png")


if __name__ == "__main__":
    for fn in (negative_question, in_after_within, excuse_sorry, would_you_mind, doctor, im_good, keep_posted, konglish, linking):
        fn()

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
BG, CARD, INK, LIME, MUTED, LINE, SOFT = "#FAF8F5", "#FFFFFF", "#2A1A12", "#CDEB5B", "#7A6A5E", "#ECE6DD", "#D9CDBE"
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
        px, bgc = content.load(), (250, 248, 245)
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


def ed_sounds():
    c = Canvas("-ed는 세 가지로 소리 나요", "앞 소리가 무엇인지에 따라 달라져요")
    rows = [("[t]  트", "p, k, s, sh, ch, f 뒤", ["helped", "worked", "watched"]),
            ("[d]  드", "그 밖의 소리(모음, b, g, l, m, n, v …) 뒤", ["played", "called", "loved"]),
            ("[ɪd]  이드", "t, d 뒤 (한 음절 늘어남)", ["wanted", "needed", "decided"])]
    for snd, when, exs in rows:
        def body(x, r, snd=snd, when=when, exs=exs):
            c.pill(x, c.y, snd, F(44, 800)); c.y += 90
            c.text(x, when, F(40, 700), MUTED, 1.45)
            xx = x
            for w in exs:
                xx += c.hl(xx, c.y, w, F(52, 800)) + 40
            c.y += int(52 * 1.3)
        c.card(body)
    c.note("t·d로 끝나는 동사만 '이드'가 붙어요. worked는 '워크드'가 아니라 '웍트'!", 40)
    c.save("ed-three-sounds.png")


def appointment_promise():
    c = Canvas("'약속'은 영어로 세 가지", "누구와, 무엇을 정했는지에 따라 달라요")
    rows = [("plans", "친구와 만나기로 한 약속", "I have plans tonight."),
            ("appointment", "병원·미용실·상담 같은 예약 약속", "I have a dentist appointment."),
            ("promise", "'꼭 그렇게 할게'라는 다짐", "I promise I'll call you.")]
    for w, ko, ex in rows:
        def body(x, r, w=w, ko=ko, ex=ex):
            c.hl(x, c.y, w, F(64, 800)); c.y += int(64 * 1.35)
            c.text(x, ko, F(42, 700), MUTED, 1.5)
            c.text(x, ex, F(44, 700), INK, 1.2)
        c.card(body)
    c.note("'I have a promise.'는 어색해요. 친구와 만날 약속은 plans!", 40)
    c.save("plans-appointment-promise.png")


def fair_enough():
    c = Canvas("Fair enough의 온도", "상대 말을 받아들일 때, 얼마나 동의하는지")
    rows = [("Totally!", "완전 동의해"), ("Makes sense.", "듣고 보니 이해돼"), ("Fair enough.", "인정, 그럴 만하네"), ("If you say so.", "네가 그렇다면야 (못 믿겠지만)")]
    def body(x, r):
        for i, (en, ko) in enumerate(rows):
            if en == "Fair enough.":
                c.hl(x, c.y, en, F(54, 800))
            else:
                c.d.text((x, c.y), en, font=F(54, 800), fill=INK)
            c.y += int(54 * 1.3)
            c.text(x, ko, F(40, 700), MUTED, 1.3)
            if i < len(rows) - 1:
                c.d.line((x, c.y + 4, r, c.y + 4), fill=LINE, width=3); c.y += 34
    c.card(body)
    c.note("위로 갈수록 적극 동의, 아래로 갈수록 시큰둥해요", 40)
    c.save("fair-enough-scale.png")


def up_to_you():
    c = Canvas("결정을 상대에게 넘길 때", "같은 '네가 정해'도 느낌이 달라요")
    rows = [("It's up to you.", "네가 정해 (가장 기본)", "무난"), ("Your call.", "네 판단에 맡길게", "짧고 쿨함"),
            ("I'm easy.", "난 아무거나 괜찮아 (영국에서 특히)", "편한 사이"), ("Whatever.", "알아서 해 (짜증)", "주의")]
    def body(x, r):
        for i, (en, ko, tag) in enumerate(rows):
            w = c.d.textlength(en, font=F(54, 800))
            c.d.text((x, c.y), en, font=F(54, 800), fill=INK)
            c.pill(x + w + 24, c.y + 4, tag, F(34, 700), bg=(LIME if tag != "주의" else "#F4D6D2"), fg=INK)
            c.y += int(54 * 1.35)
            c.text(x, ko, F(40, 700), MUTED, 1.3)
            if i < len(rows) - 1:
                c.d.line((x, c.y + 4, r, c.y + 4), fill=LINE, width=3); c.y += 34
    c.card(body)
    c.note("Whatever는 혼자 쓰면 '맘대로 해'처럼 들려요. 뒤에 works for me를 붙이면 OK!", 38)
    c.save("up-to-you-scale.png")


def slipped_mind():
    c = Canvas("'깜빡했다'도 영어로는 여러 가지", "무엇을, 어떻게 잊었는지에 따라 달라요")
    rows = [("It slipped my mind.", "할 일·약속을 깜빡했어요 (사과할 때 부드럽게)"),
            ("I forgot.", "잊어버렸어요 (가장 기본, 직설적)"),
            ("His name escapes me.", "이름이 생각이 안 나요 (현재형으로)"),
            ("It's on the tip of my tongue.", "혀끝에서 맴돌아요 (알긴 아는데)"),
            ("My mind went blank.", "머릿속이 하얘졌어요 (긴장한 순간)")]
    def body(x, r):
        for i, (en, ko) in enumerate(rows):
            if i == 0:
                c.hl(x, c.y, en, F(52, 800))
            else:
                c.d.text((x, c.y), en, font=F(52, 800), fill=INK)
            c.y += int(52 * 1.3)
            c.text(x, ko, F(38, 700), MUTED, 1.3)
            if i < len(rows) - 1:
                c.d.line((x, c.y + 4, r, c.y + 4), fill=LINE, width=3); c.y += 34
    c.card(body)
    c.note("주어는 잊힌 것! It slipped my mind.", 40)
    c.save("slipped-my-mind.png")


def rain_check():
    c = Canvas("rain check, take와 give", "거절하는 사람과 초대한 사람의 말이 달라요")
    rows = [("거절하는 사람", "Can I take a rain check?", "다음에 해도 될까?"),
            ("초대한 사람", "Sure, I'll give you a rain check.", "그래, 다음에 하자.")]
    for who, en, ko in rows:
        def body(x, r, who=who, en=en, ko=ko):
            c.pill(x, c.y, who, F(38, 700)); c.y += 84
            for ln in c.wrap(en, F(52, 800), r - x):
                c.d.text((x, c.y), ln, font=F(52, 800), fill=INK); c.y += int(52 * 1.3)
            c.text(x, ko, F(40, 700), MUTED, 1.2)
        c.card(body)
    c.note("원래는 우천 취소 경기의 다음 입장권", 40)
    c.save("rain-check-take-give.png")


def bored_boring():
    c = Canvas("bored와 boring, 화살표로 보기", "-ing는 감정을 주는 쪽, -ed는 감정을 받는 쪽")
    def body(x, r):
        c.d.text((x, c.y), "The movie", font=F(54, 800), fill=INK)
        c.d.text((r, c.y), "me", font=F(54, 800), fill=INK, anchor="ra")
        y = c.y + 34
        c.d.line((x + 300, y, r - 110, y), fill=INK, width=6)
        c.d.polygon([(r - 110, y - 16), (r - 82, y), (r - 110, y + 16)], fill=INK)
        c.y += int(54 * 1.6)
        c.hl(x, c.y, "boring", F(54, 800))
        w = c.d.textlength("bored", font=F(54, 800))
        c.hl(r - w, c.y, "bored", F(54, 800))
        c.y += int(54 * 1.35)
        c.text(x, "지루하게 만드는 쪽", F(38, 700), MUTED, 1.2)
        c.y -= int(38 * 1.2)
        c.d.text((r, c.y), "지루함을 느끼는 쪽", font=F(38, 700), fill=MUTED, anchor="ra")
        c.y += int(38 * 1.4)
    c.card(body)
    rows = [("I'm bored.", "나 지루해 (내 기분)"), ("I'm boring.", "나는 지루한 사람이야 (남을 지루하게 함)")]
    def body2(x, r):
        for i, (en, ko) in enumerate(rows):
            c.d.text((x, c.y), en, font=F(54, 800), fill=INK); c.y += int(54 * 1.3)
            c.text(x, ko, F(40, 700), MUTED, 1.3)
            if i == 0:
                c.d.line((x, c.y + 4, r, c.y + 4), fill=LINE, width=3); c.y += 34
    c.card(body2)
    c.note("내 기분은 -ed! I'm bored. I'm excited.", 40)
    c.save("bored-boring.png")


def borrow_lend():
    c = Canvas("borrow와 lend는 방향이 반대예요", "물건이 어느 쪽으로 가는지만 보면 돼요")
    rows = [("borrow", "빌리다 (나에게 온다)", "Can I borrow your pen?", "borrow + 물건 + from 사람"),
            ("lend", "빌려주다 (나에게서 간다)", "Can you lend me your pen?", "lend + 사람 + 물건")]
    for w, ko, ex, pat in rows:
        def body(x, r, w=w, ko=ko, ex=ex, pat=pat):
            c.hl(x, c.y, w, F(64, 800)); c.y += int(64 * 1.35)
            c.text(x, ko, F(42, 700), MUTED, 1.45)
            c.text(x, ex, F(46, 800), INK, 1.4)
            c.text(x, pat, F(38, 700), MUTED, 1.2)
        c.card(body)
    c.note("빌려 달라고 할 땐 Can you lend me ~?", 40)
    c.save("borrow-lend.png")


def running_late():
    c = Canvas("늦을 때 영어, 언제 무슨 말을 할까", "가는 중인지, 도착했는지에 따라 달라요")
    rows = [("가는 중, 미리 알릴 때", "I'm running late.", "좀 늦을 것 같아요"),
            ("지금 가고 있을 때", "I'm on my way.", "가는 중이에요"),
            ("도착해서 사과할 때", "Sorry I'm late.", "늦어서 미안해요"),
            ("상대를 기다리게 했을 때", "Sorry to keep you waiting.", "기다리게 해서 죄송해요")]
    def body(x, r):
        for i, (when, en, ko) in enumerate(rows):
            c.pill(x, c.y, when, F(36, 700)); c.y += 80
            if i == 0:
                c.hl(x, c.y, en, F(54, 800))
            else:
                c.d.text((x, c.y), en, font=F(54, 800), fill=INK)
            c.y += int(54 * 1.3)
            c.text(x, ko, F(40, 700), MUTED, 1.3)
            if i < len(rows) - 1:
                c.d.line((x, c.y + 4, r, c.y + 4), fill=LINE, width=3); c.y += 34
    c.card(body)
    c.note("도착 전엔 running late, 도착하면 Sorry I'm late!", 40)
    c.save("running-late-timeline.png")


def no_prep_verbs():
    c = Canvas("전치사 없이 바로 쓰는 동사", "한국어 조사를 영어로 옮기지 마세요")
    rows = [("논의하다", "discuss about the plan", "discuss the plan"),
            ("결혼하다", "marry with him", "marry him"),
            ("연락하다", "contact to me", "contact me"),
            ("들어가다", "enter into the room", "enter the room")]
    def body(x, r):
        for i, (ko, no, ok) in enumerate(rows):
            c.text(x, ko, F(40, 700), MUTED, 1.35)
            y0 = c.y
            c.d.line((x + 6, c.y + 14, x + 38, c.y + 46), fill="#E5484D", width=7)
            c.d.line((x + 38, c.y + 14, x + 6, c.y + 46), fill="#E5484D", width=7)
            c.d.text((x + 70, c.y), no, font=F(46, 700), fill=MUTED)
            w = c.d.textlength(no, font=F(46, 700))
            c.d.line((x + 70, y0 + 30, x + 70 + w, y0 + 30), fill=MUTED, width=4)
            c.y += int(46 * 1.45)
            c.d.text((x, c.y), "○", font=F(46, 800), fill="#2F9E44")
            c.hl(x + 70, c.y, ok, F(52, 800))
            c.y += int(52 * 1.35)
            if i < len(rows) - 1:
                c.d.line((x, c.y + 4, r, c.y + 4), fill=LINE, width=3); c.y += 34
    c.card(body)
    c.note("about이 꼭 쓰고 싶다면 talk about!", 40)
    c.save("no-preposition-verbs.png")


def can_cant():
    c = Canvas("can과 can't, 강세로 구별해요", "t를 찾지 말고 세게 들리는 곳을 들어 보세요")
    def row(x, parts, ko):
        xx = x
        base = c.y + 70
        for word, big in parts:
            f = F(84 if big else 44, 800 if big else 600)
            c.d.text((xx, base), word, font=f, fill=INK if big else MUTED, anchor="ls")
            xx += c.d.textlength(word + " ", font=f)
        c.y += 100
        c.text(x, ko, F(40, 700), MUTED, 1.3)
    def body(x, r):
        c.pill(x, c.y, "can = 약하게 /kən/ 컨", F(36, 700)); c.y += 84
        row(x, [("I", False), ("can", False), ("come.", True)], "동사 come이 크게 들려요")
        c.d.line((x, c.y + 16, r, c.y + 16), fill=LINE, width=3); c.y += 52
        c.pill(x, c.y, "can't = 세게 /kænt/ 캔트", F(36, 700), bg=LIME, fg=INK); c.y += 84
        row(x, [("I", False), ("can't", True), ("come.", False)], "can't가 크고 또렷하게 들려요")
    c.card(body)
    def body2(x, r):
        c.text(x, "문장 끝에서는 둘 다 세게", F(46, 800), INK, 1.4)
        c.text(x, "Yes, I can.  /  No, I can't.", F(48, 800), INK, 1.35)
        c.text(x, "Yes·No가 함께 와서 헷갈릴 일이 적어요", F(38, 700), MUTED, 1.3)
    c.card(body2)
    c.note("t는 약하거나 안 들릴 때가 많아요. 강세를 들으세요!", 40)
    c.save("can-cant-stress.png")


def me_too_neither():
    c = Canvas("'나도'는 상대 말에 따라 달라요", "긍정에는 too, 부정에는 neither")
    rows = [("상대가 긍정으로 말하면", "I like coffee.", ["Me too.", "So do I."], "나도 좋아해"),
            ("상대가 부정으로 말하면", "I don't like coffee.", ["Me neither.", "Neither do I."], "나도 안 좋아해")]
    for who, said, ans, ko in rows:
        def body(x, r, who=who, said=said, ans=ans, ko=ko):
            c.pill(x, c.y, who, F(36, 700)); c.y += 84
            c.d.text((x, c.y), said, font=F(48, 700), fill=MUTED); c.y += int(48 * 1.45)
            xx = x
            for i, a in enumerate(ans):
                w = c.hl(xx, c.y, a, F(56, 800))
                xx += w + 40
                if i == 0:
                    c.d.text((xx, c.y + 6), "/", font=F(48, 700), fill=MUTED); xx += 50
            c.y += int(56 * 1.35)
            c.text(x, ko, F(40, 700), MUTED, 1.2)
        c.card(body)
    c.note("not, never가 들리면 neither로 맞장구!", 40)
    c.save("me-too-neither.png")


def im_beat():
    c = Canvas("'피곤해'를 자리에 맞게 고르기", "위 두 개는 어디서나, 아래 두 개는 편한 사이에서")
    rows = [("어디서나 기본", "I'm tired.", "피곤해", False),
            ("회사에서도 무난", "I'm exhausted.", "진이 다 빠졌어", False),
            ("친구·편한 동료", "I'm beat.", "완전 녹초야", True),
            ("친구·편한 동료", "I'm wiped out.", "완전 뻗었어", False)]
    def body(x, r):
        for i, (when, en, ko, key) in enumerate(rows):
            c.pill(x, c.y, when, F(36, 700), bg=INK if i < 2 else LIME, fg=BG if i < 2 else INK); c.y += 80
            if key:
                c.hl(x, c.y, en, F(56, 800))
            else:
                c.d.text((x, c.y), en, font=F(56, 800), fill=INK)
            c.y += int(56 * 1.3)
            c.text(x, ko, F(40, 700), MUTED, 1.3)
            if i < len(rows) - 1:
                c.d.line((x, c.y + 4, r, c.y + 4), fill=LINE, width=3); c.y += 34
    c.card(body)
    c.note("beat는 명사 앞에 안 써요. You look beat!", 40)
    c.save("im-beat-tired.png")


def agree_preps():
    c = Canvas("agree 뒤에 오는 말", "with, to, on은 동의하는 대상이 달라요")
    rows = [("agree with", "사람·의견에 같은 생각", "I agree with you."),
            ("agree to", "제안·조건을 받아들이다", "She agreed to the plan."),
            ("agree on", "함께 정하다 (날짜·가격)", "Let's agree on a date.")]
    for w, ko, ex in rows:
        def body(x, r, w=w, ko=ko, ex=ex):
            c.hl(x, c.y, w, F(64, 800)); c.y += int(64 * 1.35)
            c.text(x, ko, F(42, 700), MUTED, 1.45)
            c.text(x, ex, F(48, 800), INK, 1.2)
        c.card(body)
    c.note("agree는 동사! I'm agree가 아니라 I agree", 40)
    c.save("agree-with-to-on.png")


def long_story_short():
    c = Canvas("Long story short, 이렇게 말해요", "사정은 접고, 결과 한 문장만")
    def before(x, r):
        c.pill(x, c.y, "앞: 길고 복잡한 사정", F(36, 700), bg=SOFT, fg=INK); c.y += 84
        for en, ko in (("Our flight was delayed.", "비행기가 지연됐고"),
                       ("We missed our connection.", "환승 편을 놓쳤고"),
                       ("We slept at the airport.", "공항에서 잤어")):
            c.d.text((x, c.y), en, font=F(46, 700), fill=MUTED); c.y += int(46 * 1.3)
            c.text(x, ko, F(38, 600), MUTED, 1.45)
    c.card(before)
    c.dark(["Long story short,"], 64, "간단히 말하면, (잠깐 쉬고)")
    def after(x, r):
        c.pill(x, c.y, "뒤: 결과 한 문장", F(36, 700), bg=LIME, fg=INK); c.y += 84
        c.hl(x, c.y, "We got home a day late.", F(58, 800)); c.y += int(58 * 1.35)
        c.text(x, "하루 늦게 집에 왔어.", F(42, 700), MUTED, 1.2)
    c.card(after)
    c.note("긴 형태는 영국 cut, 미국 make를 넣어 말해요", 40)
    c.save("long-story-short-flow.png")


def almost_most():
    c = Canvas("'대부분'을 영어로 말할 때", "명사 앞에는 이 세 가지 모양")
    rows = [("일반적인 사람·사물", "Most people", "대부분의 사람들"),
            ("정해진 무리 중에서", "Most of the students", "그 학생들 대부분"),
            ("거의 전부라고 강조", "Almost all (of) my friends", "내 친구 거의 다")]
    for when, en, ko in rows:
        def body(x, r, when=when, en=en, ko=ko):
            c.pill(x, c.y, when, F(36, 700)); c.y += 84
            c.hl(x, c.y, en, F(58, 800)); c.y += int(58 * 1.35)
            c.text(x, ko, F(42, 700), MUTED, 1.2)
        c.card(body)
    def wrong(x, r):
        c.pill(x, c.y, "이렇게는 말하지 않아요", F(36, 700), bg=SOFT, fg=INK); c.y += 84
        for en in ("Almost people", "The most people", "Most of people"):
            w = c.d.textlength(en, font=F(50, 700))
            c.d.text((x, c.y), en, font=F(50, 700), fill=MUTED)
            c.d.line((x - 4, c.y + 32, x + w + 4, c.y + 32), fill="#E5484D", width=5)
            c.y += int(50 * 1.45)
    c.card(wrong)
    c.note("almost는 부사! 명사 앞에선 almost all", 40)
    c.save("almost-most-of.png")


if __name__ == "__main__":
    for fn in (negative_question, in_after_within, excuse_sorry, would_you_mind, doctor, im_good, keep_posted, konglish, linking, ed_sounds, appointment_promise, fair_enough, up_to_you, slipped_mind, rain_check, bored_boring, borrow_lend, running_late, no_prep_verbs, can_cant, me_too_neither, im_beat, agree_preps, long_story_short, almost_most):
        fn()

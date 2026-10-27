# 카영 롱폼 공통 스타일 (2026-10 확정)
# 1) 영상 장면: 아래 검정 음영은 항상 고정, 자막 글자만 말할 때 싱크에 맞춰 나타남
# 2) 이름표(왼쪽 위 알약)는 글자를 세로 가운데 정렬
# 3) 학습 화면: 흰 바탕 · 토스 톤 · 웹과 같은 3D 아이콘, 형광 알약 대신 아이콘 + 글자
# 4) 마지막 소개: 웹 화면을 그대로 보여 주고 학습 페이지로 자연스럽게 유도
import os, re, json, hashlib, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FP = '/mnt/user-data/uploads/CafeInEnglish_Claude/CafeInEnglish_Claude/fonts/PretendardVariable.ttf'
ICON = '/mnt/user-data/uploads/CafeInEnglish_Claude/CafeInEnglish_Claude/assets/icons/'
LOGO = '/mnt/user-data/uploads/CafeInEnglish_Claude/CafeInEnglish_Claude/assets/icon-512.png'
W, H, FPS = 1920, 1080, 30
# 웹과 같은 색
WHITE, TXT, SUB, GRAY, LINE, CARD = (255, 255, 255), (25, 31, 40), (78, 89, 104), (139, 149, 161), (229, 232, 235), (242, 244, 246)
BLUE, ESP, LIME, RED, GREEN = (49, 130, 246), (42, 26, 18), (205, 235, 91), (229, 72, 77), (32, 178, 107)
CREDIT_DEFAULT = ''
BAND_TOP = 820          # 영상 음영 시작
_fc = {}


def F(size, w='Bold'):
    k = (size, w)
    if k not in _fc:
        f = ImageFont.truetype(FP, size); f.set_variation_by_name(w); _fc[k] = f
    return _fc[k]


def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))


def wrap(d, text, font, maxw):
    words = text.split(' '); lines = []; cur = ''
    for w_ in words:
        t = (cur + ' ' + w_).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w_
    if cur: lines.append(cur)
    return lines


def vcenter(d, x, ytop, h, text, font, fill, anchor_x='l'):
    """글자를 상자 높이 h 안에서 세로 가운데로"""
    bb = d.textbbox((0, 0), text, font=font)
    y = ytop + (h - (bb[3] - bb[1])) / 2 - bb[1]
    if anchor_x == 'm': x = x - (bb[2] - bb[0]) / 2 - bb[0]
    d.text((x, y), text, font=font, fill=fill)


def ctext(d, y, text, font, fill, maxw=1600, gap=1.32, cx=W / 2):
    for ln in wrap(d, text, font, maxw):
        w_ = d.textlength(ln, font=font); d.text((cx - w_ / 2, y), ln, font=font, fill=fill); y += font.size * gap
    return y


def icon(im, name, x, y, size):
    ic = Image.open(ICON + name + '.webp').convert('RGBA').resize((size, size), Image.LANCZOS)
    im.paste(ic, (int(x), int(y)), ic)


# ---------- 영상 장면 오버레이 ----------
def credit_pill(d, x, y, t, size=24):
    f = F(size, 'SemiBold'); w_ = d.textlength(t, font=f)
    d.rounded_rectangle((x - 2, y - 2, x + w_ + 26, y + size + 18), (size + 20) // 2, fill=(0, 0, 0, 120))
    d.text((x + 12, y + 6), t, font=f, fill=(255, 255, 255, 230))


def video_base(path, label=None, credit=True):
    """영상 위 판 (A안): 아래 음영 + 진갈색 장면 태그 + 오른쪽 위 출처"""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for y in range(BAND_TOP - 200, H):
        a = 215 if y >= BAND_TOP else int(215 * ((y - (BAND_TOP - 200)) / 200) ** 1.5)
        d.line((0, y, W, y), fill=(8, 10, 13, a))
    if label:
        f = F(30, 'Bold'); w_ = d.textlength(label, font=f)
        d.rounded_rectangle((64, 56, 64 + w_ + 48, 56 + 58), 29, fill=ESP + (235,))
        vcenter(d, 88, 56, 58, label, f, (255, 255, 255))
    t = 'CafeInEnglish' + ((f'  ·  영상 출처: {credit}' if isinstance(credit, str) else f'  ·  영상 출처: {CREDIT_DEFAULT}') if credit else '')
    w_ = d.textlength(t, font=F(24, 'SemiBold'))
    credit_pill(d, W - 64 - w_ - 26, 64, t)
    im.save(path)


def video_text(path, en=None, ko=None, speaker=None, narr=None):
    """자막 글자만 (음영 없음). 음영 영역 가운데에 놓음"""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rows = []
    if narr:
        for ln in wrap(d, narr, F(48, 'SemiBold'), 1600): rows.append((ln, F(48, 'SemiBold'), (255, 255, 255)))
    else:
        if speaker and en: rows.append((speaker, F(30, 'Medium'), (176, 184, 193)))
        if en:
            for ln in wrap(d, en, F(58, 'Bold'), 1640): rows.append((ln, F(58, 'Bold'), (255, 255, 255)))
        if ko:
            for ln in wrap(d, ko, F(42, 'Medium'), 1640): rows.append((ln, F(42, 'Medium'), (200, 222, 255)))
    hgt = sum(int(f.size * 1.36) for _, f, _ in rows)
    if not narr and hgt > H - BAND_TOP - 24:
        for se, sk in ((52, 38), (48, 35), (44, 32)):
            rows = []
            if speaker and en: rows.append((speaker, F(28, 'Medium'), (176, 184, 193)))
            if en:
                for ln in wrap(d, en, F(se, 'Bold'), 1720): rows.append((ln, F(se, 'Bold'), (255, 255, 255)))
            if ko:
                for ln in wrap(d, ko, F(sk, 'Medium'), 1720): rows.append((ln, F(sk, 'Medium'), (200, 222, 255)))
            hgt = sum(int(f.size * 1.36) for _, f, _ in rows)
            if hgt <= H - BAND_TOP - 24: break
    y = BAND_TOP + (H - BAND_TOP - hgt) / 2 - 6
    for ln, f, c in rows:
        w_ = d.textlength(ln, font=f); d.text(((W - w_) / 2, y), ln, font=f, fill=c, stroke_width=2, stroke_fill=(0, 0, 0))
        y += int(f.size * 1.36)
    im.save(path)


# ---------- 내레이션 싱크 (말하는 구간에만 자막) ----------
def split_sents(t):
    parts = re.split(r'(?<=[.?!])\s+', t.strip()); out = []
    for p in parts:
        if len(p) > 38 and ', ' in p:
            a = p.split(', '); cur = ''
            for x in a:
                if len(cur) + len(x) > 34 and cur: out.append(cur.strip() + ','); cur = x
                else: cur = (cur + ', ' + x) if cur else x
            out.append(cur)
        else: out.append(p)
    out = [o for o in out if o]
    # 너무 짧은 조각(예: '이재용,')은 다음 문장과 합침
    merged = []
    for o in out:
        if merged and len(merged[-1]) < 9: merged[-1] = merged[-1] + ' ' + o
        else: merged.append(o)
    if len(merged) > 1 and len(merged[-1]) < 9: merged[-2] += ' ' + merged.pop()
    return merged


def speech_spans(mp3):
    out = subprocess.run(['ffmpeg', '-i', mp3, '-af', 'silencedetect=n=-38dB:d=0.18', '-f', 'null', '-'], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', out)]
    en = [float(x) for x in re.findall(r'silence_end: ([0-9.]+)', out)]
    D = dur(mp3); sil = list(zip(st, en + [D] * (len(st) - len(en))))
    spans = []; cur = 0.0
    for a, b in sil:
        if a - cur > 0.05: spans.append((cur, a))
        cur = b
    if D - cur > 0.05: spans.append((cur, D))
    return spans, D


def narr_cues(text, mp3, offset=0.0):
    """문장마다 실제로 말하는 구간(시작~끝)만 돌려줌"""
    sents = split_sents(text); spans, D = speech_spans(mp3)
    gaps = [(spans[i][1], spans[i + 1][0]) for i in range(len(spans) - 1)]
    tot = sum(len(s) for s in sents); speech_tot = sum(b - a for a, b in spans)
    # 글자 수 비율로 목표 시점을 잡고, 가장 가까운 쉼으로 경계를 맞춤
    def at(frac):  # 말하는 시간 기준 frac 위치의 실제 시각
        need = speech_tot * frac
        for a, b in spans:
            if need <= b - a: return a + need
            need -= b - a
        return D
    bounds = []; used = -1
    acc = 0
    for s in sents[:-1]:
        acc += len(s); T = at(acc / tot)
        best = None
        for gi, (ga, gb) in enumerate(gaps):
            if gi <= used: continue
            dist = abs((ga + gb) / 2 - T)
            if best is None or dist < best[0]: best = (dist, gi)
        if best is None or best[0] > 1.6: bounds.append((T, T)); continue
        used = best[1]; bounds.append(gaps[best[1]])
    cues = []; start = spans[0][0] if spans else 0
    for i, s in enumerate(sents):
        end = bounds[i][0] if i < len(bounds) else (spans[-1][1] if spans else D)
        cues.append((offset + max(0, start - 0.08), offset + end + 0.18, s))
        if i < len(bounds): start = bounds[i][1]
    # 자막끼리 절대 겹치지 않게: 시간 순서를 강제하고, 길이가 없는 자막은 앞 자막에 합침
    fixed = []
    for a, b, t in cues:
        if fixed:
            pa, pb, pt = fixed[-1]
            a = max(a, pb + 0.03)
            if b - a < 0.4:
                fixed[-1] = (pa, max(pb, b), pt + ' ' + t); continue
        fixed.append((a, b, t))
    return fixed


# ---------- 학습 화면 (토스 톤) ----------
def canvas(label=None, ic=None):
    im = Image.new('RGB', (W, H), WHITE); d = ImageDraw.Draw(im)
    if label:
        x = 84
        if ic: icon(im, ic, x, 56, 64); x += 82
        vcenter(d, x, 56, 64, label, F(34, 'Bold'), SUB)
    f = F(28, 'SemiBold'); d.text((W - 84 - d.textlength('CafeInEnglish', font=f), 72), 'CafeInEnglish', font=f, fill=(176, 184, 193))
    return im, d


def underline(d, x, y, text, font, fill=TXT):
    """웹처럼 핵심어 아래 라임 밑줄"""
    w_ = d.textlength(text, font=font)
    d.rectangle((x - 4, y + font.size * 0.80, x + w_ + 4, y + font.size * 1.10), fill=LIME)
    d.text((x, y), text, font=font, fill=fill); return w_


def sub_pill(d, text, cy=990):
    """자막: 가운데 정렬 진한 알약 (글자 폭에 맞춤, 그림자 없음)"""
    if not text: return
    f = F(40, 'SemiBold'); rows = wrap(d, text, f, 1500)
    if len(rows) > 1: f = F(36, 'SemiBold'); rows = wrap(d, text, f, 1560)
    lh = f.size * 1.32; h = len(rows) * lh + 36; w = max(d.textlength(r, font=f) for r in rows) + 92
    d.rounded_rectangle(((W - w) / 2, cy - h / 2, (W + w) / 2, cy + h / 2), min(40, h / 2), fill=(25, 31, 40))
    y = cy - len(rows) * lh / 2 + (lh - f.size) / 2 - 5
    for r_ in rows:
        w_ = d.textlength(r_, font=f); d.text(((W - w_) / 2, y), r_, font=f, fill=(255, 255, 255)); y += lh


def sub_strip(png_in, png_out, text):
    """학습 화면 자막 (말할 때만)"""
    im = Image.open(png_in).convert('RGB'); d = ImageDraw.Draw(im)
    sub_pill(d, text)
    im.save(png_out)

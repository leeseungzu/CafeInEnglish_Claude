"""정의선 롱폼 렌더"""
import os, sys, json, re, subprocess
from PIL import ImageFilter
D = '/tmp/claude-0/-home-claude/867aec65-8c7b-57fa-a377-537e93906e02/scratchpad/hy/'
exec(open(D + 'hy_head.py').read())
exec(open(D + 'opening.py').read())
import lf_style
lf_style.CREDIT_DEFAULT = 'Hyundai CES 2022 · 백악관 · 한국경제'

# ---------- 원본 단어 타이밍 (Scribe) ----------
_cs = open(D + 'cues.py').read().split('SPEC={')[0]; exec(_cs); from lf_style import W, H   # WS, FILL
CUES = json.load(open(D + 'cues.json'))
OFFS = {'ga': 0, 'ces': 100, 'wh': 260}          # 파일 시간 = 원본 - OFFS
CRED = {'ces': 'Hyundai CES 2022 프레스 컨퍼런스', 'wh': '백악관 2025.3.24 발표', 'ga': '한국경제 · HMGMA 준공식'}
GA_CROP = 'crop=1671:940:215:0,'                  # 번인 자막/이름표를 아래로 밀어내고 가림
SPK = '정의선 · 현대차그룹 회장'
TOSS = (49, 130, 246); DARK = (25, 31, 40)

def keep_pieces(src, ranges, thr=0.95, pre=0.32):
    """말 사이 0.95초 넘는 쉼(+어/음)만 줄임. 단어는 절대 자르지 않음"""
    out = []
    for a, b in ranges:
        allw = [w for w in WS[src] if w[0] >= a - 0.4 and w[1] <= b + 0.4]
        ws = [w for w in allw if w[2] not in FILL]
        fl = [w for w in allw if w[2] in FILL]
        # 시작 직전 '어' 제거
        lead = [f for f in fl if f[1] <= ws[0][0] + 0.01 and f[1] > a]
        if lead: a = max(a, lead[-1][1] + 0.02)
        cur = a
        for x, y in zip(ws, ws[1:]):
            g = y[0] - x[1]
            if g <= thr: continue
            inner = [f for f in fl if f[0] >= x[1] - 0.02 and f[1] <= y[0] + 0.02]
            c0 = x[1] + pre
            c1 = min(y[0] - 0.08, max(y[0] - 0.22, inner[-1][1] + 0.03)) if inner else y[0] - 0.22
            if c1 - c0 > 0.25:
                if inner and inner[0][0] < c0: c0 = max(x[1] + 0.12, inner[0][0] - 0.02)
                out.append((cur, c0)); cur = c1
        out.append((cur, b))
    return out

X = 0.08
def gain_for(path, ss, t):
    """loudnorm은 끝 3초에서 소리를 앞당겨 싱크가 틀어져서, 고정 게인으로 -16 LUFS 맞춤"""
    o = subprocess.run(['ffmpeg', '-v', 'info', '-ss', f'{ss:.3f}', '-t', f'{t:.3f}', '-i', path, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    I = float(re.findall(r'I:\s+(-?[0-9.]+) LUFS', o)[-1]); pk = float(re.findall(r'Peak:\s+(-?[0-9.inf]+) dBFS', o)[-1])
    return min(-16 - I, -1.5 - pk)
def tmap(pieces):
    S = []; acc = 0
    for i, (s, e) in enumerate(pieces): S.append(acc - i * X); acc += e - s
    def m(t):
        for i, (s, e) in enumerate(pieces):
            if t < s: return S[i]
            if t <= e: return S[i] + t - s
        return S[-1] + pieces[-1][1] - pieces[-1][0]
    return m, acc - (len(pieces) - 1) * X

def namecard(path):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f1 = F(44, 'Bold'); f2 = F(34, 'SemiBold')
    w1 = d.textlength('정의선', font=f1); w2 = d.textlength('현대자동차그룹 회장', font=f2)
    d.rounded_rectangle((56, 50, 56 + 40 + w1 + 22 + w2 + 40, 50 + 86), 22, fill=DARK + (238,))
    vcenter(d, 96, 50, 86, '정의선', f1, (255, 255, 255)); vcenter(d, 96 + w1 + 22, 50, 86, '현대자동차그룹 회장', f2, TOSS)
    im.save(path)

def ga_cover(path):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for y in range(770, H):
        a = 255 if y >= 842 else int(255 * ((y - 770) / 72) ** 1.4)
        d.line((0, y, W, y), fill=(8, 10, 13, a))
    im.save(path)

def clip(name, src, ranges, cues, label=None, subs=True, nc=False, cut=True):
    if skip(name): return
    pieces = keep_pieces(src, ranges) if cut else list(ranges)
    m, L = tmap(pieces); off = OFFS[src]; A = pieces[0][0]; B = pieces[-1][1]
    base = R + name + '_base.png'
    if subs: video_base(base, label=label, credit=CRED[src])
    else:
        video_base(base, label=label, credit=CRED[src]); im = Image.open(base); d = ImageDraw.Draw(im)
        f = F(38, 'SemiBold'); t = '자막 없이 먼저 들어 보세요'; w_ = d.textlength(t, font=f)
        icon(im, 'headphone', (W - w_) / 2 - 64, BAND_TOP + (H - BAND_TOP) / 2 - 30, 48)
        d.text(((W - w_) / 2 + 6, BAND_TOP + (H - BAND_TOP) / 2 - 26), t, font=f, fill=(214, 218, 224)); im.save(base)
    n = len(pieces)
    inp = ['-ss', f'{A - off:.3f}', '-t', f'{B - A + 0.3:.3f}', '-i', D + src + '.mp4']
    fl = f'[0:v]fps={FPS},{GA_CROP if src == "ga" else ""}scale={W}:{H},setsar=1,split={n}' + ''.join(f'[vs{i}]' for i in range(n)) + ';'
    fl += f'[0:a]aresample=48000,asplit={n}' + ''.join(f'[as{i}]' for i in range(n)) + ';'
    for i, (s, e) in enumerate(pieces):
        fl += f'[vs{i}]trim=start={s - A:.3f}:end={e - A:.3f},setpts=PTS-STARTPTS[p{i}];'
        fl += f'[as{i}]atrim=start={s - A:.3f}:end={e - A:.3f},asetpts=PTS-STARTPTS[q{i}];'
    lv, la, acc = 'p0', 'q0', pieces[0][1] - pieces[0][0]
    for i in range(1, n):
        fl += f'[{lv}][p{i}]xfade=transition=fade:duration={X}:offset={acc - X:.3f}[x{i}];[{la}][q{i}]acrossfade=d={X}:c1=tri:c2=tri[y{i}];'
        lv, la = f'x{i}', f'y{i}'; acc += pieces[i][1] - pieces[i][0] - X
    k = 1; last = lv
    if src == 'ga':
        cv = R + 'ga_cover.png'; ga_cover(cv); inp += ['-loop', '1', '-i', cv]
        fl += f'[{last}][{k}:v]overlay=0:0:shortest=1[c{k}];'; last = f'c{k}'; k += 1
    inp += ['-loop', '1', '-i', base]; fl += f'[{last}][{k}:v]overlay=0:0:shortest=1[c{k}]'; last = f'c{k}'; k += 1
    if subs:
        mc = [(m(t0), m(t1), en, ko) for t0, t1, en, ko in cues if A - 0.3 <= t0 <= B]
        for i, (t0, t1, en, ko) in enumerate(mc):
            p = R + f'{name}_c{i}.png'; video_text(p, en=en, ko=ko, speaker=SPK); inp += ['-loop', '1', '-i', p]
            t1e = min(L, t1 + 0.3) if i + 1 == len(mc) else min(t1 + 0.3, mc[i + 1][0] - 0.03)
            fl += f";[{last}][{k}:v]overlay=0:0:enable='between(t,{max(0, t0 - 0.05):.3f},{t1e:.3f})':shortest=1[c{k}]"; last = f'c{k}'; k += 1
    if nc:
        p = R + 'namecard.png'; namecard(p); inp += ['-loop', '1', '-i', p]
        fl += f';[{k}:v]format=rgba,fade=t=in:st=0.35:d=0.5:alpha=1[nc];[{last}][nc]overlay=0:0:shortest=1[c{k}]'; last = f'c{k}'; k += 1
    g = gain_for(D + src + '.mp4', A - off, B - A)
    fl += f';[{la}]afade=t=in:d=0.04,afade=t=out:st={L - 0.25:.3f}:d=0.25,volume={g:.2f}dB,aresample=48000[a]'
    run(['ffmpeg', '-v', 'error', '-y'] + inp + ['-filter_complex', fl, '-map', f'[{last}]', '-map', '[a]', '-t', f'{L:.3f}'] + enc() + [R + name + '.mp4'])
    json.dump({'pieces': pieces, 'L': L}, open(R + name + '.json', 'w'))

CL = [  # 이름, 키, 소스, 구간, 장면 라벨
    ('A', 'ces', [(187.4, 238.4)], '장면 1 · CES 2022'),
    ('B', 'ces', [(598.2, 611.0)], '장면 1 · CES 2022'),
    ('C', 'wh', [(305.8, 333.5)], '장면 2 · 백악관 2025.3'),
    ('D', 'ga', [(160.5, 183.4), (208.4, 229.75)], '장면 3 · 조지아 공장 준공식'),
    ('E', 'ga', [(434.8, 482.9)], '장면 3 · 조지아 공장 준공식'),
]

# ---------- STEP 2: A안 (사이트 카드형) ----------
PB = (96, 170, 1136, 755); PW, PH = PB[2] - PB[0], PB[3] - PB[1]
CX = 1196; CW = W - 96 - CX
LOGO_M = Image.open('/mnt/user-data/uploads/CafeInEnglish_Claude/CafeInEnglish_Claude/docs/assets/logo-mark.png').convert('RGBA').resize((44, 44))

def frames_of(src, start, L):
    crop = 'crop=1316:740:392:0,' if src == 'ga' else ''
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{start - OFFS[src]:.3f}', '-t', f'{L + 0.5:.3f}', '-i', D + src + '.mp4', '-vf', f'fps={FPS},{crop}scale={PW}:{PH}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    last = None
    while True:
        b = p.stdout.read(PW * PH * 3)
        if len(b) < PW * PH * 3: break
        last = Image.frombytes('RGB', (PW, PH), b); yield last
    while True: yield last

def hl_text(d, x, y, text, f, key):
    """제목 그리기 + key 부분에 라임 형광펜"""
    if key and key in text:
        i = text.index(key); pre = text[:i]
        x1 = x + d.textlength(pre, font=f); w = d.textlength(key, font=f)
        d.rectangle((x1 - 4, y + f.size * 0.62, x1 + w + 4, y + f.size * 1.08), fill=LIME)
    d.text((x, y), text, font=f, fill=TXT)

def scene(name, key, src, start, tag, title, meta, quote_ko=None, bullets=None, hl=None):
    if skip(name): return
    mp3 = NA + key + '.mp3'; lead = 0.3; L = dur(mp3) + lead + 0.7
    T = TIMING[key]; cues = [(a + lead, b + lead, t, lg) for a, b, t, lg in T]
    en = [c for c in cues if c[3] == 'en']
    wav = R + name + '.wav'; audio_track([(lead, mp3)], L, wav)
    base = Image.new('RGBA', (W, H), (255, 255, 255, 255)); d = ImageDraw.Draw(base)
    d.rounded_rectangle((48, 40, W - 48, 850), 44, fill=CARD)
    base.alpha_composite(LOGO_M, (96, 82)); d = ImageDraw.Draw(base)
    d.text((152, 86), '카페인영어', font=F(28, 'Bold'), fill=TXT); d.text((300, 90), 'CafeInEnglish', font=F(26, 'SemiBold'), fill=GRAY)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((PB[0], PB[1] + 12, PB[2], PB[3] + 12), 28, fill=(17, 24, 39, 40))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(30))); d = ImageDraw.Draw(base)
    # 오른쪽 글
    ft = F(64 if len(title) < 14 else 56, 'Black'); trows = sum([wrap(d, x, ft, CW) for x in title.split('\n')], [])
    q = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dq = ImageDraw.Draw(q)
    qh = 0
    if en:
        fe = F(40, 'ExtraBold'); fk = F(28, 'SemiBold')
        er = wrap(dq, en[0][2], fe, CW - 72); kr = wrap(dq, quote_ko, fk, CW - 72)
        qh = len(er) * 54 + 14 + len(kr) * 40 + 72
    bh = len(bullets) * 96 - 16 if bullets else 0
    lh = int(ft.size * 1.25)
    blk = 48 + 30 + len(trows) * lh + 8 + 34 + ((36 + qh) if qh else 0) + ((36 + bh) if bh else 0)
    top = int((PB[1] + PB[3]) / 2 - blk / 2)
    fg = F(26, 'Bold'); w_ = d.textlength(tag, font=fg)
    d.rounded_rectangle((CX, top, CX + w_ + 40, top + 48), 24, fill=ESP); vcenter(d, CX + 20, top, 48, tag, fg, WHITE)
    y = top + 78
    for r_ in trows: hl_text(d, CX, y, r_, ft, hl); y += lh
    d.text((CX + 2, y + 8), meta, font=F(28, 'SemiBold'), fill=GRAY); y += 8 + 34 + 36
    if en:
        dq.rounded_rectangle((CX, y, W - 96, y + qh), 28, fill=(255, 255, 255, 255))
        yy = y + 36
        for r_ in er: dq.text((CX + 36, yy), r_, font=fe, fill=TXT); yy += 54
        yy += 14
        for r_ in kr: dq.text((CX + 36, yy), r_, font=fk, fill=BLUE); yy += 40
    blay = []
    if bullets:
        for i, (st, txt) in enumerate(bullets):
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
            yy = y + i * 96
            dl.rounded_rectangle((CX, yy, W - 96, yy + 80), 24, fill=(255, 255, 255, 255))
            chip(dl, CX + 44, yy + 40, str(i + 1), r=22, fill=BLUE, size=24)
            vcenter(dl, CX + 84, yy, 80, txt, F(32, 'Bold'), TXT)
            blay.append((st + lead, lay))
    fr_it = frames_of(src, start, L)
    m = Image.new('L', (PW, PH), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, PW, PH), 28, fill=255)
    cr = '영상 출처: ' + CRED[src]; fc = F(20, 'Medium')
    base = base.convert('RGB')
    pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', wav, '-t', f'{L:.3f}'] + enc() + [R + name + '.mp4'], stdin=subprocess.PIPE)
    for n in range(int(L * FPS) + 1):
        t = n / FPS
        fr = base.copy(); fr.paste(next(fr_it), (PB[0], PB[1]), m)
        dd = ImageDraw.Draw(fr, 'RGBA'); wc = dd.textlength(cr, font=fc)
        dd.rounded_rectangle((PB[2] - wc - 46, PB[3] - 50, PB[2] - 16, PB[3] - 16), 12, fill=(0, 0, 0, 130)); dd.text((PB[2] - wc - 32, PB[3] - 45), cr, font=fc, fill=(255, 255, 255))
        fr = fr.convert('RGBA')
        if en and t >= en[0][0] - 0.2:
            a = min(1, (t - en[0][0] + 0.2) / 0.3)
            qq = q if a >= 1 else q.copy()
            if a < 1: qq.putalpha(q.getchannel('A').point(lambda v: int(v * a)))
            fr = Image.alpha_composite(fr, qq)
        for st, lay in blay:
            if t >= st - 0.1:
                a = min(1, (t - st + 0.1) / 0.25); ll = lay if a >= 1 else lay.copy()
                if a < 1: ll.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
                fr = Image.alpha_composite(fr, ll)
        tx = next((c[2] for c in cues if c[0] - 0.05 <= t <= c[1] + 0.15 and c[3] == 'ko'), '')
        sub_pill(ImageDraw.Draw(fr), tx, 950)
        pr.stdin.write(fr.convert('RGB').tobytes())
    pr.stdin.close(); pr.wait()

# =================== 조립 ===================
# 0. 훅 (이름표 한 번)
clip('00_hook', 'ces', [(605.9, 611.0)], CUES['B'][1][1:], nc=True)
# 1. 오프닝
seg_broll('01_open', [('ces', 40.0, 47.0), ('ces', 88.0, 95.0), ('wh', 42.0, 49.0)], 'O1')
# STEP 1
step('s1', 1, '자막 없이 듣기', '세 장면, 먼저 귀로만 들어 보세요', 'headphone')
for nm, src, rg, lab in CL: clip(f'1{nm}_raw', src, rg, [], label=lab, subs=False)
# STEP 2
step('s2', 2, '장면 해설', '그의 영어가 마음을 움직인 이유', 'light-bulb')
scene('21_D1', 'D1', 'ces', 207.0, '장면 1 · CES 2022', '로봇은 꿈이 아니라, 지금', '2022.1 라스베이거스 · 현대차 프레스 컨퍼런스', '로봇은 더 이상 꿈속 이야기가 아니에요. 로봇은 바로 지금이에요.', hl='지금')
scene('22_D2', 'D2', 'ces', 598.2, '장면 1 · CES 2022', '한계를 두지 않고,\n한계에 도전한다', '단어 순서만 바꾼 한 문장', '도전에 한계를 두지 않아요. 한계에 도전하죠.', hl='한계에 도전')
scene('23_D3', 'D3', 'wh', 305.8, '장면 2 · 백악관', '지금까지, 그리고 앞으로', '2025.3.24 워싱턴 · 210억 달러 투자 발표', hl='그리고 앞으로')
scene('24_D4', 'D4', 'ga', 160.5, '장면 3 · 조지아', '공장 대신, 뿌리', '2025.3.26 HMGMA 준공식', '공장만 지으러 오지 않아요. 뿌리를 내리러 와요.', hl='뿌리')
scene('25_D5', 'D5', 'ga', 434.8, '장면 3 · 조지아', '주인공은 여러분', '연설의 마지막 한 문장', '여러분이 바로 현대예요.', hl='여러분')
scene('26_T1', 'T1', 'ces', 222.0, '정리', '세 장면이 알려 준 것', '말하기에 바로 옮길 3가지', bullets=[(T[0], t) for T, t in zip(TIMING['T1'][1:], ['숫자보다 사람 이야기 먼저', '짧은 문장, 뒤집어 남기기', '듣는 사람을 주인공으로'])])
scene('27_T2', 'T2', 'ga', 468.5, '하나 더', '완벽한 영어보다,\n전하고 싶은 한 문장', '멈추고 고르며 말해도 마음은 전해져요', hl='한 문장')

# 오늘의 표현
EXPR = [
    ('E1', 'first and foremost', '무엇보다도, 가장 먼저', 'We invest first and foremost in relationships.', ('First and foremost, thank you all for coming.', '무엇보다 먼저, 와 주셔서 모두 감사해요.')),
    ('E2', 'put down roots', '뿌리를 내리다, 자리 잡다', 'We come to put down roots.', ('We want to put down roots in this town.', '우리는 이 동네에 자리 잡고 싶어요.')),
    ('E3', 'the stuff of dreams', '꿈같은 이야기, 꿈에서나 볼 법한 것', 'Robotics is no longer the stuff of dreams.', ('A house by the sea is the stuff of dreams.', '바닷가 집은 꿈같은 이야기예요.')),
    ('E4', 'challenge our limits', '우리의 한계에 도전하다', 'We challenge our limits.', ('This marathon will challenge my limits.', '이 마라톤은 제 한계에 도전하는 일이에요.')),
    ('E5', 'greater than the sum of its parts', '부분의 합보다 크다', 'like every vehicle, greater than the sum of its parts', ('Our team is greater than the sum of its parts.', '우리 팀은 한 사람 한 사람을 합친 것보다 강해요.')),
]
for n, (key, ex, mean, orig, (exen, exko)) in enumerate(EXPR, 1):
    nm = f'3{n}_{key}'
    def fn(im, d, ex=ex, mean=mean, orig=orig, exen=exen, exko=exko):
        f = F(100 if len(ex) < 22 else 76, 'Black'); w_ = d.textlength(ex, font=f); underline(d, W / 2 - w_ / 2, 200, ex, f)
        ctext(d, 370, mean, F(54, 'Bold'), BLUE)
        fo = F(32, 'SemiBold'); t = f'정의선 회장의 문장  ·  "{orig}"'; ctext(d, 462, t, fo, GRAY, maxw=1500)
        card(d, (240, 570, W - 240, 800)); icon(im, 'light-bulb', 290, 640, 80)
        dd = ImageDraw.Draw(im); fe = F(46 if len(exen) < 44 else 40, 'Bold')
        dd.text((400, 622), exen, font=fe, fill=TXT); dd.text((400, 702), exko, font=F(36, 'Medium'), fill=SUB)
    p = slide(nm, f'오늘의 표현 {n} / 5', 'headphone', fn); slide_narr(nm, p, key)

# STEP 3
step('s3', 3, '한영 자막으로 다시 듣기', '처음보다 얼마나 들리는지 확인해 보세요', 'headphone')
for nm, src, rg, lab in CL: clip(f'4{nm}_sub', src, rg, CUES[nm][1], label=lab, subs=True)
# STEP 4
step('s4', 4, '입으로 마무리', '핵심 문장 따라 말하고 퀴즈 하나', 'speech-balloon')
drill('51_d1', 'We come to put down roots.', '우리는 뿌리를 내리러 와요.', 1, 2, '따라 말하기', 'ear')
drill('52_d2', "We don't limit our challenges.\nWe challenge our limits.", '도전에 한계를 두지 않고, 한계에 도전해요.', 2, 2, '따라 말하기', 'ear')

nm = '55_quiz'
if not skip(nm):
    qt, sub, opts, ans = '"We come to put down roots."', '여기서 put down roots의 뜻은?', ['뿌리를 내리다', '나무를 심다', '짐을 내려놓다', '기반을 무너뜨리다'], 0
    def draw(reveal, count=None):
        im, d = canvas('퀴즈', 'question-mark')
        y = ctext(d, 180, qt, F(64, 'ExtraBold'), TXT, maxw=1500); ctext(d, y + 6, sub, F(38, 'Medium'), GRAY)
        for i, o in enumerate(opts):
            yy = 410 + i * 128; ok = reveal and i == ans
            card(d, (380, yy, W - 380, yy + 108), fill=GREEN if ok else CARD, r=26)
            chip(d, 440, yy + 54, 'ABCD'[i], r=28, fill=WHITE if ok else ESP, fg=GREEN if ok else WHITE, size=28)
            vcenter(d, 496, yy, 108, o, F(44, 'Bold'), WHITE if ok else TXT)
            if ok: icon(im, 'check', W - 380 - 96, yy + 22, 64)
        if count:
            d.ellipse((1640, 180, 1800, 340), fill=BLUE); vcenter(d, 1720, 180, 160, str(count), F(100, 'Black'), WHITE, 'm')
        return im
    pq = R + f'{nm}_q.png'; draw(False).save(pq); pcs = []
    for c in (3, 2, 1):
        pc = R + f'{nm}_c{c}.png'; draw(False, c).save(pc); pcs.append(pc)
    pa = R + f'{nm}_a.png'; draw(True).save(pa)
    qm, am = NA + 'JQ1.mp3', NA + 'JA1.mp3'; qd, ad = dur(qm), dur(am); t0 = 0.3 + qd + 0.3
    fr = []
    for (st, png, key, mp, lead) in ((0, pq, 'JQ1', qm, 0.3), (t0 + 3, pa, 'JA1', am, t0 + 3.4)):
        b = png[:-4] + '_s_.png'; sub_strip(png, b, ''); fr.append((st, b))
        for j, (c0, c1, tx) in enumerate(narr_cues(NTEXT[key], mp, lead)):
            sp = png[:-4] + f'_s{j}.png'; sub_strip(png, sp, tx); fr += [(c0, sp), (c1, b)]
    for k, c in enumerate(pcs):
        b = c[:-4] + '_s_.png'; sub_strip(c, b, ''); fr.append((t0 + k, b))
    fr = sorted(fr, key=lambda x: x[0])
    seg_slide(nm, fr, [(0.3, qm), (t0, TICK), (t0 + 1, TICK), (t0 + 2, TICK), (t0 + 3, DING), (t0 + 3.4, am)], t0 + 3.4 + ad + 1.0)

def s_out(im, d):
    lg = Image.open(LOGO).convert('RGBA').resize((110, 110)); im.paste(lg, (170, 170), lg)
    d.text((300, 182), '카페인영어', font=F(64, 'Black'), fill=TXT); d.text((302, 258), 'CafeInEnglish', font=F(30, 'SemiBold'), fill=GRAY)
    d.text((170, 360), '완벽한 영어보다,', font=F(70, 'ExtraBold'), fill=TXT)
    d.text((170, 450), '전하고 싶은 한 문장', font=F(70, 'ExtraBold'), fill=BLUE)
    rows = [('headphone', '원어민 발음과 장면 다시 듣기'), ('question-mark', '퀴즈 · 오답노트로 복습'), ('check', '가입 없이 전부 무료')]
    y = 600
    for ic, t in rows:
        icon(im, ic, 170, y, 60); vcenter(d, 252, y, 60, t, F(40, 'SemiBold'), SUB); y += 86
    f = F(40, 'Bold'); t = 'cafeinenglish.com  ·  설명란 링크'; w_ = d.textlength(t, font=f)
    d.rounded_rectangle((170, 880, 170 + w_ + 96, 960), 40, fill=BLUE); vcenter(d, 218, 880, 80, t, f, WHITE)
    ph = (1180, 90, 1180 + 520, 90 + 960)
    d.rounded_rectangle((ph[0] - 14, ph[1] - 14, ph[2] + 14, ph[3] + 14), 74, fill=TXT)
    shot = Image.open(D + 'site_notes.png').convert('RGB')
    sw = ph[2] - ph[0]; sh = ph[3] - ph[1]
    sc = sw / shot.width; shot = shot.resize((sw, int(shot.height * sc)), Image.LANCZOS); shot = shot.crop((0, 0, sw, sh))
    m = Image.new('L', (sw, sh), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, sw, sh), 62, fill=255)
    im.paste(shot, (ph[0], ph[1]), m)
    d.rounded_rectangle((ph[0] + sw / 2 - 70, ph[1] + 16, ph[0] + sw / 2 + 70, ph[1] + 50), 17, fill=TXT)
if not skip('60_out'):
    im = Image.new('RGB', (W, H), WHITE); d = ImageDraw.Draw(im); s_out(im, d); p = R + '60_out.png'; im.save(p)
    seg_slide('60_out', [(0, p)], [(0.4, NA + 'N13.mp3')], dur(NA + 'N13.mp3') + 2.2)

seen = []; [seen.append(s) for s in SEGS if s not in seen]
open(D + 'list.txt', 'w').write(''.join(f"file '{s}'\n" for s in seen))
print('done', len(seen))

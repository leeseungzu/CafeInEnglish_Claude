import os, sys, json, hashlib, subprocess
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lf_style import *

D = '/tmp/claude-0/-home-claude/867aec65-8c7b-57fa-a377-537e93906e02/scratchpad/lf/'
R = D + 'r2/'; NA = D + 'na/'; KO = '/mnt/user-data/outputs/kayoung/lc/audio/'
os.makedirs(R, exist_ok=True)
ONLY = set(sys.argv[1:])  # 샘플만 만들 때 세그먼트 이름
NTEXT = json.load(open(D + 'narr.json'))
SEGS = []


def run(cmd): subprocess.run(cmd, check=True)
def enc(): return ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2']
def skip(name):
    out = R + name + '.mp4'
    if out not in SEGS: SEGS.append(out)
    return (ONLY and name not in ONLY) or os.path.exists(out)
def kokoro(t):
    k = hashlib.md5(f"af_heart|{t.replace('~','...')}".encode()).hexdigest()[:12]
    p = KO + k + '.mp3'; assert os.path.exists(p), t; return p


def seg_clip(name, src, a, b, cues, speaker):
    if skip(name): return
    base = R + name + '_base.png'; video_base(base)
    inp = ['-ss', str(a), '-t', str(b - a), '-i', D + src + '.mp4', '-loop', '1', '-i', base]
    fl = f'[0:v]fps={FPS},scale={W}:{H},setsar=1[v0];[v0][1:v]overlay=0:0:shortest=1[v1]'; last = 'v1'
    for i, (t0, t1, en, ko) in enumerate(cues):
        p = R + f'{name}_c{i}.png'; video_text(p, en=en, ko=ko, speaker=speaker); inp += ['-loop', '1', '-i', p]
        fl += f";[{last}][{i+2}:v]overlay=0:0:enable='between(t,{t0-a:.2f},{t1-a+0.25:.2f})':shortest=1[v{i+2}]"; last = f'v{i+2}'
    L = b - a
    fl += f';[0:a]afade=t=in:d=0.15,afade=t=out:st={L-0.3:.2f}:d=0.3,loudnorm=I=-16:TP=-1.5,aresample=48000[a]'
    run(['ffmpeg', '-v', 'error', '-y'] + inp + ['-filter_complex', fl, '-map', f'[{last}]', '-map', '[a]', '-t', f'{L:.2f}'] + enc() + [R + name + '.mp4'])


def seg_broll(name, parts, key, label=None, pad=0.6):
    if skip(name): return
    mp3 = NA + key + '.mp3'; L = dur(mp3) + pad
    base = R + name + '_base.png'; video_base(base, label=label)
    inp = []; fl = ''; each = L / len(parts)
    for i, (src, a, b) in enumerate(parts):
        inp += ['-ss', str(a), '-t', f'{each+0.1:.2f}', '-i', D + src + '.mp4']
        fl += f'[{i}:v]fps={FPS},scale={W}:{H},setsar=1,trim=duration={each:.2f},setpts=PTS-STARTPTS,eq=brightness=-0.05:saturation=0.92[p{i}];'
    n = len(parts); fl += ''.join(f'[p{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=0[vc];'
    inp += ['-loop', '1', '-i', base]; fl += f'[vc][{n}:v]overlay=0:0:shortest=1[w0]'; last = 'w0'; idx = n + 1
    for j, (t0, t1, tx) in enumerate(narr_cues(NTEXT[key], mp3, 0.25)):
        p = R + f'{name}_n{j}.png'; video_text(p, narr=tx); inp += ['-loop', '1', '-i', p]
        fl += f";[{last}][{idx}:v]overlay=0:0:enable='between(t,{t0:.2f},{t1:.2f})':shortest=1[w{idx}]"; last = f'w{idx}'; idx += 1
    inp += ['-i', mp3]
    fl += f';[{idx}:a]adelay=250|250,apad,atrim=0:{L:.2f},loudnorm=I=-16:TP=-1.5,aresample=48000[a]'
    run(['ffmpeg', '-v', 'error', '-y'] + inp + ['-filter_complex', fl, '-map', f'[{last}]', '-map', '[a]', '-t', f'{L:.2f}'] + enc() + [R + name + '.mp4'])


SR = 48000; tt = np.arange(int(.5 * SR)) / SR
DING = (np.sin(2*np.pi*880*tt)*np.exp(-tt*6)*.30 + np.sin(2*np.pi*1320*tt)*np.exp(-tt*8)*.2).astype(np.float32)
t2 = np.arange(int(.08 * SR)) / SR
TICK = (np.sin(2*np.pi*1500*t2)*np.exp(-t2*60)*.35).astype(np.float32)


def audio_track(items, L, path):
    mix = np.zeros(int(L * SR) + SR, dtype=np.float32)
    for st, src in items:
        a = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-af', 'loudnorm=I=-16:TP=-1.5', '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout, dtype=np.float32) if isinstance(src, str) else src
        i = int(st * SR); mix[i:i + len(a)] += a[:max(0, len(mix) - i)]
    mix = mix[:int(L * SR)]; pk = np.abs(mix).max()
    if pk > .98: mix = mix / pk * .98
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-ac', '2', path], input=mix.tobytes(), check=True)


def seg_slide(name, frames, items, L):
    if skip(name): return
    wav = R + name + '.wav'; audio_track(items, L, wav)
    lst = R + name + '_frames.txt'
    with open(lst, 'w') as f:
        for i, (t0, png) in enumerate(frames):
            t1 = frames[i + 1][0] if i + 1 < len(frames) else L
            f.write(f"file '{png}'\nduration {max(0.04, t1 - t0):.3f}\n")
        f.write(f"file '{frames[-1][1]}'\n")
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', wav, '-vf', f'fps={FPS},format=yuv420p', '-t', f'{L:.2f}'] + enc() + [R + name + '.mp4'])


def slide(name, label, ic, draw):
    im, d = canvas(label, ic); draw(im, d); p = R + name + '.png'; im.save(p); return p


def slide_narr(name, png, key, lead=0.3):
    """학습 화면 + 내레이션. 아래 자막 띠는 계속 있고 글자는 말할 때만"""
    mp3 = NA + key + '.mp3'; L = dur(mp3) + lead + 0.6
    blank = R + f'{name}_s_.png'; sub_strip(png, blank, '')
    frames = [(0, blank)]
    for j, (t0, t1, tx) in enumerate(narr_cues(NTEXT[key], mp3, lead)):
        p = R + f'{name}_s{j}.png'; sub_strip(png, p, tx)
        frames.append((t0, p)); frames.append((t1, blank))
    frames = sorted(frames, key=lambda x: x[0])
    seg_slide(name, frames, [(lead, mp3)], L)


def slide_plain(name, png, items, L):
    blank = R + f'{name}_s_.png'; sub_strip(png, blank, ''); seg_slide(name, [(0, blank)], items, L)


def card(d, box, fill=CARD, outline=None, width=3, r=32):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width if outline else 0)


def chip(d, cx, cy, text, r=34, fill=ESP, fg=WHITE, size=34):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill); vcenter(d, cx, cy - r, 2 * r, text, F(size, 'Bold'), fg, 'm')


# ---------- 따라 말하기 ----------
def drill(name, en, ko, idx, total, label, ic='ear'):
    if skip(name): return
    def fn(im, d):
        ctext(d, 250, f'따라 말해 보세요  {idx} / {total}', F(32, 'SemiBold'), GRAY)
        card(d, (200, 330, W - 200, 760), fill=CARD)
        y = 400; f = F(74, 'ExtraBold'); rows = wrap(d, en, f, 1380)
        y = 545 - (len(rows) * f.size * 1.3 + 70) / 2
        for ln in rows:
            w_ = d.textlength(ln, font=f); d.text(((W - w_) / 2, y), ln, font=f, fill=TXT); y += f.size * 1.3
        ctext(d, y + 18, ko, F(42, 'Medium'), SUB)
    p1 = slide(name + '_a', label, ic, fn)
    im = Image.open(p1); d = ImageDraw.Draw(im); f = F(36, 'Bold')
    t = '이제 소리 내서 말해 보세요'; w_ = d.textlength(t, font=f); x0 = W / 2 - w_ / 2 - 46
    d.rounded_rectangle((x0, 800, W / 2 + w_ / 2 + 46, 880), 40, fill=BLUE); vcenter(d, W / 2, 800, 80, t, f, WHITE, 'm')
    p2 = R + name + '_b.png'; im.save(p2)
    au = kokoro(en); a = dur(au); t1 = 0.4; t2_ = t1 + a + 0.7; t3 = t2_ + a + 0.3; L = t3 + max(2.6, a + 1.0)
    b1 = R + name + '_a_s.png'; sub_strip(p1, b1, ''); b2 = R + name + '_b_s.png'; sub_strip(p2, b2, '')
    seg_slide(name, [(0, b1), (t3, b2)], [(t1, au), (t2_, au)], L)


# ============ 구성 ============
LEE, CHEY = '이재용 삼성전자 회장', '최태원 SK그룹 회장'
seg_broll('01_open', [('lee', 155, 162), ('chey', 120, 127), ('lee', 176, 183)], 'N01')
seg_broll('02_ctx', [('lee', 5.5, 29)], 'N02', label='2026.9.28 뉴욕 · 코리아소사이어티 연례 만찬')
seg_broll('04_n3', [('lee', 60, 70)], 'N03')
seg_clip('05_L2', 'lee', 94.4, 106.6, [(94.6, 97.7, '...because we have three things in common.', '우리에겐 공통점이 세 가지 있거든요.'), (99.6, 104.9, 'First, both of our companies are all in on AI.', '첫째, 두 회사 모두 AI에 올인했죠.')], LEE)
seg_clip('06_L3', 'lee', 113.0, 119.2, [(113.6, 118.7, 'Second, we both have a daughter named Madison.', '둘째, 둘 다 매디슨이라는 딸이 있어요.')], LEE)
seg_clip('07_L4', 'lee', 171.8, 190.3, [(172.4, 182.3, 'And third, we both love this innovation... Galaxy Z Fold.', '그리고 셋째, 둘 다 이 혁신을 사랑하죠. 갤럭시 Z 폴드.')], LEE)

def s_rule(im, d):
    ctext(d, 170, '공통점 세 가지 = Rule of Three', F(66, 'ExtraBold'), TXT)
    rows = [('Both of our companies are all in on AI.', 'AI에 올인', SUB), ('We both have a daughter named Madison.', '딸 이름이 매디슨', SUB), ('We both love this innovation, Galaxy Z Fold.', '반전! 자기 회사 폰 자랑', RED)]
    y = 320
    for i, (en, ko, c) in enumerate(rows):
        last = i == 2
        card(d, (230, y, W - 230, y + 160), fill=WHITE if last else CARD, outline=BLUE if last else None, width=4)
        chip(d, 310, y + 80, str(i + 1), fill=BLUE if last else ESP)
        d.text((380, y + 30), en, font=F(46, 'Bold'), fill=TXT); d.text((380, y + 92), ko, font=F(34, 'SemiBold'), fill=c)
        y += 190
if not skip('08_rule'): slide_narr('08_rule', slide('08_rule', '이재용 회장 축사', 'speech-balloon', s_rule), 'N04')
seg_broll('09_n5', [('lee', 192, 210)], 'N05')
seg_clip('10_L5', 'lee', 228.5, 238.0, [(229.0, 232.4, "I'm sorry to break it to you.", '이런 말 해서 미안하지만,'), (233.4, 236.0, "You're going to live forever.", '당신은 영원히 살 거예요.')], LEE)

def s_break(im, d):
    card(d, (300, 190, W - 300, 450))
    f = F(76, 'ExtraBold'); t1 = "I'm sorry to "; t2 = 'break it to you.'
    w1 = d.textlength(t1, font=f); w2 = d.textlength(t2, font=f); x = W / 2 - (w1 + w2) / 2
    d.text((x, 250), t1, font=f, fill=TXT); underline(d, x + w1, 250, t2, f)
    ctext(d, 365, '이런 말 해서 미안하지만… (안 좋은 소식을 전할 때)', F(38, 'Medium'), SUB)
    d.rounded_rectangle((W / 2 - 70, 478, W / 2 + 70, 538), 30, fill=RED); vcenter(d, W / 2, 478, 60, '반전!', F(32, 'Bold'), WHITE, 'm')
    card(d, (300, 566, W - 300, 826), fill=WHITE, outline=BLUE, width=4)
    ctext(d, 626, "You're going to live forever.", F(76, 'ExtraBold'), TXT)
    ctext(d, 741, '당신은 영원히 살 거예요 (덕담)', F(38, 'Medium'), SUB)
if not skip('11_break'): slide_narr('11_break', slide('11_break', '반전 화법', 'grimacing-face', s_break), 'N06')
seg_broll('12_n7', [('chey', 18, 30)], 'N07')
seg_clip('13_C1', 'chey', 38.2, 42.6, [(39.4, 41.4, 'Can you make it faster?', '(젠슨이 만날 때마다 묻는 말) 더 빨리 되나요?')], CHEY)

def s_fast(im, d):
    for i, (en, ko) in enumerate([('Can you make it faster?', '빨리빨리!'), ('ahead of schedule', '예정보다 빨리')]):
        y = 230 + i * 330; card(d, (320, y, W - 320, y + 270))
        ctext(d, y + 55, en, F(74, 'ExtraBold'), TXT); ctext(d, y + 165, ko, F(44, 'Bold'), BLUE)
if not skip('15_fast'): slide_narr('15_fast', slide('15_fast', '최태원 회장 건배사', 'rocket', s_fast), 'N08')
seg_clip('16_C3', 'chey', 59.8, 85.2, [(60.0, 64.3, 'For Nvidia and SK, the partnership is simple.', '엔비디아와 SK의 협력은 간단해요.'), (65.3, 74.0, 'Nvidia designs the brain, and SK builds the memory.', '엔비디아는 두뇌를 설계하고, SK는 기억을 만들죠.'), (75.6, 84.8, 'Nvidia thinks lightning fast, and SK makes sure it never forgets.', '엔비디아는 번개처럼 생각하고, SK는 그걸 절대 잊지 않게 해요.')], CHEY)
seg_clip('17_C4', 'chey', 85.2, 98.4, [(86.8, 96.6, 'And whenever Jensen forgets something, he knows exactly who to call.', '그리고 젠슨은 뭔가 잊어버리면, 누구에게 전화할지 정확히 알죠.')], CHEY)

def s_brain(im, d):
    for i, (who, what, ko) in enumerate([('NVIDIA', 'designs the brain', '두뇌를 설계'), ('SK', 'builds the memory', '기억을 만든다')]):
        x = 250 + i * 740; card(d, (x, 230, x + 680, 700), fill=ESP if i == 0 else CARD)
        c = WHITE if i == 0 else TXT
        ctext(d, 300, who, F(92, 'Black'), c, cx=x + 340); ctext(d, 450, what, F(52, 'Bold'), c, cx=x + 340)
        ctext(d, 560, ko, F(42, 'SemiBold'), LIME if i == 0 else BLUE, cx=x + 340)
    ctext(d, 760, '비유 하나로 두 회사 관계를 정리', F(40, 'SemiBold'), GRAY)
if not skip('18_brain'): slide_narr('18_brain', slide('18_brain', '비유의 힘', 'light-bulb', s_brain), 'N09')
seg_clip('19_C5', 'chey', 199.8, 211.0, [(201.0, 207.0, 'May our partnership scale even faster than GPU demand.', '우리 협력이 GPU 수요보다 더 빠르게 커지길.')], CHEY)

def s_may(im, d):
    f = F(86, 'ExtraBold'); t = 'May + 주어 + 동사원형'; d.text((W / 2 - d.textlength(t, font=f) / 2, 210), t, font=f, fill=TXT)
    ctext(d, 345, '~하기를 바랍니다  ·  건배사·축하 카드 마지막 줄', F(42, 'SemiBold'), BLUE)
    card(d, (260, 480, W - 260, 770))
    ctext(d, 540, 'May our partnership scale even faster than GPU demand.', F(56, 'Bold'), TXT, maxw=1300)
    ctext(d, 694, '우리 협력이 GPU 수요보다 더 빠르게 커지길.', F(38, 'Medium'), SUB)
if not skip('20_may'):
    p = slide('20_may', '건배사 마지막 줄', 'clinking-glasses', s_may); au = kokoro('May our partnership scale even faster than GPU demand.')
    slide_plain('20_may', p, [(0.5, DING), (1.2, au), (1.2 + dur(au) + 0.8, au)], 1.2 + 2 * dur(au) + 2.2)

def s_sec(im, d):
    icon(im, 'party-popper', W / 2 - 110, 190, 220)
    ctext(d, 450, '오늘 건진 영어 표현', F(62, 'Bold'), TXT); ctext(d, 545, '4개', F(150, 'Black'), BLUE)
    ctext(d, 760, '예문이 나오면 소리 내서 따라 해 보세요', F(40, 'Medium'), GRAY)
if not skip('21_sec'): slide_plain('21_sec', slide('21_sec', None, None, s_sec), [(0.3, DING)], 4.0)

EXPR = [
    ('E1', 'all in on ~', '~에 올인하다, 전부 걸다', '포커에서 칩을 전부 거는 all in에서 왔어요. 대상 앞엔 on!', [("We're all in on this project.", '우리 이 프로젝트에 올인했어.'), ("She's all in on her new business.", '그녀는 새 사업에 모든 걸 걸었어.')]),
    ('E2', 'break it to you', '(안 좋은 소식을) 조심스럽게 전하다', 'I hate to break it to you, but ~ = 이런 말 하기 그렇지만', [("I hate to break it to you, but the store is closed.", '이런 말 하기 그렇지만, 가게 문 닫았어.'), ('How do I break it to her?', '그녀한테 이걸 어떻게 말하지?')]),
    ('E3', 'ahead of schedule', '예정보다 빨리', 'on schedule 예정대로 · behind schedule 예정보다 늦게', [('We finished the project ahead of schedule.', '우리는 프로젝트를 예정보다 빨리 끝냈어요.'), ('The construction is behind schedule.', '공사가 예정보다 늦어지고 있어요.')]),
    ('E4', 'raise your glass to ~', '~를 위해 잔을 들어 주세요 (건배)', '회식 건배사는 이 한 문장이면 충분해요', [('Please raise your glass to our team!', '우리 팀을 위해 잔을 들어 주세요!'), ("Let's raise a glass to the happy couple.", '행복한 두 사람을 위해 건배해요.')]),
]
for n, (key, ex, mean, note, exs) in enumerate(EXPR, 1):
    nm = f'2{n}_{key}'
    def fn(im, d, ex=ex, mean=mean, note=note):
        f = F(124, 'Black'); w_ = d.textlength(ex, font=f); underline(d, W / 2 - w_ / 2, 230, ex, f)
        ctext(d, 440, mean, F(56, 'Bold'), BLUE)
        card(d, (300, 590, W - 300, 760)); icon(im, 'light-bulb', 350, 635, 80)
        dd = ImageDraw.Draw(im); vcenter(dd, 460, 590, 170, note, F(40, 'SemiBold'), SUB)
    if not skip(nm):
        p = slide(nm, f'오늘의 표현 {n} / 4', 'headphone', fn)
        if os.path.exists(NA + key + '.mp3'): slide_narr(nm, p, key)
        else: slide_plain(nm, p, [(0.3, DING)], 5.0)
    for i, (en, ko) in enumerate(exs, 1): drill(f'{nm}_d{i}', en, ko, i, 2, f'오늘의 표현 {n} / 4  ·  {ex}')

def s_formula(im, d):
    ctext(d, 190, '두 회장의 축사 공식', F(60, 'Bold'), TXT)
    x = 260
    for i, t in enumerate(['이야기 하나', '비유 하나', '농담 하나']):
        card(d, (x + i * 480, 330, x + i * 480 + 420, 530), fill=ESP if i == 2 else CARD)
        vcenter(d, x + i * 480 + 210, 330, 200, t, F(58, 'ExtraBold'), WHITE if i == 2 else TXT, 'm')
    ctext(d, 640, '공통점 세 가지 공식  →  We have three things in common.', F(44, 'Bold'), BLUE)
if not skip('30_formula'): slide_narr('30_formula', slide('30_formula', '나도 써먹기', 'check', s_formula), 'N12')
drill('31_t1', 'We have three things in common.', '우리에겐 공통점이 세 가지 있어요.', 1, 2, '나도 써먹기', 'check')
drill('32_t2', 'We both love coffee, we both hate Mondays, and we both love this team.', '둘 다 커피를 좋아하고, 월요일을 싫어하고, 이 팀을 사랑하죠.', 2, 2, '나도 써먹기', 'check')

QUIZ = [
    ('Q1', 'A1', '"I hate to ___ to you, but the store is closed."', '이런 말 하기 그렇지만, 가게 문 닫았어.', ['break it', 'tell it', 'give it', 'bring it'], 0),
    ('Q2', 'A2', '"우리는 프로젝트를 예정보다 빨리 끝냈어요."', '영어로 하면?', ['We finished it ahead of schedule.', 'We finished it behind schedule.', 'We finished it on schedule.', 'We finished it out of schedule.'], 0),
    ('Q3', 'A3', '회식에서 "우리 팀을 위해 건배해요!"', '영어로 하면?', ['Please raise your glass to our team!', 'Please raise your hand to our team!', 'Please break your glass to our team!', 'Please put your glass on our team!'], 0),
]
for n, (q, a, qt, sub, opts, ans) in enumerate(QUIZ, 1):
    nm = f'4{n}_quiz'
    if skip(nm): continue
    def draw(reveal, count=None):
        im, d = canvas(f'퀴즈 {n} / 3', 'question-mark')
        y = ctext(d, 180, qt, F(60, 'ExtraBold'), TXT, maxw=1400); ctext(d, y + 6, sub, F(38, 'Medium'), GRAY)
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
    qm, am = NA + q + '.mp3', NA + a + '.mp3'; qd, ad = dur(qm), dur(am); t0 = 0.3 + qd + 0.3
    fr = []
    for (st, png, key, mp, lead) in ((0, pq, q, qm, 0.3), (t0 + 3, pa, a, am, t0 + 3.4)):
        b = png[:-4] + '_s_.png'; sub_strip(png, b, ''); fr.append((st, b))
        for j, (c0, c1, tx) in enumerate(narr_cues(NTEXT[key], mp, lead)):
            sp = png[:-4] + f'_s{j}.png'; sub_strip(png, sp, tx); fr += [(c0, sp), (c1, b)]
    for k, c in enumerate(pcs):
        b = c[:-4] + '_s_.png'; sub_strip(c, b, ''); fr.append((t0 + k, b))
    fr = sorted(fr, key=lambda x: x[0])
    seg_slide(nm, fr, [(0.3, qm), (t0, TICK), (t0 + 1, TICK), (t0 + 2, TICK), (t0 + 3, DING), (t0 + 3.4, am)], t0 + 3.4 + ad + 1.0)

# 마지막: 웹과 이어지는 소개
def s_out(im, d):
    lg = Image.open(LOGO).convert('RGBA').resize((110, 110)); im.paste(lg, (170, 170), lg)
    d.text((300, 182), '카페인영어', font=F(64, 'Black'), fill=TXT); d.text((302, 258), 'CafeInEnglish', font=F(30, 'SemiBold'), fill=GRAY)
    d.text((170, 360), '오늘 표현,', font=F(70, 'ExtraBold'), fill=TXT)
    d.text((170, 450), '장면으로 다시 들어 볼까요?', font=F(70, 'ExtraBold'), fill=TXT)
    rows = [('headphone', '듣기 버튼 하나로 그 장면만 바로'), ('question-mark', '퀴즈 · 오답노트로 복습'), ('check', '가입 없이 전부 무료')]
    y = 600
    for ic, t in rows:
        icon(im, ic, 170, y, 60); vcenter(d, 252, y, 60, t, F(40, 'SemiBold'), SUB); y += 86
    f = F(40, 'Bold'); t = 'cafeinenglish.com  ·  설명란 링크'; w_ = d.textlength(t, font=f)
    d.rounded_rectangle((170, 880, 170 + w_ + 96, 960), 40, fill=BLUE); vcenter(d, 218, 880, 80, t, f, WHITE)
    # 휴대폰 속 실제 글 화면
    ph = (1180, 90, 1180 + 520, 90 + 960)
    d.rounded_rectangle((ph[0] - 14, ph[1] - 14, ph[2] + 14, ph[3] + 14), 74, fill=TXT)
    shot = Image.open(D + 'site_expr.png').convert('RGB')
    sw = ph[2] - ph[0]; sh = ph[3] - ph[1]
    sc = sw / shot.width; shot = shot.resize((sw, int(shot.height * sc)), Image.LANCZOS)
    shot = shot.crop((0, 0, sw, sh))
    m = Image.new('L', (sw, sh), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, sw, sh), 62, fill=255)
    im.paste(shot, (ph[0], ph[1]), m)
    d.rounded_rectangle((ph[0] + sw / 2 - 70, ph[1] + 16, ph[0] + sw / 2 + 70, ph[1] + 50), 17, fill=TXT)
if not skip('50_out'):
    im = Image.new('RGB', (W, H), WHITE); d = ImageDraw.Draw(im); s_out(im, d); p = R + '50_out.png'; im.save(p)
    seg_slide('50_out', [(0, p)], [(0.4, NA + 'N13.mp3')], dur(NA + 'N13.mp3') + 2.2)

# 순서대로 목록 (skip()이 넣은 경로 기준, 중복 제거)
seen = []; [seen.append(s) for s in SEGS if s not in seen]
open(R + 'list.txt', 'w').write(''.join(f"file '{s}'\n" for s in seen))
print('segments', len(seen))

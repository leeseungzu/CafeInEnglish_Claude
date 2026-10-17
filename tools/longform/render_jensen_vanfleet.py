import os, sys, json, hashlib, subprocess
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/tmp/claude-0/-home-claude/867aec65-8c7b-57fa-a377-537e93906e02/scratchpad/lf')
from lf_style import *

D = '/tmp/claude-0/-home-claude/867aec65-8c7b-57fa-a377-537e93906e02/scratchpad/jh/'
R = D + 'r/'; NA = D + 'na/'; KO = D + 'ko/'
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
        t1e = t1 + 0.25 if i + 1 == len(cues) else min(t1 + 0.25, cues[i + 1][0] - 0.03)
        fl += f";[{last}][{i+2}:v]overlay=0:0:enable='between(t,{t0-a:.2f},{t1e-a:.2f})':shortest=1[v{i+2}]"; last = f'v{i+2}'
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



def band_base(path, text):
    """자막 없는 구간: 음영은 그대로, 가운데에 작은 안내 글자"""
    video_base(path); im = Image.open(path); d = ImageDraw.Draw(im)
    f = F(36, 'SemiBold'); w_ = d.textlength(text, font=f)
    d.text(((W - w_) / 2, BAND_TOP + (H - BAND_TOP) / 2 - 24), text, font=f, fill=(200, 205, 212)); im.save(path)

def seg_plain(name, src, a, b, text, top=None):
    if skip(name): return
    base = R + name + '_base.png'; band_base(base, text)
    if top:
        im = Image.open(base); d = ImageDraw.Draw(im); f = F(80, 'ExtraBold'); w_ = d.textlength(top, font=f)
        d.rounded_rectangle((W/2 - w_/2 - 50, 120, W/2 + w_/2 + 50, 250), 30, fill=(25, 31, 40, 225))
        vcenter(d, W/2, 120, 130, top, f, WHITE, 'm'); im.save(base)
    L = b - a
    fl = f'[0:v]fps={FPS},scale={W}:{H},setsar=1[v0];[v0][1:v]overlay=0:0:shortest=1[v]'
    fl += f';[0:a]afade=t=in:d=0.15,afade=t=out:st={L-0.3:.2f}:d=0.3,loudnorm=I=-16:TP=-1.5,aresample=48000[a]'
    run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a), '-t', str(L), '-i', D + src + '.mp4', '-loop', '1', '-i', base, '-filter_complex', fl, '-map', '[v]', '-map', '[a]', '-t', f'{L:.2f}'] + enc() + [R + name + '.mp4'])

def step(name, n, title, sub, ic):
    if skip(name): return
    def fn(im, d):
        icon(im, ic, W/2 - 90, 200, 180)
        f = F(40, 'Bold'); t = f'STEP {n}'; w_ = d.textlength(t, font=f)
        d.rounded_rectangle((W/2 - w_/2 - 34, 420, W/2 + w_/2 + 34, 486), 33, fill=BLUE); vcenter(d, W/2, 420, 66, t, f, WHITE, 'm')
        ctext(d, 520, title, F(84, 'ExtraBold'), TXT); ctext(d, 650, sub, F(42, 'Medium'), GRAY)
    p = slide(name, None, None, fn); slide_plain(name, p, [(0.15, DING)], 1.8)


# ============ 젠슨 황 밴 플리트상 수상 소감 롱폼 ============
JH = '젠슨 황 엔비디아 CEO'
CLIPS = [
    ('c_A', 10.5, 25.6, [(10.7, 13.9, "I have to admit, I'm rather uncomfortable with all this attention,", '솔직히 말하면, 이렇게 관심을 받는 게 좀 불편하네요.'),
                        (15.75, 23.5, "and usually when people mention my name this many times, I'm usually in trouble somehow.", '보통 사람들이 제 이름을 이렇게 많이 부르면, 제가 뭔가 사고를 친 거거든요.')]),
    ('c_C', 84.0, 114.4, [(84.2, 91.7, 'I had no idea that Nvidia was so popular with Koreans until the first time I went there.', '처음 한국에 가기 전까진 엔비디아가 한국에서 그렇게 인기 있는 줄 몰랐어요.'),
                         (92.1, 100.0, 'The young people were so passionate about StarCraft, and they were so passionate about Nvidia,', '젊은이들이 스타크래프트에 푹 빠져 있었고, 엔비디아에도 열광했죠.'),
                         (100.2, 110.2, 'and it was the first time I heard the name of the company I helped create chanted out loud, and it took my breath away.', '제가 만든 회사 이름을 사람들이 외치는 걸 처음 들었는데, 숨이 멎는 줄 알았어요.'),
                         (110.5, 113.9, "It's hard not to have fallen in love with Korea.", '한국과 사랑에 빠지지 않을 수가 없었죠.')]),
    ('c_F1', 296.0, 299.4, [(296.2, 298.4, 'Excuse me. Could somebody pass me my phone?', '실례지만, 누가 제 휴대폰 좀 건네주실래요?')]),
    ('c_F2', 307.3, 380.4, [(307.55, 309.9, "I'm expecting a phone call.", '전화 올 데가 있어서요.'),
                           (317.0, 318.1, "It wasn't made up.", '지어낸 얘기가 아니에요.'),
                           (319.4, 321.4, 'I was on stage,', '제가 무대에 있었는데,'),
                           (322.5, 328.7, "and Janine, who's here, she was waving my phone, and nobody waves my phone.", '여기 와 있는 재닌이 제 휴대폰을 흔들고 있었어요. 아무도 제 폰을 흔들지 않거든요.'),
                           (329.0, 334.4, 'And this phone, as it turns out, outputs a lot of light.', '그런데 이 폰이 알고 보니 빛이 엄청 밝더라고요.'),
                           (335.6, 342.9, 'And I saw from a hundred feet away the name of the person who called me.', '30미터 떨어진 곳에서도 전화한 사람 이름이 보였어요.'),
                           (344.5, 349.5, 'And I said, "Oh no, it must be something urgent."', "그래서 '이런, 급한 일인가 보다' 했죠."),
                           (350.5, 363.2, 'And so, anyhow, I think several hundred million people went on to try to figure out what phone this was.', '그 뒤로 수억 명이 이 폰이 뭔지 알아내려고 했던 것 같아요.'),
                           (363.7, 367.4, 'Ladies and gentlemen, this is a Samsung Galaxy,', '신사 숙녀 여러분, 이건 삼성 갤럭시예요.'),
                           (374.6, 378.2, 'the brightest phone in the world.', '세상에서 가장 밝은 폰이죠.')]),
    ('c_G', 465.9, 481.0, [(466.0, 473.6, 'Well, no company, no people are better at building factories than Koreans.', '공장을 짓는 데 한국 사람들보다 뛰어난 회사, 뛰어난 사람들은 없어요.'),
                          (475.4, 478.0, 'And now you are building the factory of intelligence.', "이제 여러분은 '지능의 공장'을 짓고 있어요."),
                          (478.7, 480.5, "And we're building it together.", '그리고 우리가 함께 짓고 있죠.')]),
]

# 0. 훅
# (훅 삭제) seg_plain('00_hook', 'jh', 363.5, 380.4, '끝까지 보면 이 말이 들려요', top='젠슨 황이 무대에서 꺼낸 휴대폰의 정체는?')
seg_broll('01_open', [('jh', 40, 58)], 'J01', label='2026.9.28 뉴욕 · 코리아소사이어티 연례 만찬')
# STEP 1
step('s1', 1, '자막 없이 들어 보세요', '몇 문장이나 들리나요? 들린 단어만 기억해 두세요', 'ear')
for n, a, b, _ in CLIPS: seg_plain('p_' + n, 'jh', a, b, f'{JH}  ·  자막 없이 듣기')
# STEP 2
step('s2', 2, '장면 해설', '왜 웃겼는지, 어떤 표현을 썼는지', 'light-bulb')

def s_reasons(im, d):
    ctext(d, 170, '이 상이 의미 있는 세 가지 이유', F(64, 'ExtraBold'), TXT)
    rows = [('a great sense of gratitude', '한국과의 우정에 대한 감사', True), ('incredibly proud', '두 나라 사이에 서 있다는 자부심', False), ('a great sense of optimism', '함께 만들 미래에 대한 낙관', False)]
    y = 320
    for i, (en, ko, hi) in enumerate(rows):
        card(d, (230, y, W - 230, y + 160), fill=WHITE if hi else CARD, outline=BLUE if hi else None, width=4)
        chip(d, 310, y + 80, str(i + 1), fill=BLUE if hi else ESP)
        d.text((380, y + 30), en, font=F(48, 'Bold'), fill=TXT); d.text((380, y + 94), ko, font=F(34, 'SemiBold'), fill=BLUE if hi else SUB)
        y += 190
slide_narr('10_reasons', slide('10_reasons', '수상 소감', 'speech-balloon', s_reasons), 'J03')

def s_breath(im, d):
    f = F(84, 'ExtraBold'); t1 = 'It took my '; t2 = 'breath away.'
    w1 = d.textlength(t1, font=f); w2 = d.textlength(t2, font=f); x = W / 2 - (w1 + w2) / 2
    d.text((x, 220), t1, font=f, fill=TXT); underline(d, x + w1, 220, t2, f)
    ctext(d, 350, '숨이 멎을 만큼 감동했다', F(52, 'Bold'), BLUE)
    card(d, (260, 500, W - 260, 780))
    ctext(d, 548, 'the first time I heard the name of the company', F(44, 'Bold'), TXT, maxw=1300)
    ctext(d, 610, 'I helped create chanted out loud', F(44, 'Bold'), TXT, maxw=1300)
    ctext(d, 700, '제가 만든 회사 이름을 사람들이 외치는 걸 처음 들은 순간', F(36, 'Medium'), SUB)
slide_narr('11_breath', slide('11_breath', '스타크래프트와 엔비디아', 'party-popper', s_breath), 'J04')

def s_phone(im, d):
    icon(im, 'mobile-phone', W / 2 - 80, 170, 160)
    card(d, (300, 380, W - 300, 690), fill=WHITE, outline=BLUE, width=4)
    ctext(d, 430, 'Ladies and gentlemen,', F(56, 'Bold'), SUB)
    ctext(d, 510, 'this is a Samsung Galaxy,', F(76, 'ExtraBold'), TXT)
    ctext(d, 610, 'the brightest phone in the world.', F(48, 'Bold'), BLUE)
    ctext(d, 760, '30미터 밖에서도 발신자 이름이 보였다는 그 폰', F(40, 'SemiBold'), GRAY)
slide_narr('12_phone', slide('12_phone', '가장 크게 웃음 터진 장면', 'grimacing-face', s_phone), 'J05')

def s_factory(im, d):
    card(d, (260, 190, W - 260, 470))
    ctext(d, 240, 'No people are better at', F(64, 'ExtraBold'), TXT)
    ctext(d, 330, 'building factories than Koreans.', F(64, 'ExtraBold'), TXT)
    ctext(d, 520, '공장을 짓는 데 한국 사람보다 뛰어난 사람은 없다', F(44, 'Bold'), BLUE)
    card(d, (420, 620, W - 420, 780), fill=ESP)
    vcenter(d, W / 2, 620, 160, 'the factory of intelligence = 지능의 공장', F(46, 'Bold'), WHITE, 'm')
slide_narr('13_factory', slide('13_factory', '한국에 대한 칭찬', 'thumbs-up', s_factory), 'J06')

EXPR = [
    ('JE1', 'I have to admit', '솔직히 말하면, 인정하자면', ("I have to admit, I was a little nervous.", '솔직히 좀 긴장했어요.')),
    ('JE2', 'take my breath away', '숨이 멎을 만큼 감동적이다', ('The view took my breath away.', '경치가 숨이 멎을 만큼 멋졌어요.')),
    ('JE3', 'Could somebody pass me ~?', '누가 ~ 좀 건네주실래요?', ('Could somebody pass me the salt?', '누가 소금 좀 건네주실래요?')),
    ('JE4', 'No one is better at ~ than …', '~하는 데는 …가 최고예요', ('No one is better at making kimchi than my mom.', '김치 담그는 건 우리 엄마가 최고예요.')),
]
for n, (key, ex, mean, (exen, exko)) in enumerate(EXPR, 1):
    nm = f'2{n}_{key}'
    def fn(im, d, ex=ex, mean=mean, exen=exen, exko=exko):
        f = F(108 if len(ex) < 22 else 88, 'Black'); w_ = d.textlength(ex, font=f); underline(d, W / 2 - w_ / 2, 220, ex, f)
        ctext(d, 410, mean, F(56, 'Bold'), BLUE)
        card(d, (260, 560, W - 260, 790)); icon(im, 'light-bulb', 310, 630, 80)
        dd = ImageDraw.Draw(im); dd.text((420, 610), exen, font=F(46, 'Bold'), fill=TXT); dd.text((420, 690), exko, font=F(36, 'Medium'), fill=SUB)
    p = slide(nm, f'오늘의 표현 {n} / 4', 'headphone', fn); slide_narr(nm, p, key)

# STEP 3
step('s3', 3, '한영 자막으로 다시 듣기', '처음보다 얼마나 들리는지 확인해 보세요', 'headphone')
for n, a, b, cues in CLIPS: seg_clip(n, 'jh', a, b, cues, JH)
# STEP 4
step('s4', 4, '입으로 마무리', '핵심 문장 따라 말하고 퀴즈 하나', 'speech-balloon')
drill('41_d1', 'I have to admit, I was a little nervous.', '솔직히 좀 긴장했어요.', 1, 2, '따라 말하기', 'ear')
drill('42_d2', 'Could somebody pass me the salt?', '누가 소금 좀 건네주실래요?', 2, 2, '따라 말하기', 'ear')

nm = '45_quiz'
if not skip(nm):
    qt, sub, opts, ans = '"It took my breath away."', '젠슨 황이 한 이 말의 뜻은?', ['숨이 멎을 만큼 감동했다', '숨이 차서 힘들었다', '너무 놀라서 화가 났다', '숨을 꾹 참았다'], 0
    def draw(reveal, count=None):
        im, d = canvas('퀴즈', 'question-mark')
        y = ctext(d, 180, qt, F(64, 'ExtraBold'), TXT, maxw=1400); ctext(d, y + 6, sub, F(38, 'Medium'), GRAY)
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

SEGS.append('/tmp/claude-0/-home-claude/867aec65-8c7b-57fa-a377-537e93906e02/scratchpad/lf/r2/50_out.mp4')
seen = []; [seen.append(s) for s in SEGS if s not in seen]
open(R + 'list.txt', 'w').write(''.join(f"file '{s}'\n" for s in seen))
print('segments', len(seen))

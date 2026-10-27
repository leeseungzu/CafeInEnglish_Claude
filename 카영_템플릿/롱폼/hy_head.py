import os, sys, json, hashlib, subprocess
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lf_style import *

D = '/tmp/claude-0/-home-claude/867aec65-8c7b-57fa-a377-537e93906e02/scratchpad/hy/'
R = D + 'r/'; NA = D + 'N/'; KO = D + 'ko/'
os.makedirs(R, exist_ok=True)
ONLY = set(sys.argv[1:])  # 샘플만 만들 때 세그먼트 이름
import re as _re
NTEXT = {}
SEGS = []


def run(cmd): subprocess.run(cmd, check=True)
def enc(): return ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2']
def skip(name):
    out = R + name + '.mp4'
    if out not in SEGS: SEGS.append(out)
    return (ONLY and name not in ONLY) or os.path.exists(out)
from build_audio import cora
def kokoro(t):  # 이름은 그대로 두고 Azure 코라로 만들어요 (롱폼 영어 목소리)
    os.makedirs(KO, exist_ok=True); k = hashlib.md5(t.encode()).hexdigest()[:12]
    p = KO + k + '.mp3'; cora(t, p); return p


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
        y = 400; f = F(74, 'ExtraBold'); rows = sum([wrap(d, x, f, 1380) for x in en.split('\n')], [])
        y = 545 - (len(rows) * f.size * 1.3 + 70) / 2
        for ln in rows:
            w_ = d.textlength(ln, font=f); d.text(((W - w_) / 2, y), ln, font=f, fill=TXT); y += f.size * 1.3
        ctext(d, y + 18, ko, F(42, 'Medium'), SUB)
    p1 = slide(name + '_a', label, ic, fn)
    im = Image.open(p1); d = ImageDraw.Draw(im); f = F(36, 'Bold')
    t = '이제 소리 내서 말해 보세요'; w_ = d.textlength(t, font=f); x0 = W / 2 - w_ / 2 - 46
    d.rounded_rectangle((x0, 800, W / 2 + w_ / 2 + 46, 880), 40, fill=BLUE); vcenter(d, W / 2, 800, 80, t, f, WHITE, 'm')
    p2 = R + name + '_b.png'; im.save(p2)
    au = kokoro(en.replace('\n', ' ')); a = dur(au); t1 = 0.4; t2_ = t1 + a + 0.7; t3 = t2_ + a + 0.3; L = t3 + max(2.6, a + 1.0)
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



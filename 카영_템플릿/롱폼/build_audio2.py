"""문장 단위 조각을 이어 붙이고, 각 문장의 정확한 시작/끝을 timing.json에 기록 (자막 싱크용)"""
import json, subprocess, os
from build_audio import cora
D = os.path.dirname(os.path.abspath(__file__)) + '/'
SR = 48000
def trimnorm(i, o):
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', i, '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    env = np.convolve(np.abs(x), np.ones(480) / 480, mode='same')
    idx = np.where(env > 0.006)[0]
    a = max(0, idx[0] - 960) if len(idx) else 0; b = min(len(x), idx[-1] + 2400) if len(idx) else len(x)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', '48000', '-ac', '1', '-i', '-', '-af', 'loudnorm=I=-16:TP=-1.5,aresample=48000', '-ac', '1', o], input=x[a:b].tobytes(), check=True)
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))
def sil(t, p): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono', '-t', f'{t:.3f}', p], check=True)
if __name__ == '__main__':
    for d in ('en', 'nk2', 'N'): os.makedirs(D + d, exist_ok=True)
    U = json.load(open(D + 'units.json'))
    keys = []
    for k, *_ in U:
        if k not in keys: keys.append(k)
    timing = {}
    for k in keys:
        parts, cues, t = [], [], 0.0
        us = [u for u in U if u[0] == k]
        for j, (_, i, lang, txt) in enumerate(us):
            src = D + (f'ns/{k}_{i}.mp3' if lang == 'ko' else f'en/{k}_{i}.mp3')
            if lang == 'en': cora(txt, src)
            w = D + f'nk2/{k}_{i}.wav'; trimnorm(src, w); L = dur(w)
            if parts:
                g = 0.45 if (lang == 'en' or us[j - 1][2] == 'en') else 0.3
                s = D + f'nk2/sil_{int(g*100)}.wav'
                if not os.path.exists(s): sil(g, s)
                parts.append(s); t += g
            parts.append(w); cues.append([round(t, 3), round(t + L, 3), txt, lang]); t += L
        lst = D + 'l2.txt'; open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-ac', '1', '-b:a', '192k', D + f'N/{k}.mp3'], check=True)
        timing[k] = cues
        print(k, round(t, 2), len(cues))
    json.dump(timing, open(D + 'timing.json', 'w'), ensure_ascii=False, indent=0)

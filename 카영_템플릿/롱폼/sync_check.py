import json, subprocess, numpy as np
T = json.load(open('timing.json')); SR = 16000; bad = 0; n = 0
def load(p):
    return np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',p,'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout, dtype=np.float32)
def rms(x,a,b):
    s=x[max(0,int(a*SR)):max(0,int(b*SR))]; return float(np.sqrt(np.mean(s**2))) if len(s) else 0
for k, cues in T.items():
    x = load(f'N/{k}.mp3')
    for a, b, t, l in cues:
        n += 1
        on = rms(x, a, a + 0.25); off_before = rms(x, a - 0.25, a - 0.03) if a > 0.3 else 0; end_after = rms(x, b + 0.03, b + 0.25)
        ok = on > 0.02 and off_before < 0.01 and end_after < 0.01
        if not ok: bad += 1; print('CHECK', k, round(a,2), round(b,2), round(on,3), round(off_before,4), round(end_after,4), t[:25])
print('cues', n, 'flagged', bad)

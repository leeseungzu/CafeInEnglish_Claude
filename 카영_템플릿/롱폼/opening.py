# ---- 문장 단위 타이밍으로 자막 (추정 없음) ----
TIMING = json.load(open(D + 'timing.json'))
for _k in TIMING: NTEXT.setdefault(_k, ' '.join(c[2] for c in TIMING[_k]))
def narr_cues(text, mp3, offset=0.0):
    k = os.path.basename(mp3)[:-4]
    return [(a + offset, b + offset, t) for a, b, t, _ in TIMING[k]]

# ---- 오프닝: 실제 사진 + 인용 카드 (좌 사진 / 우 텍스트) ----
OFF = (250, 248, 245)
CREDIT = {'P_arnold1.png': 'Photo: Gage Skidmore (CC BY-SA 2.0)'}
def _photo(p):
    return Image.open(D + 'art/' + p).convert('RGB')

def _panel(src, t, box=(90, 120, 1010, 900)):
    """사진을 박스에 꽉 차게 자르고 살짝 확대(1.0→1.06)"""
    bw, bh = box[2] - box[0], box[3] - box[1]
    z = 1.0 + 0.06 * t
    s = max(bw / src.width, bh / src.height) * z
    vw, vh = bw / s, bh / s
    x0 = (src.width - vw) / 2; y0 = (src.height - vh) * (0.1 if src.height > src.width else 0.35)
    return src.resize((bw, bh), Image.LANCZOS, box=(x0, y0, x0 + vw, y0 + vh))

def _sub(d, text):
    if not text: return
    d.rounded_rectangle((140, 950, W - 140, 1040), 26, fill=(42, 26, 18, 30))
    d.rounded_rectangle((140, 946, W - 140, 1036), 26, fill=(255, 255, 255, 255), outline=(229, 232, 235, 255), width=2)
    if not text: return
    f = F(40, 'SemiBold'); rows = wrap(d, text, f, 1560)
    if len(rows) > 1: f = F(34, 'SemiBold'); rows = wrap(d, text, f, 1580)
    tot = len(rows) * f.size * 1.25; y = 946 + (90 - tot) / 2 - 4
    for r_ in rows:
        w_ = d.textlength(r_, font=f); d.text(((W - w_) / 2, y), r_, font=f, fill=TXT); y += f.size * 1.25

def photo_story(name, key, tag, who, meta, photos, quote_ko):
    """photos: [(시작초, 파일)] / 영어 문장(Cora)이 나오는 동안 오른쪽에 인용 카드"""
    if skip(name): return
    mp3 = NA + key + '.mp3'; lead = 0.25; L = dur(mp3) + lead + 0.5
    cues = narr_cues('', mp3, lead); en = [c for c, u in zip(cues, TIMING[key]) if u[3] == 'en']
    srcs = {p: _photo(p) for _, p in photos}
    wav = R + name + '.wav'; audio_track([(lead, mp3)], L, wav)
    pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', wav, '-t', f'{L:.2f}'] + enc() + [R + name + '.mp4'], stdin=subprocess.PIPE)
    # 고정 레이어(오른쪽 텍스트)
    base = Image.new('RGB', (W, H), OFF); d = ImageDraw.Draw(base)
    x = 1080
    q = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dq = ImageDraw.Draw(q)
    fe = F(54, 'ExtraBold'); fk = F(34, 'Bold'); rows = wrap(dq, en[0][2], fe, 720) if en else []
    kr = wrap(dq, quote_ko, fk, 720)
    qh = len(rows) * 72 + len(kr) * 48 + 96
    top = int(510 - (54 + 26 + 96 + 44 + 40 + qh) / 2)
    f = F(30, 'Bold'); w_ = d.textlength(tag, font=f)
    d.rounded_rectangle((x, top, x + w_ + 44, top + 54), 27, fill=LIME); d.text((x + 22, top + 7), tag, font=f, fill=TXT)
    d.text((x, top + 80), who, font=F(78, 'Black'), fill=TXT)
    d.text((x + 2, top + 188), meta, font=F(28, 'SemiBold'), fill=GRAY)
    y = top + 260
    dq.rounded_rectangle((x - 6, y, W - 90, y + qh), 30, fill=(255, 255, 255, 255), outline=BLUE, width=4)
    yy = y + 40
    for r_ in rows: dq.text((x + 34, yy), r_, font=fe, fill=TXT); yy += 72
    yy += 8
    for r_ in kr: dq.text((x + 34, yy), r_, font=fk, fill=BLUE); yy += 48
    XF = 0.4; N = int(L * FPS) + 1
    for n in range(N):
        t = n / FPS
        i = max(j for j, (s, _) in enumerate(photos) if s <= t)
        def frame_of(j):
            s0 = photos[j][0]; s1 = photos[j + 1][0] if j + 1 < len(photos) else L
            return _panel(srcs[photos[j][1]], min(1, (t - s0) / max(0.1, s1 - s0)))
        pan = frame_of(i)
        if i > 0 and t - photos[i][0] < XF: pan = Image.blend(frame_of(i - 1), pan, (t - photos[i][0]) / XF)
        fr = base.copy().convert('RGBA'); dd = ImageDraw.Draw(fr)
        dd.rounded_rectangle((96, 130, 1016, 910), 34, fill=(42, 26, 18, 28))
        m = Image.new('L', pan.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, pan.width, pan.height), 30, fill=255)
        fr.paste(pan, (90, 120), m)
        cr = CREDIT.get(photos[i][1])
        if cr:
            fc = F(20, 'Medium'); wc = dd.textlength(cr, font=fc)
            ImageDraw.Draw(fr, 'RGBA').rounded_rectangle((1000 - wc - 28, 860, 1000, 892), 12, fill=(0, 0, 0, 130)); ImageDraw.Draw(fr).text((1000 - wc - 14, 865), cr, font=fc, fill=(255, 255, 255))
        if en and t >= en[0][0] - 0.2:
            a = min(1, (t - en[0][0] + 0.2) / 0.3)
            qq = q.copy(); qq.putalpha(q.getchannel('A').point(lambda v: int(v * a))); fr = Image.alpha_composite(fr, qq)
        tx = next((c[2] for c, u in zip(cues, TIMING[key]) if c[0] <= t <= c[1] + 0.15 and u[3] == 'ko'), '')
        _sub(ImageDraw.Draw(fr), tx)
        pr.stdin.write(fr.convert('RGB').tobytes())
    pr.stdin.close(); pr.wait()

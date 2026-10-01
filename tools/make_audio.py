#!/usr/bin/env python3
"""예문 원어민 음성(mp3) 만들기 — Kokoro TTS (오프라인 신경망 음성)

글의 예문(<span class="en">, expressions[].ex)을 찾아 audio/<키>.mp3 와 audio/index.json 을 만듭니다.
이미 만든 문장은 건너뛰므로, 새 글을 쓴 뒤 한 번만 돌리면 됩니다.

    pip install kokoro-onnx soundfile   (+ ffmpeg)
    모델: github.com/thewh1teagle/kokoro-onnx/releases (kokoro-v1.0.onnx, voices-v1.0.bin)
    KOKORO_DIR=/모델/폴더 python3 tools/make_audio.py
"""
import hashlib, html, json, os, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "audio"
VOICE = "af_heart"          # 미국 여성, 자연스러운 톤
MODEL_DIR = Path(os.environ.get("KOKORO_DIR", "/home/claude/tts"))


def norm(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def spoken(text):
    """화면 문장 → 읽을 문장. 'going to → gonna' 는 '원래 발음... 줄인 발음' 으로 읽어요."""
    if "→" in text:
        a, b = [x.strip() for x in text.split("→", 1)]
        a = re.sub(r"[()]", "", a)
        return f"{a} ... {b}"
    return text


def sentences():
    out = set()
    for f in sorted((ROOT / "content" / "posts").glob("*.json")):
        p = json.loads(f.read_text("utf-8"))
        for m in re.findall(r'<span class="en">(.*?)</span>', p.get("body_html", ""), re.S):
            out.add(norm(m))
        for x in p.get("expressions", []):
            if x.get("ex"):
                out.add(norm(x["ex"]))
    return sorted(t for t in out if re.search(r"[A-Za-z]", t))


def main():
    AUDIO.mkdir(exist_ok=True)
    idx_f = AUDIO / "index.json"
    index = json.loads(idx_f.read_text("utf-8")) if idx_f.exists() else {}
    todo = []
    for t in sentences():
        key = hashlib.md5(f"{VOICE}|{spoken(t)}".encode()).hexdigest()[:12]
        index[t] = f"{key}.mp3"
        if not (AUDIO / f"{key}.mp3").exists():
            todo.append((t, key))
    if todo:
        from kokoro_onnx import Kokoro
        import soundfile as sf
        k = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
        for t, key in todo:
            samples, sr = k.create(spoken(t), voice=VOICE, speed=1.0, lang="en-us")
            with tempfile.NamedTemporaryFile(suffix=".wav") as w:
                sf.write(w.name, samples, sr)
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", w.name, "-af",
                                "afade=t=in:d=0.02,apad=pad_dur=0.15", "-ac", "1", "-b:a", "64k",
                                str(AUDIO / f"{key}.mp3")], check=True)
            print("🔊", t)
    used = set(index[t] for t in sentences())
    index = {t: v for t, v in index.items() if v in used}
    idx_f.write_text(json.dumps(index, ensure_ascii=False, indent=1), "utf-8")
    print(f"✅ 음성 {len(index)}개 (새로 만든 것 {len(todo)}개)")


if __name__ == "__main__":
    main()

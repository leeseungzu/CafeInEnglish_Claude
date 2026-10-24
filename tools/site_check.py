"""사이트 점검 (빌드 뒤 실행): python3 tools/site_check.py
새 도구·글·카테고리를 늘릴 때마다 돌려서 검색·애드센스·속도 기본기를 확인해요.
- 검색: 제목 중복·길이, 설명 길이, h1 개수, canonical, 사이트맵 누락, 깨진 내부 링크, JSON-LD 오류, 이미지 alt
- 애드센스: ads.txt, 얇은 페이지(본문 글자 수), 개인정보처리방침·문의·소개 페이지
- 속도: CSS·JS·폰트·HTML 크기(gzip 기준)
"""
import collections, gzip, json, re, sys
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "docs"
DOMAIN = "https://www.cafeinenglish.com"
pages = {}
for f in D.rglob("*.html"):
    rel = f.parent.relative_to(D).as_posix()
    p = ("/" + rel + "/").replace("/./", "/").replace("//", "/") if f.name == "index.html" else "/" + f.relative_to(D).as_posix()
    pages[p] = f.read_text("utf-8")
sm = set(re.findall(rf"<loc>{re.escape(DOMAIN)}([^<]+)</loc>", (D / "sitemap.xml").read_text("utf-8")))
bad, warn = collections.defaultdict(list), collections.defaultdict(list)
titles, links = collections.Counter(), set()
for p, h in pages.items():
    ni = "noindex" in h
    t = (re.search(r"<title>(.*?)</title>", h, re.S) or [None, ""])[1]
    titles[t] += 0 if ni else 1
    d = (re.search(r'<meta name="description" content="([^"]*)"', h) or [None, ""])[1]
    if not ni:
        if not d: bad["설명 없음"].append(p)
        elif not 50 <= len(d) <= 160: warn["설명 길이(50~160자 권장)"].append(f"{p} {len(d)}")
        if len(t) > 70: warn["제목 70자 넘음"].append(f"{p} {len(t)}")
        if len(re.findall(r"<h1[\s>]", h)) != 1 and p != "/404.html": bad["h1이 1개가 아님"].append(p)
        c = re.search(rf'rel="canonical" href="{re.escape(DOMAIN)}([^"]*)"', h)
        if c and c.group(1) != p: bad["canonical 불일치"].append(f"{p} → {c.group(1)}")
        if p not in sm and p != "/404.html": bad["사이트맵 누락"].append(p)
        txt = re.sub(r"\s+", "", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style|header|footer|nav)[^>]*>.*?</\1>", "", h, flags=re.S)))
        if len(txt) < 600 and p not in ("/404.html", "/contact/"): warn["본문이 짧음(600자 미만)"].append(f"{p} {len(txt)}")
    elif p in sm:
        bad["noindex인데 사이트맵에 있음"].append(p)
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try: json.loads(m)
        except Exception: bad["JSON-LD 오류"].append(p)
    if re.search(r"<img(?![^>]*\balt=)[^>]*>", h): bad["img alt 없음"].append(p)
    links.update(re.findall(r'href="(/[^"#?]*)"', h))
for t, n in titles.items():
    if n > 1: bad["제목 중복"].append(f"{t[:40]} ×{n}")
for l in links:
    q = D / l.lstrip("/")
    if not (q.exists() or (q / "index.html").exists()): bad["깨진 내부 링크"].append(l)
for p in sm:
    if p not in pages: bad["사이트맵에 있는데 페이지 없음"].append(p)
for need in ("/privacy/", "/contact/", "/about/"):
    if need not in pages: bad["필수 페이지 없음"].append(need)
if not (D / "ads.txt").exists(): bad["ads.txt 없음"].append("ads.txt")
gz = lambda f: len(gzip.compress((D / f).read_bytes(), 9)) // 1024
sizes = {f: gz(f) for f in ("assets/site.css", "assets/app.js", "assets/tools.js") if (D / f).exists()}
font = (D / "assets/pretendard-subset.woff2").stat().st_size // 1024
home = gz("index.html")
if sizes.get("assets/site.css", 0) > 45: warn["CSS가 큼(gzip 45KB 넘음)"].append(f"{sizes['assets/site.css']}KB")
if font > 200: warn["폰트 서브셋이 큼(200KB 넘음)"].append(f"{font}KB")
if home > 45: warn["홈 HTML이 큼(gzip 45KB 넘음)"].append(f"{home}KB")
print(f"페이지 {len(pages)}개 · 사이트맵 {len(sm)}개 · 내부 링크 {len(links)}개")
print("크기(gzip):", ", ".join(f"{k.split('/')[-1]} {v}KB" for k, v in sizes.items()), f"· 폰트 {font}KB · 홈 HTML {home}KB")
for k, v in bad.items(): print(f"❌ {k} ({len(v)}): {', '.join(v[:8])}")
for k, v in warn.items(): print(f"⚠️ {k} ({len(v)}): {', '.join(v[:8])}")
print("✅ 문제 없음" if not bad else "")
sys.exit(1 if bad else 0)

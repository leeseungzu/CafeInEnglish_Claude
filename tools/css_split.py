"""페이지 묶음별로 실제 쓰는 CSS 규칙만 남겨 site-<묶음>.css 로 나눈다 (모바일 첫 화면 속도).
남기는 기준(보수적): 선택자 안의 클래스·아이디가 모두 그 묶음 HTML 또는 사이트 JS 어딘가에 글자로 나오면 남김.
:not() :is() :where() 안은 따지지 않고 남김. @font-face·@keyframes 는 항상 남김."""
import re
from pathlib import Path

TOK = re.compile(r"[A-Za-z_][\w-]*")

def _rules(css):
    out, depth, start, i = [], 0, 0, 0
    n = len(css)
    while i < n:
        ch = css[i]
        if ch == '"' or ch == "'":
            j = css.index(ch, i + 1)
            i = j + 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                out.append(css[start:i + 1].strip())
                start = i + 1
        elif ch == ";" and depth == 0:
            out.append(css[start:i + 1].strip())
            start = i + 1
        i += 1
    tail = css[start:].strip()
    if tail:
        out.append(tail)
    return [r for r in out if r]

def _split_sel(sel):
    parts, depth, cur = [], 0, ""
    for ch in sel:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts

def _strip_fn(s):
    # :not(...) :is(...) :where(...) 안은 지움 (괄호 중첩 처리)
    while True:
        m = re.search(r":(not|is|where)\(", s)
        if not m:
            return s
        i, depth = m.end(), 1
        while i < len(s) and depth:
            if s[i] == "(":
                depth += 1
            elif s[i] == ")":
                depth -= 1
            i += 1
        s = s[:m.start()] + s[i:]

def _need(sel):
    s = re.sub(r"\[[^\]]*\]", "", sel)
    s = _strip_fn(s)
    return re.findall(r"[.#](-?[A-Za-z_][\w-]*)", s)

class Purger:
    def __init__(self, tokens, prefixes):
        self.t, self.p = tokens, tuple(prefixes)
    def ok(self, name):
        return name in self.t or (self.p and name.startswith(self.p))
    def keep_sel(self, sel):
        return all(self.ok(n) for n in _need(sel))
    def purge(self, css):
        out = []
        for r in _rules(css):
            if r.startswith("@"):
                head = r[:r.find("{")] if "{" in r else r
                if re.match(r"@(media|supports|container|layer)\b", head) and "{" in r:
                    inner = self.purge(r[r.find("{") + 1:-1])
                    if inner:
                        out.append(head + "{" + inner + "}")
                else:
                    out.append(r)  # @font-face, @keyframes, @import, @charset ...
                continue
            if "{" not in r:
                continue
            sel, body = r[:r.find("{")], r[r.find("{"):]
            kept = [s for s in _split_sel(sel) if self.keep_sel(s)]
            if kept:
                out.append(",".join(kept) + body)
        return "".join(out)

def js_tokens(js_texts):
    toks, pre = set(), set()
    for t in js_texts:
        toks.update(TOK.findall(t))
        for m in re.finditer(r"([A-Za-z_][\w-]*-)\s*(?:[\"'`]\s*\+|\$\{)", t):
            pre.add(m.group(1))
    return toks, pre

def group_of(rel):
    first = rel.split("/")[0] if "/" in rel else ""
    if rel == "index.html":
        return "home"
    if first in ("p", "think", "travel", "notes"):
        return "post" if first in ("p", "think") else first
    if first in ("category", "series"):
        return "list"
    if first in ("tools", "today", "cafe"):
        return first
    return "etc"


def split_site_css(out, light_css, dark_css, css_v, dark_v):
    """빌드 끝에 실행: docs/ 의 HTML을 묶음별로 모아, 묶음마다 쓰는 규칙만 담은
    /assets/css/<묶음>.site.css · <묶음>.dark.css 를 만들고 링크를 바꾼다.
    (전체판 /assets/site.css·dark.css 는 그대로 둬서 옛 페이지도 안전)"""
    import hashlib, gzip
    out = Path(out)
    js = [f.read_text("utf-8", errors="ignore") for f in (out / "assets").glob("*.js")]
    jt, pre = js_tokens(js)
    old_l, old_d = f"/assets/site.css?v={css_v}", f"/assets/dark.css?v={dark_v}"
    pages, toks = {}, {}
    for f in out.rglob("*.html"):
        h = f.read_text("utf-8", errors="ignore")
        if old_l not in h:
            continue
        g = group_of(str(f.relative_to(out)).replace("\\", "/"))
        pages.setdefault(g, []).append(f)
        toks.setdefault(g, set()).update(TOK.findall(h))
    (out / "assets" / "css").mkdir(parents=True, exist_ok=True)
    report = []
    for g, files in pages.items():
        P = Purger(toks[g] | jt, pre)
        lc, dc = P.purge(light_css), P.purge(dark_css)
        lv, dv = hashlib.md5(lc.encode()).hexdigest()[:8], hashlib.md5(dc.encode()).hexdigest()[:8]
        (out / "assets" / "css" / f"{g}.site.css").write_text(lc, "utf-8")
        (out / "assets" / "css" / f"{g}.dark.css").write_text(dc, "utf-8")
        new_l, new_d = f"/assets/css/{g}.site.css?v={lv}", f"/assets/css/{g}.dark.css?v={dv}"
        for f in files:
            h = f.read_text("utf-8")
            f.write_text(h.replace(old_l, new_l).replace(old_d, new_d), "utf-8")
        report.append(f"{g} {len(files)}쪽 {len(gzip.compress(lc.encode())) // 1024}KB")
    print("🎨 CSS 묶음별로 나눔 (gzip):", ", ".join(sorted(report)))

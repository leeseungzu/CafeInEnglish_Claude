"""여행영어 PDF 만들기: python3 tools/make_travel_pdf.py travel.html → 크롬(Playwright)으로 A4 PDF 인쇄 → files/travel-english.pdf
상황 글(content/posts) 내용을 그대로 읽어 만들어요. 글을 고치면 다시 돌리면 돼요. (pip install segno)"""
import json, re, html, segno, sys
from pathlib import Path
U = str(Path(__file__).resolve().parent.parent)  # 저장소 루트
OUT = sys.argv[1]
un = html.unescape
SIT = [("기내", "airplane", "in-flight"), ("입국심사", "passport-control", "immigration"), ("수하물·세관", "luggage", "baggage-customs"),
       ("교통", "taxi", "transportation"), ("호텔", "hotel", "hotel-check-in"), ("카페", "hot-beverage", "travel-cafe"), ("식당", "fork-knife-plate", "travel-restaurant"),
       ("쇼핑·계산", "shopping-bags", "shopping-checkout"), ("길 찾기", "world-map", "asking-directions"), ("문제 상황", "pill", "travel-trouble")]
PLAN = [("D-7", "기내 + 살아남는 문장", [0]), ("D-6", "입국심사 + 수하물·세관", [1, 2]), ("D-5", "교통", [3]), ("D-4", "호텔", [4]),
        ("D-3", "카페 + 식당", [5, 6]), ("D-2", "쇼핑 + 길 찾기", [7, 8]), ("D-1", "문제 상황 + 전체 복습", [9])]
DOM = "https://www.cafeinenglish.com"
def qr(url, scale=3):
    return segno.make(url, error="m").svg_inline(scale=scale, border=0, dark="#191F28")
def ic(name): return f'<img class="ic" src="file://{U}/assets/icons/{name}.webp">'
def strip(s): return un(re.sub(r"<[^>]+>", "", s)).strip()
def alt_text(li):
    m = re.search(r'<small>바꿔 쓰기</small>(.*?)</span>', li, re.S)
    return un(m.group(1)) if m else ""
def parse(p):
    b = p["body_html"]
    qs = []
    hu = re.search(r'<ul class="ex hear qa">(.*?)\n</ul>', b, re.S).group(1)
    for li in re.findall(r'<li>(.*?)</li>', hu, re.S):
        en = strip(re.search(r'<span class="en">(.*?)</span>', li).group(1))
        ko = strip(re.search(r'<span class="ko">(.*?)</span>', li).group(1))
        snd = strip(re.search(r'<small>실제로 들리는 소리</small>(.*?)</span>', li).group(1))
        reps = [(strip(a), strip(k)) for a, k in re.findall(r'<div class="rep-a"><span class="en">(.*?)</span><span class="ko">(.*?)</span>', li)]
        qs.append((en, ko, snd, reps))
    secs = {}
    for t, body in re.findall(r'<h2>(.*?)</h2>(.*?)(?=<h2>|<a class="pdf-cta")', b, re.S):
        secs[strip(t)] = body
    first = []
    if "내가 먼저 말할 때" in secs:
        for li in re.findall(r'<li>(.*?)</li>', secs["내가 먼저 말할 때"], re.S):
            first.append((strip(re.search(r'<span class="hn">(.*?)</span>', li).group(1)), strip(re.search(r'<span class="en">(.*?)</span>', li).group(1)), strip(re.search(r'<span class="ko">(.*?)</span>', li).group(1))))
    extra_t, extra = None, []
    for t, body in secs.items():
        if t in ("내가 먼저 말할 때", "실제로는 이렇게 흘러가요", "미리 준비해 두면 좋은 것", "쉐도잉 3단계 (5분)") or 'class="ex ans"' not in body: continue
        extra_t = t
        extra = [(strip(re.search(r'<span class="en">(.*?)</span>', li).group(1)), strip(re.search(r'<span class="ko">(.*?)</span>', li).group(1))) for li in re.findall(r'<li>(.*?)</li>', body, re.S)]
    know = re.search(r'<b class="lbl">알아 두기</b>(.*?)</p>', b, re.S)
    prep = re.findall(r'<div><b>(.*?)</b><span>(.*?)</span></div>', secs.get("미리 준비해 두면 좋은 것", ""))
    memo = re.search(r'<b class="lbl">연상법</b>(.*?)</div>', b, re.S)
    return dict(qs=qs, first=first, extra_t=extra_t, extra=extra, know=strip(know.group(1)) if know else "", prep=[(strip(x), strip(y)) for x, y in prep],
                memo=strip(memo.group(1)) if memo else "")
E = html.escape
posts = [json.load(open(f"{U}/content/posts/{pid}.json")) for _, _, pid in SIT]
data = [parse(p) for p in posts]
nq = sum(len(d["qs"]) for d in data)

css = f"""
@font-face{{font-family:P;src:url(file://{U}/fonts/PretendardVariable.ttf);font-weight:100 900}}
@font-face{{font-family:J;src:url(file://{U}/fonts/PlusJakartaSans-Bold.ttf);font-weight:700}}
@page{{size:A4;margin:0}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:P;color:#333D4B;-webkit-print-color-adjust:exact;print-color-adjust:exact;font-size:10pt;line-height:1.5}}
.pg{{width:210mm;height:297mm;padding:13mm 14mm 16mm;position:relative;break-after:page;overflow:hidden}}
.pg:last-child{{break-after:auto}}
.foot{{position:absolute;left:15mm;right:15mm;bottom:8mm;display:flex;justify-content:space-between;font-size:7.5pt;color:#8B95A1}}
.logo{{display:inline-flex;align-items:center;gap:6px;font-weight:800;color:#191F28;font-size:9.5pt}}
.logo i{{width:20px;height:20px;border-radius:6px;background:#2A1A12;color:#F4EEE4;font-style:normal;font-family:J;display:inline-flex;align-items:center;justify-content:center;font-size:11pt;position:relative}}
.logo i::after{{content:"";position:absolute;width:4px;height:4px;border-radius:50%;background:#CDEB5B;right:3px;bottom:4px}}
.lbl{{display:inline-block;background:#CDEB5B;color:#191F28;font-weight:800;font-size:8pt;border-radius:4px;padding:1px 7px}}
h1,h2,h3{{color:#191F28;letter-spacing:-.02em;margin:0}}
/* cover */
.cover{{background:#F9FAFB;display:flex;flex-direction:column}}
.cover h1{{font-size:34pt;line-height:1.25;margin:16mm 0 5mm;font-weight:800}}
.cover h1 b{{background:linear-gradient(transparent 62%,#CDEB5B 62%)}}
.cover .sub{{font-size:13pt;color:#4E5968}}
.cover .ics{{display:flex;justify-content:space-between;margin:12mm 0 9mm}}
.cover .ics .ic{{width:15mm;height:15mm}}
.demo{{background:#fff;border-radius:4mm;padding:6mm;margin-top:8mm}}
.demo small{{font-size:8pt;font-weight:800;color:#8B95A1}}
.demo .row{{display:flex;align-items:center;gap:3mm;margin-top:3mm}}
.demo .who{{font-size:8pt;color:#8B95A1;width:10mm}}
.demo .bub{{background:#F2F4F6;border-radius:4mm;padding:2.5mm 4mm;font-weight:700;color:#191F28;font-size:12pt}}
.demo .bub.me{{background:#191F28;color:#fff;margin-left:auto}}
.demo .hear{{margin:2mm 0 0 13mm;color:#3182F6;font-weight:800;font-size:15pt}}
.demo .hear span{{font-size:8pt;color:#6B9AE8;margin-right:2mm}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm}}
.stats div{{background:#fff;border-radius:4mm;padding:5mm;text-align:center}}
.stats b{{display:block;font-size:22pt;color:#191F28;font-family:J}}
.stats span{{font-size:9pt;color:#6B7684}}
.cover .qrbox{{margin-top:auto;display:flex;gap:5mm;align-items:center;background:#fff;border-radius:4mm;padding:5mm}}
.cover .qrbox b{{display:block;color:#191F28;font-size:11pt}}
.cover .qrbox span{{font-size:9pt;color:#6B7684}}
/* how */
h2.t{{font-size:17pt;margin:0 0 4mm}}
.how{{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin-bottom:9mm}}
.how div{{background:#F9FAFB;border-radius:3mm;padding:4mm}}
.how .ic{{width:9mm;height:9mm}}
.how small{{display:block;font-size:7.5pt;font-weight:800;color:#3182F6;margin-top:2mm}}
.how b{{display:block;color:#191F28;font-size:10.5pt}}
.how span{{font-size:8.5pt;color:#6B7684;line-height:1.45;display:block}}
.plan div.r{{display:grid;grid-template-columns:14mm 1fr 30mm;gap:4mm;align-items:center;padding:3mm 0;border-bottom:1px solid #EEF0F2}}
.plan .d{{background:#F2F4F6;border-radius:3mm;text-align:center;font-family:J;font-size:11pt;color:#191F28;padding:2mm 0}}
.plan .r b{{color:#191F28;font-size:10.5pt}} .plan .r span{{display:block;font-size:8.5pt;color:#8B95A1}}
.plan .chk{{display:flex;gap:2mm;justify-content:flex-end;font-size:8pt;color:#8B95A1;align-items:center}}
.box{{width:4mm;height:4mm;border:1.4px solid #B0B8C1;border-radius:1mm;display:inline-block;flex:none}}
.surv{{margin-top:8mm;background:#191F28;border-radius:4mm;padding:6mm;color:#fff}}
.surv h3{{color:#fff;font-size:12.5pt;margin-bottom:3mm}}
.surv .s{{display:grid;grid-template-columns:1fr 1fr;gap:2.5mm 6mm}}
.surv .s div{{font-size:10pt}} .surv .s div b{{display:block;color:#CDEB5B;font-weight:700}} .surv .s div span{{font-size:8.5pt;color:#B0B8C1}}
/* situation */
.sh{{display:flex;align-items:center;gap:5mm;margin-bottom:4mm}}
.sh .ic{{width:16mm;height:16mm}}
.sh .n{{font-size:8pt;font-weight:800;color:#3182F6;letter-spacing:.04em}}
.sh h2{{font-size:20pt;line-height:1.2}}
.sh p{{margin:1mm 0 0;font-size:9pt;color:#6B7684}}
.sh .q{{margin-left:auto;text-align:center;font-size:7pt;color:#6B7684;line-height:1.3}}
.sh .q svg{{display:block;margin:0 auto 1mm;width:18mm;height:18mm}}
.qa{{border:1px solid #E5E8EB;border-radius:3mm;padding:2.2mm 3.5mm;margin-bottom:1.8mm;break-inside:avoid;display:grid;grid-template-columns:1fr 52mm;gap:1.5mm 4mm}}
.qa .qn{{font-size:7.5pt;font-weight:800;color:#3182F6}}
.qa .en{{font-weight:700;color:#191F28;font-size:10pt;line-height:1.3}}
.qa .ko{{font-size:8.5pt;color:#6B7684}}
.qa .snd{{background:#F2F7FF;border-radius:2mm;padding:1.5mm 3mm;color:#3182F6;font-weight:800;font-size:10pt;line-height:1.3;align-self:start}}
.qa .snd small{{display:block;font-size:6.5pt;color:#6B9AE8;font-weight:700}}
.qa .rp{{grid-column:1/3;border-top:1px dashed #E5E8EB;padding-top:1.5mm;display:flex;flex-wrap:wrap;gap:1mm 6mm;align-items:baseline}}
.qa .rp em{{font-style:normal;font-size:7pt;font-weight:800;background:#CDEB5B;color:#191F28;border-radius:1mm;padding:0 4px}}
.qa .rp b{{color:#191F28;font-size:10pt}} .qa .rp span{{font-size:8.5pt;color:#6B7684}}
.qa .rp .box{{margin-left:auto}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:3mm;margin-top:2.5mm;break-inside:avoid}}
.card{{background:#F9FAFB;border-radius:3mm;padding:3mm 3.5mm}}
.card h3{{font-size:9.5pt;margin-bottom:1.5mm}}
.card .l{{font-size:8.6pt;margin-bottom:.8mm;line-height:1.35}} .card .l b{{color:#191F28}} .card .l span{{color:#6B7684;font-size:8pt}} .card .l em{{font-style:normal;color:#3182F6;font-size:7pt;font-weight:800;margin-right:4px}}
.note{{margin-top:2.2mm;font-size:8.2pt;color:#4E5968;break-inside:avoid}}
.note b{{color:#191F28}}
/* end */
.end .emg{{display:grid;grid-template-columns:repeat(3,1fr);gap:3mm;margin:3mm 0 8mm}}
.end .emg div{{background:#F9FAFB;border-radius:3mm;padding:4mm;text-align:center}} .end .emg b{{display:block;font-family:J;font-size:20pt;color:#191F28}} .end .emg span{{font-size:8.5pt;color:#6B7684}}
.end .kk{{display:flex;gap:6mm;align-items:center;background:#191F28;border-radius:4mm;padding:6mm;color:#B0B8C1;margin-top:8mm}}
.end .kk b{{color:#fff;font-size:13pt;display:block;margin-bottom:1mm}}
.end .kk .qq{{background:#fff;border-radius:2mm;padding:2mm}}
.end .kk .qq svg{{width:24mm;height:24mm;display:block}}
"""
def foot(n): return f'<div class="foot"><span class="logo"><i>C</i>카페인영어 CafeInEnglish</span><span>cafeinenglish.com/travel · {n}</span></div>'
pages = []
# cover
pages.append(f'''<section class="pg cover"><span class="logo"><i>C</i>카페인영어 CafeInEnglish</span>
<h1>여행영어,<br><b>공항부터 호텔까지</b></h1><div class="sub">현지에서 직원이 <b>실제로 하는 말</b>이 어떻게 들리는지,<br>그리고 바로 꺼내 쓰는 대답까지 10가지 상황으로 정리했어요.</div>
<div class="ics">{"".join(ic(i) for _, i, _ in SIT)}</div>
<div class="stats"><div><b>10</b><span>상황</span></div><div><b>{nq}</b><span>직원 질문 + 들리는 소리</span></div><div><b>7</b><span>일 플랜</span></div></div>
<div class="demo"><small>이런 걸 배워요</small><div class="row"><span class="who">직원</span><span class="bub">What brings you here?</span></div>
<div class="hear"><span>이렇게 들려요</span>왓 브링쥬 히어?</div><div class="row"><span class="bub me">I'm here on vacation.</span></div>
<div style="text-align:right;font-size:8.5pt;color:#6B7684;margin-top:1.5mm">여행 왔어요</div></div>
<div class="qrbox">{qr(DOM + "/travel/", 3)}<div><b>원어민 발음은 QR로</b><span>페이지마다 있는 QR을 찍으면 그 상황의 원어민 음성을 바로 들을 수 있어요.<br>스피커를 한 번 더 누르면 느린 속도로 들려요.</span></div></div>
</section>''')
# how + plan
rows = ""
for d, t, ids in PLAN:
    sub = " · ".join(f"{SIT[i][0]} 질문 {len(data[i]['qs'])}개" for i in ids)
    if d == "D-7": sub += " · 살아남는 문장 6개"
    rows += f'<div class="r"><div class="d">{d}</div><div><b>{E(t)}</b><span>{E(sub)} · 10~15분</span></div><div class="chk"><span class="box"></span>끝냈어요</div></div>'
surv = [("Sorry, could you say that again?", "죄송한데, 다시 말씀해 주시겠어요?"), ("Could you speak a little more slowly?", "조금만 천천히 말씀해 주시겠어요?"),
        ("Excuse me.", "실례합니다 (부를 때 · 지나갈 때)"), ("Can I get ~, please?", "~ 주시겠어요? (무엇이든 부탁할 때)"),
        ("Where's the restroom?", "화장실이 어디예요?"), ("I need help, please.", "도와주세요.")]
pages.append(f'''<section class="pg"><h2 class="t">이렇게 쓰면 돼요</h2>
<div class="how"><div>{ic("page")}<small>STEP 1</small><b>출력하거나 저장</b><span>A4로 뽑거나 폰에 저장해 공항에서 꺼내 봐요</span></div>
<div>{ic("mobile-phone")}<small>STEP 2</small><b>QR로 듣기</b><span>상황마다 QR을 찍어 원어민 발음을 들어요</span></div>
<div>{ic("speech-balloon")}<small>STEP 3</small><b>주고받기</b><span>질문을 듣고 바로 대답을 소리 내어 말해요</span></div>
<div>{ic("check")}<small>STEP 4</small><b>써 본 문장 체크</b><span>여행 중에 실제로 써 본 대답에 표시해요</span></div></div>
<h2 class="t">출발 전 7일 플랜</h2><div class="plan">{rows}</div>
<div class="surv"><h3>어떤 상황에서든 살아남는 6문장</h3><div class="s">{"".join(f"<div><b>{E(a)}</b><span>{E(b)}</span></div>" for a, b in surv)}</div></div>
{foot(2)}</section>''')
for k, ((name, icn, pid), p, d) in enumerate(zip(SIT, posts, data)):
    qa = ""
    for i, (en, ko, snd, reps) in enumerate(d["qs"]):
        rp = "".join(f'<b>{E(a)}</b><span>{E(b)}</span>' for a, b in reps)
        qa += (f'<div class="qa"><div><div class="qn">Q{i + 1}</div><div class="en">{E(en)}</div><div class="ko">{E(ko)}</div></div>'
               f'<div class="snd"><small>실제로 들리는 소리</small>{E(snd)}</div>'
               + (f'<div class="rp"><em>대답</em>{rp}<span class="box" title="써 봤어요"></span></div>' if reps else "") + '</div>')
    left = ""
    if d["first"]:
        left = '<div class="card"><h3>내가 먼저 말할 때</h3>' + "".join(f'<div class="l"><b>{E(a)}</b> <span>{E(b)}</span></div>' for _, a, b in d["first"]) + '</div>'
    right = ""
    if d["extra"]:
        right = f'<div class="card"><h3>{E(d["extra_t"])}</h3>' + "".join(f'<div class="l"><b>{E(a)}</b> <span>{E(b)}</span></div>' for a, b in d["extra"]) + '</div>'
    if not left and d["prep"]:
        left = '<div class="card"><h3>미리 준비해 두면 좋은 것</h3>' + "".join(f'<div class="l"><b>{E(a)}</b> <span>{E(b)}</span></div>' for a, b in d["prep"]) + '</div>'
    note = f'<div class="note"><span class="lbl">알아 두기</span> {E(d["know"])}</div>' if d["know"] else ""
    memo = f'<div class="note"><span class="lbl">연상법</span> {E(d["memo"])}</div>' if d["memo"] else ""
    pages.append(f'''<section class="pg"><div class="sh">{ic(icn)}<div><div class="n">SITUATION {k + 1:02d}</div><h2>{E(name)}</h2><p>{E(p["lead"])}</p></div>
<div class="q">{qr(DOM + "/p/" + pid + "/", 2)}QR로 발음 듣기</div></div>
<div class="body">{qa}<div class="two">{left}{right}</div>{memo}{note}</div>{foot(k + 3)}</section>''')
pages.append(f'''<section class="pg end"><h2 class="t">급할 때 전화번호</h2>
<div class="emg"><div><b>911</b><span>미국 · 캐나다</span></div><div><b>999</b><span>영국</span></div><div><b>112</b><span>유럽 대부분</span></div></div>
<div class="note">여권을 잃어버렸다면 가까운 <b>한국 대사관·영사관</b>에 바로 연락해요. 경찰 확인서(police report)가 있으면 재발급과 보험 처리가 빨라져요.</div>
<h2 class="t" style="margin-top:10mm">여행 끝나고도 이어가고 싶다면</h2>
<div class="kk"><div class="qq">{qr("https://open.kakao.com/o/gxsl5iQi", 3)}</div><div><b>매일 아침 7시, 표현 하나씩 카톡으로</b>여행에서 들었던 그 영어, 잊기 전에 하루 한 문장씩 이어가요. 무료예요.<br>QR을 찍으면 카카오톡 오픈채팅으로 연결돼요.</div></div>
<div class="kk" style="background:#F9FAFB;color:#6B7684"><div class="qq">{qr(DOM, 3)}</div><div><b style="color:#191F28">cafeinenglish.com</b>영화·인터뷰 속 표현, 헷갈리는 표현, 퀴즈와 오답노트까지.<br>제가 공부하려고 만든 걸 같이 쓰고 있어요.</div></div>
{foot(len(SIT) + 3)}</section>''')
open(OUT, "w").write(f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>{css}</style></head><body>{"".join(pages)}</body></html>')
print("pages", len(pages), "qs", nq)

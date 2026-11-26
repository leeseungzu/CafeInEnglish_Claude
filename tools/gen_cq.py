#!/usr/bin/env python3
"""여행 시리즈 글의 '질문 N개' 파트를 세관 글 형식(cq)으로 바꿔요 (2026-11-26)
python3 tools/gen_cq.py  → content/posts/<id>.json 의 질문 파트·놓쳤다면 파트를 교체"""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
E = lambda s: s.replace("'", "&#x27;")

def li(en, ko, snd=None, i=None, hidden=False, who=None):
    a = (f' data-i="{i}"' if i else '') + (' hidden' if hidden else '')
    w = f'<span class="who{" me" if who == "나" else ""}">{who}</span>' if who else ''
    s = f'<span class="snd">{snd}</span>' if snd else ''
    return f'<li{a}>{w}<span class="en">{E(en)}</span>{s}<span class="ko">{ko}</span></li>'

def block(bl):
    kind = bl[0]
    if kind == "list":      # ("list", 라벨 or None, [(en, ko)])
        lab = f'<span class="cq-lbl lime">{bl[1]}</span>' if bl[1] else ''
        return lab + '<ul class="ex ans cq-a">' + "".join(li(en, ko) for en, ko in bl[2]) + '</ul>'
    if kind == "chips":     # ("chips", 칩 안내, [(key, 칩 한글, 칩 영어, en, ko)])
        items = bl[2]; on = items[0][0]
        bs = "".join(f'<button type="button" data-i="{k}" aria-pressed="{"true" if k == on else "false"}">{ck}<i>{ce}</i></button>' for k, ck, ce, _, _ in items)
        return (f'<div class="cq-chips"><small>{bl[1]}</small>{bs}</div><ul class="ex ans cq-a">'
                + "".join(li(en, ko, i=k, hidden=(k != on)) for k, _, _, en, ko in items) + '</ul>')
    if kind == "more":      # ("more", 라벨, [(en, ko)]) 파란 라벨 + 대답 목록
        return f'<span class="cq-lbl">{bl[1]}</span><ul class="ex ans cq-a">' + "".join(li(en, ko) for en, ko in bl[2]) + '</ul>'
    raise ValueError(kind)

def answer(ans):
    if ans[0] == "pick":    # ("pick", [(버튼, key, [blocks])], 기본 key)
        opts, on = ans[1], ans[2]
        h = '<span class="cq-lbl lime">내 상황은?</span><div class="cq-btns">' + "".join(
            f'<button type="button" data-p="{k}" aria-pressed="{"true" if k == on else "false"}">{lab}</button>' for lab, k, _ in opts) + '</div>'
        for lab, k, bls in opts:
            h += f'<div class="cq-pane" data-p="{k}"{"" if k == on else " hidden"}>' + "".join(block(b) for b in bls) + '</div>'
        return h
    if ans[0] == "chips":
        return '<span class="cq-lbl lime">이렇게 대답해요</span>' + block(ans)
    return block(("list", "이렇게 대답해요", ans[1]))

def card(n, q):
    h = (f'<section class="cq"><div class="cq-h"><span class="hn">Q{n}</span><span class="cq-k">{q["k"]}</span></div>'
         f'<h3>{E(q["h3"])}</h3><span class="cq-lbl">이렇게도 물어봐요</span><ul class="ex cq-v">'
         + "".join(li(en, ko, snd) for en, snd, ko in q["vars"]) + '</ul>')
    if q.get("tip"):
        h += f'<p class="cq-tip"><b>귀에 걸 단어</b>{E(q["tip"])}</p>'
    h += '<hr>' + answer(q["ans"])
    if q.get("next"):
        h += '<div class="cq-next"><span class="cq-lbl">이어서 이렇게 물어요</span><ul class="ex cq-n">' + "".join(li(en, ko, who=w) for w, en, ko in q["next"]) + '</ul></div>'
    if q.get("note"):
        h += f'<p class="cq-tip"><b>참고</b>{E(q["note"])}</p>'
    return h + '</section>'

COMMON = " 문장을 누르면 원어민 발음, 한 번 더 누르면 느린 속도로 들려요."

def section(d):
    ins = "".join(f'<div>{a}<small>{b}</small></div>' for a, b in d["ins"])
    h = (f'<h2>{d["h2"]}</h2><p class="h-sub">{d["sub"]}{COMMON}</p>'
         f'<div class="cq-wrap"><div class="cq-ins"><b>{d["ins_t"]}</b><div class="cq-g">{ins}</div><p class="cq-insp">{d["ins_p"]}</p></div>'
         '<div class="cq-mode"><div><b>듣기 먼저 모드</b><small>문장을 가리고 소리만 먼저 들어요. 한 번 더 누르면 보여요.</small></div>'
         '<button type="button" class="cq-sw" aria-pressed="false" aria-label="듣기 먼저 모드"></button></div>')
    h += "".join(card(i + 1, q) for i, q in enumerate(d["qs"]))
    h += (f'<div class="cq-sos"><b>{d["sos_t"]}</b><p>{d["sos_p"]}</p><ul class="ex cq-s">'
          + "".join(li(en, ko) for en, ko in d["sos"]) + '</ul></div></div>')
    return h

def apply(pid, d):
    f = ROOT / "content" / "posts" / f"{pid}.json"
    p = json.loads(f.read_text("utf-8")); b = p["body_html"]
    if 'class="cq-wrap"' in b:
        print("· 이미 적용됨", pid); return
    # 질문 파트: 첫 h2(…질문/대답/말 N개)부터 ul.hear.qa + 연상법 memo 까지
    m = re.search(r'<h2>[^<]*</h2>\s*(<p class="h-sub">.*?</p>\s*)?<ul class="ex hear qa">.*?</ul>\s*(<div class="memo">.*?</div>)?\s*', b, re.S)
    assert m and m.start() == b.index("<h2>"), pid
    b = b[:m.start()] + section(d) + "\n" + b[m.end():]
    if d.get("drop"):
        mm = re.search(r'<h2>' + re.escape(d["drop"]) + r'</h2>.*?(?=<h2>)', b, re.S); assert mm, pid
        b = b.replace(mm.group(0), "")
    p["body_html"] = b; p["updated"] = "2026-11-26"
    f.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("✓", pid, b.count('<span class="hn">Q'), "문항")

D = {}

D["immigration"] = dict(
 h2="입국심사 영어 질문, 어떻게 물어도 알아듣기",
 sub="심사관이 확인하는 건 왜 왔는지, 얼마나 어디서 머무는지, 언제 돌아가는지예요. 질문의 여러 모양을 들어 두고, 대답은 내 여행에 맞게 고르면 돼요.",
 ins_t="심사관이 확인하는 것", ins=[("방문 목적", "purpose · 여행, 출장, 가족"), ("기간·숙소", "how long · where"), ("돌아가는 표", "return ticket")],
 ins_p="purpose, how long, where, return 중 한 단어만 들려도 무슨 질문인지 알 수 있어요.",
 qs=[
  dict(k="방문 목적", h3="입국심사 방문 목적 영어, What's the purpose of your visit?",
   vars=[("What's the purpose of your visit?", "왓츠더 퍼퍼서뷰어 비짓?", "방문 목적이 뭐예요?"),
         ("What brings you here?", "왓 브링쥬 히어?", "무슨 일로 오셨어요?"),
         ("Business or pleasure?", "비즈니스어 플레져?", "출장이에요, 여행이에요?")],
   tip="purpose, brings, business 중 하나가 들리면 방문 목적 질문이에요. brings you는 '브링쥬'로 붙어요.",
   ans=("chips", "왜 왔나요?", [("vac", "여행", "vacation", "I'm here on vacation.", "여행 왔어요."),
        ("biz", "출장", "business", "I'm here on business.", "출장 왔어요."),
        ("fam", "가족 방문", "visit family", "I'm here to visit family.", "가족 보러 왔어요."),
        ("conf", "학회", "conference", "I'm here for a conference.", "학회 때문에 왔어요.")]),
   next=[("심사관", "Who are you visiting?", "누구를 만나러 오셨어요?"), ("나", "My sister. She lives in LA.", "여동생이요. LA에 살아요.")]),
  dict(k="머무는 기간", h3="How long are you staying, 얼마나 머무는지 물을 때",
   vars=[("How long are you staying?", "하울롱아유 스테잉?", "얼마나 머무세요?"),
         ("How long will you be here?", "하울롱 윌유비 히어?", "여기 얼마나 계실 거예요?"),
         ("When are you leaving?", "웬아유 리빙?", "언제 떠나세요?")],
   tip="How long이 한 덩어리로 붙어서 들려요. long이나 leaving이 들리면 기간 질문이에요.",
   ans=("chips", "얼마나 머무나요?", [("w1", "일주일", "a week", "For a week.", "일주일이요."),
        ("d5", "5일", "five days", "Five days.", "5일이요."),
        ("w2", "2주", "two weeks", "For two weeks.", "2주요.")]),
   next=[("심사관", "Where are you going after that?", "그다음엔 어디로 가세요?"), ("나", "Back to Korea.", "한국으로 돌아가요.")]),
  dict(k="숙소", h3="Where are you staying, 숙소를 물을 때",
   vars=[("Where are you staying?", "웨어라유 스테잉?", "어디서 지내세요?"),
         ("Where will you be staying?", "웨어 윌유비 스테잉?", "어디서 지내실 거예요?"),
         ("What's the address?", "왓츠디 어드레스?", "주소가 어떻게 돼요?")],
   tip="where의 r이 are로 이어져 '웨어라유'가 돼요. 숙소 질문은 거의 이 모양이에요.",
   ans=("pick", [("호텔", "hotel", [("list", None, [("At a hotel in downtown Seattle.", "시애틀 시내 호텔이요."), ("At the Hilton near the airport.", "공항 근처 힐튼이요.")])]),
                 ("지인 집", "friend", [("list", None, [("At my friend's place.", "친구 집이요."), ("Here's the address.", "여기 주소예요.")])])], "hotel"),
   note="숙소 이름과 주소를 폰에 적어 두면 Here's the address. 한마디로 끝나요."),
  dict(k="처음 방문", h3="Is this your first time here, 처음 왔는지 물을 때",
   vars=[("Is this your first time here?", "이즈디셔 퍼스타임 히어?", "여기 처음 오셨어요?"),
         ("Have you been here before?", "해뷰빈 히어 비포어?", "여기 와 본 적 있어요?"),
         ("First time in the US?", "퍼스타임 인더 유에스?", "미국 처음이세요?")],
   tip="this your가 '디셔'로 붙고, first의 t는 거의 안 들려요. first, before가 들리면 이 질문이에요.",
   ans=("pick", [("처음이에요", "yes", [("list", None, [("Yes, it's my first time.", "네, 처음이에요.")])]),
                 ("와 봤어요", "no", [("list", None, [("No, I've been here before.", "아니요, 와 본 적 있어요."), ("I came here two years ago.", "2년 전에 왔었어요.")])])], "yes")),
  dict(k="돌아가는 표", h3="Do you have a return ticket, 돌아가는 항공권을 물을 때",
   vars=[("Do you have a return ticket?", "두유 해버 리턴 티킷?", "돌아가는 항공권 있어요?"),
         ("When do you fly back?", "웬 두유 플라이 백?", "언제 돌아가세요?"),
         ("Can I see your return ticket?", "캐나이 씨유어 리턴 티킷?", "돌아가는 항공권 보여 주시겠어요?")],
   tip="return이나 back이 들리면 돌아가는 표 질문이에요. have a는 '해버'로 붙어요.",
   ans=("list", [("Here's my return ticket.", "여기 돌아가는 항공권이요."), ("I fly back on the 15th.", "15일에 돌아가요.")]),
   note="돌아가는 항공권 화면을 미리 캡처해 두면 바로 보여 줄 수 있어요.")],
 sos_t="못 알아들었을 때, 이 세 문장", sos_p="당황해서 아무 말이나 하는 것보다 다시 물어보는 게 훨씬 좋아요.",
 sos=[("Sorry, could you repeat the question?", "죄송한데, 질문 다시 한번 말씀해 주시겠어요?"), ("Could you speak more slowly?", "조금 천천히 말씀해 주시겠어요?"), ("My English isn't very good.", "제가 영어를 잘 못해요.")],
 drop="심사관 질문을 놓쳤다면")

D["in-flight"] = dict(
 h2="기내 영어 질문, 어떻게 물어도 알아듣기",
 sub="승무원 질문은 식사, 음료, 좌석, 정리 네 가지가 거의 전부예요. 질문의 여러 모양을 들어 두고, 대답은 내 상황에 맞게 고르면 돼요.",
 ins_t="승무원이 묻는 것", ins=[("기내식", "chicken or beef"), ("음료", "anything to drink"), ("좌석·정리", "seat up · done")],
 ins_p="chicken, drink, seat, done 중 한 단어만 들려도 무슨 말인지 알 수 있어요.",
 qs=[
  dict(k="기내식", h3="기내식 영어, Chicken or beef?",
   vars=[("Chicken or beef?", "치킨어 비프?", "닭고기, 소고기 중 뭐로 하시겠어요?"),
         ("Would you like chicken or beef?", "우쥴라익 치킨어 비프?", "닭고기랑 소고기 중 뭐로 드릴까요?"),
         ("We have chicken with rice or beef with noodles.", "위해브 치킨 위드라이스 어 비프 위드누들즈", "닭고기 덮밥이랑 소고기 국수가 있어요.")],
   tip="or는 힘을 빼서 '어'처럼 짧게 지나가요. 메뉴 이름만 잡으면 돼요.",
   ans=("chips", "뭐로 할까요?", [("ch", "닭고기", "chicken", "Chicken, please.", "닭고기로 주세요."),
        ("bf", "소고기", "beef", "Beef, please.", "소고기로 주세요."),
        ("no", "안 먹어요", "skip", "I'll skip the meal, thanks.", "식사는 건너뛸게요.")]),
   next=[("승무원", "Sorry, we're out of beef.", "죄송해요, 소고기가 다 떨어졌어요."), ("나", "That's okay. Chicken is fine.", "괜찮아요. 닭고기도 좋아요.")]),
  dict(k="음료", h3="기내 음료 영어, Anything to drink?",
   vars=[("Can I get you anything to drink?", "캐나이 겟츄 에니띵 터 드링크?", "음료 뭐 드릴까요?"),
         ("Anything to drink?", "에니띵 터 드링크?", "음료 드릴까요?"),
         ("Coffee or tea?", "커피어 티?", "커피, 차 중에 뭐로 드릴까요?")],
   tip="get you가 '겟츄'로 붙어요. drink가 들리면 음료 질문이에요.",
   ans=("pick", [("주세요", "yes", [("chips", "뭐로 할까요?", [("w", "물", "water", "Can I get some water, please?", "물 좀 주시겠어요?"),
                                     ("oj", "오렌지 주스", "orange juice", "Can I get some orange juice, please?", "오렌지 주스 좀 주시겠어요?"),
                                     ("cf", "커피", "coffee", "Can I get some coffee, please?", "커피 좀 주시겠어요?")])]),
                 ("괜찮아요", "no", [("list", None, [("I'm good, thanks.", "괜찮아요, 감사해요.")])])], "yes"),
   next=[("승무원", "Ice?", "얼음 넣을까요?"), ("나", "No ice, please.", "얼음은 빼 주세요.")]),
  dict(k="좌석", h3="Could you put your seat up, 좌석·벨트 안내",
   vars=[("Could you put your seat up, please?", "쿠쥬 푸츄어 씻업 플리즈?", "좌석 등받이 좀 세워 주시겠어요?"),
         ("Please fasten your seatbelt.", "플리즈 패쓴 유어 씻벨트", "안전벨트를 매 주세요."),
         ("Could you open your window shade?", "쿠쥬 오프뉴어 윈도우 셰이드?", "창문 덮개 좀 올려 주시겠어요?")],
   tip="Could you가 '쿠쥬'로 붙어요. 식사 시간과 이착륙 전에 자주 들어요. fasten의 t는 소리 나지 않아요.",
   ans=("list", [("Oh, sorry. Sure.", "아, 죄송해요. 네.")])),
  dict(k="정리", h3="Are you done with that, 다 먹었는지 물을 때",
   vars=[("Are you done with that?", "아유 던 위댓?", "다 드셨어요? (치워 드릴까요?)"),
         ("Can I take that for you?", "캐나이 테익댓 퍼유?", "치워 드릴까요?"),
         ("Finished?", "피니쉬트?", "다 드셨어요?")],
   tip="done, take, finished 중 하나가 들리면 그릇을 치워 준다는 말이에요.",
   ans=("pick", [("다 먹었어요", "yes", [("list", None, [("Yes, I'm done. Thank you.", "네, 다 먹었어요. 감사해요.")])]),
                 ("아직이에요", "no", [("list", None, [("Not yet.", "아직이요.")])])], "yes"))],
 sos_t="엔진 소리에 묻혔을 때, 이 세 문장", sos_p="기내는 시끄러워서 못 듣는 게 당연해요. 다시 물어보면 천천히 알려 줘요.",
 sos=[("Sorry, what are the options?", "죄송한데, 뭐 뭐 있어요?"), ("Sorry, I didn't catch that.", "죄송해요, 못 들었어요."), ("Could you say that again?", "다시 말씀해 주시겠어요?")],
 drop="엔진 소리에 묻혔다면")

D["transportation"] = dict(
 h2="택시·버스 영어 질문, 어떻게 물어도 알아듣기",
 sub="기사님이 확인하는 건 어디로 가는지, 어떻게 낼지, 어디서 갈아탈지예요. 질문의 여러 모양을 들어 두고, 대답은 내 상황에 맞게 고르면 돼요.",
 ins_t="기사님·직원이 묻는 것", ins=[("목적지", "where to"), ("결제·영수증", "cash or card · receipt"), ("갈아타기", "transfer · get off")],
 ins_p="where, card, receipt, transfer 중 한 단어만 들려도 무슨 말인지 알 수 있어요.",
 qs=[
  dict(k="목적지", h3="Where to 뜻, 택시에서 목적지를 물을 때",
   vars=[("Where to?", "웨어 투?", "어디로 가세요?"),
         ("Where are you headed?", "웨어라유 헤디드?", "어디로 가세요?"),
         ("Where would you like to go?", "웨어 우쥴라익 터 고?", "어디로 모실까요?")],
   tip="Where to?는 Where are you going to?를 줄인 말이에요. headed도 '가는 중'이라는 뜻이에요.",
   ans=("chips", "어디로 가나요?", [("ad", "주소 보여 주기", "this address", "To this address, please.", "이 주소로 가 주세요."),
        ("ap", "공항", "airport", "To the airport, please.", "공항으로 가 주세요."),
        ("ht", "호텔", "hotel", "To the Hilton Downtown, please.", "힐튼 다운타운으로 가 주세요.")]),
   next=[("기사", "Which terminal?", "몇 터미널이요?"), ("나", "Terminal 2, please.", "2터미널이요.")]),
  dict(k="결제·영수증", h3="Cash or card, 결제와 영수증을 물을 때",
   vars=[("Cash or card?", "캐시어 카드?", "현금이에요, 카드예요?"),
         ("Do you want a receipt?", "듀워너 리씻?", "영수증 드릴까요?"),
         ("Do you need a receipt?", "듀니러 리씻?", "영수증 필요하세요?")],
   tip="receipt의 p는 소리 나지 않아서 '리씻'으로 들려요. want a는 '워너', need a는 '니러'로 붙어요.",
   ans=("list", [("Card, please.", "카드로 할게요."), ("Yes, please.", "네, 주세요. (영수증)"), ("No, thanks.", "괜찮아요.")])),
  dict(k="버스 요금", h3="Exact change only, 버스에서 듣는 말",
   vars=[("Exact change only.", "이그잭 체인지 온리", "잔돈은 안 거슬러 드려요. (딱 맞게 내세요)"),
         ("Do you have exact change?", "두유 해브 이그잭 체인지?", "딱 맞는 잔돈 있어요?"),
         ("Tap your card here.", "탭 유어 카드 히어", "카드를 여기 대세요.")],
   tip="exact의 t가 거의 안 들려서 '이그잭'처럼 들려요. change가 들리면 잔돈 이야기예요.",
   ans=("list", [("Oh, do you take cards?", "아, 카드 되나요?"), ("Does this bus go to Union Station?", "이 버스 유니언역 가요?")])),
  dict(k="갈아타기", h3="transfer 뜻, 갈아타고 내리는 곳을 들을 때",
   vars=[("You need to transfer at Union Station.", "유 니러 트랜스퍼랫 유니언 스테이션", "유니언역에서 갈아타셔야 해요."),
         ("Change at Union Station.", "체인쟷 유니언 스테이션", "유니언역에서 갈아타세요."),
         ("Get off at the next stop.", "게로프랫 더 넥스탑", "다음 정류장에서 내리세요.")],
   tip="transfer, change는 '갈아타다', get off는 '내리다'예요. need to는 '니러'로 붙어요.",
   ans=("list", [("Got it. Which line?", "알겠어요. 몇 호선이요?"), ("Could you tell me when to get off?", "내릴 때 알려 주시겠어요?")]))],
 sos_t="못 알아들었을 때, 이 세 문장", sos_p="역·정류장 이름은 놓치기 쉬워요. 폰 지도를 보여 주며 물어봐도 돼요.",
 sos=[("Sorry, could you say that more slowly?", "죄송한데, 조금만 천천히 말씀해 주시겠어요?"), ("Is this the right stop?", "여기 맞는 정류장이에요?"), ("Could you write it down?", "적어 주시겠어요?")],
 drop="기사님 말을 놓쳤다면")

D["hotel-check-in"] = dict(
 h2="호텔 체크인 영어 질문, 어떻게 물어도 알아듣기",
 sub="프런트에서 확인하는 건 예약, 신분증과 카드, 키예요. 질문의 여러 모양을 들어 두고, 대답은 내 상황에 맞게 고르면 돼요.",
 ins_t="프런트 직원이 확인하는 것", ins=[("예약·이름", "reservation · name"), ("신분증·카드", "ID · deposit"), ("키", "how many keys")],
 ins_p="reservation, ID, keys 중 한 단어만 들려도 무슨 질문인지 알 수 있어요.",
 qs=[
  dict(k="예약", h3="Do you have a reservation, 예약을 물을 때",
   vars=[("Do you have a reservation?", "듀해버 레저베이션?", "예약하셨어요?"),
         ("Can I get a name for the reservation?", "캐나이 게러 네임 퍼더 레저베이션?", "예약자 성함이 어떻게 되세요?"),
         ("What's the last name?", "왓츠더 래스네임?", "성이 어떻게 되세요?")],
   tip="have a는 '해버', get a는 '게러'로 붙어요. reservation, name이 들리면 예약 확인이에요.",
   ans=("pick", [("예약했어요", "yes", [("list", None, [("I have a reservation under Kim.", "김(Kim) 이름으로 예약했어요."), ("I booked online.", "온라인으로 예약했어요.")])]),
                 ("안 했어요", "no", [("list", None, [("No. Do you have any rooms for tonight?", "아니요. 오늘 밤 방 있어요?")])])], "yes"),
   next=[("직원", "Could you spell that for me?", "철자 불러 주시겠어요?"), ("나", "Sure. K, I, M.", "네. 케이, 아이, 엠이요.")]),
  dict(k="신분증·보증금", h3="ID and a credit card, 신분증과 보증금을 물을 때",
   vars=[("Can I see your ID and a credit card?", "캐나이 씨유어 아이디 애너 크레딧 카드?", "신분증이랑 신용카드 보여 주시겠어요?"),
         ("I'll need a card for incidentals.", "아일 니러 카드 퍼 인시덴털즈", "부대 비용용 카드가 필요해요."),
         ("There's a 100-dollar deposit.", "데어저 헌드레드 달러 디파짓", "보증금이 100달러 있어요.")],
   tip="incidentals, deposit이 들리면 보증금 이야기예요. 쓰지 않은 금액은 체크아웃 뒤에 풀려요.",
   ans=("list", [("Here's my passport.", "여기 여권이요."), ("Is the deposit refundable?", "보증금은 돌려받는 거죠?")])),
  dict(k="키", h3="How many keys, 키를 몇 개 줄지 물을 때",
   vars=[("How many keys would you like?", "하우메니 키즈 우쥴라익?", "키 몇 개 드릴까요?"),
         ("One key or two?", "원 키 오어 투?", "키 하나 드릴까요, 두 개 드릴까요?"),
         ("How many keys?", "하우메니 키즈?", "키 몇 개요?")],
   tip="would you like가 '우쥴라익'으로 붙어요. keys만 들리면 돼요.",
   ans=("chips", "몇 개 필요해요?", [("2", "두 개", "two keys", "Two keys, please.", "키 두 개 주세요."),
        ("1", "하나", "just one", "Just one, please.", "하나만 주세요.")]),
   next=[("직원", "Breakfast is from 7 to 10.", "조식은 7시부터 10시까지예요."), ("나", "Where is breakfast served?", "조식은 어디서 먹어요?")])],
 sos_t="못 알아들었을 때, 이 세 문장", sos_p="숫자와 시간은 놓치기 쉬워요. 적어 달라고 해도 괜찮아요.",
 sos=[("Sorry, could you say that again?", "죄송한데, 다시 말씀해 주시겠어요?"), ("Could you write that down?", "적어 주시겠어요?"), ("Could you speak more slowly?", "조금 천천히 말씀해 주시겠어요?")])

D["asking-directions"] = dict(
 h2="길 안내 영어, 어떻게 말해도 알아듣기",
 sub="길 안내는 직진, 방향, 위치, 거리 네 가지로 나와요. 대답의 여러 모양을 들어 두고, 들은 걸 짧게 되말해서 확인하면 돼요.",
 ins_t="길 안내에서 나오는 것", ins=[("직진", "straight · down"), ("방향·위치", "left · right · across"), ("거리", "minute walk · far")],
 ins_p="straight, left, right, minute 중 한 단어만 들려도 어디로 가라는지 알 수 있어요.",
 qs=[
  dict(k="직진", h3="Go straight, 직진하라고 할 때",
   vars=[("Go straight for two blocks.", "고 스트레잇 퍼 투 블럭스", "두 블록 직진하세요."),
         ("Keep going straight.", "킵고잉 스트레잇", "계속 직진하세요."),
         ("Go down this street.", "고 다운 디스 스트릿", "이 길 따라 쭉 가세요.")],
   tip="for는 '퍼'로 약해지고 straight의 t는 짧게 끊겨요. down this street도 '쭉 가라'는 뜻이에요.",
   ans=("list", [("Straight for two blocks. Got it.", "두 블록 직진이요. 알겠어요.")])),
  dict(k="방향", h3="Take a left 뜻, 방향을 알려 줄 때",
   vars=[("Take a left at the light.", "테이커 레프탯더 라잇", "신호등에서 왼쪽으로 가세요."),
         ("Turn right at the corner.", "턴 라잇앳더 코너", "모퉁이에서 오른쪽으로 도세요."),
         ("Make a right after the bank.", "메이커 라잇 애프터더 뱅크", "은행 지나서 오른쪽으로 가세요.")],
   tip="take a, make a, turn 뒤에 left나 right가 오면 '그쪽으로 꺾으세요'예요.",
   ans=("list", [("Left at the light, right?", "신호등에서 왼쪽, 맞죠?")])),
  dict(k="위치", h3="It's on your right, 위치를 알려 줄 때",
   vars=[("It's on your right.", "잇쏜뉴어 라잇", "오른쪽에 있어요."),
         ("It's across the street.", "잇쳐크로스 더 스트릿", "길 건너편에 있어요."),
         ("You can't miss it.", "유캔 미씻", "금방 찾으실 거예요.")],
   tip="on your right는 '있어요', take a right는 '가세요'예요. can't의 t는 거의 안 들려요.",
   ans=("list", [("On my right. Thanks!", "오른쪽이요. 감사해요!"), ("Great, thank you so much!", "좋아요, 정말 감사해요!")])),
  dict(k="거리", h3="ten-minute walk, 얼마나 먼지 알려 줄 때",
   vars=[("It's about a ten-minute walk.", "잇써바우러 텐미닛 웍", "걸어서 10분쯤이에요."),
         ("It's a bit far.", "잇처 빗 파", "좀 멀어요."),
         ("It's just around the corner.", "잇츠 저스터라운더 코너", "바로 모퉁이 돌면 있어요.")],
   tip="about a가 '어바우러'로 붙어요. walk의 l은 소리 나지 않아요.",
   ans=("pick", [("걸어갈게요", "walk", [("list", None, [("Ten minutes? Great.", "10분이요? 좋네요.")])]),
                 ("멀면요", "far", [("list", None, [("Should I take a taxi?", "택시 타는 게 나을까요?"), ("Is there a bus?", "버스 있어요?")])])], "walk"))],
 sos_t="대답이 빨라서 놓쳤을 때, 이 세 문장", sos_p="들은 걸 되말하거나 손으로 가리키며 물어보면 바로 확인돼요.",
 sos=[("Sorry, left or right?", "죄송한데, 왼쪽이요, 오른쪽이요?"), ("Could you show me on the map?", "지도에서 보여 주시겠어요?"), ("This way?", "이쪽이요?")],
 drop="대답이 빨라서 놓쳤다면")

D["travel-cafe"] = dict(
 h2="카페 영어 질문, 어떻게 물어도 알아듣기",
 sub="카페 직원이 확인하는 건 메뉴, 사이즈, 매장·포장, 이름이에요. 질문의 여러 모양을 들어 두고, 대답은 내 주문에 맞게 고르면 돼요.",
 ins_t="카페 직원이 묻는 것", ins=[("메뉴·사이즈", "what can I get · size"), ("매장·포장", "for here or to go"), ("이름", "name for the order")],
 ins_p="get, size, here, name 중 한 단어만 들려도 무슨 질문인지 알 수 있어요.",
 qs=[
  dict(k="주문", h3="What can I get for you, 주문을 받을 때",
   vars=[("What can I get for you?", "왓캐나이 겟퍼유?", "뭐 드릴까요?"),
         ("What can I get started for you?", "왓캐나이 겟 스타릿 퍼유?", "뭐로 준비해 드릴까요?"),
         ("What would you like?", "왓 우쥴라익?", "뭐 드시겠어요?")],
   tip="can I가 '캐나이'로 붙고, for는 '퍼'로 약해져요. 주문은 Can I get ~? 하나면 돼요.",
   ans=("chips", "뭐 마실까요?", [("lt", "라떼", "latte", "Can I get a medium latte?", "라떼 미디엄 하나 주세요."),
        ("ia", "아이스 아메리카노", "iced Americano", "Can I get an iced Americano?", "아이스 아메리카노 하나 주세요."),
        ("dc", "드립 커피", "coffee", "Can I get a small coffee?", "드립 커피 작은 거 하나 주세요.")]),
   next=[("직원", "Hot or iced?", "따뜻한 거요, 아이스요?"), ("나", "Iced, please.", "아이스로 주세요.")]),
  dict(k="사이즈", h3="What size would you like, 사이즈를 물을 때",
   vars=[("What size would you like?", "왓 사이즈 우쥴라익?", "사이즈는 뭐로 하시겠어요?"),
         ("What size?", "왓 사이즈?", "사이즈는요?"),
         ("Small, medium, or large?", "스몰, 미디엄, 오어 라지?", "작은 거, 중간, 큰 거 중에요?")],
   tip="would you like가 '우쥴라익'으로 붙어요. size만 들리면 돼요.",
   ans=("chips", "어떤 크기?", [("s", "작은 거", "small", "Small, please.", "작은 거로 주세요."),
        ("m", "중간", "medium", "Medium, please.", "미디엄으로 주세요."),
        ("l", "큰 거", "large", "Large, please.", "큰 거로 주세요.")])),
  dict(k="매장·포장", h3="For here or to go 뜻, 먹고 갈지 물을 때",
   vars=[("For here or to go?", "퍼히어러 투고?", "드시고 가세요, 가져가세요?"),
         ("Is that for here?", "이즈댓 퍼히어?", "드시고 가세요?"),
         ("Dine in or to go?", "다이닌 오어 투고?", "매장에서 드세요, 가져가세요?")],
   tip="here의 r이 or와 붙어서 '히어러'가 돼요. here, go가 들리면 이 질문이에요.",
   ans=("pick", [("먹고 갈게요", "here", [("list", None, [("For here, please.", "먹고 갈게요.")])]),
                 ("가져갈게요", "go", [("list", None, [("To go, please.", "가져갈게요.")])])], "here")),
  dict(k="크림", h3="Room for cream 뜻, 우유 자리를 물을 때",
   vars=[("Room for cream?", "룸퍼 크림?", "우유(크림) 넣을 자리 남겨 드릴까요?"),
         ("Do you want room?", "두유 원 룸?", "자리 남겨 드릴까요?"),
         ("Any milk or sugar?", "에니 밀크 오어 슈거?", "우유나 설탕 넣으세요?")],
   tip="for가 '퍼'로 아주 짧게 지나가요. 드립 커피를 시키면 자주 들어요.",
   ans=("pick", [("남겨 주세요", "yes", [("list", None, [("Yes, please.", "네, 남겨 주세요.")])]),
                 ("가득 주세요", "no", [("list", None, [("No room, thanks.", "자리 안 남겨도 돼요. (가득 채워 주세요)")])])], "no")),
  dict(k="이름", h3="Name for the order, 이름을 물을 때",
   vars=[("Can I get a name for the order?", "캐나이 게러 네임 퍼디 오더?", "주문하신 분 성함이요?"),
         ("Name for the order?", "네임 퍼디 오더?", "주문자 이름은요?"),
         ("What's your name?", "왓츠 유어 네임?", "이름이 뭐예요?")],
   tip="get a가 '게러'로 붙어요. 컵에 이름을 써서 부를 때 물어봐요.",
   ans=("list", [("It's Jun.", "준이에요.")]),
   note="부르기 쉬운 짧은 이름을 정해 두면 픽업할 때도 잘 들려요.")],
 sos_t="못 알아들었을 때, 이 세 문장", sos_p="카페는 시끄러워서 못 듣는 게 당연해요. 짧게 다시 물어보세요.",
 sos=[("Sorry, what was that?", "죄송해요, 뭐라고 하셨어요?"), ("One more time?", "한 번만 더요?"), ("Could you speak more slowly?", "조금 천천히 말씀해 주시겠어요?")],
 drop="못 알아들었다면")

D["travel-restaurant"] = dict(
 h2="식당 영어 질문, 어떻게 물어도 알아듣기",
 sub="서버 질문은 인원, 음료, 주문, 식사 중 순서로 나와요. 질문의 여러 모양을 들어 두고, 대답은 내 상황에 맞게 고르면 돼요.",
 ins_t="서버가 묻는 것", ins=[("인원", "how many in your party"), ("음료·주문", "drink · ready to order"), ("식사 중", "how is everything")],
 ins_p="many, drink, order, everything 중 한 단어만 들려도 무슨 질문인지 알 수 있어요.",
 qs=[
  dict(k="인원", h3="How many in your party 뜻, 인원을 물을 때",
   vars=[("How many in your party?", "하우메니 인뉴어 파리?", "몇 분이세요?"),
         ("How many?", "하우메니?", "몇 분이세요?"),
         ("Table for how many?", "테이블 퍼 하우메니?", "몇 분 자리 드릴까요?")],
   tip="party는 '일행'이에요. in your가 '인뉴어'로 붙고, party의 t가 'ㄹ'처럼 부드러워져요.",
   ans=("chips", "몇 명이에요?", [("2", "두 명", "two", "A table for two, please.", "두 명이요."),
        ("4", "네 명", "four", "A table for four, please.", "네 명이요."),
        ("1", "혼자", "one", "Just one, please.", "한 명이요.")]),
   next=[("직원", "Do you have a reservation?", "예약하셨어요?"), ("나", "No, we don't.", "아니요, 안 했어요."), ("직원", "It'll be about a 20-minute wait.", "20분 정도 기다리셔야 해요.")]),
  dict(k="음료", h3="Something to drink, 음료를 먼저 물을 때",
   vars=[("Can I start you off with something to drink?", "캐나이 스타츄 오프 윗썸띵 터 드링크?", "음료 먼저 드릴까요?"),
         ("Can I get you something to drink?", "캐나이 겟츄 썸띵 터 드링크?", "마실 것 드릴까요?"),
         ("Anything to drink?", "에니띵 터 드링크?", "음료 드릴까요?")],
   tip="start you는 '스타츄', get you는 '겟츄'로 붙어요. 주문 전에 음료부터 묻는 게 보통이에요.",
   ans=("pick", [("물만", "water", [("list", None, [("Just water for now, thanks.", "일단 물만 주세요.")])]),
                 ("음료 볼게요", "menu", [("list", None, [("Can I see the drink menu?", "음료 메뉴 볼 수 있을까요?")])])], "water"),
   next=[("직원", "Still or sparkling?", "일반 물이요, 탄산수요?"), ("나", "Tap water is fine.", "그냥 수돗물이면 돼요.")]),
  dict(k="주문", h3="Are you ready to order, 주문을 받을 때",
   vars=[("Are you ready to order?", "아유 레디러 오더?", "주문하시겠어요?"),
         ("Have you decided?", "해뷰 디싸이디드?", "정하셨어요?"),
         ("What can I get for you?", "왓캐나이 겟퍼유?", "뭐 드릴까요?")],
   tip="ready to의 t가 'ㄹ'로 바뀌어 '레디러'가 돼요. order, decided가 들리면 주문 질문이에요.",
   ans=("pick", [("주문할게요", "yes", [("list", None, [("I'll have the salmon, please.", "연어 요리로 주세요."), ("What do you recommend?", "뭐가 맛있어요?")])]),
                 ("조금만 더요", "no", [("list", None, [("Can we have a few more minutes?", "조금만 더 볼게요.")])])], "yes")),
  dict(k="굽기", h3="How would you like your steak, 굽기를 물을 때",
   vars=[("How would you like your steak?", "하우 우쥴라익 유어 스테익?", "스테이크 굽기는 어떻게 해 드릴까요?"),
         ("How would you like it cooked?", "하우 우쥴라이킷 쿡트?", "어떻게 익혀 드릴까요?"),
         ("Medium or well done?", "미디엄 오어 웰던?", "미디엄이요, 완전히 익혀요?")],
   tip="would you like가 '우쥴라익'으로 붙어요. cooked가 들리면 굽기 질문이에요.",
   ans=("chips", "어떻게 익힐까요?", [("m", "미디엄", "medium", "Medium, please.", "미디엄으로 주세요."),
        ("mr", "미디엄 레어", "medium rare", "Medium rare, please.", "미디엄 레어로 주세요."),
        ("wd", "완전히", "well done", "Well done, please.", "완전히 익혀 주세요.")])),
  dict(k="식사 중", h3="How is everything, 식사 중에 물을 때",
   vars=[("How is everything?", "하우즈 에브리띵?", "음식 괜찮으세요?"),
         ("How's your food?", "하우즈 유어 푸드?", "음식은 어떠세요?"),
         ("Can I get you anything else?", "캐나이 겟츄 에니띵 엘스?", "더 필요한 거 있으세요?")],
   tip="How is가 How's로 줄어 '하우즈'가 돼요. 식사 중간에 꼭 한 번 물어봐요.",
   ans=("pick", [("괜찮아요", "good", [("list", None, [("Everything's great, thanks.", "다 맛있어요, 감사해요.")])]),
                 ("부탁할게요", "ask", [("list", None, [("Could we get the check, please?", "계산서 주시겠어요?"), ("Could I get a box for this?", "이거 포장 용기 주시겠어요?")])])], "good"))],
 sos_t="못 알아들었을 때, 이 세 문장", sos_p="메뉴 설명이 빠르면 짧게 다시 물어보거나 메뉴판을 가리키며 물어보세요.",
 sos=[("Sorry, what was that?", "죄송해요, 뭐라고 하셨어요?"), ("Could you say that again?", "다시 말씀해 주시겠어요?"), ("Sorry, what does this mean?", "죄송한데, 이게 무슨 뜻이에요?")])

D["shopping-checkout"] = dict(
 h2="쇼핑 영어 질문, 어떻게 물어도 알아듣기",
 sub="매장 직원이 묻는 건 도움이 필요한지, 입어 볼지, 봉투와 결제예요. 질문의 여러 모양을 들어 두고, 대답은 내 상황에 맞게 고르면 돼요.",
 ins_t="매장 직원이 묻는 것", ins=[("도움·입어 보기", "help · try it on"), ("봉투", "need a bag"), ("결제", "credit or debit")],
 ins_p="help, try, bag, credit 중 한 단어만 들려도 무슨 질문인지 알 수 있어요.",
 qs=[
  dict(k="도움", h3="Can I help you find anything, 매장에서 말을 걸 때",
   vars=[("Can I help you find anything?", "캐나이 헬퓨 파인 에니띵?", "찾으시는 거 있어요?"),
         ("Are you looking for anything?", "아유 루킹 퍼 에니띵?", "찾으시는 거 있어요?"),
         ("Let me know if you need anything.", "렛미노우 이퓨 니드 에니띵", "필요한 거 있으면 말씀하세요.")],
   tip="help you가 '헬퓨'로 붙고, find의 d는 거의 안 들려요.",
   ans=("pick", [("구경만요", "look", [("list", None, [("I'm just looking, thanks.", "그냥 둘러보는 거예요.")])]),
                 ("찾는 게 있어요", "find", [("list", None, [("I'm looking for a jacket.", "재킷 찾고 있어요."), ("Do you have this in a medium?", "이거 미디엄 있어요?")])])], "look")),
  dict(k="입어 보기", h3="Try it on 뜻, 입어 보라고 할 때",
   vars=[("Would you like to try it on?", "우쥴라익 터 트라이리론?", "입어 보시겠어요?"),
         ("Do you want to try it on?", "두유 워너 트라이리론?", "입어 보실래요?"),
         ("The fitting room is over there.", "더 피팅룸 이즈 오버데어", "피팅룸은 저쪽이에요.")],
   tip="try it on이 한 단어처럼 붙고, it의 t가 'ㄹ'처럼 굴러가요.",
   ans=("list", [("Sure, where's the fitting room?", "네, 피팅룸이 어디예요?"), ("It's a little big.", "조금 커요."), ("Do you have a smaller size?", "더 작은 사이즈 있어요?")])),
  dict(k="계산대·봉투", h3="Do you need a bag, 계산대에서 듣는 말",
   vars=[("Did you find everything okay?", "디쥬 파인 에브리띵 오케이?", "필요한 거 다 찾으셨어요?"),
         ("Do you need a bag?", "듀니러 백?", "봉투 필요하세요?"),
         ("Bags are 10 cents.", "백즈 아 텐 센츠", "봉투는 10센트예요.")],
   tip="Did you가 '디쥬', need a가 '니러'로 붙어요. 첫 질문은 인사라 Yes, thanks.면 돼요.",
   ans=("pick", [("필요 없어요", "no", [("list", None, [("Yes, thanks.", "네, 감사해요. (다 찾았어요)"), ("No bag, thanks.", "봉투는 괜찮아요.")])]),
                 ("봉투 주세요", "yes", [("list", None, [("Yes, thanks.", "네, 감사해요. (다 찾았어요)"), ("Yes, please.", "네, 주세요.")])])], "no")),
  dict(k="결제", h3="Credit or debit, 결제 방법을 물을 때",
   vars=[("Credit or debit?", "크레딧어 데빗?", "신용카드예요, 체크카드예요?"),
         ("How would you like to pay?", "하우 우쥴라익 터 페이?", "어떻게 결제하시겠어요?"),
         ("Do you want your receipt?", "두유 원츄어 리씻?", "영수증 드릴까요?")],
   tip="or가 '어'로 약해지고, 두 단어 모두 끝의 t가 짧게 끊겨요. pay가 들리면 결제 질문이에요.",
   ans=("list", [("Credit, please.", "신용카드요."), ("Card, please.", "카드로 할게요."), ("No receipt, thanks.", "영수증은 괜찮아요.")]))],
 sos_t="못 알아들었을 때, 이 세 문장", sos_p="금액은 숫자라 놓치기 쉬워요. 계산대 화면을 보면서 확인해도 돼요.",
 sos=[("Sorry, how much was that?", "죄송한데, 얼마라고 하셨죠?"), ("Could you say that again?", "다시 말씀해 주시겠어요?"), ("Could you speak more slowly?", "조금 천천히 말씀해 주시겠어요?")],
 drop="계산대 질문을 놓쳤다면")

D["travel-trouble"] = dict(
 h2="여행 중 문제 상황 영어, 어떻게 물어도 알아듣기",
 sub="직원이나 경찰이 확인하는 건 무슨 일인지, 언제 어디서인지, 필요한 서류예요. 질문의 여러 모양을 들어 두고, 대답은 내 상황에 맞게 고르면 돼요.",
 ins_t="직원·경찰이 확인하는 것", ins=[("무슨 일", "problem · happened"), ("언제·어디서", "when · where"), ("서류", "insurance · police report")],
 ins_p="happened, when, where, insurance 중 한 단어만 들려도 무슨 질문인지 알 수 있어요.",
 qs=[
  dict(k="무슨 일", h3="What seems to be the problem, 무슨 일인지 물을 때",
   vars=[("What seems to be the problem?", "왓 씸즈터비 더 프라블럼?", "무슨 문제가 있으세요?"),
         ("What happened?", "왓 해픈드?", "무슨 일이에요?"),
         ("How can I help you?", "하우캐나이 헬퓨?", "무엇을 도와드릴까요?")],
   tip="to be가 '터비'로 약하게 붙어요. problem, happened가 들리면 무슨 일인지 묻는 거예요.",
   ans=("chips", "무슨 일인가요?", [("w", "지갑 분실", "wallet", "I lost my wallet.", "지갑을 잃어버렸어요."),
        ("p", "폰 분실", "phone", "I lost my phone.", "폰을 잃어버렸어요."),
        ("s", "도난", "stolen", "My bag was stolen.", "가방을 도둑맞았어요."),
        ("i", "아파요", "sick", "I don't feel well.", "몸이 안 좋아요.")])),
  dict(k="언제·어디서", h3="When did you last see it, 언제 어디서인지 물을 때",
   vars=[("When did you last see it?", "웬디쥬 래스씨잇?", "마지막으로 본 게 언제예요?"),
         ("Where did you lose it?", "웨어 디쥬 루짓?", "어디서 잃어버렸어요?"),
         ("What does it look like?", "왓 더짓 룩라익?", "어떻게 생겼어요?")],
   tip="did you가 '디쥬'로 붙고, last의 t가 빠져 '래스'처럼 들려요.",
   ans=("list", [("I think I left it in the taxi.", "택시에 두고 내린 것 같아요."), ("About an hour ago.", "한 시간쯤 전에요."), ("It's a black leather wallet.", "검은 가죽 지갑이에요.")])),
  dict(k="결항·지연", h3="flight canceled, 항공편 문제를 들을 때",
   vars=[("Your flight has been canceled.", "유어 플라잇 해즈빈 캔슬드", "항공편이 결항됐어요."),
         ("Your flight is delayed.", "유어 플라잇 이즈 딜레이드", "항공편이 지연됐어요."),
         ("The next flight is tomorrow morning.", "더 넥스 플라잇 이즈 터마로우 모닝", "다음 항공편은 내일 아침이에요.")],
   tip="canceled는 결항, delayed는 지연이에요. next의 t는 거의 안 들려요.",
   ans=("list", [("Can you put me on the next flight?", "다음 항공편으로 바꿔 주실 수 있어요?"), ("Can you give me a hotel voucher?", "호텔 바우처 주실 수 있어요?")])),
  dict(k="보험·서류", h3="travel insurance, 보험과 서류를 물을 때",
   vars=[("Do you have travel insurance?", "듀해브 트래블 인슈어런스?", "여행자 보험 있으세요?"),
         ("Do you need a police report?", "두유 니러 폴리스 리포트?", "경찰 확인서 필요하세요?"),
         ("Can I see your passport?", "캐나이 씨유어 패스포트?", "여권 좀 보여 주시겠어요?")],
   tip="insurance, report가 들리면 서류 이야기예요. need a는 '니러'로 붙어요.",
   ans=("list", [("Yes, I do.", "네, 있어요."), ("Yes, I need a police report for my insurance.", "네, 보험 때문에 경찰 확인서가 필요해요.")]))],
 sos_t="말이 안 나올 때, 이 세 문장", sos_p="당황하면 아무 말도 안 떠오를 수 있어요. 이 문장으로 시작하면 상대가 질문으로 이끌어 줘요.",
 sos=[("I need help, please.", "도와주세요."), ("Could you speak more slowly?", "조금 천천히 말씀해 주시겠어요?"), ("Is there someone who speaks Korean?", "한국어 하는 분 계세요?")],
 drop="문장이 생각 안 날 때")

if __name__ == "__main__":
    for pid, d in D.items():
        apply(pid, d)

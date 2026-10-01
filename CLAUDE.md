# 카페인영어 CafeInEnglish 사이트 — 운영 규칙

이 폴더는 www.cafeinenglish.com 정적 사이트의 원본이에요.
새 대화에서 작업할 때는 이 문서를 먼저 읽고 같은 방식으로 이어서 작업해요.

## 구조

```
content/
  site.json          사이트 설정 (도메인, 카톡 채널, 문의 이메일, 애드센스, GA)
  posts/<id>.json    글 1편 = 파일 1개 (영상으로 배우기 / 영어표현 / 영어꿀팁)
  think/<id>.json    사유의 문장 1세트 = 파일 1개
  daily.json         홈 '오늘의 한 잔' 목록 [{post, en, ko, desc}] — 한국 날짜 기준 매일 하나씩 돌아가며 표시 (새 글을 쓰면 1~2개 추가)
assets/
  style.css          전체 디자인
  app.js             퀴즈 · 오답노트 · 필사 · 출력 기능
build.py             content → docs/ 로 사이트 생성
docs/                ← GitHub Pages가 서비스하는 결과물 (직접 수정 금지, build.py로만 생성)
```

## 작업 순서

1. `content/` 의 JSON을 추가하거나 고친다 (디자인은 `assets/`).
2. 예문이 새로 생겼으면 `python3 tools/make_audio.py` 로 원어민 음성(mp3)을 만든다 (Kokoro TTS, `audio/` 에 저장. 이미 만든 문장은 건너뜀).
3. `python3 build.py` 로 `docs/` 를 다시 만든다. (QR 코드에는 `pip install segno` 필요)
4. 승주가 GitHub Desktop에서 Commit → Push 하면 1~2분 뒤 사이트에 반영된다.

## 주소 규칙

- 글: `/p/<id>/` · 사유의 문장: `/think/<id>/` · 카테고리: `/category/<video|expr|tip|think>/`
- 오답노트: `/notes/` · 소개/개인정보처리방침/문의: `/about/` `/privacy/` `/contact/`
- `id` 는 영어 소문자와 하이픈만 (예: `im-swamped`). 한 번 발행한 id는 바꾸지 않는다 (출력물 QR, 검색 주소가 깨짐).

## 글(posts) JSON 형식

| 필드 | 설명 |
|---|---|
| `id`, `date`(YYYY-MM-DD), `cat` | cat: `video` 영상으로 배우기 · `expr` 영어표현 · `tip` 영어꿀팁 |
| `sub` | 세부 분류 (새 표현 / 비슷한 표현 / 헷갈리는 표현 / 회화 / 단어 / 듣기 / 발음 …) |
| `title`, `lead`, `description` | description은 검색 결과 설명문 (80~120자) |
| `seo_title` | 검색용 제목(<title>). 사람들이 실제로 검색하는 말(예: 'I'm down 뜻')을 앞에 둔다. 화면 제목(h1)은 title |
| `video` | (선택) 유튜브 영상 ID. 있으면 글 맨 위 삽입 + 출력물 영상 QR |
| `think` | (선택) 연결된 사유의 문장 id |
| `body_html` | 본문 HTML. 사용 가능한 블록: `.box` `.memo`(연상법) `ul.ex > li > span.en + span.ko` |
| `og` | (선택) `{en, ko}` 카톡·SNS 미리보기 이미지 문구. en=크게 보일 표현, ko=아래 한 줄. 없으면 첫 표현/리드 사용 |
| `expressions` | (선택) `[{t(초), end(초), en, ko, orig(원문), origKo(원문 해석), say(한글 발음), tips[연음 팁], ex, exKo, memo(연상법)}]` — t가 있으면 듣기·3번 반복 버튼 |
| `thumb` | 목록 카드 썸네일 `{ko, text, key}` — ko=위 한국어 한 줄(궁금증), text=크게 쓸 영어, key=라임으로 강조할 단어. 배경은 카테고리별 고정: 영어표현=에스프레소, 영어꿀팁=크림, 사유의 문장=올리브 (라임은 핵심 단어에만). 영상 글은 유튜브 썸네일 |
| `related` | (선택) `[{label, href}]` 추가 추천 링크 |
| `quiz` | 3문제 권장. `{tag, q, sub, options[4], answer(0부터), explain, mnemonic}` |

## 사유의 문장(think) JSON 형식

`{id, date, post, video, title, speaker, description, og{en,ko}, thumb{ko,text,key}, quotes:[{t, end, en, ko, blanks[], think, ask}]}`
- `end` 가 없으면 단어 수로 끝 시간을 대략 계산해요. 정확히 하려면 end(초)를 넣는다.
- `blanks` 는 빈칸 복기에서 가릴 단어 (소문자, 문장에 실제 있는 단어)

## 자동으로 만들어지는 것

- 글 속 도식: `python3 tools/make_diagrams.py` → `images/` (build.py가 docs/images로 복사). 본문엔 `<figure class="fig"><img alt="내용을 설명하는 alt" …><figcaption>` 로 넣는다.
- 글·사유의 문장마다 공유 미리보기 이미지 `docs/og/p-<id>.png`, `docs/og/t-<id>.png` (Pillow + `fonts/PretendardVariable.ttf`)
- 영상은 썸네일만 먼저 보여주고, 누르거나 듣기 버튼을 누를 때 유튜브 플레이어를 불러온다 (속도).
- 예문 스피커 버튼: `audio/index.json` 에 있는 문장은 원어민 음성 mp3 재생 (한 번 더 누르면 0.75배속). 없으면 브라우저 영어 음성.
- 'A → B' 형태 예문(연음)은 'A ... B' 로 읽는다.
- 구조화 데이터(JSON-LD: Article + BreadcrumbList, 홈은 WebSite), 사이트맵 lastmod(콘텐츠 파일 수정일), 글 끝 '같이 보면 좋은 글' 4개(같은 카테고리·세부분류 우선).
- 글/사유의 문장 끝에 공유 버튼 (모바일은 기기 공유창 → 카톡 선택, PC는 링크 복사). 공유 메시지 없이 링크(미리보기 카드)만 보낸다.

## 디자인 규칙 (A안)

- 색: 배경 오프화이트 #FAF8F5 (카드 흰색) · 상단 메뉴·포인트 크림 #F4EEE4 · 에스프레소 #2A1A12 · 라임 #CDEB5B, 폰트 Pretendard. 이모지 대신 라임 라벨(`.lbl`).
- 메뉴 호버/선택 = 라임 형광펜 밑줄. 내 공부방 호버 = 에스프레소 배경 + 크림 글자.
- 로고/파비콘 "C." (에스프레소 바탕, 크림 C, 라임 점).
- 모바일 메뉴는 화면 폭에 맞춰 양끝 정렬.

## 영상 구간 시간 잡기 (정확하게)

- 유튜브 영상의 영어 자동자막(json3)에는 단어마다 시작 시간이 있어요. 브라우저에서 영상 페이지를 열고 자막을 켠 뒤 timedtext 응답을 받아 단어 시간을 뽑는다.
- t = 문장 첫 단어 시간 − 0.1초, end = 다음 문장 첫 단어 시간 − 0.1초 (사이가 길면 마지막 단어 + 0.6초).
- 문장 내용은 자동자막이 아니라 영상에 넣은 자막 기준으로 쓴다.

## 콘텐츠 원칙

- 톤: "제가 공부하려고 만든 걸 같이 쓰자" — 선생님이 아니라 같이 공부하는 사람.
- 모든 퀴즈 해설에는 쉬운 설명(explain) + 연상법(mnemonic)을 꼭 넣는다.
- 인터뷰·연설 인용은 짧게, 출처(누가·어디서)를 밝히고, 해설을 붙인다. 대본 통째로 옮기지 않는다.
- 원문은 자동 자막이 아니라 영상에 넣은 자막으로 대조해서 정확히 쓴다.
- 브랜드 표기: "카페인영어 CafeInEnglish" (커피 이모지 없이).
- 발행 전 팩트체크: 원어민 기준 검수(뜻·뉘앙스·예문·번역·퀴즈 보기마다 정답이 하나인지·과장 표현·사실관계)를 한 번 거친다.
- 애드센스 정책: 광고를 퀴즈 버튼 바로 옆에 두지 않는다. 자동 생성 글도 사람이 검수 후 발행.

## 아직 채워야 할 것 (content/site.json)

- `kakao`: 카카오톡 오픈채팅방 링크 (현재 https://open.kakao.com/o/gxsl5iQi) (비어 있으면 SNS 메뉴에서 누를 때 "곧 열려요" 안내. 주소를 넣으면 바로 연결. youtube · instagram도 site.json에서 관리)
- `contact_email`: 문의 페이지에 공개할 이메일
- `adsense_client`: 예) `ca-pub-XXXXXXXXXXXXXXXX` — 넣으면 광고 스크립트와 ads.txt 자동 생성
- `google_verify` / `naver_verify`: 서치콘솔·서치어드바이저 'HTML 태그' 인증 코드 (content 값만)
- `ga_id`: 구글 애널리틱스 측정 ID (예: `G-XXXXXXX`)

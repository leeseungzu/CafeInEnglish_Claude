# 카페인영어 CafeInEnglish 사이트 — 운영 규칙

이 폴더는 www.cafeinenglish.com 정적 사이트의 원본이에요.
새 대화에서 작업할 때는 이 문서를 먼저 읽고 같은 방식으로 이어서 작업해요.

## 구조

```
content/
  site.json          사이트 설정 (도메인, 카톡 채널, 문의 이메일, 애드센스, GA)
  posts/<id>.json    글 1편 = 파일 1개 (영상으로 배우기 / 영어표현 / 영어꿀팁)
  think/<id>.json    사유의 문장 1세트 = 파일 1개
assets/
  style.css          전체 디자인
  app.js             퀴즈 · 오답노트 · 필사 · 출력 기능
build.py             content → docs/ 로 사이트 생성
docs/                ← GitHub Pages가 서비스하는 결과물 (직접 수정 금지, build.py로만 생성)
```

## 작업 순서

1. `content/` 의 JSON을 추가하거나 고친다 (디자인은 `assets/`).
2. `python3 build.py` 로 `docs/` 를 다시 만든다. (QR 코드에는 `pip install segno` 필요)
3. 승주가 GitHub Desktop에서 Commit → Push 하면 1~2분 뒤 사이트에 반영된다.

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
| `video` | (선택) 유튜브 영상 ID. 있으면 글 맨 위 삽입 + 출력물 영상 QR |
| `think` | (선택) 연결된 사유의 문장 id |
| `body_html` | 본문 HTML. 사용 가능한 블록: `.box` `.memo`(연상법) `ul.ex > li > span.en + span.ko` |
| `expressions` | (선택) `[{t(초), en, ko, orig(원문), ex, exKo, memo(연상법)}]` — t가 있으면 ▶ 듣기 버튼 |
| `related` | (선택) `[{label, href}]` 추가 추천 링크 |
| `quiz` | 3문제 권장. `{tag, q, sub, options[4], answer(0부터), explain, mnemonic}` |

## 사유의 문장(think) JSON 형식

`{id, date, post, video, title, speaker, description, quotes:[{t, en, ko, blanks[], think, ask}]}`
- `blanks` 는 빈칸 복기에서 가릴 단어 (소문자, 문장에 실제 있는 단어)

## 콘텐츠 원칙

- 톤: "제가 공부하려고 만든 걸 같이 쓰자" — 선생님이 아니라 같이 공부하는 사람.
- 모든 퀴즈 해설에는 쉬운 설명(explain) + 연상법(mnemonic)을 꼭 넣는다.
- 인터뷰·연설 인용은 짧게, 출처(누가·어디서)를 밝히고, 해설을 붙인다. 대본 통째로 옮기지 않는다.
- 원문은 자동 자막이 아니라 영상에 넣은 자막으로 대조해서 정확히 쓴다.
- 브랜드 표기: "카페인영어 CafeInEnglish" (커피 이모지 없이).
- 애드센스 정책: 광고를 퀴즈 버튼 바로 옆에 두지 않는다. 자동 생성 글도 사람이 검수 후 발행.

## 아직 채워야 할 것 (content/site.json)

- `kakao`: 카카오톡 채널 친구추가 링크 (비어 있으면 카톡 버튼이 숨겨짐)
- `contact_email`: 문의 페이지에 공개할 이메일
- `adsense_client`: 예) `ca-pub-XXXXXXXXXXXXXXXX` — 넣으면 광고 스크립트와 ads.txt 자동 생성
- `ga_id`: 구글 애널리틱스 측정 ID (예: `G-XXXXXXX`)

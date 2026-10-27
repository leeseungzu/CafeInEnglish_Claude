# 카영 롱폼 템플릿 (A안 · 사이트 카드형, 2026-10-20 확정)

기준 영상: 정의선 회장 롱폼. 디자인 규칙은 `레퍼런스/롱폼_디자인_가이드_A안.md`, 시안은 `A안_시안.png`.
새 롱폼은 이 코드를 복사해서 경로·클립·문구만 바꿔 쓴다. 새로 짜지 않는다.

## 파일
| 파일 | 역할 |
|---|---|
| lf_style.py | 색·폰트·자막 알약(sub_pill)·영상 판(video_base, 진갈색 태그 + 출처 알약)·영상 자막(video_text) |
| hy_head.py | 공통 함수: step 카드, slide, slide_narr, drill, seg_broll, audio_track, seg_slide |
| opening.py | timing.json 기반 내레이션 자막(narr_cues) |
| render_hy.py | 전체 조립: 훅 → 오프닝 → STEP1(자막 없음) → STEP2 해설 scene() → 표현 → STEP3(한영 자막) → STEP4 → 아웃트로 |
| cues.py | Scribe 단어 타이밍으로 원본 클립 자막 시간 계산 → cues.json |
| build_audio.py / build_audio2.py | 문장 단위 TTS 이어 붙이기 + timing.json (영어는 Azure 코라, 키는 secrets/azure_tts.txt에서만 읽음) |
| sync_check.py | 내레이션 자막 시작·끝 에너지 검사 |
| vclip.py / vframe.py | 클립 조각별 원본 대비 소리(ms)·화면(프레임) 싱크 검증 |
| mkcc.py | list.txt 순서로 재인코딩 concat → full.mp4, offsets.json(챕터 시간) |

## 순서
1. 원본에서 인물 구간 Scribe → words.json, cues.py로 cues.json
2. units.json(내레이션 문장) → TTS → build_audio2.py → sync_check.py (0 flagged)
3. render_hy.py 수정: OFFS(파일 시간 보정), CRED(출처), CL(클립 구간·장면 라벨), scene() 문구와 hl(형광펜 단어), EXPR, drill, 퀴즈
4. 렌더 → vclip.py·vframe.py로 싱크 확인 → mkcc.py → 전체 드리프트 확인 → 프레임 시트로 눈 검수

## 꼭 지킬 것
- 쉼(0.95초 초과)과 "어/음"만 약 0.4초로 줄이고 단어는 자르지 않음, 잘린 곳 0.08초 디졸브
- 원본 클립 음량은 고정 게인(gain_for). loudnorm 금지(클립 끝 3초 싱크 틀어짐)
- 번인 자막 있는 원본은 GA_CROP처럼 확대 + 아래 불투명 가림
- 이름 카드는 첫 등장 한 번만, 자막은 말할 때만
- STEP 1(자막 없이 듣기) 클립에는 음영 띠 가운데에 🎧 헤드폰 아이콘 + "자막 없이 먼저 들어 보세요"(38px SemiBold, #D6DAE0)를 구간 내내 띄운다. 음영만 있고 문구가 빠지면 안 됨. render_hy.py의 clip(subs=False) 분기를 그대로 쓰고, 새로 짤 때도 반드시 넣는다. 렌더 후 프레임 시트로 확인.
- 렌더 중인 파일은 덜 써진 상태로 존재하니, 중간에 끊겼으면 해당 mp4 지우고 다시

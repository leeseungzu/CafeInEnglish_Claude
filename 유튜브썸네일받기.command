#!/bin/bash
# 카페인영어: 사이트에 아직 없는 유튜브 썸네일 원본을 받아 둡니다 (더블클릭하면 실행).
# Claude 작업 환경은 유튜브에 접속이 안 돼서, 이 파일로 승주 맥에서 한 번 받아 두면
# 다음 빌드 때 사이트용 작은 webp(640·400px)로 바뀌어요.
cd "$(dirname "$0")"
mkdir -p yt_src
ids=$( (cat yt_src/need.txt 2>/dev/null; grep -rhoE 'i\.ytimg\.com/vi/[A-Za-z0-9_-]{11}' docs 2>/dev/null | sed 's#.*/vi/##') | sort -u )
n=0
for id in $ids; do
  [ -f "images/yt/$id.webp" ] && continue
  [ -s "yt_src/$id.jpg" ] && continue
  curl -sfL "https://i.ytimg.com/vi/$id/maxresdefault.jpg" -o "yt_src/$id.jpg" || curl -sfL "https://i.ytimg.com/vi/$id/hqdefault.jpg" -o "yt_src/$id.jpg"
  [ -s "yt_src/$id.jpg" ] && { echo "받음: $id"; n=$((n+1)); } || echo "실패: $id"
done
echo ""
echo "완료: $n개 받았어요. 이 창은 닫아도 돼요. Claude에게 '썸네일 받았어'라고 알려 주세요."

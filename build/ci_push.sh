#!/usr/bin/env bash
# 데이터 갱신 잡 공용 커밋·푸시
#
#   사용: build/ci_push.sh "<커밋 메시지>" <스테이징할 경로…>
#   환경: WATCH(기본 data/) · MAX_TRIES(기본 5)
#
# ── 왜 스크립트로 뺐나 ────────────────────────────────────────────────
# 갱신 잡 5개가 같은 main에 밀어 넣는다. 크론 분(minute)을 어긋나게 잡아뒀지만
# 그건 확률을 낮출 뿐이고, 사람이 손으로 푸시하는 순간과도 겹친다. 경합은 예외가
# 아니라 정상 동작이다.
#
# 2026-07-25 regime 잡이 정확히 그렇게 죽었다. 워크플로마다 인라인 bash로
#   git push || (git pull --rebase origin main && git push)
# 를 조금씩 다르게 복사해 두고 있었는데, 이 1회 재시도로는 원리상 절대 못 넘는
# 충돌이 하나 있다 — data/asof.json.
#
# 이 파일은 원본이 바뀔 때마다 다시 굽는 **파생물**이고, 구울 때마다 generated에
# 새 UTC 타임스탬프가 박힌다. 그래서 두 잡이 각자 구우면 내용이 반드시 달라지고,
# 리베이스는 반드시 충돌한다. 재시도해도 같은 충돌이 또 난다.
#
# ── 그래서 충돌을 '해결'하지 않고 없앤다 ──────────────────────────────
#   1) 리베이스에서 asof.json이 충돌하면 상대(upstream) 것을 그냥 받는다.
#      어느 쪽을 고르든 상관없다 — 어차피 다음 줄에서 덮어쓴다.
#   2) 리베이스가 끝난 뒤 원본에서 정본을 **다시 굽는다**. 그 시점엔 두 잡의 원본이
#      모두 트리에 반영돼 있으므로, 다시 구운 결과가 유일하게 옳은 값이다.
#      (한쪽 것을 고르고 끝냈다면 상대 잡의 갱신이 정본에서 누락된 채 배포된다.)
#   3) 달라졌으면 amend 해서 커밋 하나로 유지한다.
#
# asof.json 외의 파일이 충돌하면 자동 해소하지 않는다 — 사람이 봐야 하는 상황이므로
# abort 하고 실패시킨다. 파생물에만 쓰는 규칙을 원본에 적용하면 데이터가 조용히 사라진다.
set -euo pipefail

MSG="${1:?커밋 메시지가 필요하다}"
shift
PATHS=("$@")
if [ ${#PATHS[@]} -eq 0 ]; then
  echo "::error::스테이징할 경로를 하나 이상 넘겨야 한다"
  exit 1
fi

WATCH="${WATCH:-data/}"
MAX_TRIES="${MAX_TRIES:-5}"
ASOF="data/asof.json"
# Actions 러너에는 python·python3 둘 다 있지만 macOS 로컬엔 python3만 있다.
# 재시도 경로에서만 쓰는 호출이라, 여기서 못 찾으면 경합이 났을 때만 터진다 — 가장 늦게 들키는 자리다.
PY="$(command -v python3 || command -v python)"

git config user.name  "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

# ── 변경 감지는 WATCH 전체로 본다 ────────────────────────────────────
# 특정 산출물 경로만 보면, 과거 사고 유형(새 산출물 파일만 생기고 기존 경로는 무변경)에서
# else로 빠져 아래 누락 가드가 아예 돌지 않는다.
if [ -z "$(git status --porcelain -- "$WATCH")" ]; then
  echo "변경 없음 — 스킵"
  exit 0
fi

git add -- "${PATHS[@]}"

# ── 누락 가드 ────────────────────────────────────────────────────────
# 이 잡이 WATCH 아래에 만든 변경 중 **스테이징되지 않은 것**이 남아 있으면 실패시킨다.
# (git status --porcelain 1열=index·2열=worktree. 1열이 공백이거나 '??'면 누락)
# 과거 home_reco.json·target_history.json 을 git add에서 빠뜨려 영구 유실시킨 사고가 3번 있었다.
LEFT="$(git status --porcelain -- "$WATCH" | grep -E '^([ ?])' || true)"
if [ -n "$LEFT" ]; then
  echo "::error::$WATCH 산출물이 커밋 목록에서 빠졌습니다(과거 home_reco·target_history 유실 사고와 동일 유형):"
  echo "$LEFT"
  exit 1
fi

if git diff --cached --quiet; then
  echo "스테이징 결과가 비었다 — 스킵"
  exit 0
fi

git commit -m "$MSG"

# asof.json을 이 잡이 커밋에 포함했는가. 포함한 잡만 리베이스 뒤 다시 굽는다.
WANTS_ASOF=0
for p in "${PATHS[@]}"; do
  [ "$p" = "$ASOF" ] && WANTS_ASOF=1
done

for ((try = 1; try <= MAX_TRIES; try++)); do
  if git push origin HEAD:main; then
    echo "푸시 완료 (시도 $try/$MAX_TRIES) → GitHub Pages 자동 재빌드"
    exit 0
  fi

  echo "푸시 거절 — 그 사이 원격이 앞섰다. 리베이스 후 재시도 ($try/$MAX_TRIES)"
  git fetch origin +refs/heads/main:refs/remotes/origin/main

  if ! git rebase origin/main; then
    CONFLICTS="$(git diff --name-only --diff-filter=U)"
    if [ "$CONFLICTS" != "$ASOF" ]; then
      echo "::error::파생물이 아닌 파일이 충돌했습니다 — 자동 해소하지 않습니다. 사람이 봐야 합니다:"
      echo "$CONFLICTS"
      git rebase --abort || true
      exit 1
    fi
    # 파생물이다. 여기서 고른 값은 바로 아래에서 다시 구워 덮어쓴다.
    echo "asof.json 충돌 — 파생물이므로 upstream 것을 받고 리베이스 뒤 다시 굽는다"
    git checkout --ours -- "$ASOF"
    git add -- "$ASOF"
    GIT_EDITOR=true git rebase --continue
  fi

  if [ "$WANTS_ASOF" = "1" ]; then
    # 상대 잡의 원본까지 반영된 상태에서 다시 굽는다 — 이게 유일하게 옳은 정본이다.
    "$PY" build/asof_index.py
    if [ -n "$(git status --porcelain -- "$ASOF")" ]; then
      git add -- "$ASOF"
      git commit --amend --no-edit
      echo "기준일 정본 재생성 후 커밋에 합침"
    fi
  fi
done

echo "::error::${MAX_TRIES}회 재시도에도 푸시하지 못했습니다. main 경합이 비정상적으로 잦습니다."
exit 1

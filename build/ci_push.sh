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
#   1) 리베이스에서 파생물이 충돌하면 상대(upstream) 것을 그냥 받는다.
#      어느 쪽을 고르든 상관없다 — 어차피 다음 줄에서 덮어쓴다.
#   2) 리베이스가 끝난 뒤 원본에서 정본을 **다시 굽는다**. 그 시점엔 두 잡의 원본이
#      모두 트리에 반영돼 있으므로, 다시 구운 결과가 유일하게 옳은 값이다.
#      (한쪽 것을 고르고 끝냈다면 상대 잡의 갱신이 정본에서 누락된 채 배포된다.)
#   3) 달라졌으면 amend 해서 커밋 하나로 유지한다.
#
# 표에 없는 파일이 충돌하면 자동 해소하지 않는다 — 사람이 봐야 하는 상황이므로
# abort 하고 실패시킨다. 파생물에만 쓰는 규칙을 원본에 적용하면 데이터가 조용히 사라진다.
#
# ── 2026-07-31: 대상을 asof.json 하나에서 파생물 전반으로 넓혔다 ───────
# 위 원리는 asof.json 고유의 것이 아니다. "원본에서 다시 굽는 파일"이면 전부 같다.
# 그런데 구현이 asof.json 하나에 하드코딩돼 있어서, 그날 refresh-assets 가 28분치
# 생성물을 통째로 버렸다 — 10:08 체크아웃 → 10:36 푸시 시도, 그 2분 전(10:34)에
# 사람이 strategy_index.json·strategy_charts.json 을 건드린 커밋을 밀었다.
# 둘 다 '원본에서 굽는 파일'이라 리베이스 후 다시 구우면 그만인데, 표에 없어서
# abort 했다. 그 결과 그날 자산 패널·스타일 성과가 하루 통째로 낡은 채 남았다.
#
# ⚠ 표에 올릴 조건 — **원본만 있으면 언제든 똑같이 재현되는 순수 파생물**일 것.
#   수집물(assets.json·stocks.json 처럼 외부에서 받아온 것)은 절대 올리면 안 된다.
#   다시 구울 수 없으므로 한쪽을 버리는 순간 그 잡의 수집 결과가 영구 유실된다.
#   또 **봇 잡이 커밋하는 파일**만 올린다. 사람이 손으로 굽는 것(data/schedule.json — 크론을
#   고칠 때만 다시 굽는다)은 여기 있어도 영원히 안 쓰이는 사문이라 오해만 만든다.
#   두 방향 다 build/validate_site.py 가 CI 에서 강제한다(2개 잡 이상이 커밋하는데 표에 없으면 실패,
#   표에 있는데 커밋하는 잡이 없어도 실패).
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

# ── 파생물 재생성 표 ─────────────────────────────────────────────────
# "경로|생성명령". 여기 있는 파일만 충돌을 자동 해소하고, 리베이스 뒤 이 순서대로 다시 굽는다.
# 순서 = 의존 순서다. strategy_index 가 charts 보다 먼저고, 모든 축의 as_of 를 읽는
# asof.json 이 맨 마지막이다.
# 같은 명령이 두 줄에 나오면(style_perf·style_trails) 한 번만 실행한다.
REBAKE_TABLE="\
data/strategy_index.json|build/strategy_index.py
data/strategy_charts.json|build/strategy_charts.py
data/market_board.json|build/market_board.py
data/style_perf.json|build/style_top_pdf.py --json
data/style_trails.json|build/style_top_pdf.py --json
data/home_flow.json|build/home_flow.py
data/style_top.json|build/style_top.py
data/home_market.json|build/home_market.py
data/asof.json|build/asof_index.py"

# 경로 → 생성명령 (없으면 빈 문자열). bash 3.2(macOS)에도 도는 방식으로 연관배열을 피한다.
# ⚠ 파이프라인(`printf | while`)으로 쓰면 안 된다 — 마지막 read 가 EOF 에서 1을 내고
#   그게 함수의 종료코드가 되어, 호출부의 `c="$(...)"` 대입이 set -e 로 잡을 안 죽인다.
#   (실측: 표에 없는 첫 경로 data/assets.json 에서 스크립트가 통째로 멎었다.)
#   그래서 here-string 으로 서브셸을 없애고 종료코드를 명시한다.
rebake_cmd_for() {
  local line
  while IFS= read -r line; do
    case "$line" in
      "$1|"*) printf '%s' "${line#*|}"; return 0 ;;
    esac
  done <<< "$REBAKE_TABLE"
  return 0
}
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

# 이 잡이 커밋에 포함한 파생물은 무엇인가. 그것만 리베이스 뒤 다시 굽는다.
# (충돌은 이 잡이 커밋한 파일에서만 날 수 있으므로, 이 목록이 곧 자동 해소 가능 범위다.)
MINE=""
for p in "${PATHS[@]}"; do
  c="$(rebake_cmd_for "$p")"
  if [ -n "$c" ]; then
    MINE="$MINE$p|$c
"
  fi
done

# 표 순서대로, 명령 중복은 한 번만 실행한다(style_perf·style_trails 가 한 명령을 공유한다).
rebake_all() {
  local ran="" line p c
  while IFS= read -r line; do
    p="${line%%|*}"; c="${line#*|}"
    case "$MINE" in *"$p|$c"*) ;; *) continue ;; esac
    case "$ran" in *"[$c]"*) continue ;; esac
    ran="$ran[$c]"
    echo "  다시 굽는다: $c"
    # shellcheck disable=SC2086
    "$PY" $c
  done <<< "$REBAKE_TABLE"
  return 0
}

for ((try = 1; try <= MAX_TRIES; try++)); do
  if git push origin HEAD:main; then
    echo "푸시 완료 (시도 $try/$MAX_TRIES) → GitHub Pages 자동 재빌드"
    exit 0
  fi

  echo "푸시 거절 — 그 사이 원격이 앞섰다. 리베이스 후 재시도 ($try/$MAX_TRIES)"
  git fetch origin +refs/heads/main:refs/remotes/origin/main

  if ! git rebase origin/main; then
    CONFLICTS="$(git diff --name-only --diff-filter=U)"
    # 리베이스는 충돌 말고도 실패한다(미스테이징 변경이 남아 있는 경우 등). 그때 충돌 목록은 비고,
    # 빈 목록을 '전부 파생물'로 읽으면 --continue 가 "no rebase in progress"로 터진다.
    # (실측으로 잡음: 원래 코드는 `!= data/asof.json` 비교라 이 경우가 우연히 걸러졌었다.)
    if [ -z "$CONFLICTS" ]; then
      echo "::error::리베이스가 충돌 없이 실패했습니다 — 자동 해소 대상이 아닙니다:"
      git status --porcelain | head -20
      git rebase --abort || true
      exit 1
    fi
    BAD=""
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      case "$MINE" in *"$f|"*) ;; *) BAD="$BAD$f
" ;; esac
    done <<< "$CONFLICTS"
    if [ -n "$BAD" ]; then
      echo "::error::다시 구울 수 없는 파일이 충돌했습니다 — 자동 해소하지 않습니다. 사람이 봐야 합니다:"
      echo "$BAD"
      git rebase --abort || true
      exit 1
    fi
    # 전부 파생물이다. 여기서 고른 값은 바로 아래에서 다시 구워 덮어쓴다.
    echo "파생물 충돌 — upstream 것을 받고 리베이스 뒤 다시 굽는다:"
    echo "$CONFLICTS" | sed 's/^/  · /'
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      git checkout --ours -- "$f"
      git add -- "$f"
    done <<< "$CONFLICTS"
    GIT_EDITOR=true git rebase --continue
  fi

  if [ -n "$MINE" ]; then
    # 상대 잡의 원본까지 반영된 상태에서 다시 굽는다 — 이게 유일하게 옳은 정본이다.
    rebake_all
    if [ -n "$(git status --porcelain -- "$WATCH")" ]; then
      git add -- "${PATHS[@]}"
      # 재생성이 PATHS 밖 파일을 건드렸다면 그건 조용히 흘리면 안 되는 신호다(위 누락 가드와 같은 규칙).
      LEFT="$(git status --porcelain -- "$WATCH" | grep -E '^([ ?])' || true)"
      if [ -n "$LEFT" ]; then
        echo "::error::재생성 결과가 커밋 목록 밖의 파일을 바꿨습니다 — 사람이 봐야 합니다:"
        echo "$LEFT"
        exit 1
      fi
      if ! git diff --cached --quiet; then
        # ⚠ 충돌을 전부 upstream 것으로 받으면 우리 커밋이 '빈 커밋'이 되어 리베이스에서 떨어져 나간다.
        #   그 상태에서 --amend 하면 **남의 커밋**을 고쳐 쓰게 된다(git이 거부하면 재생성 결과가 통째로
        #   커밋되지 않은 채 남고, 다음 푸시는 up-to-date 라 잡은 초록불로 끝난다 — 조용한 유실).
        #   그래서 HEAD가 아직 우리 커밋인지 제목으로 확인하고, 아니면 새 커밋을 만든다.
        if [ "$(git log -1 --format=%s)" = "$MSG" ]; then
          git commit --amend --no-edit
          echo "파생물 정본 재생성 후 커밋에 합침"
        else
          git commit -m "$MSG"
          echo "리베이스에서 우리 커밋이 비워졌다 — 재생성 결과로 새 커밋을 만든다"
        fi
      fi
    fi
  fi
done

echo "::error::${MAX_TRIES}회 재시도에도 푸시하지 못했습니다. main 경합이 비정상적으로 잦습니다."
exit 1

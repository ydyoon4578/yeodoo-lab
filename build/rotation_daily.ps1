# 전략 탐색 풀 일일 갱신 — 로컬 작업 스케줄러(KB_RotationDaily)가 매일 부른다.
#
# 🚨 이 잡을 왜 로컬에서 도나: 웹 리서치가 필요해서 GitHub Actions 로 못 옮긴다
#   (러너에 Claude 인증이 없다). 그래서 이 PC 가 유일한 생산자다 — 이 PC 가 꺼져 있으면
#   그날 풀은 안 돈다. 2026-08-07~10 에 실제로 나흘 멈췄고, 멈춘 것을 아무도 몰랐다.
#   그래서 build/validate_site.py 가 3영업일부터 경고하고 rotation.html 도 같은 문턱으로
#   화면에 띄운다. **이 스크립트가 시끄럽게 죽는 것보다 조용히 안 도는 것이 훨씬 나쁘다.**
#
# 하는 일:
#   ① origin 을 따라간다 → ② 검증 기준선을 잰다 → ③ 헤드리스 Claude 에게 풀 갱신을 시킨다
#   → ④ 결과를 기계로 검사한다(고친 파일이 풀 하나뿐인가 · FRESH_OK · 검증 회귀 없음)
#   → ⑤ 통과하면 커밋·푸시
#
# ⚠ 실패했을 때 작업물을 되돌리지 않는다. 웹 리서치는 비용을 치른 것이고 되돌리면 그날
#   알아낸 것이 사라진다. 대신 푸시를 막고 로그에 크게 남긴다 — 사람이 보고 판단한다.
#
# 사용(수동 실행):
#   powershell -ExecutionPolicy Bypass -File build\rotation_daily.ps1
#   powershell -ExecutionPolicy Bypass -File build\rotation_daily.ps1 -DryRun   # 커밋·푸시 안 함

param(
  [string]$Repo = "C:\Users\USER\yeodoo-lab",
  [string]$Python = "python",
  [switch]$DryRun,
  [int]$TimeoutMinutes = 40
)

# 단계마다 직접 판정한다 — 예외로 죽으면 로그가 안 남아 '왜 안 돌았는지'를 못 본다.
$ErrorActionPreference = "Continue"
$log = Join-Path $Repo "_rotation.log"
# 로그는 매일 쌓인다. 1MB 를 넘으면 한 세대만 남기고 갈아 끼운다 —
# 무한히 자라게 두면 언젠가 이 파일 때문에 무언가가 느려지고, 그때는 원인을 못 찾는다.
if ((Test-Path $log) -and ((Get-Item $log).Length -gt 1MB)) {
  $old = $log + ".1"
  if (Test-Path $old) { Remove-Item $old -Force }
  Move-Item $log $old
}
function Say($m) {
  $s = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m
  Write-Host $s
  Add-Content -Path $log -Value $s -Encoding utf8
}
function Fail($m) {
  Say ("[X] " + $m)
  Say "-- 중단. 작업물은 그대로 둔다(git status 로 확인할 것)."
  exit 1
}

Say "===== 전략 탐색 풀 일일 갱신 시작 ====="
if (-not (Test-Path $Repo)) { Say ("[X] 저장소 경로 없음: " + $Repo); exit 1 }
Set-Location $Repo

# ── ① origin 을 따라간다 ────────────────────────────────────────────────
# autostash — 어제 실패해서 남은 작업물이 있어도 rebase 가 죽지 않는다.
#
# 🚨 2026-09-01 — **이 잡이 나흘 연속(08-29~09-01) 여기서 죽어 있었다.**
#   기전: pull 이 충돌하면 git 은 리베이스를 **열어 둔 채** 실패한다. 종전에는 그대로
#   Fail 로 나갔고, 그러면 다음 날 실행은 «이미 리베이스 중» 이라 2초 만에 또 죽는다.
#   한 번 걸리면 사람이 손대기 전까지 영영 못 돈다 — 실제로 나흘이 그렇게 갔고,
#   그 나흘 동안 rotation.html 의 «최근 동향» 이 멈춰 있었다.
#   ⚠ 게다가 열린 리베이스는 **이 저장소에서 사람이 하던 작업까지 망가뜨린다.**
#     autostash 가 워킹트리를 stash 로 걷어간 채 멈추기 때문이다(실측: 그 상태에서
#     커밋해 «구현이 빠진 커밋» 이 만들어졌고 되돌려 다시 커밋해야 했다).
#
# 그래서 둘을 고친다 —
#   (a) 시작할 때 **남아 있는 리베이스/머지를 먼저 걷는다.** 어제 것이 남아 있으면
#       오늘도 반드시 죽으므로, 정리하고 시작하는 것이 «다시 시도할 기회» 를 만든다.
#   (b) pull 이 실패하면 **리베이스를 abort 해서 원래 상태로 되돌린 뒤** 나간다.
#       충돌을 자동으로 해결하지는 **않는다** — 부딪치는 것이 생성물(asof·strategy_index·
#       strategy_charts·strategy_report)이고 어느 쪽이 맞는지는 «어느 빌드가 최신인가» 에
#       달렸다. 기계가 고르면 조용히 틀린 쪽을 실을 수 있다. 사람이 정한다.
# ⚠ 이것은 «충돌을 없애는 고침» 이 아니라 «충돌이 잡을 영구히 죽이지 못하게 하는 고침» 이다.
#   충돌 자체는 랩 작업과 CI 자동 커밋이 같은 생성물을 건드리는 한 계속 난다.
$gitDir = (git rev-parse --git-dir)
if ((Test-Path (Join-Path $gitDir "rebase-merge")) -or (Test-Path (Join-Path $gitDir "rebase-apply"))) {
  Say "[!] 지난 실행이 남긴 리베이스가 있다 - 걷고 시작한다(그대로 두면 오늘도 죽는다)."
  git rebase --abort 2>&1 | Out-Null
}
if (Test-Path (Join-Path $gitDir "MERGE_HEAD")) {
  Say "[!] 지난 실행이 남긴 머지가 있다 - 걷고 시작한다."
  git merge --abort 2>&1 | Out-Null
}

git fetch --quiet origin
git pull --rebase --autostash --quiet origin main
if ($LASTEXITCODE -ne 0) {
  # 🚨 열린 리베이스를 두고 나가지 않는다. abort 가 autostash 도 되돌려 준다.
  $u = @(git diff --name-only --diff-filter=U)
  $gd = (git rev-parse --git-dir)
  if ((Test-Path (Join-Path $gd "rebase-merge")) -or (Test-Path (Join-Path $gd "rebase-apply"))) {
    git rebase --abort 2>&1 | Out-Null
    Say "    (열린 리베이스를 abort 했다 - 저장소는 pull 이전 상태로 돌아갔다)"
  }
  if ($u.Count -gt 0) { Say ("    충돌하던 파일: " + ($u -join ", ")) }
  Say "    보통 원인은 생성물(asof·strategy_index·strategy_charts·strategy_report)이"
  Say "    랩 작업과 CI 자동 커밋 양쪽에서 바뀐 것이다. 손으로 정리할 것:"
  Say "      git rebase origin/main   후 충돌 파일을 한쪽으로 정하고 --continue,"
  Say "      그다음 build/ 사슬을 다시 돌려 생성물을 일치시킨다."
  Fail "git pull 실패 - 충돌이 남아 있는지 확인할 것"
}
$headBefore = (git rev-parse --short HEAD)
Say ("저장소 " + $headBefore)

# 🚨 어제 실패해서 남은 풀 변경 위에 오늘 것을 얹으면 안 된다.
#   아래 ②의 검증 기준선을 **더러운 상태에서** 재게 되고, 그러면 어제 깬 것이
#   '원래 깨져 있던 것'으로 둔갑해 오늘 통과하고 게시된다. 관문이 정확히 반대로 작동한다.
#   → 풀이 이미 수정돼 있으면 시작하지 않는다. 사람이 보고 정리해야 한다.
#   ⚠ 하루 안 도는 것보다 어제 실패한 것을 조용히 게시하는 것이 훨씬 나쁘다.
#     안 돈 사실은 validate_site 가 3영업일부터, rotation.html 이 같은 문턱으로 알린다.
$dirty0 = @(git status --porcelain)
if ($dirty0.Count -gt 0) { Say ("[!] 시작 전부터 작업 트리가 더럽다: " + ($dirty0 -join " / ")) }
# 🚨 2026-08-13 — 시작 전부터 더러웠던 **경로**를 따로 남긴다. 아래 ④(a) 관문이
#   '사람이 원래 작업 중이던 파일'과 'claude 가 이번에 건드린 파일'을 갈라야 하기 때문이다.
#   ⚠ 이걸 안 갈랐더니 2026-08-13 에 리서치가 성공하고도 커밋이 통째로 막혔다 —
#     같은 저장소에서 사람이 작업 중이면 매일 막힌다(_rotation.log 08-13 08:09 참조).
$before = @($dirty0 | ForEach-Object { ($_ -replace '^..\s+', '').Trim() } | Where-Object { $_ })
if ($dirty0 | Where-Object { $_ -match "data/rotation_pool\.json" }) {
  Say "[X] data/rotation_pool.json 이 이미 수정돼 있다 - 지난 실행이 실패하고 남긴 것으로 본다."
  Say "    git diff data/rotation_pool.json 으로 확인하고, 쓸 만하면 커밋을, 아니면"
  Say "    git checkout -- data/rotation_pool.json 으로 되돌린 뒤 다시 돌릴 것."
  exit 1
}

# ── ② 검증 기준선 ──────────────────────────────────────────────────────
# 🚨 절대 기준으로 걸면 이 잡과 무관한 결함 때문에 그날 리서치를 통째로 버린다.
#   수집 잡 네 개가 2026-08-05 에 실제로 그렇게 죽었다(build/validate_gate.py 머리말).
$vb = & $Python (Join-Path $Repo "build\validate_gate.py") baseline 2>&1
$vb | ForEach-Object { Say ("  " + $_) }

# ── ③ 헤드리스 Claude ──────────────────────────────────────────────────
$promptPath = Join-Path $Repo "build\rotation_daily_prompt.md"
if (-not (Test-Path $promptPath)) { Fail ("지시서가 없다: " + $promptPath) }

# claude 는 npm 전역 설치라 .cmd 를 직접 부른다. PATH 해석은 작업 스케줄러 환경에서
# 종종 달라져서, 여기서 실제 경로를 찾아 두는 편이 안전하다.
$claudeExe = $null
$cc = Get-Command claude.cmd -ErrorAction SilentlyContinue
if ($cc) { $claudeExe = $cc.Source }
if (-not $claudeExe) {
  $cand = Join-Path $env:APPDATA "npm\claude.cmd"
  if (Test-Path $cand) { $claudeExe = $cand }
}
if (-not $claudeExe) { Fail "claude CLI 를 못 찾았다 - npm i -g @anthropic-ai/claude-code" }
Say ("claude: " + $claudeExe)

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $env:TEMP ("rotation_claude_{0}.out.txt" -f $stamp)
$errFile = Join-Path $env:TEMP ("rotation_claude_{0}.err.txt" -f $stamp)

# 프롬프트는 stdin 으로 넘긴다 — 인자로 넘기면 길이·따옴표·한글 인코딩에서 깨진다.
# --allowedTools 로 도구를 좁히되 Bash 는 연다: 101종 JSON 을 Edit 로 한 줄씩 고치는 것보다
# 작은 파이썬 스크립트를 쓰는 편이 안전하고 실제로 그렇게 돈다.
# 🚨 진짜 방어선은 도구 목록이 아니라 아래 ④(a) '고친 파일이 풀 하나뿐인가' 검사다.
$claudeArgs = @(
  "-p",
  "--permission-mode", "acceptEdits",
  "--allowedTools", "Read", "Edit", "Write", "Glob", "Grep", "Bash", "WebSearch", "WebFetch",
  "--add-dir", $env:TEMP
)

Say ("헤드리스 Claude 실행 중... (최대 " + $TimeoutMinutes + "분)")
$p = Start-Process -FilePath $claudeExe -ArgumentList $claudeArgs `
                   -WorkingDirectory $Repo -NoNewWindow -PassThru `
                   -RedirectStandardInput $promptPath `
                   -RedirectStandardOutput $outFile `
                   -RedirectStandardError $errFile
if (-not $p.WaitForExit($TimeoutMinutes * 60 * 1000)) {
  try { $p.Kill() } catch {}
  Fail ("헤드리스 Claude 가 " + $TimeoutMinutes + "분 안에 안 끝났다")
}
# ⚠ 시간 제한이 있는 WaitForExit($ms) 뒤에는 ExitCode 가 아직 안 채워져 있을 수 있다
#   (첫 실행에서 실제로 빈 값이 찍혔다). 인자 없는 WaitForExit() 을 한 번 더 불러
#   출력 스트림까지 닫히기를 기다린 뒤 읽는다.
$p.WaitForExit()
Say ("claude 종료코드 " + $p.ExitCode)
$outTxt = if (Test-Path $outFile) { Get-Content $outFile -Raw -Encoding utf8 } else { "" }
$errTxt = if (Test-Path $errFile) { Get-Content $errFile -Raw -Encoding utf8 } else { "" }
if ($errTxt -and $errTxt.Trim()) { Say ("claude stderr: " + $errTxt.Trim()) }

# 보고 한 줄(DONE ...)을 커밋 메시지에 쓴다. 없으면 기본 문구로 간다.
$doneLine = ($outTxt -split "`n" | Where-Object { $_ -match "^\s*DONE\s" } | Select-Object -Last 1)
if ($doneLine) { $doneLine = ($doneLine.Trim() -replace "^DONE\s*", "") } else { $doneLine = "최근동향 갱신" }
Say ("보고: " + $doneLine)

# ── ④ 기계 검사 셋 ─────────────────────────────────────────────────────
# (a) 고친 파일이 풀 하나뿐인가 — 지시서 규칙 1의 실제 집행 지점이다.
$changed = @(git status --porcelain | ForEach-Object { ($_ -replace '^..\s+', '').Trim() } | Where-Object { $_ })
if ($changed.Count -eq 0) { Fail ("아무것도 안 바뀌었다 - claude 가 일을 못 했다(" + $outFile + " 확인)") }
# 🚨 2026-08-13 — 종전에는 '풀 이외의 파일이 하나라도 바뀌면 중단'이었다. 혼자 쓰는
#   저장소면 맞지만, 같은 저장소에서 사람이 동시에 작업하면 **매일 막힌다.** 실제로
#   08-13 에 리서치를 다 끝내고(13종 갱신 + 신규 E43) 커밋 직전에 막혔고, 그 작업물은
#   다른 세션의 autostash 로 치워져 하마터면 사라질 뻔했다.
#   → 관문이 잡으려던 것은 '사람의 작업물'이 아니라 **claude 가 엉뚱한 파일을 고친 것**이다.
#     그러니 시작 전부터 더러웠던 경로를 빼고 본다. 그것이 이 관문의 원래 질문이다.
#   ⚠ 커밋 대상은 아래에서 이미 세 파일로 한정돼 있다(git add ...) — 사람의 작업물이
#     딸려 들어가지 않는다. 그래서 중단하지 않아도 안전하다.
$unexpected = @($changed | Where-Object { $_ -ne "data/rotation_pool.json" -and $before -notcontains $_ })
$carried    = @($changed | Where-Object { $_ -ne "data/rotation_pool.json" -and $before -contains $_ })
if ($carried.Count -gt 0) {
  Say ("[i] 시작 전부터 사람이 작업 중이던 파일 " + $carried.Count + "개는 건드리지 않는다: " + ($carried -join ", "))
}
if ($unexpected.Count -gt 0) { Fail ("claude 가 풀 말고 다른 파일을 고쳤다: " + ($unexpected -join ", ")) }
if ($changed -notcontains "data/rotation_pool.json") { Fail "풀이 안 바뀌었다 - claude 가 일을 못 했다" }

# (b) 오늘 화면에 뜰 10선이 전부 오늘 갱신됐는가
$sel = & $Python (Join-Path $Repo "build\rotation_select.py") 2>&1
$fresh = @($sel | Where-Object { $_ -match "^(FRESH_OK|NOTFRESH)" }) | Select-Object -Last 1
Say ("신선도: " + $fresh)
if ($fresh -notmatch "^FRESH_OK") { Fail "오늘 화면 10선 중 갱신 안 된 카드가 있다 - 지시서의 '순서' 절 참조" }

# (c) 검증이 기준선보다 나빠지지 않았는가
$ai = & $Python (Join-Path $Repo "build\asof_index.py") 2>&1
if ($LASTEXITCODE -ne 0) { $ai | ForEach-Object { Say ("  " + $_) }; Fail "asof_index 실패" }
$vc = & $Python (Join-Path $Repo "build\validate_gate.py") check 2>&1
$vcExit = $LASTEXITCODE
$vc | ForEach-Object { Say ("  " + $_) }
if ($vcExit -ne 0) { Fail "검증이 기준선보다 나빠졌다 - 오늘 갱신이 무언가를 깼다" }

# ── ⑤ 갱신 피드 + 커밋·푸시 ────────────────────────────────────────────
$today = Get-Date -Format "yyyy-MM-dd"
$lu = & $Python (Join-Path $Repo "build\log_update.py") "rotation" $doneLine 2>&1
$lu | ForEach-Object { Say ("  " + $_) }

if ($DryRun) { Say "[DryRun] 여기까지. 커밋·푸시는 안 한다."; Say "===== 끝 ====="; exit 0 }

git add data/rotation_pool.json data/updates.json data/asof.json
# 🚨 git status 의 'M' 만 믿으면 안 된다. 이 저장소는 core.autocrlf=true 이고 커밋본은 LF 인데
#   파이썬이 파일을 LF 로 다시 쓰면 **내용이 똑같아도** 작업본이 M 으로 뜬다(줄끝 정규화).
#   그 상태로 커밋하면 'nothing to commit' 으로 죽는다. 스테이지에 실제로 뭔가 올라갔는지 본다.
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
  Fail "스테이지가 비었다 - 파일은 다시 써졌지만 내용이 그대로다. claude 가 실질적으로 아무것도 안 바꿨다."
}
git commit --quiet -m ("chore(rotation): " + $doneLine + " (" + $today + ")")
if ($LASTEXITCODE -ne 0) { Fail "커밋 실패" }
git push --quiet origin main
if ($LASTEXITCODE -ne 0) { Fail "푸시 실패 - 커밋은 남아 있다. 수동으로 push 할 것" }

Say ("[O] 완료 " + $headBefore + " -> " + (git rev-parse --short HEAD))
Say "===== 끝 ====="
exit 0

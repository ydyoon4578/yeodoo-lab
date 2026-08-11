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
git fetch --quiet origin
git pull --rebase --autostash --quiet origin main
if ($LASTEXITCODE -ne 0) { Fail "git pull 실패 - 충돌이 남아 있는지 확인할 것" }
$headBefore = (git rev-parse --short HEAD)
Say ("저장소 " + $headBefore)

# 시작 시점에 이미 더러우면 그것부터 알린다. 우리가 만든 변경과 안 섞이게.
$dirty0 = @(git status --porcelain)
if ($dirty0.Count -gt 0) { Say ("[!] 시작 전부터 작업 트리가 더럽다: " + ($dirty0 -join " / ")) }

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
$unexpected = @($changed | Where-Object { $_ -ne "data/rotation_pool.json" })
if ($unexpected.Count -gt 0) { Fail ("풀 말고 다른 파일이 바뀌었다: " + ($unexpected -join ", ")) }

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
git commit --quiet -m ("chore(rotation): " + $doneLine + " (" + $today + ")")
if ($LASTEXITCODE -ne 0) { Fail "커밋 실패" }
git push --quiet origin main
if ($LASTEXITCODE -ne 0) { Fail "푸시 실패 - 커밋은 남아 있다. 수동으로 push 할 것" }

Say ("[O] 완료 " + $headBefore + " -> " + (git rev-parse --short HEAD))
Say "===== 끝 ====="
exit 0

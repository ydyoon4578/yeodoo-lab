# 사내 배포 — 공개 저장소를 따라가서 배포본을 다시 굽는다.
# Windows 작업 스케줄러에 매일 걸어 두는 용도다.
#
# 🚨 이 스크립트가 하는 일은 **받아서 굽는 것뿐**이다. 자료 수집(refresh_*.py)은 하지 않는다.
#   그건 GitHub Actions 가 공개 저장소에서 하고 있고, 사내는 그 결과를 git pull 로 받는다.
#   단일 출처를 둘로 만들면 두 사이트가 다른 날짜를 말하는 사고가 난다.
#
# ⚠ 사내가 공개보다 **늦을 수는 있어도 앞설 수는 없다.** 그 시차는 사이트의 기준일 표가
#   스스로 보여 준다 — 숨기지 말 것.
#
# 사용:
#   powershell -ExecutionPolicy Bypass -File build\deploy_local.ps1 `
#              -Repo C:\yeodoo-lab -Base http://lab.corp.local -Web C:\inetpub\yeodoo

param(
  [Parameter(Mandatory=$true)][string]$Repo,   # 사내 체크아웃 경로
  [Parameter(Mandatory=$true)][string]$Base,   # 사내 URL 뿌리
  [Parameter(Mandatory=$true)][string]$Web,    # 웹서버가 읽는 경로
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$log = Join-Path $Repo "_deploy.log"
function Say($m) { $s = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m; Write-Host $s; Add-Content -Path $log -Value $s -Encoding utf8 }

Say "── 사내 배포 시작"
Set-Location $Repo

# ① 공개 저장소를 따라간다. 사내에서 저장소를 고치지 않았다면 늘 fast-forward 다.
$before = (git rev-parse --short HEAD)
git fetch --quiet origin
git reset --hard origin/main --quiet     # 🚨 사내 체크아웃은 **읽기 전용**이다. 여기서
                                          #   고쳤다면 그 수정은 지워진다 — 그러라고 둔 것이다.
                                          #   사내 전용 자료는 gitignore 대상이라 살아남는다.
$after = (git rev-parse --short HEAD)
if ($before -eq $after) { Say "저장소 변동 없음 ($after)" } else { Say "저장소 $before → $after" }

# ② 배포본을 굽는다(매번 새로).
Say "배포본 굽는 중…"
& $Python (Join-Path $Repo "build\deploy_local.py") --base $Base 2>&1 | ForEach-Object { Say "  $_" }
if ($LASTEXITCODE -ne 0) { Say "❌ 배포본 생성 실패 — 웹 경로는 건드리지 않는다"; exit 1 }

$src = Join-Path $Repo "_deploy"
if (-not (Test-Path (Join-Path $src "index.html"))) { Say "❌ index.html 이 없다 — 중단"; exit 1 }

# ③ 웹 경로로 옮긴다. 🚨 지우고 복사하지 않는다 — 그 사이에 접속하면 빈 사이트를 본다.
#    새 것을 옆에 만들고 **폴더 이름만 바꾼다**(거의 원자적).
$stage = "$Web.new"; $old = "$Web.old"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
Copy-Item $src $stage -Recurse
if (Test-Path $old) { Remove-Item $old -Recurse -Force }
if (Test-Path $Web) { Rename-Item $Web $old }
Rename-Item $stage $Web
if (Test-Path $old) { Remove-Item $old -Recurse -Force }

$n = (Get-ChildItem $Web -Recurse -File).Count
$mb = [math]::Round(((Get-ChildItem $Web -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 1)
Say "✅ 배포 완료 — $Web · 파일 $n 개 · $mb MB"
Say "   ⚠ gzip 과 data/*.json 짧은 캐시가 켜져 있는지 확인할 것(_nginx.conf · web.config 참고)"

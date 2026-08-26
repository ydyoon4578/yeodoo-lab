# pf — 운용 포트폴리오 갱신 명령을 이 PC 의 PowerShell 어디서나 쓸 수 있게 등록한다.
#
# 🚨 2026-08-26. 사내 PC 에서 `pf` 를 쳤더니 «용어가 인식되지 않습니다» 가 났다.
#   pf.bat 은 저장소 뿌리에 있는데, **PowerShell 은 보안상 현재 폴더의 명령을 안 부른다**
#   (cmd 는 부른다). 그래서 저장소 안에 서 있어도 `.\pf.bat` 이라고 쳐야 했다.
#   매번 그러기 번거로우니 프로필에 함수를 하나 박는다. 그러면 어느 폴더에서든 `pf` 다.
#
# ⚠ 저장소 경로를 이 파일에 **적지 않는다.** 이 스크립트가 놓인 자리($PSScriptRoot)에서
#   거슬러 올라가 pf.bat 을 찾는다 — PC 마다 클론 위치가 다르고(개인 PC C:\Users\USER\...,
#   사내 PC C:\Projects\...), 경로를 박으면 한쪽에서 조용히 엉뚱한 곳을 가리킨다.
#
# 사용:
#   powershell -ExecutionPolicy Bypass -File build\pf_alias_install.ps1
#   powershell -ExecutionPolicy Bypass -File build\pf_alias_install.ps1 -Remove
#
# 등록 뒤에는 **PowerShell 창을 새로 열어야** 적용된다(프로필은 시작할 때 한 번 읽는다).
#   지금 창에서 바로 쓰려면:  . $PROFILE

param(
  [switch]$Remove
)

$ErrorActionPreference = "Stop"

$BEGIN = "# >>> yeodoo-lab pf >>>"
$END   = "# <<< yeodoo-lab pf <<<"

# ── pf.bat 찾기 — 이 파일 기준 한 단계 위 ─────────────────────────────────────
$repo = Split-Path -Parent $PSScriptRoot
$bat  = Join-Path $repo "pf.bat"
if (-not $Remove -and -not (Test-Path $bat)) {
  Write-Host ("[X] pf.bat 을 못 찾았다: " + $bat)
  Write-Host "    이 스크립트는 저장소의 build\ 안에 있어야 한다(뿌리의 pf.bat 을 찾는다)."
  exit 1
}

# ── 프로필 파일 준비 ──────────────────────────────────────────────────────────
# ⚠ 파일에 New-Item -Force 를 쓰지 않는다 — 이미 있는 프로필을 통째로 비운다.
#   폴더에만 -Force 를 쓰고(없으면 만들고 있으면 그냥 넘어간다), 파일은 없을 때만 만든다.
$profileDir = Split-Path -Parent $PROFILE
if (-not (Test-Path $profileDir)) {
  New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
}
if (-not (Test-Path $PROFILE)) {
  New-Item -ItemType File -Path $PROFILE | Out-Null
  Write-Host ("[O] 프로필을 새로 만들었다: " + $PROFILE)
}

# 있던 내용에서 우리 블록만 걷어낸다(멱등 — 여러 번 돌려도 하나만 남는다)
$lines = @(Get-Content -Path $PROFILE -Encoding UTF8 -ErrorAction SilentlyContinue)
$kept  = New-Object System.Collections.Generic.List[string]
$inBlk = $false
$had   = $false
foreach ($ln in $lines) {
  if ($ln -eq $BEGIN) { $inBlk = $true; $had = $true; continue }
  if ($ln -eq $END)   { $inBlk = $false; continue }
  if (-not $inBlk)    { $kept.Add($ln) }
}

if ($Remove) {
  Set-Content -Path $PROFILE -Value $kept -Encoding UTF8
  if ($had) { Write-Host ("[O] pf 함수를 걷었다: " + $PROFILE) }
  else      { Write-Host "[-] 등록돼 있지 않았다 — 한 것 없음" }
  Write-Host "    새 PowerShell 창부터 반영된다."
  exit 0
}

# ── 이름 충돌 확인 ────────────────────────────────────────────────────────────
# ⚠ 남의 pf 를 조용히 덮지 않는다. 우리가 넣은 것(블록이 있던 경우)이면 갱신이고,
#   그 밖의 것이면 사람이 정할 일이다.
$existing = Get-Command pf -ErrorAction SilentlyContinue
if ($existing -and -not $had -and $existing.CommandType -ne "Application") {
  Write-Host ("[!] 이미 다른 pf 가 있다: " + $existing.CommandType + " — " + $existing.Source)
  Write-Host "    덮지 않는다. 그 정의를 지우고 다시 돌리거나, 다른 이름을 쓸 것."
  exit 1
}

$kept.Add($BEGIN)
$kept.Add("# 운용 포트폴리오 갱신 — build\pf_alias_install.ps1 이 넣었다(2026-08-26).")
$kept.Add("#   PowerShell 은 현재 폴더의 명령을 안 부르므로 저장소 안에서도 .\pf.bat 이어야 했다.")
$kept.Add(('function pf { & "' + $bat + '" @args }'))
$kept.Add($END)
Set-Content -Path $PROFILE -Value $kept -Encoding UTF8

$what = if ($had) { "pf 함수를 갱신했다" } else { "pf 함수를 넣었다" }
Write-Host ("[O] " + $what + ": " + $PROFILE)
Write-Host ("    pf -> " + $bat)
Write-Host ""
Write-Host '새 PowerShell 창을 열면 어느 폴더에서든 pf 로 돌아간다.'
Write-Host '지금 창에서 바로 쓰려면:  . $PROFILE'

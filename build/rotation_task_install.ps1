# KB_RotationDaily — 전략 탐색 풀 일일 갱신 작업을 이 PC 의 작업 스케줄러에 등록한다.
#
# 🚨 2026-08-11. 이 작업은 원래 회사 PC 에서 돌던 것이고, 그 PC 를 안 쓰게 되면서
#   2026-08-07 을 마지막으로 풀이 나흘 멈췄다. 멈춘 것을 아무도 몰랐다 —
#   등록 스크립트가 저장소에 없어서 '무엇이 어디서 돌고 있는지'가 어느 파일에도 안 적혀
#   있었기 때문이다. 그래서 이 파일을 저장소에 둔다. 다음에 PC 를 옮길 때는 이것만 돌리면 된다.
#
# 사용:
#   powershell -ExecutionPolicy Bypass -File build\rotation_task_install.ps1
#   powershell -ExecutionPolicy Bypass -File build\rotation_task_install.ps1 -At 09:20
#   powershell -ExecutionPolicy Bypass -File build\rotation_task_install.ps1 -Remove
#
# 확인:
#   Get-ScheduledTask KB_RotationDaily | Get-ScheduledTaskInfo    # 마지막 실행·결과
#   Start-ScheduledTask KB_RotationDaily                          # 지금 한 번 돌려 보기
#   Get-Content C:\Users\USER\yeodoo-lab\_rotation.log -Tail 40   # 무슨 일이 있었나

param(
  [string]$Repo = "C:\Users\USER\yeodoo-lab",
  [string]$At   = "07:55",      # KST. 사용자 결정 2026-08-11 — 갱신은 08:00 이전.
  [string]$Name = "KB_RotationDaily",
  [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
  if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    Write-Host ("[O] 작업 제거: " + $Name)
  } else {
    Write-Host ("작업이 없다: " + $Name)
  }
  exit 0
}

$runner = Join-Path $Repo "build\rotation_daily.ps1"
if (-not (Test-Path $runner)) { throw ("러너가 없다: " + $runner) }

# powershell.exe 를 직접 부른다. -NoProfile 은 프로파일 때문에 환경이 달라지는 것을 막고,
# -ExecutionPolicy Bypass 는 서명 없는 저장소 스크립트를 돌리기 위한 것이다.
$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $runner + '" -Repo "' + $Repo + '"') `
  -WorkingDirectory $Repo

$trigger = New-ScheduledTaskTrigger -Daily -At $At

# ⚠ 설정 하나하나가 실제 사고를 막는 것들이다:
#   StartWhenAvailable  — PC 가 그 시각에 꺼져 있었으면 켜진 뒤 곧바로 실행(사용자 결정).
#                         이게 없으면 그날은 통째로 건너뛴다. 나흘 멈춘 사고의 재발 지점이다.
#   DontStopIfGoingOnBatteries / AllowStartIfOnBatteries — 노트북에서 배터리로 바뀌어도 안 죽는다.
#   RunOnlyIfNetworkAvailable — 웹 리서치와 git push 가 필요하다. 망 없으면 시작도 안 한다.
#   ExecutionTimeLimit 2시간 — 러너 자체가 40분 타임아웃을 걸지만 이중으로 둔다.
#   MultipleInstances IgnoreNew — 어제 것이 아직 돌고 있으면 오늘 것을 새로 띄우지 않는다.
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -DontStopIfGoingOnBatteries `
  -AllowStartIfOnBatteries `
  -RunOnlyIfNetworkAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
  -MultipleInstances IgnoreNew

# 🚨 로그온한 사용자로 돈다(Interactive). '사용자 로그온 여부와 관계없이 실행'으로 두면
#   claude CLI 가 이 사용자의 OAuth 자격을 못 읽어 인증에서 죽는다. 무인 실행을 원하면
#   ANTHROPIC_API_KEY 를 시스템 환경변수로 두고 principal 을 바꿔야 하는데,
#   그건 키를 PC 에 평문으로 남기는 일이라 여기서는 안 한다.
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
                                        -LogonType Interactive -RunLevel Limited

if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $Name -Confirm:$false
  Write-Host ("기존 작업 제거 후 재등록: " + $Name)
}
Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger `
                       -Settings $settings -Principal $principal `
                       -Description ("여두 전략 랩 - 전략 탐색 풀(data/rotation_pool.json) 일일 웹리서치 갱신. " +
                                     "러너: build\rotation_daily.ps1 · 로그: _rotation.log") | Out-Null

$t = Get-ScheduledTask -TaskName $Name
Write-Host ("[O] 등록 완료: " + $Name + " · 매일 " + $At + " · 상태 " + $t.State)
Write-Host ("   러너 " + $runner)
Write-Host ("   로그 " + (Join-Path $Repo "_rotation.log"))
Write-Host "   지금 한 번 돌려 보려면: Start-ScheduledTask $Name"

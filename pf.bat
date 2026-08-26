@echo off
rem 운용 포트폴리오 갱신 — 이 파일을 더블클릭하거나 cmd 에서 `pf` 라고 치면 된다.
rem
rem ⚠ PowerShell 에서는 `pf` 가 안 먹는다 — 현재 폴더의 명령을 안 부르기 때문이다.
rem   그때는 `.\pf.bat` 이라고 치거나, 한 번만 아래를 돌려 프로필에 등록해 두면 된다:
rem     powershell -ExecutionPolicy Bypass -File build\pf_alias_install.ps1
python "%~dp0build\portfolio_go.py" %*

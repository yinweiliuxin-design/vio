@echo off
chcp 65001 >nul
set PYTHONDONTWRITEBYTECODE=1
set TEMP=E:\codex\Temp
set TMP=E:\codex\Temp
if exist E:\codex\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe (
  E:\codex\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -X utf8 "%~dp0restore.py"
) else (
  py -3 "%~dp0restore.py"
)
pause

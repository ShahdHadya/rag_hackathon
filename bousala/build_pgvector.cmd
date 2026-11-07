@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
set "PGROOT=C:\Program Files\PostgreSQL\18"
cd /d "%~dp0vendor\pgvector"
nmake /F Makefile.win
exit /b %errorlevel%

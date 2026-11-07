@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
set "PGROOT=C:\Program Files\PostgreSQL\18"
cd /d "%~dp0vendor\pgvector"
nmake /F Makefile.win install > "%~dp0reports\pgvector_install.log" 2>&1
set "install_result=%errorlevel%"
echo %install_result% > "%~dp0reports\pgvector_install.exitcode"
exit /b %install_result%

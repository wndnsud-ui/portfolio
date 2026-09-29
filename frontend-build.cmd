@echo off
set "NODE_DIR=%~dp0.tools\node-v24.19.0-win-x64"
set "PATH=%NODE_DIR%;%PATH%"
cd /d "%~dp0frontend"
call "%NODE_DIR%\npm.cmd" run build

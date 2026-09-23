@echo off
setlocal
cd /d "%~dp0dist\PodcastEpisodeTool"

if not exist "PodcastEpisodeTool.exe" (
    echo [ERROR] PodcastEpisodeTool.exe was not found.
    echo Run build_windows.ps1 first.
    pause
    exit /b 1
)

start "" "PodcastEpisodeTool.exe"
if errorlevel 1 (
    echo.
    echo [ERROR] The app stopped with an error.
    pause
)

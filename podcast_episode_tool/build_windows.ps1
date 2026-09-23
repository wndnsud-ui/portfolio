$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$output = Join-Path $PSScriptRoot "dist\PodcastEpisodeTool"
$savedEnv = Join-Path ([System.IO.Path]::GetTempPath()) ("PodcastEpisodeTool-" + [guid]::NewGuid().ToString("N") + ".env")
if (Test-Path -LiteralPath (Join-Path $output ".env")) {
    Copy-Item -LiteralPath (Join-Path $output ".env") -Destination $savedEnv -Force
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python 3.11 또는 3.12를 먼저 설치하고 PATH에 추가해 주세요."
    }
    $python = $pythonCommand.Source
}

$version = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0) {
    throw "실행 가능한 Python을 찾지 못했습니다. Microsoft Store 별칭이 아닌 Python이 필요합니다."
}
if ($version -notin @("3.11", "3.12")) {
    throw "Python 3.11 또는 3.12가 필요합니다. 현재 버전: $version"
}

Write-Host "Python $version 환경에서 빌드를 시작합니다."
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements-desktop.txt
& $python -m pip install "pyinstaller>=6.10"
& $python -m PyInstaller --noconfirm --clean PodcastEpisodeDesktop.spec

Copy-Item -LiteralPath ".env.example" -Destination $output -Force
if (Test-Path -LiteralPath $savedEnv) {
    Move-Item -LiteralPath $savedEnv -Destination (Join-Path $output ".env") -Force
}
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
$ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
if ($ffmpeg -and $ffprobe) {
    Copy-Item -LiteralPath $ffmpeg.Source -Destination $output -Force
    Copy-Item -LiteralPath $ffprobe.Source -Destination $output -Force
    Write-Host "FFmpeg와 FFprobe를 배포 폴더에 포함했습니다."
} else {
    Write-Warning "FFmpeg/FFprobe를 찾지 못해 포함하지 않았습니다. 음성 분할을 사용할 PC에 별도 설치가 필요합니다."
}
Write-Host ""
Write-Host "빌드 완료: $output\PodcastEpisodeTool.exe"
Write-Host "배포할 때는 PodcastEpisodeTool 폴더 전체를 전달하세요."

$archive = Join-Path $PSScriptRoot "dist\PodcastEpisodeTool-Windows.zip"
Compress-Archive -Path "$output\*" -DestinationPath $archive -Force
Write-Host "배포 ZIP: $archive"

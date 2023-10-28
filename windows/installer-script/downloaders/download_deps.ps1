# A script to download and install dependencies listed in a requirements file from pip
# Usage: .\download_deps.ps1 [-RequirementsFile <RequirementsFile>] [-PipPath <PipPath>]
# Example: .\download_deps.ps1 requirements.txt C:\Python\3.8.0\Scripts\pip.exe

param(
    [Parameter()]
    [string]$RequirementsFile="requirements.txt",
    [Parameter()]
    [string]$PipPath="Scripts\pip.exe",
    [Parameter()]
    [switch]$Update = $false
)

Write-Host "Installing dependencies"
& $PipPath config set global.index-url "https://pypi.tuna.tsinghua.edu.cn/simple"
if ($Update) {
    & $PipPath install -r $RequirementsFile --no-warn-script-location
} else {
    & $PipPath install -U embykeeper --no-warn-script-location
}
Write-Host "Done installing dependencies"


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
if ($Update) {
    & $PipPath install -i "https://pypi.tuna.tsinghua.edu.cn/simple" -r $RequirementsFile --no-warn-script-location
} else {
    & $PipPath install -i "https://pypi.tuna.tsinghua.edu.cn/simple" -U embykeeper --no-warn-script-location
}

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "Done installing dependencies"
} else {
    Write-Host "Failed to install dependencies, exit code: $exitCode"
}
exit $exitCode

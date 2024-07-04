# A script to download and install pip using get-pip.py
# Usage: .\download_pip.ps1 [-TargetDirectory <TargetDirectory>]
# Example: .\download_pip.ps1 -TargetDirectory C:\Python\3.8.0

param(
    [Parameter()]
    [string]$TargetDirectory=(Get-Location).Path
)

$PipUrl = "https://bootstrap.pypa.io/get-pip.py"
$PipFile = "$TargetDirectory\get-pip.py"
$PipExe = "$TargetDirectory\Scripts\pip.exe"

if (Test-Path $PipExe) {
    Write-Host "Pip already downloaded"
    exit 0
}

Write-Host "Downloading get-pip.py"
$Proxy = [System.Net.WebRequest]::GetSystemWebproxy()
$ProxyBypassed = $Proxy.IsBypassed($PipUrl)
if ($ProxyBypassed){
    Invoke-WebRequest -Uri $PipUrl -OutFile $PipFile
} else {
    $ProxyUrl = $Proxy.GetProxy($PipUrl)
    Invoke-WebRequest -Uri $PipUrl -OutFile $PipFile -Proxy $ProxyUrl -ProxyUseDefaultCredentials
}

Write-Host "Installing pip"
& $TargetDirectory\python.exe $PipFile --no-warn-script-location -i "https://pypi.tuna.tsinghua.edu.cn/simple"
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "Done installing pip"
} else {
    Write-Host "Failed to install pip, exit code: $exitCode"
}
exit $exitCode
# NOP Certificate Downloader - Launcher
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"
python "$PSScriptRoot\certificate-downloader\download_by_nop.py"

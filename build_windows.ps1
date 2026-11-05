param([string]$Python = 'python', [string]$SourceCache = $env:AZB_SOURCE_CACHE, [switch]$OfflineSources)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'vendor/ffmpeg.exe')) {
    throw 'Build the audio-only LGPL FFmpeg first; see vendor/README.md.'
}
& $Python -m PyInstaller --noconfirm --clean --distpath dist --workpath build studio.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
$taskRelease = Join-Path $PSScriptRoot 'dist/Voxriva'
New-Item -ItemType Directory -Path (Join-Path $taskRelease 'app') -Force | Out-Null
Get-ChildItem -LiteralPath app -Filter '*.py' -File | Copy-Item -Destination (Join-Path $taskRelease 'app') -Force
Copy-Item -LiteralPath README.md, README_FA.md, LICENSE, THIRD_PARTY_NOTICES.md -Destination $taskRelease -Force
$taskNoticeArgs = @('scripts/prepare_notices.py', '--release', $taskRelease)
if ($SourceCache) { $taskNoticeArgs += @('--source-cache', $SourceCache) }
if ($OfflineSources) { $taskNoticeArgs += '--offline' }
if ($env:AZB_QT_PATH) { $taskNoticeArgs += @('--package-path', $env:AZB_QT_PATH) }
& $Python @taskNoticeArgs
if ($LASTEXITCODE -ne 0) { throw 'Matching source/notice preparation failed; do not redistribute this incomplete build.' }
Copy-Item -LiteralPath FEATURES_2_1.md -Destination $taskRelease -Force
Copy-Item -LiteralPath installer/NSIS-COPYING.txt -Destination (Join-Path $taskRelease 'Licenses/NSIS-COPYING.txt') -Force
Write-Host 'Model-free binary, matching source archives and third-party notices prepared.'

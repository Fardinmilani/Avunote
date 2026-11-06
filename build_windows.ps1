param([string]$Python = 'python', [string]$SourceCache = $env:AZB_SOURCE_CACHE, [switch]$OfflineSources)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'vendor/ffmpeg.exe')) {
    throw 'Build the audio-only LGPL FFmpeg first; see vendor/README.md.'
}
& $Python -m PyInstaller --noconfirm --clean --distpath dist --workpath build studio.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
$taskRelease = Join-Path $PSScriptRoot 'dist/Avunote'
New-Item -ItemType Directory -Path (Join-Path $taskRelease 'app') -Force | Out-Null
Get-ChildItem -LiteralPath app -Filter '*.py' -File | Copy-Item -Destination (Join-Path $taskRelease 'app') -Force
Copy-Item -LiteralPath README.md, README_FA.md, LICENSE, THIRD_PARTY_NOTICES.md -Destination $taskRelease -Force
New-Item -ItemType Directory -Path (Join-Path $taskRelease 'docs') -Force | Out-Null
Copy-Item -LiteralPath docs/BRAND.md -Destination (Join-Path $taskRelease 'docs') -Force
Copy-Item -LiteralPath docs/UPDATES.md -Destination (Join-Path $taskRelease 'docs') -Force
New-Item -ItemType Directory -Path (Join-Path $taskRelease 'scripts') -Force | Out-Null
Copy-Item -LiteralPath scripts/build_brand_assets.py -Destination (Join-Path $taskRelease 'scripts') -Force
New-Item -ItemType Directory -Path (Join-Path $taskRelease 'assets') -Force | Out-Null
Copy-Item -LiteralPath assets/avunote-logo-transparent.png, assets/avunote-mark.png, assets/avunote-brand-preview.png, assets/avunote.ico -Destination (Join-Path $taskRelease 'assets') -Force
New-Item -ItemType Directory -Path (Join-Path $taskRelease 'assets/fonts') -Force | Out-Null
Copy-Item -Path assets/fonts/* -Destination (Join-Path $taskRelease 'assets/fonts') -Force
$taskNoticeArgs = @('scripts/prepare_notices.py', '--release', $taskRelease)
if ($SourceCache) { $taskNoticeArgs += @('--source-cache', $SourceCache) }
if ($OfflineSources) { $taskNoticeArgs += '--offline' }
if ($env:AZB_QT_PATH) { $taskNoticeArgs += @('--package-path', $env:AZB_QT_PATH) }
& $Python @taskNoticeArgs
if ($LASTEXITCODE -ne 0) { throw 'Matching source/notice preparation failed; do not redistribute this incomplete build.' }
Copy-Item -LiteralPath FEATURES_2_2.md -Destination $taskRelease -Force
Copy-Item -LiteralPath installer/NSIS-COPYING.txt -Destination (Join-Path $taskRelease 'Licenses/NSIS-COPYING.txt') -Force
Write-Host 'Model-free binary, matching source archives and third-party notices prepared.'

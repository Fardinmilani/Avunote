<#
Build from the current checkout; never repack an old application runtime.

Machine-local optional configuration: .local/build-settings.json
  Python, QtPath, SourceCache, Makensis
Paths are relative to the repository root unless absolute. No credentials belong
in this file. Keep .local/ ignored in Git. Dependencies are not installed here.
#>
param(
    [string]$Version,
    [switch]$CheckOnly,
    [switch]$SkipTests,
    [switch]$AllowSourceDownloads,
    [switch]$DownloadNsis
)

$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskLocal = Join-Path $taskRoot '.local'
$taskLogs = Join-Path $taskLocal 'build-logs'
$taskExit = 1
$taskTranscript = $false
$taskLock = $null
$taskLocationPushed = $false
$taskEnvironmentNames = @('PYTHONPATH','AZB_QT_PATH','AZB_SOURCE_CACHE',
    'VOXRIVA_SUPPRESS_PROMPTS','VOXRIVA_DATA_DIR','QT_QPA_PLATFORM',
    'HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HUB_DISABLE_TELEMETRY')
$taskOriginalEnvironment = @{}
foreach ($taskName in $taskEnvironmentNames) {
    $taskOriginalEnvironment[$taskName] = [Environment]::GetEnvironmentVariable($taskName, 'Process')
}

function Resolve-BuildPath([string]$Value) {
    if (-not $Value) { return $null }
    if ([IO.Path]::IsPathRooted($Value)) { return [IO.Path]::GetFullPath($Value) }
    return [IO.Path]::GetFullPath((Join-Path $taskRoot $Value))
}

function Get-LocalSetting([object]$Settings, [string]$Name) {
    if ($Settings -and $Settings.PSObject.Properties[$Name]) {
        return [string]$Settings.PSObject.Properties[$Name].Value
    }
    return $null
}

try {
    New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null
    $taskStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $taskLog = Join-Path $taskLogs ("setup-"+$taskStamp+'.log')
    Start-Transcript -LiteralPath $taskLog -Force | Out-Null
    $taskTranscript = $true
    try {
        $taskLock = [IO.File]::Open((Join-Path $taskLocal 'setup-build.lock'),
            [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    } catch {
        throw 'Another Voxriva Setup build is running. Wait for it to finish before starting another.'
    }
    Push-Location -LiteralPath $taskRoot
    $taskLocationPushed = $true

    if (-not $Version) { $Version = (Get-Content -LiteralPath (Join-Path $taskRoot 'VERSION') -Raw).Trim() }
    if ($Version -notmatch '^\d+\.\d+\.\d+$' -or @($Version.Split('.') | Where-Object { [int64]$_ -gt 65535 }).Count) {
        throw 'VERSION must contain a Windows-compatible version such as 2.1.1 (three numbers, each <= 65535).'
    }
    Write-Host "Voxriva $Version - build from current source"
    Write-Host "Project: $taskRoot"
    Write-Host "Log: $taskLog"
    $taskSettingsPath = Join-Path $taskLocal 'build-settings.json'
    $taskSettings = $null
    if (Test-Path -LiteralPath $taskSettingsPath) {
        $taskSettings = Get-Content -LiteralPath $taskSettingsPath -Raw | ConvertFrom-Json
    }

    $taskPythonValue = Get-LocalSetting $taskSettings 'Python'
    if ($taskPythonValue) {
        $taskPython = Resolve-BuildPath $taskPythonValue
    } elseif (Test-Path -LiteralPath (Join-Path $taskRoot '.venv/Scripts/python.exe')) {
        $taskPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
    } else {
        throw 'Build Python is missing. Prepare a project-local .venv as described in README, or set Python in .local/build-settings.json.'
    }
    if (-not (Test-Path -LiteralPath $taskPython -PathType Leaf)) {
        throw "Build Python does not exist: $taskPython. Update .local/build-settings.json or create .venv."
    }
    $taskQt = Resolve-BuildPath (Get-LocalSetting $taskSettings 'QtPath')
    if ($taskQt -and -not (Test-Path -LiteralPath $taskQt -PathType Container)) { throw "QtPath is missing: $taskQt" }
    $env:PYTHONPATH = Join-Path $taskRoot 'app'
    if ($taskQt) {
        $env:PYTHONPATH = $taskQt+[IO.Path]::PathSeparator+$env:PYTHONPATH
        $env:AZB_QT_PATH = $taskQt
    } else {
        Remove-Item Env:AZB_QT_PATH -ErrorAction SilentlyContinue
    }
    $env:VOXRIVA_SUPPRESS_PROMPTS = '1'
    $env:VOXRIVA_DATA_DIR = Join-Path $taskLocal 'build-test-profile'
    $env:QT_QPA_PLATFORM = 'offscreen'
    $env:HF_HUB_OFFLINE = '1'
    $env:TRANSFORMERS_OFFLINE = '1'
    $env:HF_HUB_DISABLE_TELEMETRY = '1'

    $taskSourceCache = Resolve-BuildPath (Get-LocalSetting $taskSettings 'SourceCache')
    if (-not $taskSourceCache) { $taskSourceCache = Join-Path $taskLocal 'source-cache' }
    $env:AZB_SOURCE_CACHE = $taskSourceCache
    $taskFfmpeg = Join-Path $taskRoot 'vendor/ffmpeg.exe'
    if (-not (Test-Path -LiteralPath $taskFfmpeg -PathType Leaf)) {
        throw 'vendor/ffmpeg.exe is missing. Build the matching LGPL decoder described in vendor/README.md, or use the GitHub Actions Windows build. No replacement decoder is downloaded automatically.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'vendor/FFmpeg-source') -PathType Container) -and
        -not (Test-Path -LiteralPath (Join-Path $taskSourceCache 'FFmpeg-build') -PathType Container)) {
        throw 'Matching FFmpeg build records are missing. Restore vendor/FFmpeg-source or the source-cache FFmpeg-build directory; see vendor/README.md.'
    }

    $taskMakensis = Resolve-BuildPath (Get-LocalSetting $taskSettings 'Makensis')
    if (-not $taskMakensis -and $env:NSIS_HOME) { $taskMakensis = Join-Path $env:NSIS_HOME 'makensis.exe' }
    if (-not $taskMakensis) {
        $taskCompiler = Get-Command makensis.exe -ErrorAction SilentlyContinue
        if ($taskCompiler) { $taskMakensis = $taskCompiler.Source }
    }
    if ($taskMakensis -and -not (Test-Path -LiteralPath $taskMakensis -PathType Leaf)) {
        throw "NSIS compiler is missing: $taskMakensis. Update Makensis in .local/build-settings.json."
    }
    if (-not $taskMakensis -and -not $DownloadNsis) {
        throw 'NSIS 3.13 is missing. Set Makensis in .local/build-settings.json, or explicitly run BUILD_SETUP.cmd -DownloadNsis (2.36 MB, local portable tool only).'
    }
    if ($taskMakensis) {
        $taskCompilerVersion = ([string](& $taskMakensis /VERSION)).Trim()
        if ($LASTEXITCODE -ne 0 -or $taskCompilerVersion -ne 'v3.13') { throw 'This project uses the pinned NSIS 3.13 compiler.' }
    }

    # The Python check imports the actual build environment and the source pins
    # maintained by prepare_notices.py, rather than duplicating those hashes.
    $taskPreflight = @'
import hashlib, importlib.metadata as m, os, pathlib, sys
if not (sys.platform == 'win32' and sys.maxsize > 2**32 and (3,11) <= sys.version_info[:2] <= (3,13)):
    raise RuntimeError('Use Windows x64 CPython 3.11-3.13 in the local build environment.')
import PyInstaller, PySide6.QtWidgets, torch, transformers, tokenizers, ctranslate2, numpy, psutil, requests, sounddevice, safetensors
if torch.version.cuda is not None:
    raise RuntimeError('Use the CPU-only PyTorch build documented in README to avoid bundling multi-gigabyte CUDA libraries.')
if m.version('PySide6-Essentials') != '6.12.0' or m.version('shiboken6') != '6.12.0':
    raise RuntimeError('Matching source notices require PySide6-Essentials/shiboken6 6.12.0.')
sys.path.insert(0, str(pathlib.Path(sys.argv[1])/'scripts'))
from prepare_notices import SOURCES, INTEL_PACKAGE, INTEL_PACKAGE_SHA256
cache=pathlib.Path(sys.argv[2]); allow=sys.argv[3] == 'True'; missing=[]
for name, expected in [(x[0],x[2]) for x in SOURCES]+[(INTEL_PACKAGE,INTEL_PACKAGE_SHA256)]:
    path=cache/name
    if not path.is_file():
        missing.append(name); continue
    with path.open('rb') as stream:
        actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual != expected:
        raise RuntimeError('Matching-source cache hash mismatch: '+name)
if missing and not allow:
    raise RuntimeError('Matching-source cache is incomplete: '+', '.join(missing)+'. Restore SourceCache, or explicitly use -AllowSourceDownloads (about 85 MB library sources + 2.2 MB Intel runtime, no ASR models).')
print('Build Python and CPU runtime verified: '+sys.executable)
print('Matching-source cache verified.' if not missing else 'Explicit source download enabled for: '+', '.join(missing))
'@
    & $taskPython -c $taskPreflight $taskRoot $taskSourceCache ([string][bool]$AllowSourceDownloads)
    if ($LASTEXITCODE -ne 0) { throw 'Build prerequisites are not ready. Read the Python diagnostic above; no dependencies were installed.' }
    $taskDrive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($taskRoot))
    Write-Host ('Free disk space: {0:N1} GB' -f ($taskDrive.AvailableFreeSpace/1GB))
    if ($CheckOnly) {
        Write-Host 'Prerequisite check passed. No application or Setup build was started.'
        $taskExit = 0
    } else {
        if ($taskDrive.AvailableFreeSpace -lt 4GB) { throw 'At least 4 GB of free workspace is needed for a fresh runtime and Setup build.' }
        if ($AllowSourceDownloads) { Write-Host 'Matching library-source downloads are explicitly allowed (about 85 MB + 2.2 MB if absent). No language model is downloaded.' }
        if ($DownloadNsis -and -not $taskMakensis) { Write-Host 'The pinned NSIS portable compiler may be downloaded (2.36 MB).' }
        if (-not $SkipTests) {
            Write-Host 'Running local regression tests without model downloads...'
            & $taskPython -m unittest discover -s (Join-Path $taskRoot 'tests') -v
            if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed. No new installer will be produced.' }
        }
        Write-Host 'Rebuilding the application from the current source...'
        & (Join-Path $taskRoot 'build_windows.ps1') -Python $taskPython -SourceCache $taskSourceCache -OfflineSources:(-not $AllowSourceDownloads)
        $taskRelease = Join-Path $taskRoot 'dist/Voxriva'
        foreach ($taskSource in Get-ChildItem -LiteralPath (Join-Path $taskRoot 'app') -Filter '*.py' -File) {
            $taskCopied = Join-Path $taskRelease ('app/'+$taskSource.Name)
            if (-not (Test-Path -LiteralPath $taskCopied) -or
                (Get-FileHash -LiteralPath $taskSource.FullName -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $taskCopied -Algorithm SHA256).Hash) {
                throw 'The source changed during the build or was not copied completely. Wait for editing to finish, then build again.'
            }
        }
        $taskOutput = Join-Path $taskRoot ("release/Voxriva-$Version-Windows-x64-Setup.exe")
        $taskInstallerArguments = @{ ReleaseDir=$taskRelease; Version=$Version; OutputPath=$taskOutput }
        if ($taskMakensis) { $taskInstallerArguments['Makensis'] = $taskMakensis }
        if ($DownloadNsis) { $taskInstallerArguments['DownloadNsis'] = $true }
        & (Join-Path $taskRoot 'scripts/build_installer.ps1') @taskInstallerArguments
        if (-not (Test-Path -LiteralPath $taskOutput -PathType Leaf)) { throw 'Installer output was not created.' }
        Write-Host ''
        Write-Host "SETUP READY: $taskOutput" -ForegroundColor Green
        Write-Host "SHA-256: $taskOutput.sha256.txt"
        Write-Host "Portable app: $taskRelease"
        Write-Host 'Publish the Setup file in GitHub Releases. Keep .local, build, dist, release and model files out of Git.'
        $taskExit = 0
    }
} catch {
    Write-Host ''
    Write-Host ('BUILD FAILED: '+$_.Exception.Message) -ForegroundColor Red
    if ($taskLog) { Write-Host "Log: $taskLog" }
} finally {
    if ($taskLock) { $taskLock.Dispose() }
    if ($taskLocationPushed) { Pop-Location }
    foreach ($taskName in $taskEnvironmentNames) {
        [Environment]::SetEnvironmentVariable($taskName, $taskOriginalEnvironment[$taskName], 'Process')
    }
    if ($taskTranscript) { Stop-Transcript | Out-Null }
}
exit $taskExit

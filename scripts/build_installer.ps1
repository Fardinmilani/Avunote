param(
    [Parameter(Mandatory=$true)][string]$ReleaseDir,
    [string]$OutputPath,
    [string]$Makensis,
    [ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version = '2.1.1',
    [switch]$DownloadNsis,
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$taskSourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskReleaseRoot = (Resolve-Path -LiteralPath $ReleaseDir).Path.TrimEnd('\','/')
if (-not $OutputPath) { $OutputPath = Join-Path $taskSourceRoot "release/Voxriva-$Version-Windows-x64-Setup.exe" }
$taskOutput = [IO.Path]::GetFullPath($OutputPath)
$taskBuild = Join-Path $taskSourceRoot 'build/installer'
New-Item -ItemType Directory -Path $taskBuild -Force | Out-Null
New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($taskOutput)) -Force | Out-Null

foreach ($taskRequired in @('Voxriva.exe','LICENSE','THIRD_PARTY_NOTICES.md','Licenses','_internal','app')) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskReleaseRoot $taskRequired))) { throw "Incomplete release: $taskRequired" }
}
$taskEntries = @(Get-ChildItem -LiteralPath $taskReleaseRoot -Recurse -Force)
if ($taskEntries | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
    throw 'Release payload must not contain symlinks, junctions or other reparse points.'
}
$taskFiles = @()
function Get-PayloadRelative([string]$FullName) {
    if (-not $FullName.StartsWith($taskReleaseRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Payload path escaped release directory' }
    return $FullName.Substring($taskReleaseRoot.Length+1).Replace('/','\')
}
foreach ($taskFile in $taskEntries | Where-Object { -not $_.PSIsContainer }) {
    $taskRelative = Get-PayloadRelative $taskFile.FullName
    $taskParts = $taskRelative.Split('\')
    if ($taskParts -contains '__pycache__' -or $taskFile.Extension -eq '.log') { continue }
    if ($taskParts[0] -in @('Data','data','models','cache','recordings','results','validation','ai-chats') -or
        $taskRelative -match '(^|\\)assets\\models(\\|$)' -or
        $taskRelative -match '(^|\\)ai-chats(\\|$)' -or $taskFile.Name -eq 'ai-profiles.json' -or
        $taskFile.Extension.ToLowerInvariant() -in @('.safetensors','.pt','.pth','.onnx','.gguf','.part','.wav','.mp3','.m4a','.ogg','.flac','.aac') -or
        $taskFile.Name -eq 'model.bin' -or $taskFile.Name -match '^openvino_.*\.bin$' -or $taskRelative -match '(^|\\)\.env($|\.)') {
        throw "Refusing private data or model weights in installer: $taskRelative"
    }
    if ($taskParts.Count -eq 1 -and $taskFile.Name -notin @('Voxriva.exe','LICENSE','README.md','README_FA.md','THIRD_PARTY_NOTICES.md','FEATURES_2_1.md','manifest.json')) {
        throw "Unrecognized release-root file; do not package machine-local state: $taskRelative"
    }
    if ($taskRelative -match '(^|\\)\.\.($|\\)' -or [IO.Path]::IsPathRooted($taskRelative)) { throw 'Unsafe payload path' }
    $taskFiles += [pscustomobject]@{ Relative = $taskRelative; Bytes = $taskFile.Length }
}
if ($taskOutput.StartsWith($taskReleaseRoot+'\',[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Installer output must not be placed inside its input payload.'
}
function ConvertTo-NsisLiteral([string]$Value) { return $Value.Replace('$','$$').Replace('"','$\"') }
$taskLines = [Collections.Generic.List[string]]::new()
$taskLines.Add('; Generated exact-file removal list. Unknown files and user data are retained.')
foreach ($taskFile in $taskFiles) {
    $taskLines.Add('Delete "$INSTDIR\'+(ConvertTo-NsisLiteral $taskFile.Relative)+'"')
}
$taskDirs = @($taskEntries | Where-Object { $_.PSIsContainer } | ForEach-Object {
    Get-PayloadRelative $_.FullName
} | Where-Object { $_.Split('\') -notcontains '__pycache__' } | Sort-Object { $_.Length } -Descending)
foreach ($taskDir in $taskDirs) { $taskLines.Add('RMDir "$INSTDIR\'+(ConvertTo-NsisLiteral $taskDir)+'"') }
$taskManifest = Join-Path $taskBuild 'uninstall-files.nsh'
[IO.File]::WriteAllLines($taskManifest,$taskLines,[Text.UTF8Encoding]::new($false))
$taskPayloadManifest = Join-Path $taskBuild 'payload-manifest.json'
$taskPayload = [ordered]@{ version=$Version; files=$taskFiles; total_bytes=($taskFiles | Measure-Object Bytes -Sum).Sum }
[IO.File]::WriteAllText($taskPayloadManifest,($taskPayload | ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
Write-Host "Verified model-free payload: $($taskFiles.Count) files, $($taskPayload.total_bytes) bytes."
if ($PrepareOnly) { Write-Host "Uninstall manifest: $taskManifest"; return }

if (-not $Makensis -and $env:NSIS_HOME) { $Makensis = Join-Path $env:NSIS_HOME 'makensis.exe' }
if (-not $Makensis) {
    $taskCommand = Get-Command makensis.exe -ErrorAction SilentlyContinue
    if ($taskCommand) { $Makensis = $taskCommand.Source }
}
if (-not $Makensis -and $DownloadNsis) {
    # Pinned official portable compiler: 2,363,925 bytes; no global installation.
    $taskToolRoot = Join-Path $taskSourceRoot 'build/nsis'
    New-Item -ItemType Directory -Path $taskToolRoot -Force | Out-Null
    $taskZipPath = Join-Path $taskToolRoot 'nsis-3.13.zip'
    $taskSha = 'ba63dffc4410ee89193e1cb5a41989991bd77c61068da17e3156d136b7b0b3d8'
    if (-not (Test-Path -LiteralPath $taskZipPath)) {
        Write-Host 'Downloading the 2.36 MB NSIS 3.13 portable compiler; models and audio are not transferred.'
        Invoke-WebRequest -Uri 'https://downloads.sourceforge.net/project/nsis/NSIS%203/3.13/nsis-3.13.zip' -OutFile $taskZipPath
    }
    if ((Get-Item -LiteralPath $taskZipPath).Length -ne 2363925 -or (Get-FileHash -LiteralPath $taskZipPath -Algorithm SHA256).Hash -ne $taskSha) {
        throw 'NSIS archive size or SHA-256 does not match the official release.'
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $taskArchive = [IO.Compression.ZipFile]::OpenRead($taskZipPath)
    try {
        foreach ($taskEntry in $taskArchive.Entries) {
            $taskTarget = [IO.Path]::GetFullPath((Join-Path $taskToolRoot $taskEntry.FullName))
            if (-not $taskTarget.StartsWith($taskToolRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe NSIS archive path' }
        }
    } finally { $taskArchive.Dispose() }
    Expand-Archive -LiteralPath $taskZipPath -DestinationPath $taskToolRoot -Force
    $Makensis = Join-Path $taskToolRoot 'nsis-3.13/makensis.exe'
}
if (-not $Makensis -or -not (Test-Path -LiteralPath $Makensis)) {
    throw 'Provide -Makensis, set NSIS_HOME, or explicitly use -DownloadNsis (2.36 MB portable build tool).'
}
$taskCompilerVersion = ([string](& $Makensis /VERSION)).Trim()
if ($LASTEXITCODE -ne 0 -or $taskCompilerVersion -ne 'v3.13') {
    throw 'Use NSIS 3.13 to match the pinned toolchain and included installer copyright/license notice.'
}
$taskEstimated = [Math]::Ceiling($taskPayload.total_bytes/1024)
$taskArgs = @('/NOCONFIG','/V3',"/DRELEASEDIR=$taskReleaseRoot", "/DUNINSTALL_INCLUDE=$taskManifest",
              "/DOUTPUT_EXE=$taskOutput", "/DSOURCE_ROOT=$taskSourceRoot", "/DAPP_VERSION=$Version", "/DESTIMATED_KIB=$taskEstimated",
              (Join-Path $taskSourceRoot 'installer/voxriva.nsi'))
& $Makensis @taskArgs
if ($LASTEXITCODE -ne 0) { throw 'NSIS installer compilation failed.' }
$taskHash = (Get-FileHash -LiteralPath $taskOutput -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText($taskOutput+'.sha256.txt',($taskHash+'  '+[IO.Path]::GetFileName($taskOutput)+[Environment]::NewLine),[Text.UTF8Encoding]::new($false))
Write-Host "Installer ready: $taskOutput"

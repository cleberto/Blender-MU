# Create the local baseline if absent, then open it in Blender 5.2.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$blenderExe = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$baseline = Join-Path $projectRoot 'work\monster03\budge-dragon-baseline-v2.blend'
if (-not (Test-Path -LiteralPath $blenderExe)) { throw "Blender 5.2 not found: $blenderExe" }
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath $baseline)) {
        py -3.9 tools\decode_legacy_textures.py
        if ($LASTEXITCODE -ne 0) { throw 'Texture decoding failed' }
        & $blenderExe -b --python tools\prepare_dragon_baseline.py
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $baseline)) { throw 'Baseline creation failed' }
    }
    Start-Process -FilePath $blenderExe -ArgumentList @($baseline)
} finally {
    Pop-Location
}

[CmdletBinding()]
param(
    [ValidateSet('build', 'smoke', 'full')][string]$Suite = 'smoke',
    [string]$GameClient = 'C:\Games\World_of_Tanks_EU',
    [string]$Profile,
    [string]$OutputDirectory,
    [string]$Python,
    [string]$Chrome,
    [switch]$FinalOnly,
    [switch]$Plan
)

$ErrorActionPreference = 'Stop'
$node = (Get-Command node -CommandType Application).Source
$deps = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $node))
$bundledPython = Join-Path $deps 'python/python.exe'
$bundledModules = Join-Path $deps 'node/node_modules'
$venv = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (!$Python) {
    if ($env:SESSIONSTATS_PYTHON) { $Python = $env:SESSIONSTATS_PYTHON }
    elseif (Test-Path -LiteralPath $venv) { $Python = $venv }
    elseif (Test-Path -LiteralPath $bundledPython) { $Python = $bundledPython }
    else { $Python = 'python' }
}
if (!$Chrome) {
    $edge = Join-Path ${env:ProgramFiles(x86)} 'Microsoft/Edge/Application/msedge.exe'
    if (Test-Path -LiteralPath $edge) { $Chrome = $edge }
}
$runner = Join-Path $PSScriptRoot 'run.cjs'
$options = @('--engine', 'chromium', '--suite', $Suite, '--python', $Python,
    '--game-client', $GameClient)
if ($OutputDirectory) { $options += @('--out', $OutputDirectory) }
if ($Profile) { $options += @('--profile', $Profile) }
if ($Chrome) { $options += @('--chrome', $Chrome) }
if ($Suite -eq 'full') { $options += '--all-ranges' }
if ($FinalOnly) { $options += @('--capture', 'final', '--image-format', 'jpeg') }
if ($Plan) { $options += '--plan' }
$originalModules = $env:NODE_PATH
try {
    if (!$originalModules -and (Test-Path -LiteralPath (Join-Path $bundledModules 'playwright'))) {
        $env:NODE_PATH = $bundledModules
    }
    & $node $runner @options
    $result = $LASTEXITCODE
} finally {
    $env:NODE_PATH = $originalModules
}
exit $result

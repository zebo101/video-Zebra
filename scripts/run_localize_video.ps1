$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillDir = Split-Path -Parent $scriptDir
$scriptPath = Join-Path $scriptDir "localize_video.py"
$venvPython = Join-Path $skillDir ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
  & $venvPython $scriptPath @args
  exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
  & $python.Source $scriptPath @args
  exit $LASTEXITCODE
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
  & $py.Source -3 $scriptPath @args
  exit $LASTEXITCODE
}

Write-Error "Missing Python runtime. Create $skillDir\.venv or install Python."
exit 1

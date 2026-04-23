# nexo bootstrap script - ensures nexo is available in any terminal session
# Usage: powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\nexo\bin\nexo-bootstrap.ps1"
# Or after install: powershell -ExecutionPolicy Bypass -File "$(dirname (Get-Command nexo).Source)\nexo-bootstrap.ps1"

$ErrorActionPreference = "SilentlyContinue"

# Determine the install directory (where this script lives)
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$NEXO_OUT_DIR = "nexo-out"

# Create nexo-out directory if it doesn't exist
if (!(Test-Path $NEXO_OUT_DIR)) {
    New-Item -ItemType Directory -Path $NEXO_OUT_DIR | Out-Null
}

# Step 1: Try to find 'nexo' command on PATH
$nexoCmd = Get-Command nexo -ErrorAction SilentlyContinue

if ($nexoCmd) {
    # Verify it works
    & $nexoCmd.Source --help 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Found working 'nexo' command: $($nexoCmd.Source)"
        $nexoCmd.Source | Out-File -FilePath "$NEXO_OUT_DIR\.nexo_bin" -Encoding utf8 -NoNewline
        exit 0
    }
}

# Step 2: Fallback to python -m nexo
Write-Host "nexo command not found, trying python..."
$python = Get-Command python -ErrorAction SilentlyContinue

if ($python) {
    & $python.Source -c "import nexo" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing nexo via pip..."
        & $python.Source -m pip install nexo -q 2>$null
        if ($LASTEXITCODE -ne 0) {
            & $python.Source -m pip install nexo -q --break-system-packages 2>&1 | Out-Null
        }
    }

    & $python.Source -c "import nexo" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Using python -m nexo"
        "$($python.Source) -m nexo" | Out-File -FilePath "$NEXO_OUT_DIR\.nexo_bin" -Encoding utf8 -NoNewline
        exit 0
    }
}

# Step 3: Try 'py' command (Windows Python launcher)
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & $py.Source -c "import nexo" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $py.Source -m pip install nexo -q 2>$null
        if ($LASTEXITCODE -ne 0) {
            & $py.Source -m pip install nexo -q --break-system-packages 2>&1 | Out-Null
        }
    }

    & $py.Source -c "import nexo" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Using py -m nexo"
        "$($py.Source) -m nexo" | Out-File -FilePath "$NEXO_OUT_DIR\.nexo_bin" -Encoding utf8 -NoNewline
        exit 0
    }
}

# Failure
Write-Error "Failed to find or install nexo. Please install it manually: pip install nexo"
exit 1

# Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
# See NOTICE and CHANGELOG.md for the nature of the modifications.
# ======================================================================
#  VibecodersCrew — Windows source installer
# ======================================================================
#  Run this script from a local checkout. It builds the in-tree dashboard,
#  creates an isolated Python environment, and installs the package in
#  editable mode. It performs local source setup only; remote infrastructure,
#  model downloads, and provider logins remain explicit follow-up actions.
#
#  Usage (PowerShell):
#    Set-ExecutionPolicy -Scope Process Bypass
#    .\install.ps1 [-Voice] [-NonInteractive]
#
#  -Voice          Install the optional voice dependencies.
#  -NonInteractive Keep compatibility with automation callers. This installer
#                  has no prompts and does not launch a service.
# ======================================================================
[CmdletBinding()]
param(
    [switch]$Voice,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"

function Write-Step([int]$n, [int]$total, [string]$msg) {
    Write-Host ""
    Write-Host ("  [{0}/{1}] {2}" -f $n, $total, $msg) -ForegroundColor Cyan
}

function Write-Ok([string]$msg)   { Write-Host "  [ok] $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Info([string]$msg) { Write-Host "  ->  $msg" -ForegroundColor Gray }
function Have([string]$cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter()][string[]]$Arguments = @()
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed (exit $LASTEXITCODE)."
    }
}

function Find-Python {
    $probe = "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    $candidates = @(
        [pscustomobject]@{ Executable = "py"; Prefix = @("-3") },
        [pscustomobject]@{ Executable = "python"; Prefix = @() },
        [pscustomobject]@{ Executable = "python3"; Prefix = @() }
    )

    foreach ($candidate in $candidates) {
        if (-not (Have $candidate.Executable)) { continue }
        $probeArgs = @($candidate.Prefix) + @("-c", $probe)
        $versionText = (& $candidate.Executable @probeArgs 2>$null | Select-Object -Last 1)
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($versionText)) { continue }
        try {
            $version = [version]$versionText.Trim()
        } catch {
            continue
        }
        if ($version -ge [version]"3.10") {
            return [pscustomobject]@{
                Executable = $candidate.Executable
                Prefix = @($candidate.Prefix)
                Version = $version
            }
        }
    }
    return $null
}

function New-CmdShim {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string]$Directory
    )

    $shimPath = Join-Path $Directory ("{0}.cmd" -f $Name)
    # Double embedded quotes for cmd.exe. The executable path is absolute, so
    # the shim remains valid when the caller's working directory changes.
    $quotedExecutable = $Executable.Replace('"', '""')
    $content = "@echo off`r`n`"$quotedExecutable`" %*`r`n"
    Set-Content -LiteralPath $shimPath -Value $content -Encoding ASCII
    return $shimPath
}

$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
$websiteDir = Join-Path $repoRoot "website"
$distSource = Join-Path $websiteDir "dist"
$distTarget = Join-Path $repoRoot "src\kiro_crew\static\dist"
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

Write-Host ""
Write-Host "  VibecodersCrew — Windows source install" -ForegroundColor Magenta
Write-Host "  Checkout: $repoRoot" -ForegroundColor DarkGray
Write-Host ""

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "pyproject.toml"))) {
    throw "Run this script from a VibecodersCrew checkout (pyproject.toml was not found)."
}

$totalSteps = 4

# --- 1. Runtime checks -------------------------------------------------
Write-Step 1 $totalSteps "Checking local runtimes"
$pythonInfo = Find-Python
if ($null -eq $pythonInfo) {
    throw "Python 3.10+ is required. Install it from https://www.python.org/downloads/ and re-run."
}
Write-Ok ("Python {0} ({1})" -f $pythonInfo.Version, $pythonInfo.Executable)

if (-not (Have "git")) {
    Write-Warn "git was not found. The current checkout can still be installed; add git before future updates."
} else {
    Write-Ok ((git --version 2>&1 | Select-Object -First 1).ToString())
}

if (Test-Path -LiteralPath $websiteDir) {
    if (-not (Have "node") -or -not (Have "npm")) {
        throw "Node.js 20+ and npm are required to build the dashboard. Install them from https://nodejs.org/ and re-run."
    }
    $nodeVersionText = (& node --version 2>$null | Select-Object -Last 1).ToString().Trim()
    if ($nodeVersionText -notmatch '^v(\d+)') {
        throw "Could not determine the installed Node.js version."
    }
    $nodeMajor = [int]$Matches[1]
    if ($nodeMajor -lt 20) {
        throw "Node.js 20+ is required to build the dashboard (found $nodeVersionText)."
    }
    Write-Ok ("Node.js {0}; npm {1}" -f $nodeVersionText, ((npm --version 2>$null | Select-Object -Last 1).ToString().Trim()))
}

# --- 2. Dashboard build -----------------------------------------------
Write-Step 2 $totalSteps "Building the dashboard"
if (Test-Path -LiteralPath $websiteDir) {
    Push-Location $websiteDir
    try {
        if (Test-Path -LiteralPath (Join-Path $websiteDir "package-lock.json")) {
            Invoke-Checked -Label "npm ci" -Executable "npm" -Arguments @("ci", "--no-audit", "--no-fund", "--loglevel=error")
        } else {
            Invoke-Checked -Label "npm install" -Executable "npm" -Arguments @("install", "--no-audit", "--no-fund", "--loglevel=error")
        }
        Invoke-Checked -Label "npm run build" -Executable "npm" -Arguments @("run", "build")
    } finally {
        Pop-Location
    }

    if (-not (Test-Path -LiteralPath $distSource)) {
        throw "The dashboard build did not produce website\dist."
    }
    if (Test-Path -LiteralPath $distTarget) {
        Remove-Item -LiteralPath $distTarget -Recurse -Force
    }
    New-Item -ItemType Directory -Path $distTarget -Force | Out-Null
    Get-ChildItem -LiteralPath $distSource -Force | Copy-Item -Destination $distTarget -Recurse -Force
    Write-Ok "Dashboard staged in src\kiro_crew\static\dist"
} else {
    Write-Info "No website directory found; skipping dashboard build."
}

# --- 3. Isolated Python package ---------------------------------------
Write-Step 3 $totalSteps "Creating the Python environment"
$pythonArgs = @($pythonInfo.Prefix)
if (-not (Test-Path -LiteralPath $venvPython)) {
    Invoke-Checked -Label "python -m venv" -Executable $pythonInfo.Executable -Arguments ($pythonArgs + @("-m", "venv", $venvDir))
}
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "The virtual environment was not created at $venvDir."
}

$venvVersionText = (& $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null | Select-Object -Last 1).ToString().Trim()
try { $venvVersion = [version]$venvVersionText } catch { throw "Could not determine the virtual environment Python version." }
if ($venvVersion -lt [version]"3.10") {
    throw "The existing virtual environment uses Python $venvVersionText; remove $venvDir and re-run with Python 3.10+."
}
Write-Ok "Virtual environment ready ($venvVersionText)"

Invoke-Checked -Label "pip bootstrap" -Executable $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")

$previousSkipFrontend = [Environment]::GetEnvironmentVariable("KIROCREW_SKIP_FRONTEND", "Process")
$env:KIROCREW_SKIP_FRONTEND = "1"
try {
    $installTarget = if ($Voice) { "$repoRoot[voice]" } else { $repoRoot }
    Invoke-Checked -Label "editable VibecodersCrew install" -Executable $venvPython -Arguments @("-m", "pip", "install", "-e", $installTarget)
} finally {
    if ($null -eq $previousSkipFrontend) {
        Remove-Item Env:KIROCREW_SKIP_FRONTEND -ErrorAction SilentlyContinue
    } else {
        $env:KIROCREW_SKIP_FRONTEND = $previousSkipFrontend
    }
}

# --- 4. User-facing command shims -------------------------------------
Write-Step 4 $totalSteps "Publishing the command"
$cliCandidates = @(
    (Join-Path $venvDir "Scripts\vibecoderscrew.exe"),
    (Join-Path $venvDir "Scripts\vibecoderscrew.cmd"),
    (Join-Path $venvDir "Scripts\vibecoderscrew")
)
$cli = $cliCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($null -eq $cli) {
    throw "The vibecoderscrew entry point was not installed in $venvDir."
}

$userBin = Join-Path $env:USERPROFILE ".local\bin"
New-Item -ItemType Directory -Path $userBin -Force | Out-Null
$primaryShim = New-CmdShim -Name "vibecoderscrew" -Executable $cli -Directory $userBin
$compatShim = New-CmdShim -Name "kirocrew" -Executable $cli -Directory $userBin
Write-Ok "Installed $primaryShim"
Write-Ok "Installed $compatShim (technical compatibility alias)"

Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "    Add $userBin to your user PATH, then open a new terminal."
Write-Host "    vibecoderscrew setup --agent-only"
Write-Host "    codex login"
Write-Host "    vibecoderscrew config set agent.provider codex"
Write-Host "    vibecoderscrew gateway"
Write-Host ""
Write-Info "ACP requires a separately installed kiro-cli and an explicit provider configuration."
if ($Voice) { Write-Info "Voice extras were installed." }
if ($NonInteractive) { Write-Info "NonInteractive mode complete." }

# Phase 11 Step 96 — local security scan (Windows PowerShell).
#
# Mirrors scripts/security-scan.sh for devs who run Windows. Same four
# checks, same exit codes, so the two scripts are interchangeable in
# pre-commit hooks or in a manual `pnpm run security` invocation.
#
# Usage:
#   .\scripts\security-scan.ps1
#   $env:PROD_URL = "https://psxai.example"; .\scripts\security-scan.ps1
#
# Exit code 0 = clean, non-zero = at least one finding.

$ErrorActionPreference = "Continue"  # we collect failures instead of bailing
$RepoRoot = Resolve-Path "$PSScriptRoot\.."
$Failed = 0

function Section($title) {
    Write-Host ""
    Write-Host "─── $title ─────────────────────────────────────────────"
}

function OK($msg)   { Write-Host "✓ $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "✗ $msg" -ForegroundColor Red; $script:Failed++ }

function Test-Command($name, $installHint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Warn "$name not installed — skipping that section. Install: $installHint"
        return $false
    }
    return $true
}

# 1) Python dependency CVEs ------------------------------------------------
Section "Python deps (pip-audit)"
if (Test-Command "pip-audit" "pip install pip-audit") {
    Push-Location "$RepoRoot\psx-api"
    pip-audit --strict
    if ($LASTEXITCODE -eq 0) { OK "No known CVEs in Python deps" }
    else { Fail "pip-audit reported known CVEs" }
    Pop-Location
}

# 2) Node dependency advisories -------------------------------------------
Section "Node deps (pnpm audit)"
if (Test-Command "pnpm" "npm install -g pnpm") {
    Push-Location "$RepoRoot\psx-web"
    pnpm audit --audit-level high
    if ($LASTEXITCODE -eq 0) { OK "No high+ severity issues in Node deps" }
    else { Fail "pnpm audit reported high/critical issues" }
    Pop-Location
}

# 3) Ruff Bandit (S) rules on the Python source --------------------------
Section "Python source — ruff (bandit S rules)"
if (Test-Command "ruff" "pip install ruff") {
    Push-Location "$RepoRoot\psx-api"
    ruff check --select S psx_api/
    if ($LASTEXITCODE -eq 0) { OK "No dangerous patterns flagged" }
    else { Fail "ruff/bandit flagged dangerous code" }
    Pop-Location
}

# 4) Production header check (optional, only if PROD_URL set) -------------
Section "Production headers"
$prodUrl = if ($env:PROD_URL) { $env:PROD_URL } else { "" }
if ($prodUrl) {
    try {
        $resp = Invoke-WebRequest -Uri $prodUrl -Method Head -TimeoutSec 10 -ErrorAction Stop
        foreach ($h in @("Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options")) {
            if ($resp.Headers.ContainsKey($h)) { OK "$h present" }
            else { Fail "$h missing on $prodUrl" }
        }
    } catch {
        Warn "Could not reach $prodUrl ($($_.Exception.Message)) — skipping header check"
    }
} else {
    Warn "PROD_URL not set — skipping header check"
}

# Summary -----------------------------------------------------------------
Write-Host ""
if ($Failed -eq 0) {
    Write-Host "All checks passed." -ForegroundColor Green
    exit 0
} else {
    Write-Host "$Failed check(s) failed. See SECURITY.md for triage steps." -ForegroundColor Red
    exit 1
}

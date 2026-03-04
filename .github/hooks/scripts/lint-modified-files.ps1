#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Post-session linter: runs only on files modified in the current git working tree.

.DESCRIPTION
  Triggered by the Copilot Stop hook (lint-on-stop.json).
  Collects unstaged, staged, and untracked source files via git, then:
    - Python (.py)        → uvx ruff check --fix  (picks up ruff.toml at workspace root)
    - TypeScript/React    → oxlint lint:fast:strict:fix  then  eslint lint:fix

  Always exits 0 so it never blocks the session from ending.
#>

param()

# Discard stdin (hook passes context JSON we don't need)
$null = $input

# ── Git: collect dirty + new source files ─────────────────────────────────────
$unstaged  = git diff --name-only              2>$null
$staged    = git diff --cached --name-only     2>$null
$untracked = git ls-files --others --exclude-standard 2>$null |
             Where-Object { $_ -match '\.(py|ts|tsx)$' }

$all_files = ( @($unstaged) + @($staged) + @($untracked) ) |
             Where-Object { $_ -ne $null -and $_ -ne '' } |
             Sort-Object -Unique |
             Where-Object { Test-Path $_ }

if (-not $all_files) {
    Write-Host "[lint-hook] No modified source files detected – skipping lint."
    exit 0
}

$py_files = @( $all_files | Where-Object { $_ -match '\.py$'      } )
$ts_files = @( $all_files | Where-Object { $_ -match '\.(ts|tsx)$' } )

$any_error = $false

# ── Python: ruff ──────────────────────────────────────────────────────────────
if ($py_files.Count -gt 0) {
    Write-Host "[lint-hook] Python ($($py_files.Count) file(s)) – uvx ruff check --fix"
    Write-Host "            $($py_files -join ', ')"
    uvx ruff check --fix @py_files
    if ($LASTEXITCODE -ne 0) { $any_error = $true }
}

# ── TypeScript / React: oxlint (fast) then eslint ────────────────────────────
if ($ts_files.Count -gt 0) {
    Write-Host "[lint-hook] TypeScript ($($ts_files.Count) file(s)) – oxlint (lint:fast:strict:fix)"
    Write-Host "            $($ts_files -join ', ')"
    npx oxlint --config .oxlintrc.json --tsconfig frontend/tsconfig.json `
        --type-aware --type-check --fix @ts_files
    if ($LASTEXITCODE -ne 0) { $any_error = $true }

    Write-Host "[lint-hook] TypeScript ($($ts_files.Count) file(s)) – eslint (lint:fix)"
    npx eslint --fix @ts_files
    if ($LASTEXITCODE -ne 0) { $any_error = $true }
}

if ($any_error) {
    Write-Warning "[lint-hook] Lint completed with issues – review output above."
} else {
    Write-Host "[lint-hook] All lint checks passed."
}

# Always exit 0: linting issues are warnings, not session blockers.
exit 0

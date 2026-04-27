# 1. Configuration des cibles
$targets = @{
    "FRONTEND" = "frontend"
    "BACKEND"  = "backend"
}

# 2. Filtres (Exclusions dossiers et détection tests)
$skip = "node_modules|dist|build|out|\.next|\.venv|venv|env|\.git|\.vscode|bin|obj|vendor"
$testMatch = "\.test\.|\.spec\.|/tests/|/__tests__/"

Write-Host "`n=======================================" -ForegroundColor Gray
Write-Host "   RAPPORT DE LIGNES DE CODE (SLOC)   " -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "=======================================" -ForegroundColor Gray

$stats = @{ "FrontCode" = 0; "FrontTests" = 0; "BackCode" = 0; "BackTests" = 0 }

foreach ($item in $targets.GetEnumerator()) {
    $key = $item.Key
    $path = $item.Value

    if (Test-Path $path) {
        # Collecte des fichiers en ignorant les dossiers de dépendances/build
        $allFiles = Get-ChildItem -Path $path -Recurse -File | 
                    Where-Object { $_.FullName -notmatch $skip }

        # Séparation Tests / Code
        $testFiles = $allFiles | Where-Object { $_.FullName -match $testMatch }
        $codeFiles = $allFiles | Where-Object { $_.FullName -notmatch $testMatch }

        # Comptage physique des lignes
        $c = if ($codeFiles) { ($codeFiles | Get-Content | Measure-Object -Line).Lines } else { 0 }
        $t = if ($testFiles) { ($testFiles | Get-Content | Measure-Object -Line).Lines } else { 0 }

        if ($key -eq "FRONTEND") { $stats.FrontCode = $c; $stats.FrontTests = $t }
        else { $stats.BackCode = $c; $stats.BackTests = $t }
    }
}

# 3. Affichage du Breakdown
Write-Host "`n[ FRONTEND ]" -ForegroundColor Cyan
Write-Host "  Lignes de Code  : $($stats.FrontCode)"
Write-Host "  Lignes de Tests : $($stats.FrontTests)"

Write-Host "`n[ BACKEND ]" -ForegroundColor Magenta
Write-Host "  Lignes de Code  : $($stats.BackCode)"
Write-Host "  Lignes de Tests : $($stats.BackTests)"

Write-Host "`n---------------------------------------"
Write-Host "TOTAL GÉNÉRAL : $($stats.FrontCode + $stats.FrontTests + $stats.BackCode + $stats.BackTests)" -ForegroundColor Yellow
Write-Host "=======================================`n"
# Automated backup script for Azure Architect Assistant data
# Run this manually or schedule with Windows Task Scheduler

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = "backups"
$backupDir = Join-Path $backupRoot $timestamp

Write-Host "Creating backup: $backupDir" -ForegroundColor Green

# Create backup directory
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Backup databases
Write-Host "Backing up databases..."
Copy-Item "backend/data/*.db" -Destination $backupDir -ErrorAction SilentlyContinue

# Backup KB indexes
Write-Host "Backing up knowledge base indexes..."
$kbs = Get-ChildItem "backend/data/knowledge_bases" -Directory
foreach ($kb in $kbs) {
    $indexPath = Join-Path $kb.FullName "index"
    if (Test-Path $indexPath) {
        $kbBackup = Join-Path $backupDir $kb.Name
        New-Item -ItemType Directory -Path $kbBackup -Force | Out-Null
        Copy-Item -Path $indexPath -Destination $kbBackup -Recurse -ErrorAction SilentlyContinue
        Write-Host "  ✓ Backed up $($kb.Name)"
    }
}

# Calculate backup size
$size = (Get-ChildItem $backupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB

Write-Host "`nBackup complete!" -ForegroundColor Green
Write-Host "Location: $backupDir"
Write-Host "Size: $([math]::Round($size, 2)) MB"

# Keep only last 5 backups
$oldBackups = Get-ChildItem $backupRoot -Directory | Sort-Object Name -Descending | Select-Object -Skip 5
if ($oldBackups) {
    Write-Host "`nCleaning up old backups..."
    $oldBackups | Remove-Item -Recurse -Force
}

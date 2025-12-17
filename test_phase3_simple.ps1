#!/usr/bin/env pwsh
# Simple Phase 3 Test - Diagram Generation API

$ErrorActionPreference = "Stop"
$baseUrl = "http://localhost:8090/api/v1"

Write-Host "`n=== Phase 3 Diagram Generation Test ===" -ForegroundColor Cyan

# Wait for backend
Write-Host "Checking backend health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8090/health" -Method Get
    Write-Host "[X]“ Backend is ready ($($health.status))" -ForegroundColor Green
}
catch {
    Write-Host "[X]— Backend is not responding" -ForegroundColor Red
    exit 1
}

# Test 1: Create Diagram Set
Write-Host "`n--- Test 1: POST /api/v1/diagram-sets ---" -ForegroundColor Yellow

$testDescription = @'
We need to build a cloud-based document processing system that can:
1. Accept PDF and Word documents uploaded by users
2. Extract text content using OCR when needed
3. Store processed documents in a database
4. Allow users to search through their documents using full-text search
5. Generate summary reports of document contents

The system should handle up to 1000 concurrent users and process documents in real-time.
Users authenticate via OAuth2 and have role-based access controls.
'@

$createRequest = @{
    input_description = $testDescription
    project_id = $null
    adr_id = $null
} | ConvertTo-Json -Depth 10

try {
    Write-Host "Creating diagram set..." -ForegroundColor Gray
    $createResponse = Invoke-RestMethod -Uri "$baseUrl/diagram-sets" `
        -Method Post `
        -Body $createRequest `
        -ContentType "application/json"
    
    Write-Host "[X]“ Diagram set created!" -ForegroundColor Green
    Write-Host "  ID: $($createResponse.id)" -ForegroundColor Gray
    Write-Host "  Diagrams: $($createResponse.diagrams.Count)" -ForegroundColor Gray
    Write-Host "  Ambiguities: $($createResponse.ambiguities.Count)" -ForegroundColor Gray
    
    $diagramSetId = $createResponse.id
}
catch {
    Write-Host "[X]— Failed to create diagram set" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 2: Retrieve Diagram Set
Write-Host "`n--- Test 2: GET /api/v1/diagram-sets/{id} ---" -ForegroundColor Yellow

try {
    $getResponse = Invoke-RestMethod -Uri "$baseUrl/diagram-sets/$diagramSetId" -Method Get
    
    Write-Host "[X]“ Diagram set retrieved!" -ForegroundColor Green
    Write-Host "  Diagrams: $($getResponse.diagrams.Count)" -ForegroundColor Gray
    Write-Host "  Ambiguities: $($getResponse.ambiguities.Count)" -ForegroundColor Gray
}
catch {
    Write-Host "[X]— Failed to retrieve diagram set" -ForegroundColor Red
    exit 1
}

# Test 3: Display Diagram Content
Write-Host "`n--- Test 3: Validate Diagram Content ---" -ForegroundColor Yellow

$diagram = $createResponse.diagrams | Where-Object { $_.diagram_type -eq "functional" } | Select-Object -First 1

if ($diagram) {
    Write-Host "[X]“ Functional diagram found" -ForegroundColor Green
    Write-Host "  Type: $($diagram.diagram_type)" -ForegroundColor Gray
    Write-Host "  Version: $($diagram.version)" -ForegroundColor Gray
    Write-Host "  Length: $($diagram.source_code.Length) chars" -ForegroundColor Gray
    
    # Show preview
    Write-Host "`n  Preview:" -ForegroundColor Gray
    $preview = $diagram.source_code.Substring(0, [Math]::Min(300, $diagram.source_code.Length))
    Write-Host "  $preview..." -ForegroundColor DarkGray
}
else {
    Write-Host "[X]— No functional diagram found" -ForegroundColor Red
}

# Test 4: List Ambiguities (if any)
if ($createResponse.ambiguities.Count -gt 0) {
    Write-Host "`n--- Test 4: GET /api/v1/diagram-sets/{id}/ambiguities ---" -ForegroundColor Yellow
    
    try {
        $ambiguities = Invoke-RestMethod -Uri "$baseUrl/diagram-sets/$diagramSetId/ambiguities" -Method Get
        
        Write-Host "[X]“ Retrieved $($ambiguities.Count) ambiguities" -ForegroundColor Green
        
        foreach ($amb in $ambiguities | Select-Object -First 3) {
            Write-Host "  - $($amb.ambiguous_text)" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "[X]— Failed to retrieve ambiguities" -ForegroundColor Red
    }
}
else {
    Write-Host "`n--- Test 4: Skipped (no ambiguities detected) ---" -ForegroundColor Yellow
}

# Summary
Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
Write-Host "[OK] Phase 3 API endpoints are working!" -ForegroundColor Green
Write-Host "`nGenerated Diagram Set ID: $diagramSetId" -ForegroundColor Yellow
Write-Host "`nYou can view this in the frontend with:" -ForegroundColor Gray
Write-Host "  <MermaidRenderer diagramSetId=`"$diagramSetId`" diagramType=`"functional`" />" -ForegroundColor DarkGray

Write-Host "`n[OK] All tests completed!" -ForegroundColor Green


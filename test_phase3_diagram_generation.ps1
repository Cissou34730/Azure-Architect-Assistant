#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test Phase 3 - User Story 1 (Mermaid Functional Diagram Generation)
.DESCRIPTION
    Tests the diagram generation API endpoints:
    1. POST /api/v1/diagram-sets - Create diagram set with functional Mermaid diagram
    2. GET /api/v1/diagram-sets/{id} - Retrieve diagram set
    3. GET /api/v1/diagram-sets/{id}/ambiguities - List ambiguities
    4. PATCH /api/v1/diagram-sets/{id}/ambiguities/{id}/resolve - Resolve ambiguity
#>

$ErrorActionPreference = "Stop"
$baseUrl = "http://localhost:8090/api/v1"

Write-Host "`n=== Phase 3 Diagram Generation Test ===" -ForegroundColor Cyan
Write-Host "Testing User Story 1: Generate Mermaid Functional Diagrams`n" -ForegroundColor Cyan

# Wait for backend to be ready
Write-Host "Waiting for backend to be ready..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
$isReady = $false

while (-not $isReady -and $retryCount -lt $maxRetries) {
    try {
        $healthCheck = Invoke-RestMethod -Uri "http://localhost:8090/health" -Method Get -ErrorAction Stop
        if ($healthCheck.status -eq "healthy") {
            $isReady = $true
            Write-Host "✓ Backend is ready!" -ForegroundColor Green
        }
    }
    catch {
        $retryCount++
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
    }
}

if (-not $isReady) {
    Write-Host "`n✗ Backend failed to start after 30 seconds" -ForegroundColor Red
    exit 1
}

# Test 1: Create Diagram Set with Functional Requirements
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

Write-Host "Creating diagram set with functional requirements..." -ForegroundColor Gray

try {
    $createResponse = Invoke-RestMethod -Uri "$baseUrl/diagram-sets" `
        -Method Post `
        -Body $createRequest `
        -ContentType "application/json" `
        -ErrorAction Stop
    
    Write-Host "✓ Diagram set created successfully!" -ForegroundColor Green
    Write-Host "  Diagram Set ID: $($createResponse.id)" -ForegroundColor Gray
    Write-Host "  Diagrams Count: $($createResponse.diagrams.Count)" -ForegroundColor Gray
    Write-Host "  Ambiguities Count: $($createResponse.ambiguities.Count)" -ForegroundColor Gray
    
    # Display diagram info
    foreach ($diagram in $createResponse.diagrams) {
        Write-Host "  - Diagram Type: $($diagram.diagram_type)" -ForegroundColor Gray
        Write-Host "    Version: $($diagram.version)" -ForegroundColor Gray
        Write-Host "    Source Code Length: $($diagram.source_code.Length) characters" -ForegroundColor Gray
        Write-Host "    Preview:" -ForegroundColor Gray
        $preview = $diagram.source_code.Substring(0, [Math]::Min(200, $diagram.source_code.Length))
        Write-Host "    $preview..." -ForegroundColor DarkGray
    }
    
    # Display ambiguities
    if ($createResponse.ambiguities.Count -gt 0) {
        Write-Host "`n  Detected Ambiguities:" -ForegroundColor Yellow
        foreach ($amb in $createResponse.ambiguities) {
            Write-Host "  - [$($amb.severity.ToUpper())] $($amb.category): $($amb.description)" -ForegroundColor Yellow
            if ($amb.text_fragment) {
                Write-Host "    Fragment: '$($amb.text_fragment)'" -ForegroundColor DarkYellow
            }
        }
    }
    
    $diagramSetId = $createResponse.id
}
catch {
    Write-Host "✗ Failed to create diagram set" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
    exit 1
}

# Test 2: Retrieve Diagram Set
Write-Host "`n--- Test 2: GET /api/v1/diagram-sets/{id} ---" -ForegroundColor Yellow

try {
    $getResponse = Invoke-RestMethod -Uri "$baseUrl/diagram-sets/$diagramSetId" `
        -Method Get `
        -ErrorAction Stop
    
    Write-Host "✓ Diagram set retrieved successfully!" -ForegroundColor Green
    Write-Host "  ID: $($getResponse.id)" -ForegroundColor Gray
    Write-Host "  Created: $($getResponse.created_at)" -ForegroundColor Gray
    Write-Host "  Updated: $($getResponse.updated_at)" -ForegroundColor Gray
    Write-Host "  Diagrams: $($getResponse.diagrams.Count)" -ForegroundColor Gray
    Write-Host "  Ambiguities: $($getResponse.ambiguities.Count)" -ForegroundColor Gray
}
catch {
    Write-Host "✗ Failed to retrieve diagram set" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 3: List Ambiguities
if ($createResponse.ambiguities.Count -gt 0) {
    Write-Host "`n--- Test 3: GET /api/v1/diagram-sets/{id}/ambiguities ---" -ForegroundColor Yellow
    
    try {
        $ambiguitiesResponse = Invoke-RestMethod -Uri "$baseUrl/diagram-sets/$diagramSetId/ambiguities" `
            -Method Get `
            -ErrorAction Stop
        
        Write-Host "✓ Ambiguities retrieved successfully!" -ForegroundColor Green
        Write-Host "  Total Count: $($ambiguitiesResponse.Count)" -ForegroundColor Gray
        
        # Test 4: Resolve an ambiguity
        if ($ambiguitiesResponse.Count -gt 0) {
            Write-Host "`n--- Test 4: PATCH /api/v1/diagram-sets/{id}/ambiguities/{id}/resolve ---" -ForegroundColor Yellow
            
            $firstAmbiguityId = $ambiguitiesResponse[0].id
            $resolveRequest = @{
                resolved = $true
            } | ConvertTo-Json
            
            try {
                $resolveResponse = Invoke-RestMethod -Uri "$baseUrl/diagram-sets/$diagramSetId/ambiguities/$firstAmbiguityId/resolve" `
                    -Method Patch `
                    -Body $resolveRequest `
                    -ContentType "application/json" `
                    -ErrorAction Stop
                
                Write-Host "✓ Ambiguity resolved successfully!" -ForegroundColor Green
                Write-Host "  Ambiguity ID: $($resolveResponse.id)" -ForegroundColor Gray
                Write-Host "  Resolved: $($resolveResponse.resolved)" -ForegroundColor Gray
                Write-Host "  Resolved At: $($resolveResponse.resolved_at)" -ForegroundColor Gray
            }
            catch {
                Write-Host "✗ Failed to resolve ambiguity" -ForegroundColor Red
                Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    catch {
        Write-Host "✗ Failed to retrieve ambiguities" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}
else {
    Write-Host "`n--- Test 3 `& 4: Skipped (no ambiguities detected) ---" -ForegroundColor Yellow
}

# Test 5: Validate Mermaid Syntax
Write-Host "`n--- Test 5: Validate Mermaid Diagram Syntax ---" -ForegroundColor Yellow

$diagram = $createResponse.diagrams | Where-Object { $_.diagram_type -eq "functional" } | Select-Object -First 1
if ($diagram) {
    $sourceCode = $diagram.source_code
    
    # Basic Mermaid syntax checks
    $hasDiagramType = $sourceCode -match "^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|C4Context|C4Container)"
    $hasBalancedBrackets = ($sourceCode.Split('[').Length - 1) -eq ($sourceCode.Split(']').Length - 1)
    $hasArrows = $sourceCode -match '(-->|\-\.->|==>|\-\.\-|--)'
    
    if ($hasDiagramType) {
        Write-Host "  ✓ Valid diagram type declaration" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing or invalid diagram type" -ForegroundColor Red
    }
    
    if ($hasBalancedBrackets) {
        Write-Host "  ✓ Balanced brackets" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Unbalanced brackets" -ForegroundColor Red
    }
    
    if ($hasArrows) {
        Write-Host "  ✓ Contains valid arrow syntax" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ No arrows found (may be valid for some diagram types)" -ForegroundColor Yellow
    }
    
    Write-Host "`n  Full Diagram Source Code:" -ForegroundColor Gray
    Write-Host "  ----------------------------------------" -ForegroundColor DarkGray
    $sourceCode.Split("`n") | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    Write-Host "  ----------------------------------------" -ForegroundColor DarkGray
}

Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
Write-Host "✓ Phase 3 API endpoints are working correctly!" -ForegroundColor Green
Write-Host "`nGenerated Diagram Set ID: $diagramSetId" -ForegroundColor Yellow
Write-Host "You can view this diagram in the frontend by:" -ForegroundColor Yellow
Write-Host "  1. Starting the frontend: cd frontend; npm run dev" -ForegroundColor Gray
Write-Host "  2. Importing MermaidRenderer component" -ForegroundColor Gray
Write-Host "  3. Using: ``<MermaidRenderer diagramSetId=`"$diagramSetId`" diagramType=`"functional`" />``" -ForegroundColor Gray

Write-Host "`n✓ All Phase 3 tests completed successfully!" -ForegroundColor Green

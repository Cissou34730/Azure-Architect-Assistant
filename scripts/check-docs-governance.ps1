$ErrorActionPreference = "Stop"

$requiredOpsDocs = @(
    "docs/operations/DOCUMENTATION_GOVERNANCE.md",
    "docs/operations/SOURCE_OF_TRUTH_MATRIX.md",
    "docs/operations/WORKFLOW_TRACEABILITY_RUNBOOK.md",
    "docs/operations/ACTIVE_ASSET_REGISTRY.md"
)

foreach ($docPath in $requiredOpsDocs) {
    if (-not (Test-Path $docPath)) {
        throw "Missing required governance document: $docPath"
    }
}

$docsReadme = Get-Content -Raw "docs/README.md"
$requiredReadmeLinks = @(
    "operations/DOCUMENTATION_GOVERNANCE.md",
    "operations/SOURCE_OF_TRUTH_MATRIX.md",
    "operations/WORKFLOW_TRACEABILITY_RUNBOOK.md",
    "operations/ACTIVE_ASSET_REGISTRY.md",
    "agents/README.md"
)

foreach ($requiredLink in $requiredReadmeLinks) {
    if ($docsReadme -notmatch [Regex]::Escape($requiredLink)) {
        throw "docs/README.md is missing required link target: $requiredLink"
    }
}

$agentDocs = Get-ChildItem "docs/agents" -Filter "*.agent.md"
if ($agentDocs.Count -eq 0) {
    throw "No agent lane documents found in docs/agents."
}

$requiredSections = @(
    "## Purpose",
    "## Current State",
    "## Do / Don't",
    "## Decision Summary",
    "## Update Triggers"
)

foreach ($agentDoc in $agentDocs) {
    $content = Get-Content -Raw $agentDoc.FullName
    foreach ($section in $requiredSections) {
        if ($content -notmatch [Regex]::Escape($section)) {
            throw "Agent doc $($agentDoc.FullName) is missing required section: $section"
        }
    }
}

Write-Host "Docs governance/lane integrity checks passed."

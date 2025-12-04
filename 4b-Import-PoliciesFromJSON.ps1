# Create Conditional Access Policies from JSON Files

# Define input folder
$inputFolder = "ConditionalAccessPolicies-ForImport"

# Verify connection
$context = Get-MgContext
if (-not $context) {
    Write-Error "Not connected to Microsoft Graph. Run 4a-Connect-MgGraphTenant-Write.ps1 first."
    exit 1
}

# Verify we have write permissions
if ($context.Scopes -notcontains "Policy.ReadWrite.ConditionalAccess") {
    Write-Error "Insufficient permissions. Required scope: Policy.ReadWrite.ConditionalAccess"
    Write-Host "Please run 4a-Connect-MgGraphTenant-Write.ps1 to connect with the correct permissions." -ForegroundColor Yellow
    exit 1
}

Write-Host "Connected as: $($context.Account)" -ForegroundColor Green
Write-Host "Tenant: $($context.TenantId)" -ForegroundColor Green
Write-Host ""

# Verify input folder exists
if (-not (Test-Path $inputFolder)) {
    Write-Error "Input folder '$inputFolder' not found. Run 3-Convert-YAMLToImportJSON.ps1 first."
    exit 1
}

# Get all JSON files
$jsonFiles = Get-ChildItem -Path $inputFolder -Filter "*.json"

if ($jsonFiles.Count -eq 0) {
    Write-Warning "No JSON files found in '$inputFolder'"
    Write-Host "Please run 3-Convert-YAMLToImportJSON.ps1 to generate JSON files from YAML." -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($jsonFiles.Count) policy file(s) to import" -ForegroundColor Cyan
Write-Host ""

# Confirm before proceeding
Write-Host "WARNING: This will create $($jsonFiles.Count) new Conditional Access policies in your tenant!" -ForegroundColor Red
Write-Host "Tenant: $($context.TenantId)" -ForegroundColor Yellow
Write-Host ""
$confirmation = Read-Host "Do you want to proceed? (yes/no)"

if ($confirmation -ne "yes") {
    Write-Host "Operation cancelled by user." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Creating policies..." -ForegroundColor Cyan
Write-Host ""

$successCount = 0
$failCount = 0
$results = @()

foreach ($file in $jsonFiles) {
    try {
        # Read JSON file
        $jsonContent = Get-Content -Path $file.FullName -Raw
        $policy = $jsonContent | ConvertFrom-Json
        
        Write-Host "Creating policy: $($policy.displayName)" -ForegroundColor Cyan
        
        # Create the policy via Graph API
        $uri = "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies"
        $response = Invoke-MgGraphRequest -Uri $uri -Method POST -Body $jsonContent -ContentType "application/json"
        
        Write-Host "  ✓ SUCCESS - Policy created with ID: $($response.id)" -ForegroundColor Green
        Write-Host "    State: $($response.state)" -ForegroundColor Gray
        
        $results += [PSCustomObject]@{
            FileName = $file.Name
            PolicyName = $policy.displayName
            Status = "Success"
            PolicyId = $response.id
            State = $response.state
            Error = ""
        }
        
        $successCount++
    }
    catch {
        $errorMessage = $_.Exception.Message
        
        # Try to extract more specific error from Graph API response
        if ($_.ErrorDetails.Message) {
            try {
                $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
                if ($errorDetails.error.message) {
                    $errorMessage = $errorDetails.error.message
                }
            }
            catch {
                # If parsing fails, use the original error message
            }
        }
        
        Write-Host "  ✗ FAILED - $errorMessage" -ForegroundColor Red
        
        $results += [PSCustomObject]@{
            FileName = $file.Name
            PolicyName = $policy.displayName
            Status = "Failed"
            PolicyId = ""
            State = ""
            Error = $errorMessage
        }
        
        $failCount++
    }
    
    Write-Host ""
}

# Summary
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "IMPORT SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Total policies processed: $($jsonFiles.Count)" -ForegroundColor White
Write-Host "Successfully created: $successCount" -ForegroundColor Green
if ($failCount -gt 0) {
    Write-Host "Failed: $failCount" -ForegroundColor Red
}
Write-Host ""

# Display detailed results
Write-Host "Detailed Results:" -ForegroundColor Cyan
Write-Host ""
$results | Format-Table -AutoSize

# Save results to file
$resultsFile = "import-results-$(Get-Date -Format 'yyyyMMdd-HHmmss').csv"
$results | Export-Csv -Path $resultsFile -NoTypeInformation -Encoding UTF8
Write-Host "Results saved to: $resultsFile" -ForegroundColor Cyan
Write-Host ""

# Next steps
if ($successCount -gt 0) {
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Review the created policies in Azure Portal" -ForegroundColor Yellow
    Write-Host "  2. If you used 'enabledForReportingButNotEnforced', check sign-in logs" -ForegroundColor Yellow
    Write-Host "  3. When ready, change policy state to 'enabled' in the portal" -ForegroundColor Yellow
    Write-Host ""
}

if ($failCount -gt 0) {
    Write-Host "Some policies failed to import. Common issues:" -ForegroundColor Red
    Write-Host "  - User/Group/Role GUIDs don't exist in this tenant" -ForegroundColor Yellow
    Write-Host "  - Named location GUIDs are invalid" -ForegroundColor Yellow
    Write-Host "  - App GUIDs are not available in this tenant" -ForegroundColor Yellow
    Write-Host "  - Duplicate policy names" -ForegroundColor Yellow
    Write-Host "  - Invalid policy configuration" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Review the errors above and update the YAML files in ConditionalAccessPolicies-ToImport/" -ForegroundColor Yellow
    Write-Host "Then run scripts 3 and 4b again." -ForegroundColor Yellow
}

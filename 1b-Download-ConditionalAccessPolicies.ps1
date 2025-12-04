# Download Conditional Access Policies
# Assumes Microsoft Graph context is already established

# Verify connection
$context = Get-MgContext
if (-not $context) {
    Write-Error "Not connected to Microsoft Graph. Run 1a-Connect-MgGraphTenant-Read.ps1 first."
    exit 1
}

Write-Host "Connected as: $($context.Account)" -ForegroundColor Green
Write-Host "Tenant: $($context.TenantId)" -ForegroundColor Green

# Create output directory
$outputFolder = "ConditionalAccessPolicies"
if (-not (Test-Path $outputFolder)) {
    New-Item -ItemType Directory -Path $outputFolder | Out-Null
}

# Get all Conditional Access policies using SDK cmdlet
Write-Host "`nRetrieving Conditional Access policies..."
$policies = Get-MgIdentityConditionalAccessPolicy -All

# Export each policy as JSON
foreach ($policy in $policies) {
    $fileName = "$outputFolder\$($policy.DisplayName -replace '[\\/:*?"<>|]', '_').json"
    $policy | ConvertTo-Json -Depth 10 | Out-File -FilePath $fileName -Encoding UTF8
    Write-Host "Exported: $($policy.DisplayName)"
}

Write-Host "`nTotal policies exported: $($policies.Count)" -ForegroundColor Green
Write-Host "Files saved to: $((Get-Item $outputFolder).FullName)"

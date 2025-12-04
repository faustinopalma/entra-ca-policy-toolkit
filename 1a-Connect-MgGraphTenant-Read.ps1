# Connect to Microsoft Graph with Device Code Authentication

# Load tenant ID from .env file if it exists
$tenantId = $null
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^TENANT_ID=(.+)$') {
            $tenantId = $matches[1].Trim()
            if ($tenantId -eq 'your-tenant-id-here') {
                $tenantId = $null
            }
        }
    }
}

# Connect to Microsoft Graph with read permissions
if ($tenantId) {
    Write-Host "Connecting to tenant: $tenantId" -ForegroundColor Cyan
    Connect-MgGraph -Scopes "Policy.Read.All" -UseDeviceCode -NoWelcome -ContextScope Process -TenantId $tenantId
} else {
    Write-Host "Connecting to default tenant..." -ForegroundColor Cyan
    Connect-MgGraph -Scopes "Policy.Read.All" -UseDeviceCode -NoWelcome -ContextScope Process
}

# Verify connection
$context = Get-MgContext
if ($context) {
    Write-Host "`nConnected successfully!" -ForegroundColor Green
    Write-Host "Account: $($context.Account)" -ForegroundColor Green
    Write-Host "Tenant ID: $($context.TenantId)" -ForegroundColor Green
    Write-Host "Scopes: $($context.Scopes -join ', ')" -ForegroundColor Green
    Write-Host "`nYou can now run script 1b to download Conditional Access policies" -ForegroundColor Yellow
} else {
    Write-Error "Failed to connect to Microsoft Graph"
    exit 1
}

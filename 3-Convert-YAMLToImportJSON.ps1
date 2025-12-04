# Convert YAML Conditional Access Policies to JSON format for Microsoft Graph API

# Define input and output folders
$inputFolder = "ConditionalAccessPolicies-ToImport"
$outputFolder = "ConditionalAccessPolicies-ForImport"

# Verify input folder exists
if (-not (Test-Path $inputFolder)) {
    Write-Error "Input folder '$inputFolder' not found. Place your YAML policy files in this folder first."
    exit 1
}

# Create output directory
if (-not (Test-Path $outputFolder)) {
    New-Item -ItemType Directory -Path $outputFolder | Out-Null
}

# Check if powershell-yaml module is installed
if (-not (Get-Module -ListAvailable -Name powershell-yaml)) {
    Write-Host "powershell-yaml module not found. Installing..." -ForegroundColor Yellow
    try {
        Install-Module -Name powershell-yaml -Scope CurrentUser -Force -AllowClobber
        Write-Host "powershell-yaml module installed successfully" -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to install powershell-yaml module. Please run: Install-Module -Name powershell-yaml -Scope CurrentUser"
        exit 1
    }
}

Import-Module powershell-yaml

# Helper function to convert policy to API-ready format
function ConvertTo-ApiFormat {
    param($policy)
    
    # Create the API-ready structure
    # Reference: https://learn.microsoft.com/en-us/graph/api/conditionalaccessroot-post-policies
    
    $apiPolicy = [ordered]@{
        displayName = $policy.DisplayName
        state = $policy.State
    }
    
    # Conditions object (required)
    $conditions = [ordered]@{}
    
    # Users (required)
    if ($policy.Conditions.Users) {
        $users = [ordered]@{}
        
        if ($policy.Conditions.Users.IncludeUsers) {
            $users.includeUsers = @($policy.Conditions.Users.IncludeUsers)
        }
        if ($policy.Conditions.Users.ExcludeUsers) {
            $users.excludeUsers = @($policy.Conditions.Users.ExcludeUsers)
        }
        if ($policy.Conditions.Users.IncludeGroups) {
            $users.includeGroups = @($policy.Conditions.Users.IncludeGroups)
        }
        if ($policy.Conditions.Users.ExcludeGroups) {
            $users.excludeGroups = @($policy.Conditions.Users.ExcludeGroups)
        }
        if ($policy.Conditions.Users.IncludeRoles) {
            $users.includeRoles = @($policy.Conditions.Users.IncludeRoles)
        }
        if ($policy.Conditions.Users.ExcludeRoles) {
            $users.excludeRoles = @($policy.Conditions.Users.ExcludeRoles)
        }
        
        $conditions.users = $users
    }
    
    # Applications (required)
    if ($policy.Conditions.Applications) {
        $applications = [ordered]@{}
        
        if ($policy.Conditions.Applications.IncludeApplications) {
            $applications.includeApplications = @($policy.Conditions.Applications.IncludeApplications)
        }
        if ($policy.Conditions.Applications.ExcludeApplications) {
            $applications.excludeApplications = @($policy.Conditions.Applications.ExcludeApplications)
        }
        if ($policy.Conditions.Applications.IncludeUserActions) {
            $applications.includeUserActions = @($policy.Conditions.Applications.IncludeUserActions)
        }
        
        $conditions.applications = $applications
    }
    
    # Client App Types
    if ($policy.Conditions.ClientAppTypes) {
        $conditions.clientAppTypes = @($policy.Conditions.ClientAppTypes)
    }
    
    # Platforms
    if ($policy.Conditions.Platforms) {
        $platforms = [ordered]@{}
        
        if ($policy.Conditions.Platforms.IncludePlatforms) {
            $platforms.includePlatforms = @($policy.Conditions.Platforms.IncludePlatforms)
        }
        if ($policy.Conditions.Platforms.ExcludePlatforms) {
            $platforms.excludePlatforms = @($policy.Conditions.Platforms.ExcludePlatforms)
        }
        
        $conditions.platforms = $platforms
    }
    
    # Locations
    if ($policy.Conditions.Locations) {
        $locations = [ordered]@{}
        
        if ($policy.Conditions.Locations.IncludeLocations) {
            $locations.includeLocations = @($policy.Conditions.Locations.IncludeLocations)
        }
        if ($policy.Conditions.Locations.ExcludeLocations) {
            $locations.excludeLocations = @($policy.Conditions.Locations.ExcludeLocations)
        }
        
        $conditions.locations = $locations
    }
    
    # Device States
    if ($policy.Conditions.DeviceStates) {
        $deviceStates = [ordered]@{}
        
        if ($policy.Conditions.DeviceStates.IncludeStates) {
            $deviceStates.includeStates = @($policy.Conditions.DeviceStates.IncludeStates)
        }
        if ($policy.Conditions.DeviceStates.ExcludeStates) {
            $deviceStates.excludeStates = @($policy.Conditions.DeviceStates.ExcludeStates)
        }
        
        $conditions.deviceStates = $deviceStates
    }
    
    # Risk Levels
    if ($policy.Conditions.SignInRiskLevels) {
        $conditions.signInRiskLevels = @($policy.Conditions.SignInRiskLevels)
    }
    if ($policy.Conditions.UserRiskLevels) {
        $conditions.userRiskLevels = @($policy.Conditions.UserRiskLevels)
    }
    
    $apiPolicy.conditions = $conditions
    
    # Grant Controls
    if ($policy.GrantControls) {
        $grantControls = [ordered]@{}
        
        if ($policy.GrantControls.Operator) {
            $grantControls.operator = $policy.GrantControls.Operator
        }
        
        if ($policy.GrantControls.BuiltInControls) {
            $grantControls.builtInControls = @($policy.GrantControls.BuiltInControls)
        }
        
        if ($policy.GrantControls.CustomAuthenticationFactors) {
            $grantControls.customAuthenticationFactors = @($policy.GrantControls.CustomAuthenticationFactors)
        }
        
        if ($policy.GrantControls.TermsOfUse) {
            $grantControls.termsOfUse = @($policy.GrantControls.TermsOfUse)
        }
        
        $apiPolicy.grantControls = $grantControls
    }
    
    # Session Controls
    if ($policy.SessionControls) {
        $sessionControls = [ordered]@{}
        
        if ($policy.SessionControls.ApplicationEnforcedRestrictions) {
            $sessionControls.applicationEnforcedRestrictions = @{
                isEnabled = [bool]$policy.SessionControls.ApplicationEnforcedRestrictions.IsEnabled
            }
        }
        
        if ($policy.SessionControls.CloudAppSecurity) {
            $cloudAppSec = @{
                isEnabled = [bool]$policy.SessionControls.CloudAppSecurity.IsEnabled
            }
            if ($policy.SessionControls.CloudAppSecurity.CloudAppSecurityType) {
                $cloudAppSec.cloudAppSecurityType = $policy.SessionControls.CloudAppSecurity.CloudAppSecurityType
            }
            $sessionControls.cloudAppSecurity = $cloudAppSec
        }
        
        if ($policy.SessionControls.SignInFrequency) {
            $signInFreq = @{
                isEnabled = [bool]$policy.SessionControls.SignInFrequency.IsEnabled
            }
            if ($policy.SessionControls.SignInFrequency.Value) {
                $signInFreq.value = $policy.SessionControls.SignInFrequency.Value
                $signInFreq.type = $policy.SessionControls.SignInFrequency.Type
            }
            $sessionControls.signInFrequency = $signInFreq
        }
        
        if ($policy.SessionControls.PersistentBrowser) {
            $persistBrowser = @{
                isEnabled = [bool]$policy.SessionControls.PersistentBrowser.IsEnabled
            }
            if ($policy.SessionControls.PersistentBrowser.Mode) {
                $persistBrowser.mode = $policy.SessionControls.PersistentBrowser.Mode
            }
            $sessionControls.persistentBrowser = $persistBrowser
        }
        
        $apiPolicy.sessionControls = $sessionControls
    }
    
    return $apiPolicy
}

# Process all YAML files
$yamlFiles = Get-ChildItem -Path $inputFolder -Filter "*.yaml","*.yml"

if ($yamlFiles.Count -eq 0) {
    Write-Warning "No YAML files found in '$inputFolder'"
    exit 0
}

Write-Host "Found $($yamlFiles.Count) YAML file(s)" -ForegroundColor Cyan
Write-Host "Converting to API-ready JSON..." -ForegroundColor Cyan
Write-Host ""

$successCount = 0
$failCount = 0
$skippedCount = 0

foreach ($file in $yamlFiles) {
    try {
        # Read file content
        $fileContent = Get-Content -Path $file.FullName -Raw
        
        # Check if file is marked as example (skip if first non-empty line contains "EXAMPLE POLICY")
        $firstLines = ($fileContent -split "`n" | Where-Object { $_.Trim() -ne "" } | Select-Object -First 3) -join " "
        if ($firstLines -match "(?i)#.*EXAMPLE\s+POLICY") {
            Write-Host "⊘ Skipped (example): $($file.Name)" -ForegroundColor Yellow
            $skippedCount++
            continue
        }
        
        # Parse YAML
        $policy = $fileContent | ConvertFrom-Yaml
        
        # Convert to API format
        $apiPolicy = ConvertTo-ApiFormat -policy $policy
        
        # Convert to JSON with proper formatting
        $json = $apiPolicy | ConvertTo-Json -Depth 10
        
        # Save to file
        $outputFile = Join-Path $outputFolder "$($file.BaseName).json"
        $json | Out-File -FilePath $outputFile -Encoding UTF8
        
        Write-Host "✓ Converted: $($file.Name)" -ForegroundColor Green
        $successCount++
    }
    catch {
        Write-Warning "✗ Failed to convert $($file.Name): $_"
        $failCount++
    }
}

Write-Host ""
Write-Host "Conversion complete!" -ForegroundColor Green
Write-Host "  Converted: $successCount" -ForegroundColor Green
Write-Host "  Skipped (examples): $skippedCount" -ForegroundColor Yellow
if ($failCount -gt 0) {
    Write-Host "  Failed: $failCount" -ForegroundColor Red
}
Write-Host "JSON files saved to: $((Get-Item $outputFolder).FullName)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps to import policies:" -ForegroundColor Yellow
Write-Host "  1. Review the JSON files in the output folder" -ForegroundColor Yellow
Write-Host "  2. Ensure you have the right Graph API permissions:" -ForegroundColor Yellow
Write-Host "     - Policy.ReadWrite.ConditionalAccess" -ForegroundColor Yellow
Write-Host "  3. Use this command to create a policy:" -ForegroundColor Yellow
Write-Host "     `$json = Get-Content 'path\to\policy.json' -Raw" -ForegroundColor Gray
Write-Host "     Invoke-MgGraphRequest -Uri 'https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies' -Method POST -Body `$json -ContentType 'application/json'" -ForegroundColor Gray
Write-Host ""
Write-Host "IMPORTANT NOTES:" -ForegroundColor Red
Write-Host "  - IDs (users, groups, roles, apps) from the source tenant may not exist in target tenant" -ForegroundColor Red
Write-Host "  - Review and update GUIDs before importing" -ForegroundColor Red
Write-Host "  - Consider setting state to 'enabledForReportingButNotEnforced' for testing" -ForegroundColor Red
Write-Host "  - The Id field is removed - new IDs will be generated on import" -ForegroundColor Red

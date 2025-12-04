# Convert Conditional Access Policies from JSON to YAML (Human and Computer Readable)

# Define input and output folders
$inputFolder = "ConditionalAccessPolicies"
$outputFolder = "ConditionalAccessPolicies-YAML"

# Verify input folder exists
if (-not (Test-Path $inputFolder)) {
    Write-Error "Input folder '$inputFolder' not found. Run 1b-Download-ConditionalAccessPolicies.ps1 first."
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

# Helper function to remove empty/null properties recursively
function Remove-EmptyProperties {
    param(
        [Parameter(ValueFromPipeline)]
        $InputObject
    )
    
    if ($null -eq $InputObject) {
        return $null
    }
    
    if ($InputObject -is [Array]) {
        $result = @()
        foreach ($item in $InputObject) {
            $cleaned = Remove-EmptyProperties -InputObject $item
            if ($null -ne $cleaned) {
                $result += $cleaned
            }
        }
        return if ($result.Count -gt 0) { $result } else { $null }
    }
    
    if ($InputObject -is [PSCustomObject] -or $InputObject -is [Hashtable]) {
        $result = @{}
        
        foreach ($property in $InputObject.PSObject.Properties) {
            $value = $property.Value
            
            # Skip null, empty arrays, empty strings, and empty objects
            if ($null -eq $value) { continue }
            if ($value -is [String] -and [string]::IsNullOrWhiteSpace($value)) { continue }
            if ($value -is [Array] -and $value.Count -eq 0) { continue }
            
            # Recursively clean nested objects
            $cleanedValue = Remove-EmptyProperties -InputObject $value
            
            if ($null -ne $cleanedValue) {
                # Check if it's an empty object
                if ($cleanedValue -is [Hashtable] -and $cleanedValue.Count -eq 0) {
                    continue
                }
                if ($cleanedValue -is [PSCustomObject] -and @($cleanedValue.PSObject.Properties).Count -eq 0) {
                    continue
                }
                
                $result[$property.Name] = $cleanedValue
            }
        }
        
        return if ($result.Count -gt 0) { [PSCustomObject]$result } else { $null }
    }
    
    return $InputObject
}

# Helper function to create a clean policy structure
function ConvertTo-CleanPolicy {
    param($policy)
    
    $cleanPolicy = [ordered]@{
        DisplayName = $policy.DisplayName
        State = $policy.State
    }
    
    # Add metadata only if present
    if ($policy.Id) { $cleanPolicy.Id = $policy.Id }
    if ($policy.CreatedDateTime) { $cleanPolicy.CreatedDateTime = $policy.CreatedDateTime }
    if ($policy.ModifiedDateTime) { $cleanPolicy.ModifiedDateTime = $policy.ModifiedDateTime }
    
    # Conditions
    $conditions = [ordered]@{}
    
    # Users
    if ($policy.Conditions.Users) {
        $users = [ordered]@{}
        if ($policy.Conditions.Users.IncludeUsers -and $policy.Conditions.Users.IncludeUsers.Count -gt 0) {
            $users.IncludeUsers = $policy.Conditions.Users.IncludeUsers
        }
        if ($policy.Conditions.Users.ExcludeUsers -and $policy.Conditions.Users.ExcludeUsers.Count -gt 0) {
            $users.ExcludeUsers = $policy.Conditions.Users.ExcludeUsers
        }
        if ($policy.Conditions.Users.IncludeGroups -and $policy.Conditions.Users.IncludeGroups.Count -gt 0) {
            $users.IncludeGroups = $policy.Conditions.Users.IncludeGroups
        }
        if ($policy.Conditions.Users.ExcludeGroups -and $policy.Conditions.Users.ExcludeGroups.Count -gt 0) {
            $users.ExcludeGroups = $policy.Conditions.Users.ExcludeGroups
        }
        if ($policy.Conditions.Users.IncludeRoles -and $policy.Conditions.Users.IncludeRoles.Count -gt 0) {
            $users.IncludeRoles = $policy.Conditions.Users.IncludeRoles
        }
        if ($policy.Conditions.Users.ExcludeRoles -and $policy.Conditions.Users.ExcludeRoles.Count -gt 0) {
            $users.ExcludeRoles = $policy.Conditions.Users.ExcludeRoles
        }
        if ($users.Count -gt 0) {
            $conditions.Users = [PSCustomObject]$users
        }
    }
    
    # Applications
    if ($policy.Conditions.Applications) {
        $apps = [ordered]@{}
        if ($policy.Conditions.Applications.IncludeApplications -and $policy.Conditions.Applications.IncludeApplications.Count -gt 0) {
            $apps.IncludeApplications = $policy.Conditions.Applications.IncludeApplications
        }
        if ($policy.Conditions.Applications.ExcludeApplications -and $policy.Conditions.Applications.ExcludeApplications.Count -gt 0) {
            $apps.ExcludeApplications = $policy.Conditions.Applications.ExcludeApplications
        }
        if ($policy.Conditions.Applications.IncludeUserActions -and $policy.Conditions.Applications.IncludeUserActions.Count -gt 0) {
            $apps.IncludeUserActions = $policy.Conditions.Applications.IncludeUserActions
        }
        if ($apps.Count -gt 0) {
            $conditions.Applications = [PSCustomObject]$apps
        }
    }
    
    # Platforms
    if ($policy.Conditions.Platforms) {
        $platforms = [ordered]@{}
        if ($policy.Conditions.Platforms.IncludePlatforms -and $policy.Conditions.Platforms.IncludePlatforms.Count -gt 0) {
            $platforms.IncludePlatforms = $policy.Conditions.Platforms.IncludePlatforms
        }
        if ($policy.Conditions.Platforms.ExcludePlatforms -and $policy.Conditions.Platforms.ExcludePlatforms.Count -gt 0) {
            $platforms.ExcludePlatforms = $policy.Conditions.Platforms.ExcludePlatforms
        }
        if ($platforms.Count -gt 0) {
            $conditions.Platforms = [PSCustomObject]$platforms
        }
    }
    
    # Locations
    if ($policy.Conditions.Locations) {
        $locations = [ordered]@{}
        if ($policy.Conditions.Locations.IncludeLocations -and $policy.Conditions.Locations.IncludeLocations.Count -gt 0) {
            $locations.IncludeLocations = $policy.Conditions.Locations.IncludeLocations
        }
        if ($policy.Conditions.Locations.ExcludeLocations -and $policy.Conditions.Locations.ExcludeLocations.Count -gt 0) {
            $locations.ExcludeLocations = $policy.Conditions.Locations.ExcludeLocations
        }
        if ($locations.Count -gt 0) {
            $conditions.Locations = [PSCustomObject]$locations
        }
    }
    
    # Client App Types
    if ($policy.Conditions.ClientAppTypes -and $policy.Conditions.ClientAppTypes.Count -gt 0) {
        $conditions.ClientAppTypes = $policy.Conditions.ClientAppTypes
    }
    
    # Device States
    if ($policy.Conditions.DeviceStates) {
        $deviceStates = [ordered]@{}
        if ($policy.Conditions.DeviceStates.IncludeStates -and $policy.Conditions.DeviceStates.IncludeStates.Count -gt 0) {
            $deviceStates.IncludeStates = $policy.Conditions.DeviceStates.IncludeStates
        }
        if ($policy.Conditions.DeviceStates.ExcludeStates -and $policy.Conditions.DeviceStates.ExcludeStates.Count -gt 0) {
            $deviceStates.ExcludeStates = $policy.Conditions.DeviceStates.ExcludeStates
        }
        if ($deviceStates.Count -gt 0) {
            $conditions.DeviceStates = [PSCustomObject]$deviceStates
        }
    }
    
    # Risk Levels
    if ($policy.Conditions.SignInRiskLevels -and $policy.Conditions.SignInRiskLevels.Count -gt 0) {
        $conditions.SignInRiskLevels = $policy.Conditions.SignInRiskLevels
    }
    if ($policy.Conditions.UserRiskLevels -and $policy.Conditions.UserRiskLevels.Count -gt 0) {
        $conditions.UserRiskLevels = $policy.Conditions.UserRiskLevels
    }
    
    if ($conditions.Count -gt 0) {
        $cleanPolicy.Conditions = [PSCustomObject]$conditions
    }
    
    # Grant Controls
    if ($policy.GrantControls) {
        $grants = [ordered]@{}
        if ($policy.GrantControls.Operator) {
            $grants.Operator = $policy.GrantControls.Operator
        }
        if ($policy.GrantControls.BuiltInControls -and $policy.GrantControls.BuiltInControls.Count -gt 0) {
            $grants.BuiltInControls = $policy.GrantControls.BuiltInControls
        }
        if ($policy.GrantControls.CustomAuthenticationFactors -and $policy.GrantControls.CustomAuthenticationFactors.Count -gt 0) {
            $grants.CustomAuthenticationFactors = $policy.GrantControls.CustomAuthenticationFactors
        }
        if ($policy.GrantControls.TermsOfUse -and $policy.GrantControls.TermsOfUse.Count -gt 0) {
            $grants.TermsOfUse = $policy.GrantControls.TermsOfUse
        }
        if ($grants.Count -gt 0) {
            $cleanPolicy.GrantControls = [PSCustomObject]$grants
        }
    }
    
    # Session Controls
    if ($policy.SessionControls) {
        $sessions = [ordered]@{}
        
        if ($policy.SessionControls.ApplicationEnforcedRestrictions -and 
            $policy.SessionControls.ApplicationEnforcedRestrictions.IsEnabled) {
            $sessions.ApplicationEnforcedRestrictions = @{ IsEnabled = $true }
        }
        
        if ($policy.SessionControls.CloudAppSecurity -and 
            $policy.SessionControls.CloudAppSecurity.IsEnabled) {
            $cloudAppSec = @{ IsEnabled = $true }
            if ($policy.SessionControls.CloudAppSecurity.CloudAppSecurityType) {
                $cloudAppSec.CloudAppSecurityType = $policy.SessionControls.CloudAppSecurity.CloudAppSecurityType
            }
            $sessions.CloudAppSecurity = $cloudAppSec
        }
        
        if ($policy.SessionControls.SignInFrequency -and 
            $policy.SessionControls.SignInFrequency.IsEnabled) {
            $signInFreq = @{ IsEnabled = $true }
            if ($policy.SessionControls.SignInFrequency.Value) {
                $signInFreq.Value = $policy.SessionControls.SignInFrequency.Value
                $signInFreq.Type = $policy.SessionControls.SignInFrequency.Type
            }
            $sessions.SignInFrequency = $signInFreq
        }
        
        if ($policy.SessionControls.PersistentBrowser -and 
            $policy.SessionControls.PersistentBrowser.IsEnabled) {
            $persistBrowser = @{ IsEnabled = $true }
            if ($policy.SessionControls.PersistentBrowser.Mode) {
                $persistBrowser.Mode = $policy.SessionControls.PersistentBrowser.Mode
            }
            $sessions.PersistentBrowser = $persistBrowser
        }
        
        if ($sessions.Count -gt 0) {
            $cleanPolicy.SessionControls = [PSCustomObject]$sessions
        }
    }
    
    return [PSCustomObject]$cleanPolicy
}

# Process all JSON files
$jsonFiles = Get-ChildItem -Path $inputFolder -Filter "*.json"

if ($jsonFiles.Count -eq 0) {
    Write-Warning "No JSON files found in '$inputFolder'"
    exit 0
}

Write-Host "Converting $($jsonFiles.Count) policies to YAML..." -ForegroundColor Cyan

foreach ($file in $jsonFiles) {
    try {
        # Read and parse JSON
        $jsonContent = Get-Content -Path $file.FullName -Raw | ConvertFrom-Json
        
        # Create clean policy structure
        $cleanPolicy = ConvertTo-CleanPolicy -policy $jsonContent
        
        # Convert to YAML
        $yaml = $cleanPolicy | ConvertTo-Yaml
        
        # Save to file
        $outputFile = Join-Path $outputFolder "$($file.BaseName).yaml"
        $yaml | Out-File -FilePath $outputFile -Encoding UTF8
        
        Write-Host "Converted: $($file.Name)" -ForegroundColor Green
    }
    catch {
        Write-Warning "Failed to convert $($file.Name): $_"
    }
}

Write-Host "`nConversion complete!" -ForegroundColor Green
Write-Host "YAML files saved to: $((Get-Item $outputFolder).FullName)" -ForegroundColor Green
Write-Host "`nYAML format benefits:" -ForegroundColor Yellow
Write-Host "  - Human-readable with clear hierarchy and structure" -ForegroundColor Yellow
Write-Host "  - Easy to parse programmatically" -ForegroundColor Yellow
Write-Host "  - Supports comments (you can add # comments)" -ForegroundColor Yellow
Write-Host "  - Version control friendly (clear diffs)" -ForegroundColor Yellow
Write-Host "  - No empty fields cluttering the output" -ForegroundColor Yellow

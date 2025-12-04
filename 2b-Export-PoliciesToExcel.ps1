# Convert Conditional Access Policies from JSON to Excel for Comparison

# Define input and output folders
$inputFolder = "ConditionalAccessPolicies"
$outputFile = "ConditionalAccessPolicies-Comparison.xlsx"

# Verify input folder exists
if (-not (Test-Path $inputFolder)) {
    Write-Error "Input folder '$inputFolder' not found. Run 1b-Download-ConditionalAccessPolicies.ps1 first."
    exit 1
}

# Check if ImportExcel module is installed
if (-not (Get-Module -ListAvailable -Name ImportExcel)) {
    Write-Host "ImportExcel module not found. Installing..." -ForegroundColor Yellow
    try {
        Install-Module -Name ImportExcel -Scope CurrentUser -Force -AllowClobber
        Write-Host "ImportExcel module installed successfully" -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to install ImportExcel module. Please run: Install-Module -Name ImportExcel -Scope CurrentUser"
        exit 1
    }
}

Import-Module ImportExcel

# Helper function to safely get array values as string
function Get-ArrayAsString {
    param($array, $prefix = "")
    
    if (-not $array -or $array.Count -eq 0) {
        return ""
    }
    
    $values = @()
    foreach ($item in $array) {
        if ($item -eq "All") { $values += "All" }
        elseif ($item -eq "GuestsOrExternalUsers") { $values += "Guests/External" }
        elseif ($item -eq "AllTrusted") { $values += "All Trusted" }
        elseif ($item -eq "Office365") { $values += "Office 365" }
        elseif ($item -eq "all") { $values += "All" }
        else { $values += $item }
    }
    
    if ($prefix) {
        return "$prefix`: " + ($values -join "; ")
    }
    return $values -join "; "
}

# Process all JSON files
$jsonFiles = Get-ChildItem -Path $inputFolder -Filter "*.json"

if ($jsonFiles.Count -eq 0) {
    Write-Warning "No JSON files found in '$inputFolder'"
    exit 0
}

Write-Host "Processing $($jsonFiles.Count) policies..." -ForegroundColor Cyan

# Build the data structure
$comparisonData = @()

# Define all possible rows (conditions and controls)
$rowDefinitions = @(
    @{Category = "Policy Info"; Field = "State"; Path = "State"}
    @{Category = "Policy Info"; Field = "Created Date"; Path = "CreatedDateTime"}
    @{Category = "Policy Info"; Field = "Modified Date"; Path = "ModifiedDateTime"}
    @{Category = ""; Field = ""; Path = ""}  # Empty row for separation
    
    @{Category = "Users"; Field = "Include Users"; Path = "Conditions.Users.IncludeUsers"}
    @{Category = "Users"; Field = "Exclude Users"; Path = "Conditions.Users.ExcludeUsers"}
    @{Category = "Users"; Field = "Include Groups"; Path = "Conditions.Users.IncludeGroups"}
    @{Category = "Users"; Field = "Exclude Groups"; Path = "Conditions.Users.ExcludeGroups"}
    @{Category = "Users"; Field = "Include Roles"; Path = "Conditions.Users.IncludeRoles"}
    @{Category = "Users"; Field = "Exclude Roles"; Path = "Conditions.Users.ExcludeRoles"}
    @{Category = ""; Field = ""; Path = ""}  # Empty row
    
    @{Category = "Applications"; Field = "Include Apps"; Path = "Conditions.Applications.IncludeApplications"}
    @{Category = "Applications"; Field = "Exclude Apps"; Path = "Conditions.Applications.ExcludeApplications"}
    @{Category = "Applications"; Field = "User Actions"; Path = "Conditions.Applications.IncludeUserActions"}
    @{Category = ""; Field = ""; Path = ""}  # Empty row
    
    @{Category = "Platforms"; Field = "Include Platforms"; Path = "Conditions.Platforms.IncludePlatforms"}
    @{Category = "Platforms"; Field = "Exclude Platforms"; Path = "Conditions.Platforms.ExcludePlatforms"}
    @{Category = ""; Field = ""; Path = ""}  # Empty row
    
    @{Category = "Locations"; Field = "Include Locations"; Path = "Conditions.Locations.IncludeLocations"}
    @{Category = "Locations"; Field = "Exclude Locations"; Path = "Conditions.Locations.ExcludeLocations"}
    @{Category = ""; Field = ""; Path = ""}  # Empty row
    
    @{Category = "Client Apps"; Field = "Client App Types"; Path = "Conditions.ClientAppTypes"}
    @{Category = ""; Field = ""; Path = ""}  # Empty row
    
    @{Category = "Risk"; Field = "Sign-in Risk Levels"; Path = "Conditions.SignInRiskLevels"}
    @{Category = "Risk"; Field = "User Risk Levels"; Path = "Conditions.UserRiskLevels"}
    @{Category = ""; Field = ""; Path = ""}  # Empty row
    
    @{Category = "Device"; Field = "Include Device States"; Path = "Conditions.DeviceStates.IncludeStates"}
    @{Category = "Device"; Field = "Exclude Device States"; Path = "Conditions.DeviceStates.ExcludeStates"}
    @{Category = ""; Field = ""; Path = ""}  # Empty row
    
    @{Category = "Grant Controls"; Field = "Operator"; Path = "GrantControls.Operator"}
    @{Category = "Grant Controls"; Field = "Built-in Controls"; Path = "GrantControls.BuiltInControls"}
    @{Category = "Grant Controls"; Field = "Custom Auth Factors"; Path = "GrantControls.CustomAuthenticationFactors"}
    @{Category = "Grant Controls"; Field = "Terms of Use"; Path = "GrantControls.TermsOfUse"}
    @{Category = ""; Field = ""; Path = ""}  # Empty row
    
    @{Category = "Session Controls"; Field = "App Restrictions"; Path = "SessionControls.ApplicationEnforcedRestrictions.IsEnabled"}
    @{Category = "Session Controls"; Field = "Cloud App Security"; Path = "SessionControls.CloudAppSecurity"}
    @{Category = "Session Controls"; Field = "Sign-in Frequency"; Path = "SessionControls.SignInFrequency"}
    @{Category = "Session Controls"; Field = "Persistent Browser"; Path = "SessionControls.PersistentBrowser"}
)

# Load all policies
$policies = @()
foreach ($file in $jsonFiles) {
    try {
        $policy = Get-Content -Path $file.FullName -Raw | ConvertFrom-Json
        $policies += @{
            Name = $policy.DisplayName
            Data = $policy
        }
    }
    catch {
        Write-Warning "Failed to load $($file.Name): $_"
    }
}

# Build comparison table
foreach ($rowDef in $rowDefinitions) {
    $row = [PSCustomObject]@{
        "Category" = $rowDef.Category
        "Condition/Control" = $rowDef.Field
    }
    
    # Add each policy as a column
    foreach ($policy in $policies) {
        $value = ""
        
        if ($rowDef.Path) {
            # Navigate the object path
            $parts = $rowDef.Path -split '\.'
            $current = $policy.Data
            
            foreach ($part in $parts) {
                if ($current -and $current.PSObject.Properties[$part]) {
                    $current = $current.$part
                }
                else {
                    $current = $null
                    break
                }
            }
            
            # Format the value
            if ($current) {
                if ($current -is [Array]) {
                    $value = Get-ArrayAsString -array $current
                }
                elseif ($current -is [Boolean]) {
                    $value = if ($current) { "Yes" } else { "No" }
                }
                elseif ($current.PSObject.Properties['IsEnabled']) {
                    # Handle session controls with IsEnabled property
                    if ($current.IsEnabled) {
                        $details = @()
                        if ($current.PSObject.Properties['CloudAppSecurityType'] -and $current.CloudAppSecurityType) {
                            $details += $current.CloudAppSecurityType
                        }
                        if ($current.PSObject.Properties['Value'] -and $current.Value) {
                            $details += "$($current.Value) $($current.Type)"
                        }
                        if ($current.PSObject.Properties['Mode'] -and $current.Mode) {
                            $details += $current.Mode
                        }
                        $value = if ($details.Count -gt 0) { "Enabled: " + ($details -join ", ") } else { "Enabled" }
                    }
                    else {
                        $value = ""
                    }
                }
                elseif ($current -is [String]) {
                    $value = $current
                }
                elseif ($current -is [DateTime]) {
                    $value = $current.ToString("yyyy-MM-dd HH:mm")
                }
                else {
                    $value = $current.ToString()
                }
            }
        }
        
        # Add policy column
        $row | Add-Member -MemberType NoteProperty -Name $policy.Name -Value $value
    }
    
    $comparisonData += $row
}

# Export to Excel
Write-Host "Exporting to Excel..." -ForegroundColor Cyan

try {
    # Remove existing file if it exists
    if (Test-Path $outputFile) {
        Remove-Item $outputFile -Force
    }
    
    # Export with formatting
    $comparisonData | Export-Excel -Path $outputFile `
        -WorksheetName "Policy Comparison" `
        -AutoSize `
        -FreezeTopRow `
        -BoldTopRow `
        -AutoFilter `
        -TableName "CAComparison"
    
    Write-Host "Excel file created successfully!" -ForegroundColor Green
    Write-Host "File location: $((Get-Item $outputFile).FullName)" -ForegroundColor Green
    Write-Host "`nTips:" -ForegroundColor Yellow
    Write-Host "  - First two columns show Category and Condition/Control" -ForegroundColor Yellow
    Write-Host "  - Each subsequent column represents a policy" -ForegroundColor Yellow
    Write-Host "  - Empty cells mean that condition/control is not configured" -ForegroundColor Yellow
    Write-Host "  - Use Excel's filter and sort features to compare policies" -ForegroundColor Yellow
}
catch {
    Write-Error "Failed to create Excel file: $_"
    exit 1
}

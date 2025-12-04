# Convert Conditional Access Policies from JSON to Human-Readable Text

# Define input and output folders
$inputFolder = "ConditionalAccessPolicies"
$outputFolder = "ConditionalAccessPolicies-Text"

# Verify input folder exists
if (-not (Test-Path $inputFolder)) {
    Write-Error "Input folder '$inputFolder' not found. Run 1b-Download-ConditionalAccessPolicies.ps1 first."
    exit 1
}

# Create output directory
if (-not (Test-Path $outputFolder)) {
    New-Item -ItemType Directory -Path $outputFolder | Out-Null
}

# Helper function to convert policy object to readable text
function ConvertTo-ReadableText {
    param($policy)
    
    $text = @()
    $separator = "=" * 80
    $line = "-" * 80
    
    $text += $separator
    $text += "  $($policy.DisplayName)"
    $text += $separator
    $text += ""
    
    # Basic Information
    $text += "STATUS: $($policy.State.ToUpper())"
    if ($policy.CreatedDateTime) { $text += "Created: $($policy.CreatedDateTime)" }
    if ($policy.ModifiedDateTime) { $text += "Modified: $($policy.ModifiedDateTime)" }
    $text += ""
    $text += $line
    $text += ""
    
    # Main logic structure
    $text += "POLICY LOGIC:"
    $text += ""
    $text += "WHEN the following conditions are met:"
    $text += ""
    
    # Users
    if ($policy.Conditions.Users) {
        $text += "  • Users/Groups/Roles:"
        
        if ($policy.Conditions.Users.IncludeUsers -and $policy.Conditions.Users.IncludeUsers.Count -gt 0) {
            $text += "      Include Users:"
            foreach ($user in $policy.Conditions.Users.IncludeUsers) {
                if ($user -eq "All") { $text += "        - All users" }
                elseif ($user -eq "GuestsOrExternalUsers") { $text += "        - Guests or external users" }
                else { $text += "        - $user" }
            }
        }
        
        if ($policy.Conditions.Users.ExcludeUsers -and $policy.Conditions.Users.ExcludeUsers.Count -gt 0) {
            $text += "      EXCEPT Users:"
            foreach ($user in $policy.Conditions.Users.ExcludeUsers) {
                $text += "        - $user"
            }
        }
        
        if ($policy.Conditions.Users.IncludeGroups -and $policy.Conditions.Users.IncludeGroups.Count -gt 0) {
            $text += "      Include Groups:"
            foreach ($group in $policy.Conditions.Users.IncludeGroups) {
                $text += "        - $group"
            }
        }
        
        if ($policy.Conditions.Users.ExcludeGroups -and $policy.Conditions.Users.ExcludeGroups.Count -gt 0) {
            $text += "      EXCEPT Groups:"
            foreach ($group in $policy.Conditions.Users.ExcludeGroups) {
                $text += "        - $group"
            }
        }
        
        if ($policy.Conditions.Users.IncludeRoles -and $policy.Conditions.Users.IncludeRoles.Count -gt 0) {
            $text += "      Include Roles:"
            foreach ($role in $policy.Conditions.Users.IncludeRoles) {
                $text += "        - $role"
            }
        }
        
        if ($policy.Conditions.Users.ExcludeRoles -and $policy.Conditions.Users.ExcludeRoles.Count -gt 0) {
            $text += "      EXCEPT Roles:"
            foreach ($role in $policy.Conditions.Users.ExcludeRoles) {
                $text += "        - $role"
            }
        }
        $text += ""
    }
    
    # Applications
    if ($policy.Conditions.Applications) {
        $text += "  • Applications:"
        
        if ($policy.Conditions.Applications.IncludeApplications -and $policy.Conditions.Applications.IncludeApplications.Count -gt 0) {
            $text += "      Include:"
            foreach ($app in $policy.Conditions.Applications.IncludeApplications) {
                if ($app -eq "All") { $text += "        - All cloud apps" }
                elseif ($app -eq "Office365") { $text += "        - Office 365" }
                else { $text += "        - $app" }
            }
        }
        
        if ($policy.Conditions.Applications.ExcludeApplications -and $policy.Conditions.Applications.ExcludeApplications.Count -gt 0) {
            $text += "      EXCEPT:"
            foreach ($app in $policy.Conditions.Applications.ExcludeApplications) {
                $text += "        - $app"
            }
        }
        
        if ($policy.Conditions.Applications.IncludeUserActions -and $policy.Conditions.Applications.IncludeUserActions.Count -gt 0) {
            $text += "      User Actions:"
            foreach ($action in $policy.Conditions.Applications.IncludeUserActions) {
                $text += "        - $action"
            }
        }
        $text += ""
    }
    
    # Platforms
    if ($policy.Conditions.Platforms -and ($policy.Conditions.Platforms.IncludePlatforms -or $policy.Conditions.Platforms.ExcludePlatforms)) {
        $text += "  • Device Platforms:"
        
        if ($policy.Conditions.Platforms.IncludePlatforms -and $policy.Conditions.Platforms.IncludePlatforms.Count -gt 0) {
            $text += "      Include:"
            foreach ($platform in $policy.Conditions.Platforms.IncludePlatforms) {
                if ($platform -eq "all") { $text += "        - All platforms" }
                else { $text += "        - $platform" }
            }
        }
        
        if ($policy.Conditions.Platforms.ExcludePlatforms -and $policy.Conditions.Platforms.ExcludePlatforms.Count -gt 0) {
            $text += "      EXCEPT:"
            foreach ($platform in $policy.Conditions.Platforms.ExcludePlatforms) {
                $text += "        - $platform"
            }
        }
        $text += ""
    }
    
    # Locations
    if ($policy.Conditions.Locations -and ($policy.Conditions.Locations.IncludeLocations -or $policy.Conditions.Locations.ExcludeLocations)) {
        $text += "  • Locations:"
        
        if ($policy.Conditions.Locations.IncludeLocations -and $policy.Conditions.Locations.IncludeLocations.Count -gt 0) {
            $text += "      Include:"
            foreach ($location in $policy.Conditions.Locations.IncludeLocations) {
                if ($location -eq "All") { $text += "        - All locations" }
                elseif ($location -eq "AllTrusted") { $text += "        - All trusted locations" }
                else { $text += "        - $location" }
            }
        }
        
        if ($policy.Conditions.Locations.ExcludeLocations -and $policy.Conditions.Locations.ExcludeLocations.Count -gt 0) {
            $text += "      EXCEPT:"
            foreach ($location in $policy.Conditions.Locations.ExcludeLocations) {
                if ($location -eq "AllTrusted") { $text += "        - All trusted locations" }
                else { $text += "        - $location" }
            }
        }
        $text += ""
    }
    
    # Client Apps
    if ($policy.Conditions.ClientAppTypes -and $policy.Conditions.ClientAppTypes.Count -gt 0) {
        $text += "  • Client App Types:"
        foreach ($app in $policy.Conditions.ClientAppTypes) {
            $text += "      - $app"
        }
        $text += ""
    }
    
    # Device States
    if ($policy.Conditions.DeviceStates -and ($policy.Conditions.DeviceStates.IncludeStates -or $policy.Conditions.DeviceStates.ExcludeStates)) {
        $text += "  • Device States:"
        
        if ($policy.Conditions.DeviceStates.IncludeStates -and $policy.Conditions.DeviceStates.IncludeStates.Count -gt 0) {
            $text += "      Include:"
            foreach ($state in $policy.Conditions.DeviceStates.IncludeStates) {
                $text += "        - $state"
            }
        }
        
        if ($policy.Conditions.DeviceStates.ExcludeStates -and $policy.Conditions.DeviceStates.ExcludeStates.Count -gt 0) {
            $text += "      EXCEPT:"
            foreach ($state in $policy.Conditions.DeviceStates.ExcludeStates) {
                $text += "        - $state"
            }
        }
        $text += ""
    }
    
    # Sign-in Risk
    if ($policy.Conditions.SignInRiskLevels -and $policy.Conditions.SignInRiskLevels.Count -gt 0) {
        $text += "  • Sign-in Risk Levels:"
        foreach ($risk in $policy.Conditions.SignInRiskLevels) {
            $text += "      - $risk"
        }
        $text += ""
    }
    
    # User Risk
    if ($policy.Conditions.UserRiskLevels -and $policy.Conditions.UserRiskLevels.Count -gt 0) {
        $text += "  • User Risk Levels:"
        foreach ($risk in $policy.Conditions.UserRiskLevels) {
            $text += "      - $risk"
        }
        $text += ""
    }
    
    $text += $line
    $text += ""
    
    # Grant Controls - THE RESULT
    if ($policy.GrantControls) {
        $text += "THEN apply the following controls:"
        $text += ""
        
        if ($policy.GrantControls.Operator) {
            $operatorText = if ($policy.GrantControls.Operator -eq "OR") { 
                "  (User must satisfy ONE of the following)" 
            } else { 
                "  (User must satisfy ALL of the following)" 
            }
            $text += $operatorText
            $text += ""
        }
        
        if ($policy.GrantControls.BuiltInControls -and $policy.GrantControls.BuiltInControls.Count -gt 0) {
            foreach ($control in $policy.GrantControls.BuiltInControls) {
                $controlText = switch ($control) {
                    "mfa" { "  ✓ Require multi-factor authentication" }
                    "compliantDevice" { "  ✓ Require device to be marked as compliant" }
                    "domainJoinedDevice" { "  ✓ Require Hybrid Azure AD joined device" }
                    "approvedApplication" { "  ✓ Require approved client app" }
                    "compliantApplication" { "  ✓ Require app protection policy" }
                    "passwordChange" { "  ✓ Require password change" }
                    "block" { "  ✗ BLOCK ACCESS" }
                    default { "  ✓ $control" }
                }
                $text += $controlText
            }
        }
        
        if ($policy.GrantControls.CustomAuthenticationFactors -and $policy.GrantControls.CustomAuthenticationFactors.Count -gt 0) {
            $text += ""
            $text += "  Custom Authentication Factors:"
            foreach ($factor in $policy.GrantControls.CustomAuthenticationFactors) {
                $text += "    - $factor"
            }
        }
        
        if ($policy.GrantControls.TermsOfUse -and $policy.GrantControls.TermsOfUse.Count -gt 0) {
            $text += ""
            $text += "  Terms of Use:"
            foreach ($term in $policy.GrantControls.TermsOfUse) {
                $text += "    - $term"
            }
        }
        $text += ""
    }
    
    # Session Controls
    if ($policy.SessionControls) {
        $hasSessionControls = $false
        $sessionText = @()
        
        if ($policy.SessionControls.ApplicationEnforcedRestrictions -and $policy.SessionControls.ApplicationEnforcedRestrictions.IsEnabled) {
            $hasSessionControls = $true
            $sessionText += "  • Application enforced restrictions enabled"
        }
        
        if ($policy.SessionControls.CloudAppSecurity -and $policy.SessionControls.CloudAppSecurity.IsEnabled) {
            $hasSessionControls = $true
            $typeText = if ($policy.SessionControls.CloudAppSecurity.CloudAppSecurityType) {
                " ($($policy.SessionControls.CloudAppSecurity.CloudAppSecurityType))"
            } else { "" }
            $sessionText += "  • Cloud App Security monitoring enabled$typeText"
        }
        
        if ($policy.SessionControls.SignInFrequency -and $policy.SessionControls.SignInFrequency.IsEnabled) {
            $hasSessionControls = $true
            $freqText = if ($policy.SessionControls.SignInFrequency.Value) {
                " - require re-authentication every $($policy.SessionControls.SignInFrequency.Value) $($policy.SessionControls.SignInFrequency.Type)"
            } else { "" }
            $sessionText += "  • Sign-in frequency control enabled$freqText"
        }
        
        if ($policy.SessionControls.PersistentBrowser -and $policy.SessionControls.PersistentBrowser.IsEnabled) {
            $hasSessionControls = $true
            $modeText = if ($policy.SessionControls.PersistentBrowser.Mode) {
                " ($($policy.SessionControls.PersistentBrowser.Mode))"
            } else { "" }
            $sessionText += "  • Persistent browser session$modeText"
        }
        
        if ($hasSessionControls) {
            $text += "AND enforce these session controls:"
            $text += ""
            $text += $sessionText
            $text += ""
        }
    }
    
    $text += $separator
    $text += ""
    
    return $text -join "`n"
}

# Process all JSON files
$jsonFiles = Get-ChildItem -Path $inputFolder -Filter "*.json"

if ($jsonFiles.Count -eq 0) {
    Write-Warning "No JSON files found in '$inputFolder'"
    exit 0
}

Write-Host "Converting $($jsonFiles.Count) policies to readable text..." -ForegroundColor Cyan

foreach ($file in $jsonFiles) {
    try {
        # Read and parse JSON
        $jsonContent = Get-Content -Path $file.FullName -Raw | ConvertFrom-Json
        
        # Convert to readable text
        $readableText = ConvertTo-ReadableText -policy $jsonContent
        
        # Save to file
        $outputFile = Join-Path $outputFolder "$($file.BaseName).txt"
        $readableText | Out-File -FilePath $outputFile -Encoding UTF8
        
        Write-Host "Converted: $($file.Name)" -ForegroundColor Green
    }
    catch {
        Write-Warning "Failed to convert $($file.Name): $_"
    }
}

Write-Host "`nConversion complete!" -ForegroundColor Green
Write-Host "Text files saved to: $((Get-Item $outputFolder).FullName)"

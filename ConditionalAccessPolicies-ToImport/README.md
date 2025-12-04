# Creating Conditional Access Policies from YAML

This folder (`ConditionalAccessPolicies-ToImport`) is where you place YAML files that define Conditional Access policies you want to import into your tenant.

## YAML File Format

YAML files must follow this structure:

```yaml
DisplayName: Policy Name Here
State: enabledForReportingButNotEnforced  # or enabled, or disabled
Conditions:
  Users:
    IncludeUsers:
      - All  # or specific user GUIDs
    ExcludeUsers:
      - user-guid-here
    IncludeGroups:
      - group-guid-here
    ExcludeGroups:
      - group-guid-here
    IncludeRoles:
      - role-template-id-here
    ExcludeRoles:
      - role-template-id-here
  
  Applications:
    IncludeApplications:
      - All  # or Office365, or specific app GUIDs
    ExcludeApplications:
      - app-guid-here
  
  ClientAppTypes:
    - all  # or: browser, mobileAppsAndDesktopClients, exchangeActiveSync, other
  
  Platforms:
    IncludePlatforms:
      - all  # or: android, iOS, windows, macOS, linux
    ExcludePlatforms:
      - android
  
  Locations:
    IncludeLocations:
      - All
    ExcludeLocations:
      - AllTrusted  # or specific named location GUIDs
  
  SignInRiskLevels:
    - high
    - medium
  
  UserRiskLevels:
    - high

GrantControls:
  Operator: OR  # or AND
  BuiltInControls:
    - mfa  # Other options: compliantDevice, domainJoinedDevice, approvedApplication, compliantApplication, passwordChange, block

SessionControls:
  SignInFrequency:
    IsEnabled: true
    Value: 1
    Type: hours  # or days
  
  CloudAppSecurity:
    IsEnabled: true
    CloudAppSecurityType: mcasConfigured  # or monitorOnly, blockDownloads
  
  ApplicationEnforcedRestrictions:
    IsEnabled: true
  
  PersistentBrowser:
    IsEnabled: true
    Mode: always  # or never
```

## Important Notes

### Policy State Options

- **`disabled`** - Policy is off, not enforced
- **`enabled`** - Policy is active and enforced
- **`enabledForReportingButNotEnforced`** - Report-only mode (recommended for testing)

### Common GUIDs and Values

**Built-in Role Template IDs:**
- Global Administrator: `62e90394-69f5-4237-9190-012177145e10`
- Security Administrator: `194ae4cb-b126-40b2-bd5b-6091b380977d`
- User Administrator: `fe930be7-5e62-47db-91af-98c3a49a38b1`
- [Full list of role template IDs](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference)

**Special User/App Values:**
- `All` - All users or all cloud apps
- `GuestsOrExternalUsers` - Guest users
- `Office365` - All Office 365 apps

**Client App Types:**
- `all` - All client apps
- `browser` - Web browsers
- `mobileAppsAndDesktopClients` - Mobile apps and desktop clients
- `exchangeActiveSync` - Exchange ActiveSync clients
- `other` - Other clients (legacy authentication)

**Grant Controls:**
- `mfa` - Require multi-factor authentication
- `compliantDevice` - Require device to be marked as compliant
- `domainJoinedDevice` - Require Hybrid Azure AD joined device
- `approvedApplication` - Require approved client app
- `compliantApplication` - Require app protection policy
- `passwordChange` - Require password change
- `block` - Block access

## Workflow

### 1. Create or Edit YAML Files

Place your YAML policy files in this folder. You can:

- **Start from scratch** using the format above
- **Copy from exported policies** - Copy YAML files from `ConditionalAccessPolicies-YAML/` folder (exported by script 5)
- **Use the example** - Modify `Example-RequireMFAforAdmins.yaml` as a template

**Note:** Files marked as examples (with `# EXAMPLE POLICY` comment at the top) will be automatically skipped during conversion. Remove this comment to include them.

### 2. Update GUIDs for Target Tenant

**Critical:** GUIDs (users, groups, roles, apps, locations) from one tenant don't exist in another. You must:

- Replace user GUIDs with users from the target tenant
- Replace group GUIDs with groups from the target tenant
- Role template IDs are universal and don't need changing
- Named location GUIDs need to be updated if used
- App GUIDs should be verified or use `All` or `Office365`

### 3. Set Policy State

For testing, use:
```yaml
State: enabledForReportingButNotEnforced
```

This allows you to see what the policy would do without enforcing it.

### 4. Run the Conversion Script

```powershell
.\6-Convert-YAMLToImportJSON.ps1
```

This creates API-ready JSON files in `ConditionalAccessPolicies-ForImport/` folder.

### 5. Review Generated JSON

Check the JSON files in `ConditionalAccessPolicies-ForImport/` to ensure they look correct.

### 6. Import to Tenant

Connect to your target tenant and create the policies:

```powershell
# Connect to target tenant
.\1-Connect-MgGraphTenant.ps1

# Import a policy
$policyJson = Get-Content "ConditionalAccessPolicies-ForImport\YourPolicy.json" -Raw
Invoke-MgGraphRequest -Uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" -Method POST -Body $policyJson -ContentType "application/json"
```

## Getting User and Group GUIDs

To find GUIDs in your target tenant:

```powershell
# Find user GUID
Get-MgUser -Filter "userPrincipalName eq 'user@domain.com'" | Select-Object Id, DisplayName

# Find group GUID
Get-MgGroup -Filter "displayName eq 'Group Name'" | Select-Object Id, DisplayName

# Find all named locations
Invoke-MgGraphRequest -Uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/namedLocations"
```

## Tips

1. **Start with report-only mode** - Always test policies with `enabledForReportingButNotEnforced` first
2. **Exclude break-glass accounts** - Always exclude emergency access accounts from policies
3. **Test incrementally** - Import one policy at a time and verify it works
4. **Document your changes** - YAML supports comments with `#`, use them!
5. **Version control** - Keep YAML files in git to track policy changes over time

## Example Scenarios

### Block Legacy Authentication

```yaml
DisplayName: Block - Legacy Authentication
State: enabled
Conditions:
  Users:
    IncludeUsers:
      - All
    ExcludeUsers:
      - break-glass-account-guid
  Applications:
    IncludeApplications:
      - All
  ClientAppTypes:
    - exchangeActiveSync
    - other
GrantControls:
  Operator: OR
  BuiltInControls:
    - block
```

### Require Compliant Device for Mobile Access

```yaml
DisplayName: Require Compliant Device - Mobile
State: enabled
Conditions:
  Users:
    IncludeUsers:
      - All
  Applications:
    IncludeApplications:
      - Office365
  Platforms:
    IncludePlatforms:
      - iOS
      - android
GrantControls:
  Operator: OR
  BuiltInControls:
    - compliantDevice
```

## Troubleshooting

**Error: "User/Group/Role not found"**
- The GUID doesn't exist in the target tenant. Update with correct GUIDs.

**Error: "Named location not found"**
- Named locations are tenant-specific. Create them first or remove the location condition.

**Policy not working as expected**
- Check sign-in logs in Azure Portal
- Use report-only mode to see what would happen
- Verify exclusions are working correctly

## Reference Documentation

- [Microsoft Graph API - Create Conditional Access Policy](https://learn.microsoft.com/en-us/graph/api/conditionalaccessroot-post-policies)
- [Conditional Access Policy Schema](https://learn.microsoft.com/en-us/graph/api/resources/conditionalaccesspolicy)
- [Built-in Azure AD Roles](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference)

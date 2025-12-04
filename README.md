# Conditional Access Policy Management Scripts

A complete PowerShell toolkit for exporting, analyzing, and importing Microsoft Entra Conditional Access policies across tenants.

## Overview

This toolset allows you to:
- **Export** policies from one tenant
- **Analyze** them in multiple formats (text, Excel, YAML)
- **Modify** policies in human-readable YAML format
- **Import** policies into another tenant

Perfect for tenant migrations, policy documentation, backup/restore, or multi-tenant management.

## Prerequisites

1. **PowerShell 7+** (recommended) or Windows PowerShell 5.1
2. **Python 3.8+** (for CAPL parser - script 5)
3. **Microsoft.Graph PowerShell SDK**
   ```powershell
   Install-Module Microsoft.Graph.Identity.SignIns -Scope CurrentUser
   ```
4. **Additional modules** (auto-installed by scripts when needed):
   - `ImportExcel` - for Excel exports
   - `powershell-yaml` - for YAML format

## Setup

### PowerShell Modules

Install required modules:

```powershell
Install-Module Microsoft.Graph.Identity.SignIns -Scope CurrentUser
Install-Module ImportExcel -Scope CurrentUser
Install-Module powershell-yaml -Scope CurrentUser
```

### Python Environment (for CAPL Scripts)

Create a virtual environment and install dependencies:

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install Python requirements
python -m pip install -r requirements.txt

# Copy .env.example to .env and configure Azure OpenAI credentials
Copy-Item .env.example .env
# Edit .env with your values
```

**Note:** Activate the virtual environment each time before running Python scripts:
```powershell
.\.venv\Scripts\Activate.ps1
python 5-Validate-CAPL-With-LLM.py
python 6-Parse-CAPL-To-YAML.py
```

## Permissions Required

### For Exporting (Reading Policies)
- **Azure AD Role**: Global Reader, Security Reader, or Security Administrator
- **Graph API Permission**: `Policy.Read.All`

### For Importing (Creating Policies)
- **Azure AD Role**: Security Administrator or Conditional Access Administrator
- **Graph API Permission**: `Policy.ReadWrite.ConditionalAccess`

## Workflow

### Step 1: Export Policies from Source Tenant

**1a. Connect to Source Tenant (Read Mode)**
```powershell
.\1a-Connect-MgGraphTenant-Read.ps1
```
- Uses device code authentication
- Reads tenant ID from `.env` file (optional)
- Requires `Policy.Read.All` scope

**1b. Download Policies**
```powershell
.\1b-Download-ConditionalAccessPolicies.ps1
```
- Downloads all Conditional Access policies as JSON
- Saves to `ConditionalAccessPolicies/` folder
- Each policy saved as separate file

### Step 2: Export to Analysis Formats (Choose One or More)

**2a. Export to Human-Readable Text**
```powershell
.\2a-Export-PoliciesToText.ps1
```
- Creates plain text files with WHEN/THEN/AND logic
- Easy to read, no special viewer needed
- Output: `ConditionalAccessPolicies-Text/`

**2b. Export to Excel for Comparison**
```powershell
.\2b-Export-PoliciesToExcel.ps1
```
- Creates Excel table with policies as columns
- Each row is a condition/control for easy comparison
- Output: `ConditionalAccessPolicies-Comparison.xlsx`

**2c. Export to YAML (Recommended for Editing)**
```powershell
.\2c-Export-PoliciesToYAML.ps1
```
- Human and machine-readable format
- Perfect for version control (git)
- Easy to edit and supports comments
- Removes empty fields for clarity
- Output: `ConditionalAccessPolicies-YAML/`

### Step 3: Prepare Policies for Import (Optional)

If you want to import/recreate policies in another tenant:

**3. Convert YAML to Import-Ready JSON**
```powershell
.\3-Convert-YAMLToImportJSON.ps1
```
- Reads YAML files from `ConditionalAccessPolicies-ToImport/`
- Converts to Microsoft Graph API format
- Automatically skips example files
- Output: `ConditionalAccessPolicies-ForImport/`

**Important:** Before running step 3, you need to:
1. Copy YAML files from `ConditionalAccessPolicies-YAML/` to `ConditionalAccessPolicies-ToImport/`
2. Edit the YAML files to update GUIDs for the target tenant
3. See `ConditionalAccessPolicies-ToImport/README.md` for detailed instructions

### Step 4: Import Policies to Target Tenant

**4a. Connect to Target Tenant (Write Mode)**
```powershell
.\4a-Connect-MgGraphTenant-Write.ps1
```
- Uses device code authentication
- Requires `Policy.ReadWrite.ConditionalAccess` scope
- Be careful - this allows creating/modifying policies!

**4b. Import Policies**
```powershell
.\4b-Import-PoliciesFromJSON.ps1
```
- Creates policies from JSON files
- Shows confirmation prompt before proceeding
- Reports success/failure for each policy
- Saves detailed results to CSV file

## Configuration

### Tenant ID (Optional)

Create a `.env` file in the root folder to specify a tenant ID:

```
TENANT_ID=your-tenant-id-here
```

This is useful when you're a guest in multiple tenants. See `.env.example` for reference.

## Common Workflows

### Backup Policies
1. Run `1a` → `1b` → `2c` (Export to YAML)
2. Commit YAML files to git repository
3. You now have version-controlled policy backups!

### Compare Policies Across Tenants
1. Run `1a` → `1b` → `2b` (Export to Excel)
2. Repeat for another tenant (change tenant ID in `.env`)
3. Open both Excel files side-by-side for comparison

### Migrate Policies to New Tenant
1. **Source tenant**: Run `1a` → `1b` → `2c` (Export to YAML)
2. Copy YAML files from `ConditionalAccessPolicies-YAML/` to `ConditionalAccessPolicies-ToImport/`
3. Edit YAML files to update user/group/role/app GUIDs for target tenant
4. Run `3` (Convert YAML to JSON)
5. **Target tenant**: Run `4a` → `4b` (Import policies)

### Document Policies for Review
1. Run `1a` → `1b` → `2a` (Export to text)
2. Share text files with team for review
3. Text format is easy to read without special tools

## File Structure

```
ConditionalAccessPolicies/              # Original JSON from Graph API
ConditionalAccessPolicies-Text/         # Human-readable text format
ConditionalAccessPolicies-YAML/         # YAML format (for editing)
ConditionalAccessPolicies-Comparison.xlsx  # Excel comparison table
ConditionalAccessPolicies-ToImport/     # YAML policies to import (user-managed)
ConditionalAccessPolicies-ForImport/    # JSON ready for Graph API import
ConditionalAccessPolicies-Generated/    # YAML files generated by CAPL parser
PolicyLanguage-Draft/                   # Rough CAPL files (human-written)
PolicyLanguage/                         # Validated CAPL files (LLM-cleaned)
import-results-*.csv                    # Import operation results
```

## CAPL - Conditional Access Policy Language (Optional)

For complex policy workflows, you can use the Conditional Access Policy Language (CAPL) - a human-friendly DSL for writing policies.

### CAPL Workflow

**Step 5: Validate Rough CAPL Files with LLM**
```powershell
.\.venv\Scripts\Activate.ps1
python 5-Validate-CAPL-With-LLM.py
```
- Reads rough/imprecise CAPL files from `PolicyLanguage-Draft/`
- Uses Azure OpenAI to fix syntax errors while preserving intent
- Outputs validated CAPL to `PolicyLanguage/`
- Requires Azure OpenAI credentials in `.env` file

**Step 6: Parse CAPL to YAML**
```powershell
.\.venv\Scripts\Activate.ps1
python 6-Parse-CAPL-To-YAML.py
```
- Parses validated CAPL files from `PolicyLanguage/`
- Generates YAML policies in `ConditionalAccessPolicies-Generated/`
- Then continue with step 3 (YAML to JSON) and step 4 (import)

See `PolicyLanguage/README.md` for complete CAPL syntax documentation and examples.

## Scripts Reference

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `1a-Connect-MgGraphTenant-Read.ps1` | Connect with read permissions | `.env` (optional) | Graph connection |
| `1b-Download-ConditionalAccessPolicies.ps1` | Download policies as JSON | Graph connection | `ConditionalAccessPolicies/*.json` |
| `2a-Export-PoliciesToText.ps1` | Export to plain text | JSON files | `ConditionalAccessPolicies-Text/*.txt` |
| `2b-Export-PoliciesToExcel.ps1` | Export to Excel comparison | JSON files | `ConditionalAccessPolicies-Comparison.xlsx` |
| `2c-Export-PoliciesToYAML.ps1` | Export to YAML (editable) | JSON files | `ConditionalAccessPolicies-YAML/*.yaml` |
| `3-Convert-YAMLToImportJSON.ps1` | Convert YAML to import JSON | YAML in `ToImport/` | `ConditionalAccessPolicies-ForImport/*.json` |
| `4a-Connect-MgGraphTenant-Write.ps1` | Connect with write permissions | `.env` (optional) | Graph connection |
| `4b-Import-PoliciesFromJSON.ps1` | Create policies in tenant | JSON in `ForImport/` | Policies + CSV results |
| `5-Validate-CAPL-With-LLM.py` | Validate rough CAPL with LLM | CAPL in `PolicyLanguage-Draft/` | Validated CAPL in `PolicyLanguage/` |
| `6-Parse-CAPL-To-YAML.py` | Parse CAPL to YAML | CAPL in `PolicyLanguage/` | YAML in `ConditionalAccessPolicies-Generated/` |

## Tips and Best Practices

### Security
- Always use **break-glass accounts** and exclude them from all policies
- Test policies in **report-only mode** (`enabledForReportingButNotEnforced`) first
- Never commit `.env` file to git (already in `.gitignore`)

### Tenant Migration
- User/group/role/app GUIDs are tenant-specific
- Role template IDs are universal (don't need changing)
- Named locations must be recreated in target tenant
- Test with one policy first before bulk import

### Version Control
- YAML format is git-friendly (clear diffs)
- Add comments in YAML to document policy purpose
- Use meaningful commit messages for policy changes

### Troubleshooting

**"DeviceCodeCredential authentication failed"**
- This is a known SDK issue with cached credentials
- The scripts use `-ContextScope Process` to avoid this
- If it persists, restart PowerShell

**"User/Group/Role not found" during import**
- GUIDs from source tenant don't exist in target
- Update YAML files with correct GUIDs before step 3
- See `ConditionalAccessPolicies-ToImport/README.md` for help

**"Insufficient permissions"**
- Ensure you have the correct Azure AD role
- Check that consent was granted for the API scopes
- Try disconnecting and reconnecting with correct scope

**Import fails with duplicate name**
- Policy with same name already exists
- Either rename in YAML or delete existing policy

## Documentation

- [Microsoft Graph API - Conditional Access](https://learn.microsoft.com/en-us/graph/api/resources/conditionalaccesspolicy)
- [Conditional Access Best Practices](https://learn.microsoft.com/en-us/entra/identity/conditional-access/plan-conditional-access)
- [Azure AD Role Permissions](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference)

## Contributing

Found a bug or have a feature request? Please document it in your workflow notes.

## License

These scripts are provided as-is for managing Microsoft Entra Conditional Access policies.

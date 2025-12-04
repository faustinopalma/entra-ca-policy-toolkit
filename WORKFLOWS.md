# Complete Workflow Summary

## Overview

This toolkit provides a complete solution for managing Microsoft Entra Conditional Access policies, from export to human-friendly editing to automated deployment.

## Complete Workflows

### Workflow A: Export and Backup Policies

**Purpose:** Download and backup existing policies from a tenant

```powershell
# 1. Connect to tenant (read-only)
.\1a-Connect-MgGraphTenant-Read.ps1

# 2. Download all policies as JSON
.\1b-Download-ConditionalAccessPolicies.ps1

# 3. Export to YAML for version control
.\2c-Export-PoliciesToYAML.ps1
```

**Output:** YAML files in `ConditionalAccessPolicies-YAML/` ready for git

---

### Workflow B: Policy Analysis and Documentation

**Purpose:** Create human-readable documentation of policies

```powershell
# Steps 1-2 same as Workflow A

# 3a. Export to plain text for review
.\2a-Export-PoliciesToText.ps1

# 3b. Export to Excel for comparison
.\2b-Export-PoliciesToExcel.ps1
```

**Output:** Text files and Excel comparison table for review

---

### Workflow C: Tenant Migration

**Purpose:** Copy policies from one tenant to another

```powershell
# SOURCE TENANT
# 1. Connect and download
.\1a-Connect-MgGraphTenant-Read.ps1
.\1b-Download-ConditionalAccessPolicies.ps1
.\2c-Export-PoliciesToYAML.ps1

# 2. Prepare for import
# - Copy YAML files from ConditionalAccessPolicies-YAML/ to ConditionalAccessPolicies-ToImport/
# - Edit YAML files to update GUIDs for target tenant

# 3. Convert to import format
.\3-Convert-YAMLToImportJSON.ps1

# TARGET TENANT
# 4. Connect with write permissions
.\4a-Connect-MgGraphTenant-Write.ps1

# 5. Import policies
.\4b-Import-PoliciesFromJSON.ps1
```

**Output:** Policies created in target tenant

---

### Workflow D: Create Policies with CAPL (Natural Language)

**Purpose:** Write policies in human-friendly language with LLM validation

```powershell
# 1. Write rough policies in PolicyLanguage-Draft/
# - Use natural language
# - Don't worry about exact syntax
# - See example-rough-policies.capl

# 2. Activate Python environment
.\.venv\Scripts\Activate.ps1

# 3. Validate with LLM
python 5-Validate-CAPL-With-LLM.py
# - Reads from PolicyLanguage-Draft/
# - Uses Azure OpenAI to fix syntax
# - Saves cleaned CAPL to PolicyLanguage/

# 4. Review validated CAPL files in PolicyLanguage/

# 5. Parse CAPL to YAML
python 6-Parse-CAPL-To-YAML.py
# - Generates YAML in ConditionalAccessPolicies-Generated/

# 6. Convert YAML to JSON
# - Copy YAML files from ConditionalAccessPolicies-Generated/ to ConditionalAccessPolicies-ToImport/
# - Update GUIDs if needed
.\3-Convert-YAMLToImportJSON.ps1

# 7. Deploy policies
.\4a-Connect-MgGraphTenant-Write.ps1
.\4b-Import-PoliciesFromJSON.ps1
```

**Output:** Policies deployed from natural language descriptions

---

### Workflow E: CAPL with Manual Validation (No LLM)

**Purpose:** Write policies in CAPL without Azure OpenAI dependency

```powershell
# 1. Write policies directly in PolicyLanguage/
# - Follow CAPL syntax exactly
# - See PolicyLanguage/README.md for syntax reference
# - Use examples.capl and nested-examples.capl as templates

# 2. Activate Python environment
.\.venv\Scripts\Activate.ps1

# 3. Parse CAPL to YAML
python 6-Parse-CAPL-To-YAML.py

# 4-7. Same as Workflow D (steps 6-7)
```

**Output:** Policies deployed from manually-written CAPL

---

## Script Reference

| # | Script | Purpose | Input | Output |
|---|--------|---------|-------|--------|
| 1a | `Connect-MgGraphTenant-Read.ps1` | Connect with read permissions | `.env` (optional) | Graph connection |
| 1b | `Download-ConditionalAccessPolicies.ps1` | Download policies as JSON | Graph connection | `ConditionalAccessPolicies/*.json` |
| 2a | `Export-PoliciesToText.ps1` | Export to plain text | JSON files | `ConditionalAccessPolicies-Text/*.txt` |
| 2b | `Export-PoliciesToExcel.ps1` | Export to Excel | JSON files | `*.xlsx` |
| 2c | `Export-PoliciesToYAML.ps1` | Export to YAML | JSON files | `ConditionalAccessPolicies-YAML/*.yaml` |
| 3 | `Convert-YAMLToImportJSON.ps1` | Convert YAML to JSON | YAML in `ToImport/` | `ConditionalAccessPolicies-ForImport/*.json` |
| 4a | `Connect-MgGraphTenant-Write.ps1` | Connect with write permissions | `.env` (optional) | Graph connection |
| 4b | `Import-PoliciesFromJSON.ps1` | Create policies in tenant | JSON in `ForImport/` | Policies + CSV results |
| 5 | `Validate-CAPL-With-LLM.py` | Validate rough CAPL with LLM | `PolicyLanguage-Draft/*.capl` | `PolicyLanguage/*.capl` |
| 6 | `Parse-CAPL-To-YAML.py` | Parse CAPL to YAML | `PolicyLanguage/*.capl` | `ConditionalAccessPolicies-Generated/*.yaml` |

---

## Folder Structure

```
.
├── 1a-Connect-MgGraphTenant-Read.ps1
├── 1b-Download-ConditionalAccessPolicies.ps1
├── 2a-Export-PoliciesToText.ps1
├── 2b-Export-PoliciesToExcel.ps1
├── 2c-Export-PoliciesToYAML.ps1
├── 3-Convert-YAMLToImportJSON.ps1
├── 4a-Connect-MgGraphTenant-Write.ps1
├── 4b-Import-PoliciesFromJSON.ps1
├── 5-Validate-CAPL-With-LLM.py
├── 6-Parse-CAPL-To-YAML.py
├── .env (your configuration)
├── .env.example (template)
├── requirements.txt
├── README.md
├── WORKFLOWS.md (this file)
│
├── PolicyLanguage-Draft/          # Your rough CAPL files (step 5 input)
│   ├── README.md
│   └── *.capl
│
├── PolicyLanguage/                # Validated CAPL (step 5 output, step 6 input)
│   ├── README.md
│   ├── grammar.md
│   ├── examples.capl
│   ├── nested-examples.capl
│   └── *.capl
│
├── ConditionalAccessPolicies/     # Downloaded JSON (step 1b output)
│   └── *.json
│
├── ConditionalAccessPolicies-Text/    # Human-readable text (step 2a output)
│   └── *.txt
│
├── ConditionalAccessPolicies-YAML/    # YAML export (step 2c output)
│   └── *.yaml
│
├── ConditionalAccessPolicies-Comparison.xlsx  # Excel comparison (step 2b output)
│
├── ConditionalAccessPolicies-ToImport/    # YAML to import (step 3 input - you copy here)
│   ├── README.md
│   └── *.yaml
│
├── ConditionalAccessPolicies-ForImport/   # JSON for import (step 3 output, step 4b input)
│   └── *.json
│
└── ConditionalAccessPolicies-Generated/   # CAPL-generated YAML (step 6 output)
    └── *.yaml
```

---

## Configuration

### Environment Variables (.env)

```env
# Tenant ID (optional - only needed if guest in multiple tenants)
TENANT_ID=your-tenant-guid

# Azure OpenAI configuration (required for script 5 only)
AZURE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/openai/deployments/your-deployment/chat/completions?api-version=2024-05-01-preview
AZURE_API_KEY=your-api-key
```

### Python Setup

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Copy and configure .env
Copy-Item .env.example .env
# Edit .env with your values
```

---

## Quick Start Examples

### Example 1: Backup all policies to git

```powershell
.\1a-Connect-MgGraphTenant-Read.ps1
.\1b-Download-ConditionalAccessPolicies.ps1
.\2c-Export-PoliciesToYAML.ps1
git add ConditionalAccessPolicies-YAML/
git commit -m "Backup CA policies $(Get-Date -Format 'yyyy-MM-dd')"
```

### Example 2: Create one policy from natural language

```powershell
# 1. Create PolicyLanguage-Draft/my-policy.capl:
#    if user is all
#    and app is all cloud apps
#    require mfa

# 2. Run LLM validation
.\.venv\Scripts\Activate.ps1
python 5-Validate-CAPL-With-LLM.py

# 3. Generate YAML
python 6-Parse-CAPL-To-YAML.py

# 4. Review and deploy
# Copy from ConditionalAccessPolicies-Generated/ to ConditionalAccessPolicies-ToImport/
# Update GUIDs if needed
.\3-Convert-YAMLToImportJSON.ps1
.\4a-Connect-MgGraphTenant-Write.ps1
.\4b-Import-PoliciesFromJSON.ps1
```

### Example 3: Compare policies across two tenants

```powershell
# Tenant 1
.\1a-Connect-MgGraphTenant-Read.ps1
.\1b-Download-ConditionalAccessPolicies.ps1
.\2b-Export-PoliciesToExcel.ps1
Rename-Item "ConditionalAccessPolicies-Comparison.xlsx" "Tenant1-Policies.xlsx"

# Tenant 2 (update .env with different TENANT_ID)
.\1a-Connect-MgGraphTenant-Read.ps1
.\1b-Download-ConditionalAccessPolicies.ps1
.\2b-Export-PoliciesToExcel.ps1
Rename-Item "ConditionalAccessPolicies-Comparison.xlsx" "Tenant2-Policies.xlsx"

# Open both Excel files side-by-side
```

---

## Tips

### Security Best Practices
- Always test policies in `report-only` mode first
- Exclude break-glass accounts from all policies
- Review policies before import with `.\4b-Import-PoliciesFromJSON.ps1` (shows confirmation)

### CAPL Tips
- Use descriptive comments to explain policy logic
- Start simple - test with one IF block
- LLM validator adds `report-only` mode when policy state is unclear
- Review LLM output in `PolicyLanguage/` before parsing

### Git Workflow
- Commit YAML files (human-readable diffs)
- Don't commit generated folders (in `.gitignore`)
- Never commit `.env` file (contains secrets)

### Troubleshooting
- **Authentication errors:** Add `-ContextScope Process` (already in scripts)
- **Import fails:** Check GUIDs match target tenant
- **Parser warnings:** Review CAPL syntax in `PolicyLanguage/README.md`
- **LLM errors:** Verify `AZURE_ENDPOINT` and `AZURE_API_KEY` in `.env`

---

## Next Steps

1. Choose your workflow based on your needs
2. Follow the steps in order
3. Review outputs at each stage
4. Keep YAML files in version control

For detailed CAPL syntax, see `PolicyLanguage/README.md`

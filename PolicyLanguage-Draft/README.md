# PolicyLanguage-Draft

This folder contains **rough, human-written CAPL files** that may have syntax errors or imprecisions.

## Workflow

1. **Write your policies here** using approximate CAPL syntax
   - Don't worry about perfect syntax
   - Focus on the logic and intent
   - Use natural language descriptions if needed
   - Missing GUIDs? Leave placeholder text

2. **Run the LLM validator** to clean them up:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   python 5-Validate-CAPL-With-LLM.py
   ```

3. **Review the validated output** in the `PolicyLanguage/` folder

4. **Parse to YAML** once you're satisfied:
   ```powershell
   python 6-Parse-CAPL-To-YAML.py
   ```

## Example

Create a file like `my-policies.capl` with rough content:

```
# Require MFA for all cloud apps
if user is all users
and app is all cloud apps
then require mfa
state: enabled

# Block legacy authentication
when client is legacy auth
then block access
```

The LLM validator will convert this to proper CAPL syntax with correct keywords, indentation, and structure.

## Benefits

- **Write naturally** without memorizing exact syntax
- **LLM fixes errors** while preserving your intent
- **Faster iteration** - focus on logic, not syntax
- **Safer deployment** - LLM adds report-only mode when unclear

## Tips

- Add comments to explain complex logic
- Use descriptive variable names
- One policy per IF block
- Don't worry about GUIDs initially

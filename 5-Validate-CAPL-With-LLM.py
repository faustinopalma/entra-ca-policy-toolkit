"""
CAPL Validator - LLM-powered policy cleanup
Reads rough/imprecise CAPL files and uses Azure OpenAI to convert them to valid CAPL syntax
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")

# Validate credentials
if not AZURE_ENDPOINT or not AZURE_API_KEY:
    print("Error: Missing Azure OpenAI credentials!")
    print("Please set AZURE_ENDPOINT and AZURE_API_KEY in your .env file")
    sys.exit(1)


# System prompt explaining CAPL syntax
SYSTEM_PROMPT = """You are a Conditional Access Policy Language (CAPL) expert. Your task is to take rough, imprecise policy descriptions and convert them into valid CAPL syntax.

## CAPL Syntax Rules

### Structure
```
IF condition1
    condition2
    STATE enabled|disabled|report-only
        action1
        action2
END
```

### Variables
```
VAR VariableName = "Display Name" [guid]
```

### Conditions
All conditions on separate lines (ANDed together). Available conditions:

**User:**
- `user is All`
- `user is Guest`
- `user in group "Name" [guid]`
- `user in role "Name" [guid]`
- `user NOT in group "Name" [guid]`

**App:**
- `app is All`
- `app is Office365`
- `app in "Name" [guid]`

**Platform:**
- `platform is Windows|macOS|Linux|iOS|Android|WindowsPhone`
- `platform is iOS OR platform is Android` (for multiple)

**Device:**
- `device is Compliant`
- `device is HybridJoined`
- `device NOT is Compliant`

**Location:**
- `location is Trusted`
- `location is All`
- `location in "Name" [guid]`
- `location NOT is Trusted`

**Client:**
- `client is Browser|MobileApp|DesktopApp|ExchangeActiveSync|Other`
- `client NOT is Browser`

**Risk:**
- `signin-risk is High|Medium|Low`
- `user-risk is High|Medium|Low`

### Actions
All actions indented under STATE:

**Grant Controls:**
- `REQUIRE MFA`
- `REQUIRE CompliantDevice`
- `REQUIRE HybridJoined`
- `REQUIRE ApprovedApp`
- `REQUIRE AppProtection`
- `REQUIRE PasswordChange`
- `BLOCK`
- `ALLOW`

**Multiple requirements (all must be satisfied):**
```
REQUIRE MFA
REQUIRE CompliantDevice
```

**Alternative requirements (any one):**
```
REQUIRE AppProtection OR CompliantDevice
```

**Session Controls:**
- `SESSION signin-frequency <number> hours|days`
- `SESSION persistent-browser always|never`
- `SESSION monitor with CloudAppSecurity`
- `SESSION block-downloads`

### Nested IF-ELSE
```
IF condition1
    STATE enabled
        action1
ELSE IF condition2
    STATE enabled
        action2
ELSE
    STATE enabled
        action3
END
```

**Important:** No THEN keyword after ELSE/ELSE IF - actions follow directly after STATE.

## Your Task

1. Read the rough/imprecise policy description
2. Identify the intent (what the user wants to achieve)
3. Convert it to valid CAPL syntax following ALL rules above
4. Use proper indentation (4 spaces per level)
5. Add comments to explain complex logic
6. If GUIDs are missing, use placeholder: [00000000-0000-0000-0000-000000000000]
7. If policy state is unclear, default to "report-only" for safety
8. Preserve the semantic meaning even if syntax is wrong

## Output Format

Return ONLY the valid CAPL code. Do not include explanations, markdown code fences, or any other text.
Just return the clean, valid CAPL syntax that can be directly saved to a .capl file.

If you need to add clarifying comments, use # at the start of the line.
"""


def call_azure_llm(user_content):
    """
    Call Azure OpenAI to validate and correct CAPL syntax
    
    Args:
        user_content: The rough CAPL policy text
    
    Returns:
        The corrected CAPL text
    """
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY,
    }
    
    payload = {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        "max_completion_tokens": 16000,
        "temperature": 0.3,  # Lower temperature for more precise syntax
    }
    
    try:
        print("Calling Azure OpenAI for CAPL validation...")
        
        response = requests.post(
            AZURE_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Show token usage
        if "usage" in result:
            usage = result["usage"]
            print(f"  Token usage: {usage.get('total_tokens', 0):,} tokens")
        
        # Extract content
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
        
        print("WARNING: Could not extract content from LLM response")
        return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error calling Azure OpenAI: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        raise


def clean_llm_output(content):
    """Remove markdown code fences if LLM added them"""
    lines = content.strip().split('\n')
    
    # Remove opening code fence
    if lines[0].startswith('```'):
        lines = lines[1:]
    
    # Remove closing code fence
    if lines[-1].startswith('```'):
        lines = lines[:-1]
    
    return '\n'.join(lines)


def main():
    """Main entry point"""
    print("=" * 60)
    print("CAPL Validator - LLM-powered Policy Cleanup")
    print("=" * 60)
    print()
    
    # Setup paths
    input_folder = Path("PolicyLanguage-Draft")
    output_folder = Path("PolicyLanguage")
    output_folder.mkdir(exist_ok=True)
    
    if not input_folder.exists():
        print(f"Error: Input folder '{input_folder}' not found!")
        print()
        print("Please create this folder and add your rough .capl files there.")
        print("Example: PolicyLanguage-Draft/my-policies.capl")
        return 1
    
    # Find all .capl files
    capl_files = list(input_folder.glob("*.capl"))
    
    if not capl_files:
        print(f"No .capl files found in '{input_folder}'")
        print()
        print("Add your rough policy files to this folder and run again.")
        return 1
    
    print(f"Found {len(capl_files)} file(s) to validate:\n")
    for f in capl_files:
        print(f"  - {f.name}")
    print()
    
    # Process each file
    for capl_file in capl_files:
        print(f"Processing: {capl_file.name}")
        
        try:
            # Read rough policy
            with open(capl_file, 'r', encoding='utf-8') as f:
                rough_content = f.read()
            
            print(f"  Input size: {len(rough_content)} characters")
            
            # Call LLM to fix it
            corrected_content = call_azure_llm(rough_content)
            
            if not corrected_content:
                print(f"  ✗ Failed to get corrected content")
                continue
            
            # Clean up any markdown fences
            corrected_content = clean_llm_output(corrected_content)
            
            print(f"  Output size: {len(corrected_content)} characters")
            
            # Save corrected version
            output_file = output_folder / capl_file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(corrected_content)
            
            print(f"  ✓ Saved to: {output_file}")
            print()
            
        except Exception as e:
            print(f"  ✗ Error processing {capl_file.name}: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 60)
    print("DONE! Validated files saved to 'PolicyLanguage/' folder")
    print()
    print("Next steps:")
    print("  1. Review the corrected .capl files")
    print("  2. Run: python 6-Parse-CAPL-To-YAML.py")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

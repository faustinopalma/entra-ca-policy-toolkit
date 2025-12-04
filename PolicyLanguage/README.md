# Conditional Access Policy Language (CAPL)

A simple, declarative language for defining Conditional Access policies using human-readable IF-ELSE logic.

## Language Syntax

### Basic Structure

```
IF condition1
    condition2
    STATE enabled|disabled|report-only
        action1
        action2
END
```

**Key principles:**
- Multiple conditions on separate lines are ANDed together
- STATE keyword determines policy enforcement mode
- Actions are indented under STATE
- END keyword closes the IF block

### Nested IF-ELSE Structure

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

**Note:** No THEN keyword needed after ELSE/ELSE IF - actions follow directly.

### Complete Example from Real-World Scenario

```
# Mobile device access policy
IF platform is iOS OR platform is Android
    IF device is Compliant
        IF app is Office365
            STATE enabled
                REQUIRE CompliantDevice
                REQUIRE AppProtection
        ELSE
            # Edge/VPN or generic access
            STATE enabled
                REQUIRE CompliantDevice
    ELSE
        # Personal Mobile - BYOD scenario
        IF user in group $BYOD_Users
            IF app is Office365
                STATE enabled
                    REQUIRE AppProtection
            ELSE
                STATE enabled
                    BLOCK
        ELSE
            STATE enabled
                BLOCK
END

# Workstation access policy
IF platform is Windows OR platform is macOS
    IF device is Compliant
        STATE enabled
            REQUIRE CompliantDevice
    ELSE
        # Personal Workstation
        IF user-risk is Low
            IF client is Browser
                STATE enabled
                    REQUIRE MFA
                    SESSION block-downloads
            ELSE
                STATE enabled
                    BLOCK
        ELSE
            STATE enabled
                BLOCK
END
```

### Conditions

Conditions define when a policy applies. Multiple conditions on separate lines are ANDed together.

**User Conditions:**
```
user is All
user is Guest
user in group "Group Name" [guid]
user in role "Role Name" [guid]
user NOT in group "Group Name" [guid]
```

**App Conditions:**
```
app is All
app is Office365
app in "App Name" [guid]
```

**Platform Conditions:**
```
platform is Windows
platform is macOS
platform is Linux
platform is iOS
platform is Android
platform is WindowsPhone
platform is iOS OR platform is Android
```

**Device Conditions:**
```
device is Compliant
device is HybridJoined
device NOT is Compliant
```

**Location Conditions:**
```
location is Trusted
location is All
location in "Location Name" [guid]
location NOT is Trusted
```

**Client Conditions:**
```
client is Browser
client is MobileApp
client is DesktopApp
client is ExchangeActiveSync
client is Other
client NOT is Browser
```

**Risk Conditions:**
```
signin-risk is High
signin-risk is Medium
signin-risk is Low
user-risk is High
user-risk is Medium
user-risk is Low
```

### Actions

Actions specify what to do when conditions match. Actions are indented under STATE.

**Grant Controls:**
```
REQUIRE MFA
REQUIRE CompliantDevice
REQUIRE HybridJoined
REQUIRE ApprovedApp
REQUIRE AppProtection
REQUIRE PasswordChange

BLOCK
ALLOW
```

**Multiple Requirements (all must be satisfied):**
```
REQUIRE MFA
REQUIRE CompliantDevice
```

**Alternative Requirements (any one can be satisfied):**
```
REQUIRE AppProtection OR CompliantDevice
REQUIRE MFA OR HybridJoined
```

**Session Controls:**
```
SESSION signin-frequency <number> hours
SESSION signin-frequency <number> days
SESSION persistent-browser always
SESSION persistent-browser never
SESSION monitor with CloudAppSecurity
SESSION block-downloads
```

### Variables

Variables allow you to define reusable values:

```
VAR BreakGlassGroup = "Emergency Access" [12345678-1234-1234-1234-123456789012]
VAR GlobalAdminRole = "Global Administrator" [62e90394-69f5-4237-9190-012177145e10]

IF user is All
    user NOT in group $BreakGlassGroup
    STATE enabled
        REQUIRE MFA
END
```

### Policy States

- **enabled** - Policy is active and enforced
- **disabled** - Policy exists but is not enforced
- **report-only** - Policy logs matches but doesn't enforce (audit mode)

## Reserved Keywords

- IF, ELSE IF, ELSE, END, STATE
- user, group, role, app, platform, device, location, client
- signin-risk, user-risk
- REQUIRE, BLOCK, ALLOW, SESSION
- is, in, NOT, AND, OR
- All, Guest, Trusted, Office365, Compliant, HybridJoined
- MFA, CompliantDevice, ApprovedApp, AppProtection, PasswordChange
- enabled, disabled, report-only

## Best Practices

1. **Start with variables** - Define all GUIDs at the top for reusability
2. **Use descriptive comments** - Label each policy clearly with purpose
3. **Start with report-only** - Test policies before enabling enforcement
4. **Always exclude break-glass accounts** - Prevent admin lockout
5. **Group related policies** - Keep logical policies together in the file
6. **Use nested IF-ELSE for complex logic** - Express decision trees naturally
7. **Keep nesting depth reasonable** - More than 3-4 levels becomes hard to read
8. **Document nested branches** - Add comments explaining each decision path
9. **Consistent indentation** - Use 4 spaces per level for readability
10. **One STATE per branch** - Every IF/ELSE IF/ELSE needs its own STATE

## Why This Syntax?

**Natural expression** - Matches how you think about policy logic
```
IF this situation
    check this detail
    STATE enabled
        do this action
ELSE
    different situation
    STATE enabled
        do that action
```

**Clean and minimal** - No unnecessary keywords after ELSE
**Visual hierarchy** - Indentation shows the decision structure clearly
**Unambiguous** - STATE keyword clearly separates conditions from actions
**Single source of truth** - All logic in one place, not scattered across many policies

## How It Works

1. **Write your policies** in `.capl` files using this syntax
2. **Run the parser** (script 5) to convert CAPL → YAML policies
3. **Use script 3** to convert YAML → JSON for import
4. **Import with script 4b** to create policies in your tenant

Each unique path through a nested IF-ELSE tree becomes a separate conditional access policy with a generated name.

## Common Patterns

### Pattern 1: Risk-Based Progressive Requirements
```
IF signin-risk is High
    STATE enabled
        BLOCK
ELSE IF signin-risk is Medium
    STATE enabled
        REQUIRE MFA
ELSE
    STATE enabled
        ALLOW
END
```

### Pattern 2: Platform-Specific Requirements
```
IF platform is Windows OR platform is macOS
    STATE enabled
        REQUIRE HybridJoined
ELSE IF platform is iOS OR platform is Android
    STATE enabled
        REQUIRE CompliantDevice
ELSE
    STATE enabled
        BLOCK
END
```

### Pattern 3: Location and Device Trust Matrix
```
IF location is Trusted
    IF device is Compliant
        STATE enabled
            ALLOW
    ELSE
        STATE enabled
            REQUIRE MFA
ELSE
    IF device is Compliant
        STATE enabled
            REQUIRE MFA
    ELSE
        STATE enabled
            BLOCK
END
```

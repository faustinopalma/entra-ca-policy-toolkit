# Conditional Access Policy Language - Formal Grammar

## EBNF Grammar

```ebnf
Program       ::= ( Variable | IfStatement | COMMENT )*

Variable      ::= 'VAR' IDENTIFIER '=' STRING '[' GUID ']'

IfStatement   ::= 'IF' ConditionList
                  'STATE' PolicyState
                  ActionList
                  ( ElseIfPart* )
                  ( ElsePart )?
                  'END'

ElseIfPart    ::= 'ELSE' 'IF' ConditionList
                  'STATE' PolicyState
                  ActionList

ElsePart      ::= 'ELSE'
                  'STATE' PolicyState
                  ActionList

ConditionList ::= Condition+

Condition     ::= UserCondition
                | AppCondition
                | PlatformCondition
                | DeviceCondition
                | LocationCondition
                | ClientCondition
                | RiskCondition

UserCondition ::= 'user' 'is' ( 'All' | 'Guest' )
                | 'user' ['NOT'] 'in' 'group' STRING '[' GUID ']'
                | 'user' ['NOT'] 'in' 'role' STRING '[' GUID ']'

AppCondition  ::= 'app' 'is' ( 'All' | 'Office365' )
                | 'app' 'in' STRING '[' GUID ']'

PlatformCondition ::= 'platform' 'is' Platform ( 'OR' 'platform' 'is' Platform )*

Platform      ::= 'Windows' | 'macOS' | 'Linux' | 'iOS' | 'Android' | 'WindowsPhone'

DeviceCondition ::= 'device' 'is' DeviceState
                  | 'device' 'NOT' 'is' DeviceState

DeviceState   ::= 'Compliant' | 'HybridJoined'

LocationCondition ::= 'location' 'is' ( 'All' | 'Trusted' )
                    | 'location' ['NOT'] 'is' 'Trusted'
                    | 'location' 'in' STRING '[' GUID ']'

ClientCondition ::= 'client' ['NOT'] 'is' ClientType ( 'OR' 'client' 'is' ClientType )*

ClientType    ::= 'Browser' | 'MobileApp' | 'DesktopApp' | 'ExchangeActiveSync' | 'Other'

RiskCondition ::= ( 'signin-risk' | 'user-risk' ) 'is' RiskLevel

RiskLevel     ::= 'High' | 'Medium' | 'Low'

PolicyState   ::= 'enabled' | 'disabled' | 'report-only'

ActionList    ::= Action+
                | IfStatement

Action        ::= GrantAction | SessionAction

GrantAction   ::= 'REQUIRE' GrantControl ( 'OR' GrantControl )?
                | 'BLOCK'
                | 'ALLOW'

GrantControl  ::= 'MFA' | 'CompliantDevice' | 'HybridJoined' 
                | 'ApprovedApp' | 'AppProtection' | 'PasswordChange'

SessionAction ::= 'SESSION' SessionControl

SessionControl ::= 'signin-frequency' NUMBER ( 'hours' | 'days' )
                 | 'persistent-browser' ( 'always' | 'never' )
                 | 'monitor' 'with' 'CloudAppSecurity'
                 | 'block-downloads'

IDENTIFIER    ::= [a-zA-Z][a-zA-Z0-9_]*
STRING        ::= '"' [^"]* '"'
GUID          ::= [0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}
NUMBER        ::= [0-9]+
COMMENT       ::= '#' [^\n]*
```

## Semantic Rules

1. **Variables must be declared before use**
2. **GUIDs must be valid UUIDs**
3. **Policy names are auto-generated** based on conditions and actions
4. **At least one condition** must be specified in IF clause
5. **STATE keyword is required** - Separates conditions from actions
6. **At least one action** must be specified after STATE
7. **OR operator for conditions** - Can only be used for multiple values of same condition type
8. **Multiple REQUIRE actions** - Listed on separate lines means all must be satisfied (AND logic)
9. **REQUIRE with OR** - Single line with OR means any one can be satisfied
10. **Session controls** - Can be combined with grant controls
11. **Nested IF-ELSE** - Can be nested to any depth (recommended max 4 levels)
12. **ELSE clause is optional** - If omitted means "no policy" for that path
13. **Each IF block must end with END**
14. **Each branch needs STATE** - Every IF/ELSE IF/ELSE must declare enabled/disabled/report-only
15. **No THEN after ELSE** - Actions follow directly after ELSE/ELSE IF
16. **Indentation recommended** - Use 4 spaces per level for readability

## Example Syntax

```
# Variables
VAR BreakGlassGroup = "Emergency Access" [12345678-1234-1234-1234-123456789012]
VAR GlobalAdminRole = "Global Administrator" [62e90394-69f5-4237-9190-012177145e10]

# Simple policy
IF user is All
    app is All
    STATE enabled
        REQUIRE MFA
END

# Nested IF-ELSE
IF user-risk is High
    STATE enabled
        BLOCK
ELSE IF user-risk is Medium
    STATE enabled
        REQUIRE MFA
ELSE
    STATE enabled
        ALLOW
END

# Deeply nested logic (based on user's example)
IF platform is iOS OR platform is Android
    IF device is Compliant
        IF app is Office365
            STATE enabled
                REQUIRE CompliantDevice
                REQUIRE AppProtection
        ELSE
            STATE enabled
                REQUIRE CompliantDevice
    ELSE
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

# Admin with location check
IF user in role "Global Admin" [guid]
    IF location is Trusted
        STATE enabled
            REQUIRE MFA
            SESSION signin-frequency 4 hours
    ELSE
        STATE enabled
            BLOCK
ELSE
    STATE enabled
        REQUIRE MFA
END
```

## Invalid Expressions

```
# Cannot OR different condition types
user is All OR app is Office365  # INVALID

# Cannot AND within same condition (use separate lines)
user is All AND user in group "..." # INVALID - use two lines

# Missing END keyword
IF user is All
    STATE enabled
        REQUIRE MFA
# INVALID - missing END

# Missing STATE keyword
IF user is All
    REQUIRE MFA  # INVALID - needs STATE before actions
END

# Using THEN after IF (deprecated)
IF user is All
THEN  # INVALID - THEN not needed after IF, STATE comes directly
    STATE enabled
        REQUIRE MFA
END

# Using THEN after ELSE (deprecated)
IF user is All
    STATE enabled
        BLOCK
ELSE
THEN  # INVALID - no THEN after ELSE
    STATE enabled
        ALLOW
END

# Multiple ORs for REQUIRE (use separate lines or single OR)
REQUIRE MFA OR CompliantDevice OR HybridJoined  # INVALID - max 2 with OR
```

## Nested IF-ELSE to Policy Conversion

The parser will convert nested logic into multiple CA policies. Each unique path through the decision tree becomes a separate policy.

**Example Input:**
```
IF user in role "Admin" [guid]
    IF location is Trusted
        STATE enabled
            REQUIRE MFA
    ELSE
        STATE enabled
            BLOCK
ELSE
    STATE enabled
        ALLOW
END
```

**Generates Policies:**
1. **Policy "Generated-1-Admin-Trusted"**: 
   - Conditions: user in role Admin AND location is Trusted
   - Action: REQUIRE MFA
   - State: enabled

2. **Policy "Generated-2-Admin-NotTrusted"**: 
   - Conditions: user in role Admin AND location NOT is Trusted
   - Action: BLOCK
   - State: enabled

3. **Policy "Generated-3-NotAdmin"**: 
   - Conditions: user NOT in role Admin
   - Action: ALLOW
   - State: enabled

Each generated policy will be in YAML format ready for import using script 3.

## Design Rationale

**Why no THEN after ELSE?**
- ELSE already indicates "otherwise" - THEN is redundant
- Makes code cleaner and more readable
- Follows natural language flow

**Why STATE keyword?**
- Clearly separates conditions from actions
- Makes it unambiguous where the "what to do" begins
- Allows easy switching between enabled/disabled/report-only

**Why END keyword?**
- Clearly marks block boundaries
- Enables deep nesting without ambiguity
- Makes parsing straightforward

**Why indentation matters (but isn't required)?**
- Visual hierarchy shows decision structure
- Easier to understand nested logic
- Standard practice in modern languages

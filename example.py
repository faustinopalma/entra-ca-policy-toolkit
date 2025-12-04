import json
import uuid
import re

class PolicyCompiler:
    def __init__(self):
        self.paths = []
        # Mapping Pseudocode variables to MS Graph JSON locations
        self.mappings = {
            "DevicePlatform": "platforms",
            "DeviceTrust": "device_trust", # Special handling
            "App": "client_apps", # Simplified for this demo
            "Group": "users",
            "UserRisk": "user_risk",
            "SignInRisk": "sign_in_risk"
        }

    def parse(self, text):
        """
        Parses indentation-based IF/ELSE logic into flat scenarios.
        """
        lines = [l for l in text.split('\n') if l.strip() and not l.strip().startswith('#')]
        self._build_tree(lines, 0, [])

    def _build_tree(self, lines, current_indent, current_conditions):
        """
        Recursive function to traverse the indented code.
        """
        while lines:
            line = lines[0]
            indent = len(line) - len(line.lstrip())

            if indent < current_indent:
                return # Go back up the tree

            clean_line = line.strip()
            
            # Case 1: IF Statement
            if clean_line.startswith("IF"):
                # Extract condition: IF Variable == "Value"
                match = re.search(r'IF\s+(\w+)\s*==\s*"([^"]+)"', clean_line)
                if match:
                    var, val = match.groups()
                    lines.pop(0) # Consume line
                    
                    # Recurse for the TRUE path
                    new_conditions = current_conditions + [{'var': var, 'val': val, 'op': 'eq'}]
                    self._build_tree(lines, indent + 4, new_conditions)
                    
                    # Check for immediate ELSE
                    if lines and lines[0].strip().startswith("ELSE"):
                        lines.pop(0) # Consume ELSE
                        # Recurse for the FALSE path (Implicit negation logic could be added here)
                        # For this prototype, ELSE implies the remaining scope not covered by IF
                        # We represent ELSE as a separate path logically, usually requiring different optimization
                        self._build_tree(lines, indent + 4, current_conditions + [{'var': var, 'val': val, 'op': 'neq'}])
                else:
                    lines.pop(0) # Skip malformed line

            # Case 2: Action Statements (REQUIRE, BLOCK, SESSION)
            elif clean_line.startswith(("REQUIRE", "BLOCK", "SESSION")):
                action_type = clean_line.split(' ')[0]
                action_value = clean_line.split(' ', 1)[1] if ' ' in clean_line else None
                
                # Consume this line and any subsequent action lines at same level
                actions = {'grant': [], 'session': [], 'block': False}
                
                while lines and (len(lines[0]) - len(lines[0].lstrip()) == indent):
                    l = lines.pop(0).strip()
                    act = l.split(' ')[0]
                    val = l.split(' ', 1)[1] if ' ' in l else None
                    
                    if act == "REQUIRE": actions['grant'].append(val)
                    if act == "SESSION": actions['session'].append(val)
                    if act == "BLOCK": actions['block'] = True
                
                # Store the complete path
                self.paths.append({
                    'conditions': current_conditions,
                    'outcome': actions
                })
            else:
                lines.pop(0)

    def optimize_and_generate(self):
        """
        Groups paths by their Outcome (Grant/Session controls) to form Policies.
        """
        # 1. Group by Outcome Signature
        clusters = {}
        
        for path in self.paths:
            # Create a signature string for the outcome to use as a dict key
            if path['outcome']['block']:
                sig = "BLOCK"
            else:
                grants = sorted(path['outcome']['grant'])
                sessions = sorted(path['outcome']['session'])
                sig = f"GRANT:{','.join(grants)}|SESSION:{','.join(sessions)}"
            
            if sig not in clusters:
                clusters[sig] = {'meta': path['outcome'], 'scenarios': []}
            clusters[sig]['scenarios'].append(path['conditions'])

        # 2. Convert Clusters to JSON
        policies = []
        for sig, data in clusters.items():
            policy_json = self._map_to_graph_json(sig, data)
            policies.append(policy_json)
            
        return policies

    def _map_to_graph_json(self, signature, cluster_data):
        """
        Maps internal representation to Microsoft Graph JSON format.
        """
        policy = {
            "displayName": f"Generated Policy - {signature[:30]}...",
            "state": "enabled",
            "conditions": {
                "applications": {"includeApplications": ["All"]},
                "users": {"includeUsers": ["All"]},
                "platforms": {"includePlatforms": []},
                "locations": {"includeLocations": ["All"]}
            },
            "grantControls": {},
            "sessionControls": {}
        }

        # 1. Process Conditions (The "Optimizer" logic)
        # This is a simplified merge: We collect all 'positive' matches.
        # In a production compiler, you would need complex logic for exclusions.
        
        all_platforms = set()
        users_groups = set()
        
        for scenario in cluster_data['scenarios']:
            for cond in scenario:
                if cond['var'] == "DevicePlatform" and cond['op'] == 'eq':
                    all_platforms.add(cond['val'])
                if cond['var'] == "Group" and cond['op'] == 'eq':
                    users_groups.add(cond['val'])
                # Handle Device Trust mapping (e.g. Compliant)
                # In real graph, this is a filter, here we simplify for demo
        
        if all_platforms:
            policy["conditions"]["platforms"]["includePlatforms"] = list(all_platforms)
        
        if users_groups:
             policy["conditions"]["users"] = {"includeGroups": list(users_groups)}

        # 2. Process Grant Controls
        if cluster_data['meta']['block']:
            policy["grantControls"] = {
                "operator": "OR",
                "builtInControls": ["block"]
            }
        else:
            controls = []
            if cluster_data['meta']['grant']:
                # Map specific keywords to Graph IDs
                mapping = {
                    "MFA": "mfa",
                    "CompliantDevice": "compliantDevice",
                    "AppProtection": "compliantApplication"
                }
                controls = [mapping.get(c, c) for c in cluster_data['meta']['grant']]
            
            if controls:
                policy["grantControls"] = {
                    "operator": "AND", # Default to requiring all listed
                    "builtInControls": controls
                }

        # 3. Process Session Controls
        if cluster_data['meta']['session']:
            policy["sessionControls"] = {}
            for s in cluster_data['meta']['session']:
                if s == "BlockDownloads":
                    policy["sessionControls"]["applicationEnforcedRestrictions"] = {"isEnabled": True}

        return policy

# ==========================================
# EXAMPLE USAGE
# ==========================================

input_code = """
IF DevicePlatform == "android"
    IF DeviceTrust == "Compliant"
        REQUIRE CompliantDevice
    ELSE
        IF Group == "BYOD_Users"
            REQUIRE AppProtection
        ELSE
            BLOCK

IF DevicePlatform == "iOS"
    IF DeviceTrust == "Compliant"
        REQUIRE CompliantDevice
    ELSE
        IF Group == "BYOD_Users"
            REQUIRE AppProtection
        ELSE
            BLOCK

IF DevicePlatform == "windows"
    IF App == "Browser"
        SESSION BlockDownloads
        REQUIRE MFA
    ELSE
        BLOCK
"""

# Run the Compiler
compiler = PolicyCompiler()
compiler.parse(input_code)
optimized_policies = compiler.optimize_and_generate()

# Print Results
print(f"--- LOGIC COMPILATION COMPLETE ---")
print(f"Found {len(compiler.paths)} logic paths.")
print(f"Optimized into {len(optimized_policies)} Conditional Access Policies.")
print("-" * 30)

for i, pol in enumerate(optimized_policies):
    print(f"\n[POLICY {i+1} JSON]")
    print(json.dumps(pol, indent=2))
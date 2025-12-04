"""
Conditional Access Policy Language (CAPL) Parser with Optimization
Converts .capl files to YAML policies with path extraction and clustering optimization
"""

import re
import yaml
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class Condition:
    """Represents a single condition in the policy"""
    type: str  # user, app, platform, device, location, client, signin-risk, user-risk
    operator: str  # is, in, NOT
    value: str
    guid: Optional[str] = None
    is_negated: bool = False


@dataclass
class Action:
    """Represents an action (grant or session control)"""
    type: str  # REQUIRE, BLOCK, ALLOW, SESSION
    value: Optional[str] = None
    is_or: bool = False  # For "REQUIRE X OR Y"


@dataclass
class PolicyBranch:
    """Represents one branch of an IF-ELSE tree"""
    conditions: List[Condition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    state: str = "enabled"  # enabled, disabled, report-only
    nested_if: Optional['IfStatement'] = None


@dataclass
class IfStatement:
    """Represents an IF-ELSE IF-ELSE structure"""
    if_branch: PolicyBranch = field(default_factory=PolicyBranch)
    else_if_branches: List[PolicyBranch] = field(default_factory=list)
    else_branch: Optional[PolicyBranch] = None


@dataclass
class Variable:
    """Represents a VAR declaration"""
    name: str
    display_name: str
    guid: str


@dataclass
class PolicyPath:
    """Represents one complete path through the decision tree"""
    conditions: List[Condition]
    actions: List[Action]
    state: str
    
    def get_action_signature(self) -> str:
        """Create a signature for clustering by actions"""
        # Check if this is a BLOCK action
        if any(a.type == 'BLOCK' for a in self.actions):
            return "BLOCK"
        
        # Group by grant controls and session controls
        grant_controls = []
        session_controls = []
        
        for action in self.actions:
            if action.type == 'REQUIRE':
                if action.value:
                    grant_controls.append(action.value)
            elif action.type == 'SESSION':
                if action.value:
                    session_controls.append(action.value)
        
        # Sort for consistent signatures
        grant_controls.sort()
        session_controls.sort()
        
        grant_sig = ','.join(grant_controls) if grant_controls else 'ALLOW'
        session_sig = ','.join(session_controls) if session_controls else ''
        
        if session_sig:
            return f"GRANT:{grant_sig}|SESSION:{session_sig}"
        return f"GRANT:{grant_sig}"


class CAPLParser:
    """Parser for CAPL syntax"""
    
    def __init__(self):
        self.variables: Dict[str, Variable] = {}
        self.line_number = 0
        self.lines: List[str] = []
        
    def parse_file(self, file_path: Path) -> List[IfStatement]:
        """Parse a .capl file and return list of top-level IF statements"""
        print(f"Parsing {file_path.name}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.lines = content.split('\n')
        self.line_number = 0
        
        statements = []
        
        while self.line_number < len(self.lines):
            line = self._current_line_stripped()
            
            if not line or line.startswith('#'):
                self.line_number += 1
                continue
            
            if line.startswith('VAR '):
                self._parse_variable()
            elif line.startswith('IF '):
                statements.append(self._parse_if_statement())
            else:
                self.line_number += 1
        
        return statements
    
    def _current_line_stripped(self) -> str:
        """Get current line stripped of whitespace"""
        if self.line_number >= len(self.lines):
            return ""
        return self.lines[self.line_number].strip()
    
    def _current_line_indent(self) -> int:
        """Get indentation level of current line"""
        if self.line_number >= len(self.lines):
            return 0
        line = self.lines[self.line_number]
        return len(line) - len(line.lstrip())
    
    def _parse_variable(self):
        """Parse VAR declaration"""
        line = self._current_line_stripped()
        # VAR BreakGlassGroup = "Emergency Access" [guid]
        match = re.match(r'VAR\s+(\w+)\s*=\s*"([^"]+)"\s*\[([^\]]+)\]', line)
        if match:
            var_name, display_name, guid = match.groups()
            self.variables[var_name] = Variable(var_name, display_name, guid)
        self.line_number += 1
    
    def _parse_if_statement(self, base_indent: int = 0) -> IfStatement:
        """Parse IF-ELSE IF-ELSE-END block"""
        stmt = IfStatement()
        
        # Parse IF branch
        stmt.if_branch = self._parse_branch(base_indent)
        
        # Parse ELSE IF branches
        while self.line_number < len(self.lines):
            line = self._current_line_stripped()
            indent = self._current_line_indent()
            
            if indent < base_indent:
                break
            
            if line.startswith('ELSE IF '):
                stmt.else_if_branches.append(self._parse_branch(base_indent))
            elif line == 'ELSE':
                self.line_number += 1  # Consume ELSE
                stmt.else_branch = self._parse_branch_body(base_indent + 4)
            elif line == 'END':
                self.line_number += 1  # Consume END
                break
            else:
                break
        
        return stmt
    
    def _parse_branch(self, base_indent: int) -> PolicyBranch:
        """Parse IF or ELSE IF branch (conditions + body)"""
        branch = PolicyBranch()
        
        # Parse conditions
        line = self._current_line_stripped()
        if line.startswith('IF '):
            # First condition is on same line as IF
            cond_text = line[3:].strip()
            if cond_text:
                branch.conditions.append(self._parse_condition(cond_text))
            self.line_number += 1
        elif line.startswith('ELSE IF '):
            # First condition is on same line as ELSE IF
            cond_text = line[8:].strip()
            if cond_text:
                branch.conditions.append(self._parse_condition(cond_text))
            self.line_number += 1
        
        # Parse additional conditions (indented lines before STATE)
        while self.line_number < len(self.lines):
            line = self._current_line_stripped()
            indent = self._current_line_indent()
            
            if not line or line.startswith('#'):
                self.line_number += 1
                continue
            
            if indent <= base_indent and line in ['ELSE IF ', 'ELSE', 'END']:
                break
            
            if line.startswith('STATE '):
                break
            
            if line.startswith('IF '):
                # Nested IF statement
                break
            
            # This is a condition
            branch.conditions.append(self._parse_condition(line))
            self.line_number += 1
        
        # Parse body (STATE + actions or nested IF)
        branch = self._parse_branch_body(base_indent + 4, branch)
        
        return branch
    
    def _parse_branch_body(self, expected_indent: int, branch: Optional[PolicyBranch] = None) -> PolicyBranch:
        """Parse the body of a branch (STATE + actions or nested IF)"""
        if branch is None:
            branch = PolicyBranch()
        
        # Look for STATE keyword
        line = self._current_line_stripped()
        if line.startswith('STATE '):
            state_value = line[6:].strip()
            branch.state = state_value
            self.line_number += 1
        
        # Parse actions or nested IF
        while self.line_number < len(self.lines):
            line = self._current_line_stripped()
            indent = self._current_line_indent()
            
            if not line or line.startswith('#'):
                self.line_number += 1
                continue
            
            if indent < expected_indent - 4:
                break
            
            if line in ['ELSE IF ', 'ELSE', 'END']:
                break
            
            if line.startswith('IF '):
                # Nested IF statement
                branch.nested_if = self._parse_if_statement(indent)
            elif line.startswith(('REQUIRE ', 'BLOCK', 'ALLOW', 'SESSION ')):
                branch.actions.append(self._parse_action(line))
                self.line_number += 1
            else:
                self.line_number += 1
        
        return branch
    
    def _parse_condition(self, text: str) -> Condition:
        """Parse a condition line"""
        # Replace variables
        for var_name, var_obj in self.variables.items():
            if var_name in text:
                text = text.replace(var_name, f'"{var_obj.display_name}" [{var_obj.guid}]')
        
        # user is All
        # user is Guest
        if m := re.match(r'(user|app|platform|device|location|client)\s+is\s+(\w+)', text, re.IGNORECASE):
            return Condition(type=m.group(1).lower(), operator='is', value=m.group(2))
        
        # user NOT in group "Name" [guid]
        if m := re.match(r'(user)\s+NOT\s+in\s+(group|role)\s+"([^"]+)"\s*\[([^\]]+)\]', text, re.IGNORECASE):
            return Condition(type=m.group(1).lower(), operator='in', value=m.group(3), guid=m.group(4), is_negated=True)
        
        # user in group "Name" [guid]
        # user in role "Name" [guid]
        if m := re.match(r'(user)\s+in\s+(group|role)\s+"([^"]+)"\s*\[([^\]]+)\]', text, re.IGNORECASE):
            cond_type = f"{m.group(1).lower()}-{m.group(2).lower()}"
            return Condition(type=cond_type, operator='in', value=m.group(3), guid=m.group(4))
        
        # app in "Name" [guid]
        if m := re.match(r'(app|location)\s+in\s+"([^"]+)"\s*\[([^\]]+)\]', text, re.IGNORECASE):
            return Condition(type=m.group(1).lower(), operator='in', value=m.group(2), guid=m.group(3))
        
        # location NOT is Trusted
        if m := re.match(r'(location)\s+NOT\s+is\s+(\w+)', text, re.IGNORECASE):
            return Condition(type=m.group(1).lower(), operator='is', value=m.group(2), is_negated=True)
        
        # client NOT is Browser
        if m := re.match(r'(client)\s+NOT\s+is\s+(\w+)', text, re.IGNORECASE):
            return Condition(type=m.group(1).lower(), operator='is', value=m.group(2), is_negated=True)
        
        # platform is iOS OR platform is Android
        if ' OR ' in text:
            parts = [p.strip() for p in text.split(' OR ')]
            # Take first part for now, handle OR in conversion
            first = parts[0]
            if m := re.match(r'(platform|client)\s+is\s+(\w+)', first, re.IGNORECASE):
                values = []
                for part in parts:
                    if m2 := re.match(r'(?:platform|client)\s+is\s+(\w+)', part, re.IGNORECASE):
                        values.append(m2.group(1))
                return Condition(type=m.group(1).lower(), operator='is-or', value='|'.join(values))
        
        # signin-risk is High
        # user-risk is Medium
        if m := re.match(r'(signin-risk|user-risk)\s+is\s+(\w+)', text, re.IGNORECASE):
            return Condition(type=m.group(1).lower(), operator='is', value=m.group(2))
        
        # device is Compliant
        # device is HybridJoined
        if m := re.match(r'(device)\s+is\s+(\w+)', text, re.IGNORECASE):
            return Condition(type=m.group(1).lower(), operator='is', value=m.group(2))
        
        print(f"Warning: Could not parse condition: {text}")
        return Condition(type='unknown', operator='is', value=text)
    
    def _parse_action(self, text: str) -> Action:
        """Parse an action line"""
        # REQUIRE MFA
        # REQUIRE CompliantDevice
        if text.startswith('REQUIRE '):
            action_text = text[8:].strip()
            # Check for OR
            if ' OR ' in action_text:
                parts = action_text.split(' OR ')
                return Action(type='REQUIRE', value='|'.join(parts), is_or=True)
            else:
                return Action(type='REQUIRE', value=action_text)
        
        # BLOCK
        if text == 'BLOCK':
            return Action(type='BLOCK')
        
        # ALLOW
        if text == 'ALLOW':
            return Action(type='ALLOW')
        
        # SESSION signin-frequency 1 hours
        if text.startswith('SESSION '):
            session_text = text[8:].strip()
            return Action(type='SESSION', value=session_text)
        
        return Action(type='UNKNOWN', value=text)


class PolicyOptimizer:
    """Optimizes policies by clustering and merging compatible paths"""
    
    def __init__(self):
        self.policy_counter = 1
    
    def optimize(self, paths: List[PolicyPath]) -> List[Dict[str, Any]]:
        """
        Optimize paths using clustering and merging strategy:
        1. Extract all paths from decision tree
        2. Cluster by action signature (what grant/session controls are required)
        3. Merge conditions within each cluster
        4. Generate optimized YAML policies
        """
        print(f"  Optimizing {len(paths)} path(s)...")
        
        # Step 1: Cluster paths by action signature
        clusters = self._cluster_by_action(paths)
        
        print(f"  Clustered into {len(clusters)} group(s) by action")
        
        # Step 2: Optimize each cluster
        optimized_policies = []
        for signature, cluster_paths in clusters.items():
            merged_policy = self._merge_cluster(signature, cluster_paths)
            optimized_policies.append(merged_policy)
        
        return optimized_policies
    
    def _cluster_by_action(self, paths: List[PolicyPath]) -> Dict[str, List[PolicyPath]]:
        """Group paths that have identical actions"""
        clusters = defaultdict(list)
        
        for path in paths:
            signature = path.get_action_signature()
            # Also include state in signature to keep report-only separate
            full_signature = f"{signature}|STATE:{path.state}"
            clusters[full_signature].append(path)
        
        return clusters
    
    def _merge_cluster(self, signature: str, paths: List[PolicyPath]) -> Dict[str, Any]:
        """
        Merge all paths in a cluster into a single optimized policy
        Strategy: Union conditions of the same type
        """
        # Extract state from signature
        state = 'enabled'
        if '|STATE:' in signature:
            parts = signature.split('|STATE:')
            signature = parts[0]
            state = parts[1]
        
        # Collect all conditions by type
        condition_groups = defaultdict(list)
        
        for path in paths:
            for cond in path.conditions:
                condition_groups[cond.type].append(cond)
        
        # Merge conditions - for now, take union of values for each type
        merged_conditions = []
        for cond_type, conds in condition_groups.items():
            merged = self._merge_conditions_of_type(cond_type, conds)
            merged_conditions.extend(merged)
        
        # Get actions from first path (they're all the same in this cluster)
        actions = paths[0].actions if paths else []
        
        # Create policy
        return self._create_policy(merged_conditions, actions, state)
    
    def _merge_conditions_of_type(self, cond_type: str, conditions: List[Condition]) -> List[Condition]:
        """
        Merge conditions of the same type
        Strategy: Take union of values for list-capable types (platform, location, etc.)
        """
        if not conditions:
            return []
        
        # Types that can have multiple values in CA policies
        list_capable_types = {'platform', 'location', 'client', 'app'}
        
        if cond_type in list_capable_types:
            # Collect all unique values
            values = set()
            for cond in conditions:
                if cond.operator == 'is-or':
                    # Already has multiple values
                    values.update(cond.value.split('|'))
                else:
                    values.add(cond.value)
            
            # Return as single condition with OR operator if multiple values
            if len(values) > 1:
                return [Condition(
                    type=cond_type,
                    operator='is-or',
                    value='|'.join(sorted(values))
                )]
            else:
                return [conditions[0]]
        
        # For user groups/roles, collect all unique GUIDs
        if cond_type in {'user-group', 'user-role'}:
            unique_guids = set()
            for cond in conditions:
                if cond.guid:
                    unique_guids.add(cond.guid)
            
            # Return separate conditions for each
            result = []
            for guid in unique_guids:
                # Find original condition to get display name
                orig = next((c for c in conditions if c.guid == guid), conditions[0])
                result.append(Condition(
                    type=cond_type,
                    operator='in',
                    value=orig.value,
                    guid=guid,
                    is_negated=orig.is_negated
                ))
            return result
        
        # For other types, keep first condition
        # (user=All, device conditions, risk levels, etc.)
        return [conditions[0]]
    
    def _create_policy(self, conditions: List[Condition], actions: List[Action], state: str) -> Dict[str, Any]:
        """Create a single policy in YAML format"""
        policy_name = f"Generated-Policy-{self.policy_counter}"
        self.policy_counter += 1
        
        policy = {
            'DisplayName': policy_name,
            'State': state,
            'Conditions': self._build_conditions_dict(conditions),
            'GrantControls': self._build_grant_controls(actions),
            'SessionControls': self._build_session_controls(actions)
        }
        
        # Remove empty sections
        if not policy['SessionControls']:
            del policy['SessionControls']
        if not policy['GrantControls']:
            del policy['GrantControls']
        
        return policy
    
    def _build_conditions_dict(self, conditions: List[Condition]) -> Dict[str, Any]:
        """Build conditions dictionary"""
        cond_dict = {
            'Users': {},
            'Applications': {},
            'Platforms': {},
            'Locations': {},
            'ClientAppTypes': {},
            'DeviceStates': {},
            'SignInRiskLevels': [],
            'UserRiskLevels': []
        }
        
        for cond in conditions:
            if cond.type == 'user':
                if cond.value == 'All':
                    cond_dict['Users']['IncludeUsers'] = ['All']
                elif cond.value == 'Guest':
                    cond_dict['Users']['IncludeGuestOrExternalUserTypes'] = ['internalGuest', 'b2bCollaborationGuest']
            
            elif cond.type == 'user-group':
                if cond.is_negated:
                    if 'ExcludeGroups' not in cond_dict['Users']:
                        cond_dict['Users']['ExcludeGroups'] = []
                    cond_dict['Users']['ExcludeGroups'].append(cond.guid)
                else:
                    if 'IncludeGroups' not in cond_dict['Users']:
                        cond_dict['Users']['IncludeGroups'] = []
                    cond_dict['Users']['IncludeGroups'].append(cond.guid)
            
            elif cond.type == 'user-role':
                if 'IncludeRoles' not in cond_dict['Users']:
                    cond_dict['Users']['IncludeRoles'] = []
                cond_dict['Users']['IncludeRoles'].append(cond.guid)
            
            elif cond.type == 'app':
                if cond.value == 'All':
                    cond_dict['Applications']['IncludeApplications'] = ['All']
                elif cond.value == 'Office365':
                    cond_dict['Applications']['IncludeApplications'] = ['Office365']
                elif cond.guid:
                    if 'IncludeApplications' not in cond_dict['Applications']:
                        cond_dict['Applications']['IncludeApplications'] = []
                    cond_dict['Applications']['IncludeApplications'].append(cond.guid)
            
            elif cond.type == 'platform':
                if cond.operator == 'is-or':
                    platforms = cond.value.split('|')
                    cond_dict['Platforms']['IncludePlatforms'] = platforms
                else:
                    if 'IncludePlatforms' not in cond_dict['Platforms']:
                        cond_dict['Platforms']['IncludePlatforms'] = []
                    cond_dict['Platforms']['IncludePlatforms'].append(cond.value)
            
            elif cond.type == 'device':
                # Device conditions like Compliant, HybridJoined
                # In Graph API, these would be deviceStates filters or grant controls
                # For now, we'll note them but may need special handling
                if cond.value == 'Compliant':
                    # This could be a filter expression in production
                    cond_dict['DeviceStates']['CompliantDevice'] = True
                elif cond.value == 'HybridJoined':
                    cond_dict['DeviceStates']['DomainJoinedDevice'] = True
            
            elif cond.type == 'location':
                if cond.value == 'Trusted':
                    if cond.is_negated:
                        cond_dict['Locations']['ExcludeLocations'] = ['AllTrusted']
                    else:
                        cond_dict['Locations']['IncludeLocations'] = ['AllTrusted']
                elif cond.value == 'All':
                    cond_dict['Locations']['IncludeLocations'] = ['All']
                elif cond.guid:
                    if 'IncludeLocations' not in cond_dict['Locations']:
                        cond_dict['Locations']['IncludeLocations'] = []
                    cond_dict['Locations']['IncludeLocations'].append(cond.guid)
            
            elif cond.type == 'client':
                if cond.operator == 'is-or':
                    clients = cond.value.split('|')
                    cond_dict['ClientAppTypes'] = self._map_client_types(clients)
                else:
                    cond_dict['ClientAppTypes'] = self._map_client_types([cond.value])
            
            elif cond.type == 'signin-risk':
                cond_dict['SignInRiskLevels'].append(cond.value.lower())
            
            elif cond.type == 'user-risk':
                cond_dict['UserRiskLevels'].append(cond.value.lower())
        
        # Clean up empty sections
        for key in list(cond_dict.keys()):
            if not cond_dict[key]:
                del cond_dict[key]
        
        return cond_dict
    
    def _map_client_types(self, client_values: List[str]) -> List[str]:
        """Map client types to Entra values"""
        mapping = {
            'Browser': 'browser',
            'MobileApp': 'mobileAppsAndDesktopClients',
            'DesktopApp': 'mobileAppsAndDesktopClients',
            'ExchangeActiveSync': 'exchangeActiveSync',
            'Other': 'other'
        }
        return list(set(mapping.get(c, c.lower()) for c in client_values))
    
    def _build_grant_controls(self, actions: List[Action]) -> Dict[str, Any]:
        """Build grant controls dictionary"""
        grant_actions = [a for a in actions if a.type == 'REQUIRE']
        block_actions = [a for a in actions if a.type == 'BLOCK']
        allow_actions = [a for a in actions if a.type == 'ALLOW']
        
        if block_actions:
            return {
                'Operator': 'OR',
                'BuiltInControls': ['block']
            }
        
        if not grant_actions and not allow_actions:
            return {}
        
        built_in_controls = []
        for action in grant_actions:
            if action.value is None:
                continue
            if action.is_or:
                # OR logic - multiple controls
                controls = action.value.split('|')
                built_in_controls.extend(self._map_grant_control(c) for c in controls)
            else:
                built_in_controls.append(self._map_grant_control(action.value))
        
        if not built_in_controls:
            return {}
        
        # Remove duplicates while preserving order
        seen = set()
        unique_controls = []
        for ctrl in built_in_controls:
            if ctrl not in seen:
                seen.add(ctrl)
                unique_controls.append(ctrl)
        
        operator = 'OR' if any(a.is_or for a in grant_actions) else 'AND'
        
        return {
            'Operator': operator,
            'BuiltInControls': unique_controls
        }
    
    def _map_grant_control(self, control: str) -> str:
        """Map grant control to Entra value"""
        mapping = {
            'MFA': 'mfa',
            'CompliantDevice': 'compliantDevice',
            'HybridJoined': 'domainJoinedDevice',
            'ApprovedApp': 'approvedApplication',
            'AppProtection': 'compliantApplication',
            'PasswordChange': 'passwordChange'
        }
        return mapping.get(control, control.lower())
    
    def _build_session_controls(self, actions: List[Action]) -> Dict[str, Any]:
        """Build session controls dictionary"""
        session_actions = [a for a in actions if a.type == 'SESSION']
        
        if not session_actions:
            return {}
        
        session_controls = {}
        
        for action in session_actions:
            if not action.value:
                continue
            
            # Parse session control value
            value = action.value.strip()
            
            # signin-frequency 1 hours
            if m := re.match(r'signin-frequency\s+(\d+)\s+(hours?|days?)', value, re.IGNORECASE):
                num = int(m.group(1))
                unit = m.group(2).lower()
                session_controls['SignInFrequency'] = {
                    'Value': num,
                    'Type': 'hours' if 'hour' in unit else 'days',
                    'IsEnabled': True
                }
            
            # persistent-browser always|never
            elif m := re.match(r'persistent-browser\s+(always|never)', value, re.IGNORECASE):
                mode = m.group(1).lower()
                session_controls['PersistentBrowser'] = {
                    'Mode': mode,
                    'IsEnabled': True
                }
            
            # monitor with CloudAppSecurity
            elif 'monitor' in value.lower() and 'cloudappsecurity' in value.lower():
                session_controls['CloudAppSecurity'] = {
                    'CloudAppSecurityType': 'monitorOnly',
                    'IsEnabled': True
                }
            
            # block-downloads
            elif 'block-downloads' in value.lower():
                session_controls['ApplicationEnforcedRestrictions'] = {
                    'IsEnabled': True
                }
        
        return session_controls


class PathExtractor:
    """Extracts all paths from parsed IF statements"""
    
    def extract_paths(self, statements: List[IfStatement]) -> List[PolicyPath]:
        """Extract all unique paths through the IF-ELSE trees"""
        all_paths = []
        
        for stmt in statements:
            paths = self._extract_paths_from_statement(stmt)
            all_paths.extend(paths)
        
        return all_paths
    
    def _extract_paths_from_statement(
        self, 
        stmt: IfStatement, 
        parent_conditions: Optional[List[Condition]] = None
    ) -> List[PolicyPath]:
        """
        Extract all unique paths through an IF-ELSE tree
        Uses depth-first traversal with condition accumulation
        """
        if parent_conditions is None:
            parent_conditions = []
        
        paths = []
        
        # Process IF branch
        if_conditions = parent_conditions + stmt.if_branch.conditions
        
        if stmt.if_branch.nested_if:
            # Nested IF - recurse deeper
            paths.extend(self._extract_paths_from_statement(stmt.if_branch.nested_if, if_conditions))
        else:
            # Leaf node - create path
            path = PolicyPath(
                conditions=if_conditions[:],  # Copy list
                actions=stmt.if_branch.actions[:],
                state=stmt.if_branch.state
            )
            paths.append(path)
        
        # Process ELSE IF branches
        for else_if_branch in stmt.else_if_branches:
            branch_conditions = parent_conditions + else_if_branch.conditions
            
            if else_if_branch.nested_if:
                paths.extend(self._extract_paths_from_statement(else_if_branch.nested_if, branch_conditions))
            else:
                path = PolicyPath(
                    conditions=branch_conditions[:],
                    actions=else_if_branch.actions[:],
                    state=else_if_branch.state
                )
                paths.append(path)
        
        # Process ELSE branch
        if stmt.else_branch:
            else_conditions = parent_conditions + stmt.else_branch.conditions
            
            if stmt.else_branch.nested_if:
                paths.extend(self._extract_paths_from_statement(stmt.else_branch.nested_if, else_conditions))
            else:
                path = PolicyPath(
                    conditions=else_conditions[:],
                    actions=stmt.else_branch.actions[:],
                    state=stmt.else_branch.state
                )
                paths.append(path)
        
        return paths


def main():
    """Main entry point"""
    print("=" * 60)
    print("CAPL Parser - Conditional Access Policy Language Compiler")
    print("With Path Extraction and Clustering Optimization")
    print("=" * 60)
    print()
    
    # Setup paths
    input_folder = Path("PolicyLanguage")
    output_folder = Path("ConditionalAccessPolicies-Generated")
    output_folder.mkdir(exist_ok=True)
    
    if not input_folder.exists():
        print(f"Error: Input folder '{input_folder}' not found!")
        return 1
    
    # Find all .capl files
    capl_files = [f for f in input_folder.glob("*.capl") if not f.name.startswith('_')]
    
    if not capl_files:
        print(f"No .capl files found in '{input_folder}'")
        return 1
    
    print(f"Found {len(capl_files)} .capl file(s):\n")
    for f in capl_files:
        print(f"  - {f.name}")
    print()
    
    # Parse all files
    parser = CAPLParser()
    all_statements = []
    
    for capl_file in capl_files:
        try:
            statements = parser.parse_file(capl_file)
            all_statements.extend(statements)
            print(f"  ✓ Parsed {len(statements)} IF statement(s)")
        except Exception as e:
            print(f"  ✗ Error parsing {capl_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    
    if not all_statements:
        print("No IF statements found to process")
        return 1
    
    # Extract paths
    print("Extracting paths from decision trees...")
    extractor = PathExtractor()
    all_paths = extractor.extract_paths(all_statements)
    print(f"  Extracted {len(all_paths)} path(s)")
    print()
    
    # Optimize and generate policies
    print("Optimizing policies...")
    optimizer = PolicyOptimizer()
    policies = optimizer.optimize(all_paths)
    
    print()
    print(f"Generated {len(policies)} optimized policy/policies")
    print()
    
    # Save policies
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for i, policy in enumerate(policies, 1):
        filename = f"Policy-{i:03d}-{timestamp}.yaml"
        output_path = output_folder / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(policy, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        print(f"  ✓ {filename}")
    
    print()
    print("=" * 60)
    print("DONE! Next steps:")
    print("  1. Review YAML files in 'ConditionalAccessPolicies-Generated'")
    print("  2. Run: .\\3-Convert-YAMLToImportJSON.ps1")
    print("  3. Run: .\\4a-Connect-MgGraphTenant-Write.ps1")
    print("  4. Run: .\\4b-Import-PoliciesFromJSON.ps1")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

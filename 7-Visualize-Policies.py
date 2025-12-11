"""
Interactive Conditional Access Policy Visualizer
Uses "What If" evaluation to show effective controls for all combinations
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
import plotly.graph_objects as go
from collections import defaultdict
import itertools


class PolicyParser:
    """Parse and extract dimensions from policies"""
    
    def __init__(self, policies: List[Dict[str, Any]]):
        self.policies = policies
        self.dimensions = {
            'users': set(),
            'applications': set(),
            'platforms': set(),
            'locations': set(),
            'client_types': set(),
            'user_risks': set(),
            'signin_risks': set()
        }
        self._extract_dimensions()
    
    def _extract_dimensions(self):
        """Extract all unique values mentioned in policies"""
        for policy in self.policies:
            conditions = policy.get('Conditions', {})
            
            # Users
            users = conditions.get('Users', {})
            if 'IncludeUsers' in users:
                for user in users['IncludeUsers']:
                    if user != 'All':
                        self.dimensions['users'].add(user)
            if 'IncludeGroups' in users:
                self.dimensions['users'].update(users['IncludeGroups'])
            
            # Applications
            apps = conditions.get('Applications', {})
            if 'IncludeApplications' in apps:
                for app in apps['IncludeApplications']:
                    if app != 'All':
                        self.dimensions['applications'].add(app)
            
            # Platforms
            platforms = conditions.get('Platforms', {})
            if 'IncludePlatforms' in platforms:
                for plat in platforms['IncludePlatforms']:
                    if plat != 'all':
                        self.dimensions['platforms'].add(plat)
            
            # Locations
            locations = conditions.get('Locations', {})
            if 'IncludeLocations' in locations:
                for loc in locations['IncludeLocations']:
                    if loc not in ['All', 'AllTrusted']:
                        self.dimensions['locations'].add(loc)
            
            # Client types
            if 'ClientAppTypes' in conditions:
                self.dimensions['client_types'].update(conditions['ClientAppTypes'])
            
            # Risks
            if 'UserRiskLevels' in conditions:
                self.dimensions['user_risks'].update(conditions['UserRiskLevels'])
            if 'SignInRiskLevels' in conditions:
                self.dimensions['signin_risks'].update(conditions['SignInRiskLevels'])
        
        # Add generic/default values if sets are empty
        if not self.dimensions['users']:
            self.dimensions['users'].add('GenericUser')
        if not self.dimensions['platforms']:
            self.dimensions['platforms'] = {'windows', 'iOS', 'android', 'macOS'}
        
        # Always include GenericApp to test catch-all scenarios
        self.dimensions['applications'].add('GenericApp')
        if not self.dimensions['applications']:
            self.dimensions['applications'].add('GenericApp')
    
    def get_top_dimensions(self, max_values: int = 5) -> Dict[str, List[str]]:
        """Get most important dimensions for visualization"""
        result = {}
        
        # Always include these
        result['users'] = sorted(list(self.dimensions['users']))[:max_values]
        result['applications'] = sorted(list(self.dimensions['applications']))[:max_values]
        result['platforms'] = sorted(list(self.dimensions['platforms']))[:max_values]
        
        # Locations: Use semantic Trusted/Untrusted for better visualization
        # (Even if no specific location GUIDs found, policies often use AllTrusted/All)
        result['locations'] = ['Trusted', 'Untrusted']
        
        # Device compliance: Critical for BYOD vs managed device policies
        result['device_states'] = ['Compliant', 'Unmanaged']
        
        # Risks: Critical for Identity Protection policies
        result['user_risks'] = ['No Risk', 'High']
        result['signin_risks'] = ['No Risk', 'High']
        
        # Client Types: Browser vs Apps vs Legacy
        result['client_types'] = ['Browser', 'Mobile/Desktop', 'Legacy']
        
        return result


class GridEvaluator:
    """Evaluate policies against all possible scenarios"""
    
    def __init__(self, policies: List[Dict[str, Any]]):
        self.policies = policies
    
    def _matches_condition(self, policy: Dict[str, Any], scenario: Dict[str, str]) -> bool:
        """Check if policy applies to given scenario"""
        conditions = policy.get('Conditions', {})
        
        # CRITICAL: If policy has conditions we're not modeling in our scenarios,
        # we should NOT match it (it's conditional on things we're not showing)
        # This prevents "All users + All apps + SignInRisk=high -> BLOCK" from blocking everything
        
        # Check Client Types
        if 'ClientAppTypes' in conditions:
            policy_types = conditions['ClientAppTypes']
            # If policy has 'all', it matches everything
            if policy_types and 'all' not in policy_types:
                scenario_client = scenario.get('client_type', 'Browser')
                
                # Map scenario to policy values
                match = False
                if scenario_client == 'Browser' and 'browser' in policy_types:
                    match = True
                elif scenario_client == 'Mobile/Desktop' and 'mobileAppsAndDesktopClients' in policy_types:
                    match = True
                elif scenario_client == 'Legacy' and ('exchangeActiveSync' in policy_types or 'otherClients' in policy_types):
                    match = True
                
                if not match:
                    return False

        # Device states: NOW MODELED - check if it matches scenario
        if 'DeviceStates' in conditions:
            device_states = conditions['DeviceStates']
            include_states = device_states.get('IncludeStates', [])
            exclude_states = device_states.get('ExcludeStates', [])
            
            # Map our simplified states to Azure AD DeviceStates
            scenario_state = scenario.get('device_state', 'Unmanaged')
            
            # Azure AD uses: 'Compliant', 'DomainJoined', 'All'
            # We simplify to: 'Compliant' (managed) or 'Unmanaged' (BYOD)
            if scenario_state == 'Compliant':
                # Compliant devices are considered domain-joined/managed
                if exclude_states and ('Compliant' in exclude_states or 'DomainJoined' in exclude_states):
                    return False
                if include_states and 'All' not in include_states:
                    if 'Compliant' not in include_states and 'DomainJoined' not in include_states:
                        return False
            else:  # Unmanaged
                # Unmanaged means NOT compliant, NOT domain-joined
                if include_states and ('Compliant' in include_states or 'DomainJoined' in include_states):
                    # Policy requires compliant/domain-joined, but we're unmanaged
                    return False
        
        # User Risk
        if 'UserRiskLevels' in conditions:
            policy_risks = [r.lower() for r in conditions['UserRiskLevels']]
            scenario_risk = scenario.get('user_risk', 'No Risk').lower()
            
            if scenario_risk == 'no risk':
                # Policy requires risk, but we have none -> No match
                return False
            
            # If scenario is 'high', it matches if 'high' (or 'medium'/'low' if we want to be strict, but usually high covers high)
            # For now, exact match on 'high'
            if scenario_risk not in policy_risks:
                return False

        # Sign-in Risk
        if 'SignInRiskLevels' in conditions:
            policy_risks = [r.lower() for r in conditions['SignInRiskLevels']]
            scenario_risk = scenario.get('signin_risk', 'No Risk').lower()
            
            if scenario_risk == 'no risk':
                return False
            
            if scenario_risk not in policy_risks:
                return False
        
        # Now check the conditions we DO model
        
        # Check Users
        users = conditions.get('Users', {})
        include_users = users.get('IncludeUsers', [])
        exclude_users = users.get('ExcludeUsers', [])
        include_groups = users.get('IncludeGroups', [])
        exclude_groups = users.get('ExcludeGroups', [])
        
        user_match = (
            'All' in include_users or
            scenario['user'] in include_users or
            scenario['user'] in include_groups
        )
        
        if scenario['user'] in exclude_users or scenario['user'] in exclude_groups:
            return False
        
        if not user_match:
            return False
        
        # Check Applications
        apps = conditions.get('Applications', {})
        include_apps = apps.get('IncludeApplications', [])
        exclude_apps = apps.get('ExcludeApplications', [])
        
        app_match = (
            'All' in include_apps or
            scenario['application'] in include_apps
        )
        
        if scenario['application'] in exclude_apps:
            return False
        
        if not app_match:
            return False
        
        # Check Platforms
        if 'platform' in scenario:
            platforms = conditions.get('Platforms', {})
            if platforms:
                include_plats = platforms.get('IncludePlatforms', [])
                if include_plats and 'all' not in include_plats:
                    if scenario['platform'] not in include_plats:
                        return False
        
        # Check Locations
        if 'location' in scenario:
            locations = conditions.get('Locations', {})
            if locations:
                include_locs = locations.get('IncludeLocations', [])
                exclude_locs = locations.get('ExcludeLocations', [])
                
                if scenario['location'] == 'Trusted':
                    if exclude_locs and 'AllTrusted' in exclude_locs:
                        return False
                    if include_locs and 'All' not in include_locs and 'AllTrusted' not in include_locs:
                        return False
                elif scenario['location'] == 'Untrusted':
                    if include_locs and 'AllTrusted' in include_locs:
                        return False
        
        return True
    
    def evaluate_scenario(self, scenario: Dict[str, str]) -> Dict[str, Any]:
        """Evaluate what happens for a specific scenario"""
        matched_policies = []
        is_blocked = False
        controls = []
        session_controls = []
        
        # Check all policies
        for policy in self.policies:
            if self._matches_condition(policy, scenario):
                matched_policies.append(policy['DisplayName'])
                
                # Extract grant controls
                grant_controls = policy.get('GrantControls', {})
                built_in = grant_controls.get('BuiltInControls', [])
                
                if 'block' in built_in:
                    is_blocked = True
                else:
                    controls.extend(built_in)
                
                # Extract session controls
                session = policy.get('SessionControls', {})
                if session:
                    if session.get('ApplicationEnforcedRestrictions', {}).get('IsEnabled'):
                        session_controls.append('App Restrictions')
                    if session.get('CloudAppSecurity', {}).get('IsEnabled'):
                        session_controls.append('Conditional Access App Control')
                    if session.get('SignInFrequency', {}).get('IsEnabled'):
                        freq = session['SignInFrequency']
                        session_controls.append(f"Sign-in Frequency: {freq.get('Value', '?')} {freq.get('Type', 'hours')}")
                    if session.get('PersistentBrowser', {}).get('IsEnabled'):
                        mode = session['PersistentBrowser'].get('Mode', 'never')
                        session_controls.append(f"Persistent Browser: {mode}")
        
        # Determine effective action
        if is_blocked:
            action = 'BLOCK'
            color_value = 0.0
        elif controls or session_controls:
            unique_controls = list(set(controls))
            if 'mfa' in unique_controls and 'compliantDevice' in unique_controls:
                action = 'MFA+Compliant'
            elif 'mfa' in unique_controls:
                action = 'MFA'
            elif 'compliantDevice' in unique_controls:
                action = 'CompliantDevice'
            elif 'domainJoinedDevice' in unique_controls:
                action = 'DomainJoined'
            elif session_controls and not unique_controls:
                action = 'Session Controls'
            else:
                action = 'Multiple Controls'
            color_value = 0.5
        else:
            action = 'ALLOW'
            color_value = 1.0
        
        return {
            'action': action,
            'color_value': color_value,
            'policies': matched_policies,
            'controls': list(set(controls)),
            'session_controls': session_controls
        }


class InteractiveVisualizer:
    """Create interactive Plotly visualization"""
    
    def __init__(self, policies: List[Dict[str, Any]]):
        self.policies = policies
        self.parser = PolicyParser(policies)
        self.evaluator = GridEvaluator(policies)
    
    def create_matrix(self, max_per_dimension: int = 5) -> Tuple[List, List, List, List]:
        """Create data matrix for heatmap"""
        dimensions = self.parser.get_top_dimensions(max_per_dimension)
        
        # Build axes
        x_axis_labels = []
        y_axis_labels = []
        
        # Y-axis: User × Platform × Device State × Risks
        y_combinations = []
        for user in dimensions['users']:
            for platform in dimensions['platforms']:
                for device_state in dimensions['device_states']:
                    # To prevent matrix explosion, we'll only test "High Risk" scenarios 
                    # if there are actually policies that use risk.
                    # But for completeness, let's do a smart combination.
                    
                    # Base scenario (No Risk)
                    label = f"{user}<br>[{platform}] ({device_state})"
                    y_axis_labels.append(label)
                    y_combinations.append({
                        'user': user, 
                        'platform': platform, 
                        'device_state': device_state,
                        'user_risk': 'No Risk',
                        'signin_risk': 'No Risk'
                    })
                    
                    # High User Risk scenario
                    label_ur = f"{user}<br>[{platform}] ({device_state})<br>⚠️ User Risk: High"
                    y_axis_labels.append(label_ur)
                    y_combinations.append({
                        'user': user, 
                        'platform': platform, 
                        'device_state': device_state,
                        'user_risk': 'High',
                        'signin_risk': 'No Risk'
                    })
                    
                    # High Sign-in Risk scenario
                    label_sr = f"{user}<br>[{platform}] ({device_state})<br>⚠️ Sign-in Risk: High"
                    y_axis_labels.append(label_sr)
                    y_combinations.append({
                        'user': user, 
                        'platform': platform, 
                        'device_state': device_state,
                        'user_risk': 'No Risk',
                        'signin_risk': 'High'
                    })
        
        # X-axis: Application × Client Type × Location
        x_combinations = []
        for app in dimensions['applications']:
            for client_type in dimensions['client_types']:
                for location in dimensions['locations']:
                    label = f"{app}<br>[{client_type}]<br>({location})"
                    x_axis_labels.append(label)
                    x_combinations.append({
                        'application': app, 
                        'client_type': client_type,
                        'location': location
                    })
        
        # Build matrix
        data_matrix = []
        text_matrix = []
        
        for y_combo in y_combinations:
            row_values = []
            row_texts = []
            
            for x_combo in x_combinations:
                # Create full scenario
                scenario = {**y_combo, **x_combo}
                
                # Evaluate
                result = self.evaluator.evaluate_scenario(scenario)
                
                # Format hover text with policy names
                hover_text = f"<b>{result['action']}</b><br>"
                hover_text += f"User: {scenario['user']}<br>"
                hover_text += f"App: {scenario['application']}<br>"
                hover_text += f"Client: {scenario['client_type']}<br>"
                hover_text += f"Platform: {scenario['platform']}<br>"
                hover_text += f"Location: {scenario['location']}<br>"
                hover_text += f"Device: {scenario['device_state']}<br>"
                
                if scenario.get('user_risk') == 'High':
                    hover_text += f"User Risk: High<br>"
                if scenario.get('signin_risk') == 'High':
                    hover_text += f"Sign-in Risk: High<br>"
                
                if result['controls']:
                    hover_text += f"<br><b>Grant Controls:</b><br>"
                    for ctrl in result['controls'][:5]:
                        hover_text += f"• {ctrl}<br>"
                
                if result.get('session_controls'):
                    hover_text += f"<br><b>Session Controls:</b><br>"
                    for ctrl in result['session_controls'][:3]:
                        hover_text += f"• {ctrl}<br>"
                
                if result['policies']:
                    hover_text += f"<br><b>Matched Policies:</b><br>"
                    for policy in result['policies'][:5]:  # Show up to 5 policy names
                        hover_text += f"• {policy}<br>"
                    if len(result['policies']) > 5:
                        hover_text += f"• ... and {len(result['policies']) - 5} more"
                else:
                    hover_text += "<br><i>No policies matched (Implicit Allow)</i>"
                
                row_values.append(result['color_value'])
                row_texts.append(hover_text)
            
            data_matrix.append(row_values)
            text_matrix.append(row_texts)
        
        return x_axis_labels, y_axis_labels, data_matrix, text_matrix
    
    def plot(self, output_path: str = 'policy-matrix-interactive.html'):
        """Generate interactive visualization"""
        print("Building interactive matrix...")
        x_labels, y_labels, z_data, hover_text = self.create_matrix()
        
        print(f"  Matrix size: {len(y_labels)} × {len(x_labels)} = {len(y_labels) * len(x_labels)} cells")
        
        # Count color distribution
        from collections import Counter
        flat_z = [val for row in z_data for val in row]
        color_counts = Counter(flat_z)
        print(f"    Red (BLOCK): {color_counts.get(0.0, 0)} cells")
        print(f"    Orange (Controls): {color_counts.get(0.5, 0)} cells")
        print(f"    Green (Allow): {color_counts.get(1.0, 0)} cells")
        
        # Create heatmap with discrete colors
        # Use a discrete colorscale to ensure clear color separation
        colorscale = [
            [0.0, '#D32F2F'],    # Dark Red - Block
            [0.33, '#D32F2F'],   # Stay red until 0.33
            [0.34, '#FFA726'],   # Orange/Amber - Controls  
            [0.66, '#FFA726'],   # Stay amber until 0.66
            [0.67, '#66BB6A'],   # Green - Allow
            [1.0, '#66BB6A']     # Stay green
        ]
        
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=x_labels,
            y=y_labels,
            text=hover_text,
            hoverinfo='text',
            colorscale=colorscale,
            showscale=False,
            zmin=0.0,  # Ensure scale starts at 0
            zmax=1.0,  # Ensure scale ends at 1
            xgap=1,
            ygap=1
        ))
        
        fig.update_layout(
            title={
                'text': "Conditional Access Policy Coverage Map<br><sub>User × Platform × Device × Risk → Application × Client × Location</sub>",
                'x': 0.5,
                'xanchor': 'center'
            },
            xaxis_title="<b>Application × Client × Location</b>",
            yaxis_title="<b>User × Platform × Device × Risk</b>",
            height=max(800, len(y_labels) * 20),  # Adjusted for more rows
            width=max(1200, len(x_labels) * 50),
            xaxis=dict(
                tickangle=-45,
                side='bottom'
            ),
            yaxis=dict(
                autorange='reversed'
            ),
            margin=dict(l=200, r=200, b=150, t=100),  # More space for labels
            font=dict(size=9)  # Slightly smaller for more data
        )
        
        # Add legend with matching colors
        annotations = [
            dict(x=1.05, y=1.0, xref='paper', yref='paper', 
                 text="<b>Legend</b>", showarrow=False, xanchor='left', font=dict(size=14)),
            dict(x=1.05, y=0.95, xref='paper', yref='paper', 
                 text="🟩 Allow (Implicit)", showarrow=False, xanchor='left', font=dict(color="#66BB6A", size=12)),
            dict(x=1.05, y=0.92, xref='paper', yref='paper', 
                 text="🟧 MFA / Controls", showarrow=False, xanchor='left', font=dict(color="#FFA726", size=12)),
            dict(x=1.05, y=0.89, xref='paper', yref='paper', 
                 text="🟥 Blocked", showarrow=False, xanchor='left', font=dict(color="#D32F2F", size=12)),
        ]
        fig.update_layout(annotations=annotations)
        
        # Save
        fig.write_html(output_path)
        print(f"  ✓ Saved interactive visualization to: {output_path}")
        
        # Also try to open in browser
        try:
            import webbrowser
            webbrowser.open(f'file://{Path(output_path).absolute()}')
            print(f"  ✓ Opened in browser")
        except:
            pass
        
        return output_path


def load_policies(folder_path: Path) -> List[Dict[str, Any]]:
    """Load and deduplicate policies from YAML files"""
    policies = []
    seen_policies = set()
    
    yaml_files = list(folder_path.glob("*.yaml"))
    
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                policy = yaml.safe_load(f)
                if policy and 'Conditions' in policy:
                    # Deduplicate
                    policy_key = (
                        policy.get('DisplayName', ''),
                        str(policy.get('Conditions', {})),
                        str(policy.get('GrantControls', {}))
                    )
                    
                    if policy_key not in seen_policies:
                        policies.append(policy)
                        seen_policies.add(policy_key)
        except Exception as e:
            print(f"Warning: Could not load {yaml_file.name}: {e}")
    
    return policies


def main():
    """Main entry point"""
    import sys
    
    print("=" * 70)
    print("Interactive Conditional Access Policy Visualizer")
    print("=" * 70)
    print()
    
    # Check for command-line argument
    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
        if not folder.exists():
            print(f"❌ Error: Folder not found: {folder}")
            print()
            print("Usage: python 8-Interactive-Policy-Matrix.py [folder_path]")
            print()
            print("Available folders:")
            for candidate in ["ConditionalAccessPolicies-Generated", 
                            "ConditionalAccessPolicies-YAML",
                            "ConditionalAccessPolicies",
                            "ConditionalAccessPolicies-ToImport"]:
                if Path(candidate).exists():
                    print(f"  - {candidate}")
            return
    else:
        # Auto-detect folder (prefer Generated, then YAML, then original)
        folder = None
        candidates = [
            "ConditionalAccessPolicies-Generated",
            "ConditionalAccessPolicies-YAML", 
            "ConditionalAccessPolicies"
        ]
        
        for candidate in candidates:
            if Path(candidate).exists():
                folder = Path(candidate)
                print(f"ℹ️  No folder specified, auto-detected: {folder}")
                break
        
        if not folder:
            print("❌ Error: Could not find any policy folder")
            print()
            print("Usage: python 8-Interactive-Policy-Matrix.py [folder_path]")
            print()
            print("Example:")
            print("  python 8-Interactive-Policy-Matrix.py ConditionalAccessPolicies-YAML")
            return
    
    print(f"Loading policies from: {folder}")
    policies = load_policies(folder)
    
    if not policies:
        print(f"❌ Error: No policies found in {folder}")
        return
    
    print(f"  Loaded {len(policies)} unique policies")
    print()
    
    # Create visualizer
    visualizer = InteractiveVisualizer(policies)
    
    # Generate output filename based on folder name
    folder_name = folder.name if folder.name else "policies"
    output_file = f"policy-matrix-{folder_name}.html"
    
    # Generate interactive plot
    visualizer.plot(output_path=output_file)
    
    print()
    print("=" * 70)
    print("DONE!")
    print(f"Open '{output_file}' in your browser to explore the policy matrix")
    print("=" * 70)


if __name__ == "__main__":
    main()

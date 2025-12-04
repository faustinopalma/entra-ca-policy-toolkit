import json
import itertools
import os
import sys
import plotly.graph_objects as go
import pandas as pd

try:
    import yaml
except ImportError:
    print("Error: PyYAML is not installed. Please run 'pip install pyyaml'")
    # We don't exit immediately to allow the script to run with sample data if needed,
    # but YAML loading will fail.

# ==========================================
# 1. INPUT DATA (Fallback Sample)
# ==========================================
# This example uses the 4 Optimized Policies derived from your Flowchart
# It is used if no YAML files are found in the target folder.
sample_json_input = """
[
  {
    "displayName": "1. Baseline Security (Company Devices)",
    "state": "enabled",
    "conditions": {
      "users": { "includeUsers": ["All"] },
      "applications": { "includeApplications": ["All"] },
      "platforms": { "includePlatforms": ["all"] },
      "locations": { "includeLocations": ["All"] },
      "device_trust": ["Compliant"] 
    },
    "grantControls": {
      "operator": "AND",
      "builtInControls": ["compliantDevice"]
    }
  },
  {
    "displayName": "2. Mobile BYOD Access",
    "state": "enabled",
    "conditions": {
      "users": { "includeGroups": ["BYOD_Users"] },
      "applications": { "includeApplications": ["All"] },
      "platforms": { "includePlatforms": ["android", "iOS"] },
      "device_trust": ["Unmanaged"]
    },
    "grantControls": {
      "operator": "AND",
      "builtInControls": ["compliantApplication"]
    }
  },
  {
    "displayName": "3. Workstation Personal Browser",
    "state": "enabled",
    "conditions": {
      "users": { "includeUsers": ["All"] },
      "applications": { "includeApplications": ["All"] },
      "clientAppTypes": ["browser"],
      "platforms": { "includePlatforms": ["windows", "macOS"] },
      "device_trust": ["Unmanaged"]
    },
    "grantControls": {
      "operator": "AND",
      "builtInControls": ["mfa"]
    },
    "sessionControls": {
      "applicationEnforcedRestrictions": { "isEnabled": true }
    }
  },
  {
    "displayName": "4. Catch-All Block",
    "state": "enabled",
    "conditions": {
      "users": { "includeUsers": ["All"], "excludeGroups": ["BYOD_Users"] },
      "applications": { "includeApplications": ["All"] },
      "platforms": { "includePlatforms": ["all"] },
      "device_trust": ["Unmanaged"]
    },
    "grantControls": {
      "operator": "OR",
      "builtInControls": ["block"]
    }
  }
]
"""

class PolicyVisualizer:
    def __init__(self, policies_data):
        # Handle input: can be a JSON string (from sample) or a Python list (from YAML files)
        if isinstance(policies_data, str):
            self.policies = json.loads(policies_data)
        elif isinstance(policies_data, list):
            self.policies = policies_data
        else:
            raise ValueError("Invalid input format. Expected JSON string or List of policies.")

        self.dimensions = {
            "users": set(["Generic User"]),
            "apps": set(["Generic App"]),
            "platforms": set(["windows", "macOS", "android", "iOS"]),
            "locations": set(["Any Location"]),
            "trust": set(["Unmanaged", "Compliant"]) # Simplified device state
        }
        self._extract_dimensions()

    def _extract_dimensions(self):
        """Scans policies to find specific IDs used in conditions."""
        for p in self.policies:
            conds = p.get('conditions', {})
            
            # Users/Groups
            users = conds.get('users', {})
            if 'includeGroups' in users:
                self.dimensions['users'].update(users['includeGroups'])
            
            # Apps
            apps = conds.get('applications', {})
            if 'includeApplications' in apps:
                # Filter out "All" keyword from being a specific axis label
                specifics = [a for a in apps['includeApplications'] if a != 'All']
                self.dimensions['apps'].update(specifics)
            
            # Locations
            locs = conds.get('locations', {})
            if 'includeLocations' in locs:
                specifics = [l for l in locs['includeLocations'] if l != 'All']
                self.dimensions['locations'].update(specifics)

    def _check_match(self, policy, user, app, plat, loc, trust):
        """Determines if a policy applies to a specific scenario."""
        conds = policy.get('conditions', {})
        
        # 1. Platform Check
        p_list = conds.get('platforms', {}).get('includePlatforms', [])
        if 'all' not in p_list and plat not in p_list:
            return False

        # 2. User Check
        u_inc = conds.get('users', {}).get('includeUsers', [])
        g_inc = conds.get('users', {}).get('includeGroups', [])
        g_exc = conds.get('users', {}).get('excludeGroups', [])
        
        # Simplified Inclusion Logic
        user_match = False
        if 'All' in u_inc: user_match = True
        if user in g_inc: user_match = True
        if user in g_exc: return False # Explicit Exclude wins
        if not user_match: return False

        # 3. App Check
        a_inc = conds.get('applications', {}).get('includeApplications', [])
        if 'All' not in a_inc and app not in a_inc:
            return False

        # 4. Device Trust (Custom logic for this visualization)
        # In real JSON this is a complex filter string. We use a simplified key here.
        req_trust = conds.get('device_trust', [])
        if req_trust and trust not in req_trust:
            return False

        return True

    def evaluate_matrix(self):
        """Generates the heatmap data."""
        
        # Create Hierarchical Axes
        y_axis_labels = [] # User > Platform
        x_axis_labels = [] # App > Location > Trust
        
        # We perform a simplified Cartesian product
        # To make the chart readable, we concatenate logical groups
        
        data_matrix = []
        text_matrix = []
        
        # Sort for consistency
        users = sorted(list(self.dimensions['users']))
        platforms = sorted(list(self.dimensions['platforms']))
        apps = sorted(list(self.dimensions['apps']))
        trusts = sorted(list(self.dimensions['trust']))
        
        # Build Y Axis (Who + What Device)
        for user in users:
            for plat in platforms:
                y_label = f"{user} <br> [{plat}]"
                y_axis_labels.append(y_label)
                
                row_values = []
                row_texts = []
                
                # Build X Axis (Which App + Device State)
                # Note: We loop X inside Y loop to build the row, 
                # but we only build x_labels once.
                for app in apps:
                    for trust in trusts:
                        x_label = f"{app} <br> ({trust})"
                        if len(x_axis_labels) < (len(apps) * len(trusts)):
                            x_axis_labels.append(x_label)
                        
                        # EVALUATION CORE
                        applied_controls = []
                        is_blocked = False
                        matched_policies = []
                        
                        for pol in self.policies:
                            if self._check_match(pol, user, app, plat, "Any", trust):
                                matched_policies.append(pol['displayName'])
                                grants = pol.get('grantControls', {}).get('builtInControls', [])
                                sessions = pol.get('sessionControls', {})
                                
                                if 'block' in grants:
                                    is_blocked = True
                                else:
                                    applied_controls.extend(grants)
                                    if sessions:
                                        applied_controls.append("Session Controls")

                        # Determine Cell Color & Text
                        if is_blocked:
                            val = 0 # Red
                            txt = f"BLOCKED<br>By: {matched_policies}"
                        elif applied_controls:
                            val = 0.5 # Orange
                            unique_ctrls = list(set(applied_controls))
                            txt = f"GRANTED ({', '.join(unique_ctrls)})<br>By: {matched_policies}"
                        else:
                            # Gray (No Policy = Default Allow in Azure AD usually, 
                            # but purely visually we differentiate "Explicit" vs "Implicit")
                            val = 1 # Green (Implicit Allow)
                            txt = "Implicit Allow (No Policy Matched)"

                        row_values.append(val)
                        row_texts.append(txt)
                
                data_matrix.append(row_values)
                text_matrix.append(row_texts)

        return x_axis_labels, y_axis_labels, data_matrix, text_matrix

    def plot(self):
        x, y, z, text = self.evaluate_matrix()
        
        # Define Colorscale
        # 0 = Block (Red), 0.5 = Controls (Orange), 1 = Allow (Green)
        colors = [
            [0.0, '#EF5350'],   # Red
            [0.5, '#FFCA28'],   # Amber
            [1.0, '#66BB6A']    # Green
        ]

        fig = go.Figure(data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=text,
            hoverinfo='text', # Show our custom text on hover
            colorscale=colors,
            showscale=False,
            xgap=1, # Grid lines
            ygap=1
        ))

        fig.update_layout(
            title="Conditional Access Policy Coverage Map",
            xaxis_title="Target Application & Device State",
            yaxis_title="User Identity & Device Platform",
            height=800,
            width=1000,
            xaxis=dict(tickangle=-45),
            margin=dict(l=150, b=150)
        )
        
        # Add a custom legend (Annotations)
        fig.add_annotation(x=1.05, y=1, xref='paper', yref='paper', text="<b>Legend</b>", showarrow=False)
        fig.add_annotation(x=1.05, y=0.95, xref='paper', yref='paper', text="🟩 Allow (Implicit)", font=dict(color="green"), showarrow=False)
        fig.add_annotation(x=1.05, y=0.92, xref='paper', yref='paper', text="🟨 Grant + Controls", font=dict(color="orange"), showarrow=False)
        fig.add_annotation(x=1.05, y=0.89, xref='paper', yref='paper', text="🟥 Blocked", font=dict(color="red"), showarrow=False)

        fig.show()

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    # CONFIGURATION
    DEFAULT_FOLDER = "policies"
    target_folder = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FOLDER
    
    loaded_policies = []
    
    if os.path.exists(target_folder):
        print(f"Scanning folder: {target_folder}...")
        for filename in os.listdir(target_folder):
            if filename.lower().endswith(('.yaml', '.yml')):
                file_path = os.path.join(target_folder, filename)
                try:
                    with open(file_path, 'r') as f:
                        content = yaml.safe_load(f)
                        if isinstance(content, list):
                            loaded_policies.extend(content)
                        elif isinstance(content, dict):
                            loaded_policies.append(content)
                        print(f"Loaded: {filename}")
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
    else:
        print(f"Folder '{target_folder}' not found.")

    if loaded_policies:
        print(f"Total policies loaded: {len(loaded_policies)}")
        viz = PolicyVisualizer(loaded_policies)
        viz.plot()
    else:
        print("No YAML policies found in folder. Using built-in sample data for demonstration.")
        viz = PolicyVisualizer(sample_json_input)
        viz.plot()
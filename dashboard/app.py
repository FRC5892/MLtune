"""
MLTUNE
Copyright (C) 2025 Ruthie-FRC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

------------------------------------------------------

Comprehensive Browser-Based Dashboard for Bayesian Optimization Tuner.

This dashboard provides complete control over the tuning system with:
- GitHub-inspired professional design (pure white with orange accents)
- Two-level mode system (Normal/Advanced)
- Dark/Light theme toggle
- Collapsible sidebar navigation
- Real-time monitoring
- Advanced ML algorithm selection
- Danger Zone for sensitive operations
- Productivity features (Notes & To-Do)
- Optional visualizations
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL, MATCH, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime
import json
import sys
import os
import time
from pathlib import Path

# Add parent directory to path for tuner imports
sys.path.insert(0, str(Path(__file__).parent.parent / "MLtune" / "tuner"))

try:
    from config import TunerConfig
    from nt_interface import NetworkTablesInterface, ShotData
    from tuner import BayesianTunerCoordinator
    TUNER_AVAILABLE = True
except ImportError:
    TUNER_AVAILABLE = False
    print("Warning: Tuner modules not available. Dashboard will run in demo mode.")

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, '/assets/css/custom.css'],
    suppress_callback_exceptions=True,
    title="MLtune Dashboard"
)

# Load external JavaScript via script tags in index.html
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Global tuner coordinator instance (only if tuner is available)
tuner_coordinator = None
if TUNER_AVAILABLE:
    try:
        tuner_coordinator = BayesianTunerCoordinator()
        print("✓ Tuner coordinator initialized")
    except Exception as e:
        print(f"Warning: Could not initialize tuner coordinator: {e}")
        TUNER_AVAILABLE = False

# Global state management
app_state = {
    'mode': 'normal',  # 'normal' or 'advanced'
    'tuner_enabled': False,
    'current_coefficient': 'kDragCoefficient',
    'coefficient_values': {},
    'selected_algorithm': 'gp',
    'shot_count': 0,
    'total_hits': 0,
    'success_rate': 0.0,
    'connection_status': 'disconnected'
}

# Coefficient defaults and configuration (module-level constants for reusability)
COEFFICIENT_DEFAULTS = {
    'kDragCoefficient': 0.003,
    'kGravity': 9.81,
    'kShotHeight': 1.0,
    'kTargetHeight': 2.5,
    'kShooterAngle': 45,
    'kShooterRPM': 3000,
    'kExitVelocity': 15
}

COEFFICIENT_CONFIG = {
    'kDragCoefficient': {'step': 0.0001, 'min': 0.001, 'max': 0.01},
    'kGravity': {'step': 0.01, 'min': 9.0, 'max': 10.0},
    'kShotHeight': {'step': 0.01, 'min': 0.0, 'max': 3.0},
    'kTargetHeight': {'step': 0.01, 'min': 0.0, 'max': 5.0},
    'kShooterAngle': {'step': 1, 'min': 0, 'max': 90},
    'kShooterRPM': {'step': 50, 'min': 0, 'max': 6000},
    'kExitVelocity': {'step': 0.1, 'min': 0, 'max': 30}
}

# Ordered list of coefficient names for consistent iteration
COEFFICIENT_NAMES = list(COEFFICIENT_DEFAULTS.keys())


def clamp_coefficient_value(value, coeff_name):
    """
    Clamp a coefficient value to its configured min/max bounds.
    
    Args:
        value: The value to clamp
        coeff_name: The name of the coefficient (e.g., 'kDragCoefficient')
        
    Returns:
        The clamped value within valid bounds
    """
    config = COEFFICIENT_CONFIG.get(coeff_name, {'min': 0, 'max': 100})
    return max(config['min'], min(value, config['max']))


def create_top_nav():
    """Create the top navigation bar."""
    return html.Div(
        className="top-nav",
        children=[
            html.Div([
                html.Div("MLtune Dashboard", className="top-nav-title")
            ]),
            html.Div(
                style={'marginLeft': 'auto', 'display': 'flex', 'gap': '16px', 'alignItems': 'center'},
                children=[
                    # Connection status with icon
                    html.Div(id='connection-status', style={'display': 'flex', 'alignItems': 'center', 'gap': '8px'}, children=[
                        html.Span("● ", className="status-disconnected", style={'fontSize': '16px'}),
                        html.Div([
                            html.Div("Disconnected", style={'fontSize': '14px', 'fontWeight': '500'}),
                            html.Div("No robot", style={'fontSize': '11px', 'color': 'var(--text-tertiary)'})
                        ])
                    ]),
                ]
            )
        ]
    )


def create_sidebar():
    """Create the collapsible sidebar navigation."""
    return html.Div(
        id='sidebar',
        className="sidebar",
        children=[
            dbc.Button("☰", id='sidebar-toggle', className="btn-secondary", style={'margin': '8px'}),
            html.Hr(),
            html.Div([
                html.Button("Dashboard", id={'type': 'nav-btn', 'index': 'dashboard'}, className="sidebar-menu-item active"),
                html.Button("Coefficients", id={'type': 'nav-btn', 'index': 'coefficients'}, className="sidebar-menu-item"),
                html.Button("Workflow", id={'type': 'nav-btn', 'index': 'workflow'}, className="sidebar-menu-item"),
                html.Button("Graphs", id={'type': 'nav-btn', 'index': 'graphs'}, className="sidebar-menu-item"),
                html.Button("Settings", id={'type': 'nav-btn', 'index': 'settings'}, className="sidebar-menu-item"),
                html.Button("Robot Status", id={'type': 'nav-btn', 'index': 'robot'}, className="sidebar-menu-item"),
                html.Button("System Logs", id={'type': 'nav-btn', 'index': 'logs'}, className="sidebar-menu-item"),
                html.Button("Help", id={'type': 'nav-btn', 'index': 'help'}, className="sidebar-menu-item"),
            ])
        ]
    )


# Robot game view removed



def create_dashboard_view():
    """Create the main dashboard view with quick actions."""
    return html.Div([

        # Breadcrumb navigation
        html.Div(className="breadcrumb", children=[
            html.Span("Home", className="breadcrumb-item"),
            html.Span("/", className="breadcrumb-separator"),
            html.Span("Dashboard", className="breadcrumb-item active"),
        ]),
        
        # Main dashboard grid
        html.Div(className='dashboard-grid', children=[
            # Left column - Quick actions and status
            html.Div([
                # Export coefficients
                html.Div(className="card", style={'marginBottom': '12px'}, children=[
                    html.Div("Export Data", className="card-header"),
                    html.Div(style={'display': 'flex', 'flexDirection': 'column', 'gap': '6px'}, children=[
                        dbc.Button("📥 Export Current Coefficients", id='export-current-coeffs-btn', className="btn-primary", style={'width': '100%', 'padding': '8px', 'fontSize': '13px'}),
                        dbc.Button("📊 Export All Logs (CSV)", id='export-all-logs-btn', className="btn-secondary", style={'width': '100%', 'padding': '8px', 'fontSize': '13px'}),
                    ]),
                    html.Div(id='export-status', style={'marginTop': '6px', 'fontSize': '11px', 'color': 'var(--text-secondary)'})
                ]),
                
                # Quick actions card
                html.Div(className="card", style={'marginBottom': '12px'}, children=[
                    html.Div("Quick Actions", className="card-header"),
                    html.Div(style={'display': 'flex', 'flexDirection': 'column', 'gap': '6px'}, children=[
                        dbc.Button("Start Tuner", id='start-tuner-btn', className="btn-primary", style={'width': '100%', 'padding': '8px', 'fontSize': '13px'}),
                        dbc.Button("Stop Tuner", id='stop-tuner-btn', className="btn-danger", style={'width': '100%', 'padding': '8px', 'fontSize': '13px'}),
                        dbc.Button("Run Optimization", id='run-optimization-btn', className="btn-primary", style={'width': '100%', 'padding': '8px', 'fontSize': '13px'}),
                        dbc.Button("Skip Coefficient", id='skip-coefficient-btn', className="btn-secondary", style={'width': '100%', 'padding': '8px', 'fontSize': '13px'}),
                    ])
                ]),
                
                # Current status card
                html.Div(className="card", style={'marginBottom': '12px'}, children=[
                    html.Div("Current Status", className="card-header"),
                    html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '8px'}, children=[
                        html.Div([
                            html.Label("Mode", style={'fontSize': '11px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                            html.P(f"{app_state['mode'].title()}", id='mode-display', style={'fontSize': '14px', 'fontWeight': '600', 'margin': '2px 0'}),
                        ]),
                        html.Div([
                            html.Label("Coefficient", style={'fontSize': '11px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                            html.P(f"{app_state['current_coefficient']}", id='coeff-display', style={'fontSize': '14px', 'fontWeight': '600', 'margin': '2px 0'}),
                        ]),
                        html.Div([
                            html.Label("Shot Count", style={'fontSize': '11px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                            html.P(f"{app_state['shot_count']}", id='shot-display', style={'fontSize': '14px', 'fontWeight': '600', 'margin': '2px 0'}),
                        ]),
                        html.Div([
                            html.Label("Success Rate", style={'fontSize': '11px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                            html.P(f"{app_state['success_rate']:.1%}", id='success-display', style={'fontSize': '14px', 'fontWeight': '600', 'margin': '2px 0', 'color': 'var(--success)'}),
                        ]),
                    ])
                ]),
            ]),
            
            # Right column - Navigation and fine tuning
            html.Div([
                # Coefficient navigation
                html.Div(className="card", style={'marginBottom': '12px'}, children=[
                    html.Div("Coefficient Navigation", className="card-header"),
                    html.Div(style={'display': 'flex', 'gap': '8px'}, children=[
                        dbc.Button("◀ Previous", id='prev-coeff-btn', className="btn-secondary", style={'flex': '1', 'padding': '8px', 'fontSize': '13px'}),
                        dbc.Button("Next ▶", id='next-coeff-btn', className="btn-secondary", style={'flex': '1', 'padding': '8px', 'fontSize': '13px'}),
                    ])
                ]),
                
                # Fine tuning controls
                html.Div(className="card", style={'marginBottom': '12px'}, children=[
                    html.Div("Fine Tuning Controls", className="card-header"),
                    html.Div(style={'display': 'flex', 'flexDirection': 'row', 'gap': '8px', 'justifyContent': 'center'}, children=[
                        dbc.Button("⬆ Up", id='fine-tune-up-btn', className="btn-secondary", style={'flex': '1', 'maxWidth': '100px', 'padding': '6px', 'fontSize': '13px'}),
                        dbc.Button("Reset", id='fine-tune-reset-btn', className="btn-secondary", style={'flex': '1', 'maxWidth': '100px', 'padding': '6px', 'fontSize': '13px'}),
                        dbc.Button("⬇ Down", id='fine-tune-down-btn', className="btn-secondary", style={'flex': '1', 'maxWidth': '100px', 'padding': '6px', 'fontSize': '13px'}),
                    ])
                ]),
                
                # Shot Recording - Prominent HIT/MISS buttons
                html.Div(className="card", style={'marginBottom': '12px'}, children=[
                    html.Div("Record Shot Result", className="card-header"),
                    html.Div(style={'display': 'flex', 'flexDirection': 'column', 'gap': '8px'}, children=[
                        dbc.Button(
                            "✓ HIT", 
                            id='record-hit-btn', 
                            style={
                                'width': '100%', 
                                'padding': '16px', 
                                'fontSize': '20px', 
                                'fontWeight': 'bold',
                                'backgroundColor': '#1a7f37',
                                'borderColor': '#1a7f37',
                                'color': 'white'
                            }
                        ),
                        dbc.Button(
                            "✗ MISS", 
                            id='record-miss-btn',
                            style={
                                'width': '100%', 
                                'padding': '16px', 
                                'fontSize': '20px', 
                                'fontWeight': 'bold',
                                'backgroundColor': '#cf222e',
                                'borderColor': '#cf222e',
                                'color': 'white'
                            }
                        ),
                    ])
                ]),
            ]),
        ]),
    ])


def create_coefficients_view():
    """Create the coefficients management view with all 7 parameters and orange sliders."""
    # All 7 coefficients with their actual ranges and defaults
    coefficients = {
        'kDragCoefficient': {'min': 0.001, 'max': 0.01, 'default': 0.003, 'step': 0.0001},
        'kGravity': {'min': 9.0, 'max': 10.0, 'default': 9.81, 'step': 0.01},
        'kShotHeight': {'min': 0.0, 'max': 3.0, 'default': 1.0, 'step': 0.01},
        'kTargetHeight': {'min': 0.0, 'max': 5.0, 'default': 2.5, 'step': 0.01},
        'kShooterAngle': {'min': 0, 'max': 90, 'default': 45, 'step': 1},
        'kShooterRPM': {'min': 0, 'max': 6000, 'default': 3000, 'step': 50},
        'kExitVelocity': {'min': 0, 'max': 30, 'default': 15, 'step': 0.1}
    }
    
    return html.Div([
        # Header with summary
        html.Div(className="card", children=[
            html.Div("All Coefficients - Real-Time Control", className="card-header"),
            html.P("Adjust all 7 shooting parameters with interactive sliders. Changes sync to robot in real-time."),
            html.Div(style={'display': 'flex', 'gap': '8px', 'flexWrap': 'wrap', 'marginTop': '16px'}, children=[
                dbc.Button("⬆ Increase All 10%", id='increase-all-btn', className="btn-secondary", size="sm"),
                dbc.Button("⬇ Decrease All 10%", id='decrease-all-btn', className="btn-secondary", size="sm"),
                dbc.Button("Reset All to Defaults", id='reset-all-coeff-btn', className="btn-secondary", size="sm"),
                dbc.Button("Copy Current Values", id='copy-coeff-btn', className="btn-secondary", size="sm"),
            ])
        ]),
        
        # Individual coefficient cards with sliders
        html.Div([
            html.Div(id={'type': 'coeff-card', 'index': coeff}, className="card", style={'marginBottom': '12px'}, children=[
                # Header row with coefficient name
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '12px'}, children=[
                    html.Div([
                        html.Span(coeff, style={'fontWeight': 'bold', 'fontSize': '16px'}),
                        html.Span(f" (Current: ", style={'color': 'var(--text-secondary)', 'fontSize': '14px', 'marginLeft': '8px'}),
                        html.Span(f"{params['default']}", id={'type': 'coeff-current-display', 'index': coeff}, style={'color': 'var(--text-secondary)', 'fontSize': '14px'}),
                        html.Span(")", style={'color': 'var(--text-secondary)', 'fontSize': '14px'}),
                    ]),
                    dbc.Button("Jump to", id={'type': 'jump-to-btn', 'index': coeff}, size="sm", className="btn-primary")
                ]),
                
                # Range info
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'fontSize': '12px', 'color': 'var(--text-secondary)', 'marginBottom': '8px'}, children=[
                    html.Span(f"Min: {params['min']}"),
                    html.Span(f"Default: {params['default']}"),
                    html.Span(f"Max: {params['max']}")
                ]),
                
                # Main slider (orange)
                dcc.Slider(
                    id={'type': 'coeff-slider', 'index': coeff},
                    min=params['min'],
                    max=params['max'],
                    value=params['default'],
                    step=params['step'],
                    marks={
                        params['min']: str(params['min']),
                        params['default']: {'label': str(params['default']), 'style': {'color': 'var(--accent-primary)'}},
                        params['max']: str(params['max'])
                    },
                    tooltip={'placement': 'bottom', 'always_visible': True}
                ),
                
                # Fine adjustment buttons
                html.Div(style={'display': 'flex', 'gap': '4px', 'marginTop': '12px', 'justifyContent': 'center'}, children=[
                    dbc.Button("--", id={'type': 'fine-dec-large', 'index': coeff}, size="sm", className="btn-secondary", title=f"-{params['step']*10}"),
                    dbc.Button("-", id={'type': 'fine-dec', 'index': coeff}, size="sm", className="btn-secondary", title=f"-{params['step']}"),
                    dbc.Button("Reset", id={'type': 'reset-coeff', 'index': coeff}, size="sm", className="btn-secondary"),
                    dbc.Button("+", id={'type': 'fine-inc', 'index': coeff}, size="sm", className="btn-secondary", title=f"+{params['step']}"),
                    dbc.Button("++", id={'type': 'fine-inc-large', 'index': coeff}, size="sm", className="btn-secondary", title=f"+{params['step']*10}"),
                ]),
            ]) for coeff, params in coefficients.items()
        ]),
        
        # Coefficient History Table
        html.Div(className="card", style={'marginTop': '16px'}, children=[
            html.Div("Coefficient History", className="card-header"),
            html.P("Track all coefficient changes over time", style={'color': 'var(--text-secondary)', 'fontSize': '14px', 'marginBottom': '12px'}),
            html.Div(id='coefficient-history-table', children=[
                html.Table(className="table-github", children=[
                    html.Thead([
                        html.Tr([
                            html.Th("Timestamp"),
                            html.Th("Coefficient"),
                            html.Th("Old Value"),
                            html.Th("New Value"),
                            html.Th("Reason"),
                        ])
                    ]),
                    html.Tbody([
                        html.Tr([
                            html.Td("--:--:--"),
                            html.Td("--"),
                            html.Td("--"),
                            html.Td("--"),
                            html.Td("No history yet")
                        ])
                    ])
                ])
            ])
        ]),
    ])


def create_graphs_view():
    """Create comprehensive graphs and analytics view with ALL visualizations."""
    return html.Div([
        # Graph controls
        html.Div(className="card", children=[
            html.Div("Graph Visibility & Controls", className="card-header"),
            html.P("Toggle individual graphs on/off to customize your view", style={'color': 'var(--text-secondary)'}),
            dbc.Checklist(
                id='graph-toggles',
                options=[
                    {'label': 'Shot Success Rate Over Time', 'value': 'success_rate'},
                    {'label': 'Coefficient Value History', 'value': 'coefficient_history'},
                    {'label': 'Optimization Progress by Coefficient', 'value': 'optimization_progress'},
                    {'label': 'Shot Distribution Analysis', 'value': 'shot_distribution'},
                    {'label': 'Algorithm Performance Comparison (Advanced)', 'value': 'algorithm_comparison'},
                    {'label': '📉 Convergence Plot (Advanced)', 'value': 'convergence'},
                    {'label': 'Heat Map - Distance vs Angle', 'value': 'heatmap'},
                    {'label': 'Shot Velocity Distribution', 'value': 'velocity_dist'},
                ],
                value=['success_rate', 'coefficient_history', 'optimization_progress'],
                switch=True
            ),
            html.Small("Success Rate Over Time: Track how success rate improves with each shot (hover to see coefficients)", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '4px'}),
            html.Small("Coefficient History: See how coefficient values change throughout optimization", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '2px'}),
            html.Small("Optimization Progress: Bar chart showing tuning progress for each coefficient", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '2px'}),
            html.Small("Shot Distribution: Analyze the spread and accuracy of your shots", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '2px'}),
            html.Small("Algorithm Comparison: Compare performance of different ML algorithms (Advanced mode)", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '2px'}),
            html.Small("Convergence Plot: Visualize how quickly the optimization converges (Advanced mode)", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '2px'}),
            html.Small("Heat Map: 2D visualization of shot success by distance and angle", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '2px'}),
            html.Small("Velocity Distribution: Histogram showing shot velocity patterns", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '2px'}),
            html.Hr(),
            html.Div(style={'display': 'flex', 'gap': '8px', 'flexWrap': 'wrap'}, children=[
                dbc.Button("📥 Export All Graphs", id='export-graphs-btn', className="btn-secondary", size="sm"),
                dbc.Button("Refresh Data", id='refresh-graphs-btn', className="btn-secondary", size="sm"),
                dbc.Button("Pause Auto-Update", id='pause-graphs-btn', className="btn-secondary", size="sm"),
            ])
        ]),
        
        # Graph container with all visualizations
        html.Div(id='graphs-container', children=[
            # Shot Success Rate Over Time
            html.Div(id='graph-success-rate', className="card", children=[
                html.Div("Shot Success Rate Over Time", className="card-header"),
                html.Small("Hover over data points to see coefficient values used", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginBottom': '8px'}),
                dcc.Graph(
                    id='chart-success-rate',
                    figure=go.Figure(
                        data=[],
                        layout=go.Layout(
                            xaxis={'title': 'Shot Number'},
                            yaxis={'title': 'Success Rate', 'range': [0, 1]},
                            template='plotly',
                            hovermode='closest',
                            annotations=[{
                                'text': 'No shot data available - Start tuning to see results',
                                'xref': 'paper',
                                'yref': 'paper',
                                'x': 0.5,
                                'y': 0.5,
                                'showarrow': False,
                                'font': {'size': 14}
                            }]
                        )
                    )
                )
            ]),
            
            # Coefficient Value History
            html.Div(id='graph-coefficient-history', className="card", children=[
                html.Div("Coefficient Value History", className="card-header"),
                dcc.Graph(
                    id='chart-coeff-history',
                    figure=go.Figure(
                        data=[],
                        layout=go.Layout(
                            xaxis={'title': 'Iteration'},
                            yaxis={'title': 'Coefficient Value'},
                            template='plotly',
                            hovermode='x unified',
                            legend={'orientation': 'h', 'y': -0.2},
                            annotations=[{
                                'text': 'No coefficient history - Start tuning to track changes',
                                'xref': 'paper',
                                'yref': 'paper',
                                'x': 0.5,
                                'y': 0.5,
                                'showarrow': False,
                                'font': {'size': 14}
                            }]
                        )
                    )
                )
            ]),
            
            # Optimization Progress
            html.Div(id='graph-optimization-progress', className="card", children=[
                html.Div("Optimization Progress by Coefficient", className="card-header"),
                dcc.Graph(
                    id='chart-optimization-progress',
                    figure=go.Figure(
                        data=[],
                        layout=go.Layout(
                            xaxis={'title': 'Coefficient'},
                            yaxis={'title': 'Optimization Progress (%)', 'range': [0, 100]},
                            template='plotly',
                            annotations=[{
                                'text': 'No optimization data - Run tuning to see progress',
                                'xref': 'paper',
                                'yref': 'paper',
                                'x': 0.5,
                                'y': 0.5,
                                'showarrow': False,
                                'font': {'size': 14}
                            }]
                        )
                    )
                )
            ]),
            
            # Shot Distribution
            html.Div(id='graph-shot-distribution', className="card", style={'display': 'none'}, children=[
                html.Div("Shot Distribution Analysis", className="card-header"),
                dcc.Graph(
                    id='chart-shot-distribution',
                    figure=go.Figure(
                        data=[],
                        layout=go.Layout(
                            xaxis={'title': 'Shot Distance (m)'},
                            yaxis={'title': 'Target Height (m)'},
                            template='plotly',
                            annotations=[{
                                'text': 'No shot data available',
                                'xref': 'paper',
                                'yref': 'paper',
                                'x': 0.5,
                                'y': 0.5,
                                'showarrow': False,
                                'font': {'size': 14}
                            }]
                        )
                    )
                )
            ]),
            
            # Algorithm Performance Comparison (Advanced only)
            html.Div(id='graph-algorithm-comparison', className="card", style={'display': 'none'}, children=[
                html.Div("🧠 Algorithm Performance Comparison", className="card-header"),
                dcc.Graph(
                    id='chart-algorithm-comparison',
                    figure=go.Figure(
                        data=[],
                        layout=go.Layout(
                            xaxis={'title': 'Algorithm'},
                            yaxis={'title': 'Success Rate', 'range': [0, 1]},
                            template='plotly',
                            annotations=[{
                                'text': 'No algorithm comparison data available',
                                'xref': 'paper',
                                'yref': 'paper',
                                'x': 0.5,
                                'y': 0.5,
                                'showarrow': False,
                                'font': {'size': 14}
                            }]
                        )
                    )
                )
            ]),
            
            # Convergence Plot (Advanced only)
            html.Div(id='graph-convergence', className="card", style={'display': 'none'}, children=[
                html.Div("📉 Convergence Plot", className="card-header"),
                dcc.Graph(
                    id='chart-convergence',
                    figure=go.Figure(
                        data=[],
                        layout=go.Layout(
                            xaxis={'title': 'Iteration'},
                            yaxis={'title': 'Objective Function Value'},
                            template='plotly',
                            annotations=[{
                                'text': 'No convergence data available',
                                'xref': 'paper',
                                'yref': 'paper',
                                'x': 0.5,
                                'y': 0.5,
                                'showarrow': False,
                                'font': {'size': 14}
                            }]
                        )
                    )
                )
            ]),
            
            # Heat Map
            html.Div(id='graph-heatmap', className="card", style={'display': 'none'}, children=[
                html.Div("🔥 Heat Map - Distance vs Angle Success Rate", className="card-header"),
                dcc.Graph(
                    id='chart-heatmap',
                    figure=go.Figure(
                        data=[
                            go.Heatmap(
                                z=[[0.2, 0.4, 0.6, 0.8, 0.9],
                                   [0.3, 0.5, 0.7, 0.85, 0.95],
                                   [0.4, 0.6, 0.8, 0.9, 0.85],
                                   [0.5, 0.7, 0.85, 0.95, 0.8],
                                   [0.6, 0.8, 0.9, 0.9, 0.75]],
                                x=['30°', '35°', '40°', '45°', '50°'],
                                y=['1m', '2m', '3m', '4m', '5m'],
                                colorscale='RdYlGn',
                                text=[[0.2, 0.4, 0.6, 0.8, 0.9],
                                      [0.3, 0.5, 0.7, 0.85, 0.95],
                                      [0.4, 0.6, 0.8, 0.9, 0.85],
                                      [0.5, 0.7, 0.85, 0.95, 0.8],
                                      [0.6, 0.8, 0.9, 0.9, 0.75]],
                                texttemplate='%{text:.0%}',
                                textfont={'size': 12}
                            )
                        ],
                        layout=go.Layout(
                            xaxis={'title': 'Shooter Angle'},
                            yaxis={'title': 'Distance'},
                            template='plotly'
                        )
                    )
                )
            ]),
            
            # Velocity Distribution
            html.Div(id='graph-velocity-dist', className="card", style={'display': 'none'}, children=[
                html.Div("Shot Velocity Distribution", className="card-header"),
                dcc.Graph(
                    id='chart-velocity-dist',
                    figure=go.Figure(
                        data=[
                            go.Histogram(
                                x=[14.5, 14.8, 15.0, 15.2, 15.0, 14.9, 15.1, 15.3, 14.7, 15.0,
                                   15.2, 15.1, 14.9, 15.0, 15.1, 14.8, 15.2, 15.0, 14.9, 15.1],
                                nbinsx=20,
                                marker={'color': '#FF8C00'},
                                name='Exit Velocity'
                            )
                        ],
                        layout=go.Layout(
                            xaxis={'title': 'Exit Velocity (m/s)'},
                            yaxis={'title': 'Frequency'},
                            template='plotly',
                            showlegend=False
                        )
                    )
                )
            ]),
        ])
    ])


def create_workflow_view():
    """Create the order & workflow management view."""
    return html.Div([
        # Tuning Order Management
        html.Div(className="card", children=[
            html.Div("Tuning Order & Sequence", className="card-header"),
            html.P("Drag to reorder, click to enable/disable coefficients in the tuning sequence"),
            html.Div(id='tuning-order-list', children=[
                html.Div(className="card", style={'marginBottom': '8px', 'cursor': 'move', 'padding': '12px'}, children=[
                    html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
                        html.Div([
                            html.Span("1. ", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                            html.Span("kDragCoefficient"),
                        ]),
                        html.Div(style={'display': 'flex', 'gap': '8px'}, children=[
                            dbc.Button("⬆", id={'type': 'move-up', 'index': 0}, size="sm", className="btn-secondary"),
                            dbc.Button("⬇", id={'type': 'move-down', 'index': 0}, size="sm", className="btn-secondary"),
                            dbc.Checklist(
                                id={'type': 'enable-coeff', 'index': 0},
                                options=[{'label': 'Enabled', 'value': 'enabled'}],
                                value=['enabled'],
                                switch=True,
                                inline=True
                            ),
                        ])
                    ])
                ]) for i in range(7)
            ])
        ]),
        
        # Workflow Controls
        html.Div(className="card", children=[
            html.Div("Workflow Controls", className="card-header"),
            html.Div(style={'display': 'flex', 'gap': '8px', 'flexWrap': 'wrap'}, children=[
                dbc.Button("Start from Beginning", id='start-workflow-btn', className="btn-primary"),
                dbc.Button("Skip to Next", id='skip-workflow-btn', className="btn-secondary"),
                dbc.Button("Go to Previous", id='prev-workflow-btn', className="btn-secondary"),
                dbc.Button("Reset Progress", id='reset-workflow-btn', className="btn-secondary"),
            ])
        ]),
        
        # Current Workflow State
        html.Div(className="card", children=[
            html.Div("Current Workflow State", className="card-header"),
            html.Div(id='workflow-state', children=[
                html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '16px'}, children=[
                    html.Div([
                        html.Label("Current Coefficient:", style={'fontWeight': 'bold'}),
                        html.P("kDragCoefficient", id='current-coeff-display')
                    ]),
                    html.Div([
                        html.Label("Progress:", style={'fontWeight': 'bold'}),
                        html.P("1 of 7 (14%)", id='workflow-progress-display')
                    ]),
                    html.Div([
                        html.Label("Shots Collected:", style={'fontWeight': 'bold'}),
                        html.P("5 / 10", id='shots-collected-display')
                    ]),
                    html.Div([
                        html.Label("Estimated Time Remaining:", style={'fontWeight': 'bold'}),
                        html.P("~25 minutes", id='time-remaining-display')
                    ]),
                ])
            ])
        ]),
        
        # Backtrack Controls
        html.Div(className="card", children=[
            html.Div("Backtrack to Previous Coefficients", className="card-header"),
            html.P("Re-tune coefficients that may have been affected by later changes", style={'color': 'var(--text-secondary)'}),
            html.Div(style={'display': 'flex', 'gap': '8px', 'flexWrap': 'wrap'}, children=[
                dbc.Button("← kDragCoefficient", id={'type': 'backtrack', 'index': 'kDragCoefficient'}, className="btn-secondary", size="sm"),
                dbc.Button("← kGravity", id={'type': 'backtrack', 'index': 'kGravity'}, className="btn-secondary", size="sm"),
                dbc.Button("← kShotHeight", id={'type': 'backtrack', 'index': 'kShotHeight'}, className="btn-secondary", size="sm"),
                dbc.Button("← kTargetHeight", id={'type': 'backtrack', 'index': 'kTargetHeight'}, className="btn-secondary", size="sm"),
                dbc.Button("← kShooterAngle", id={'type': 'backtrack', 'index': 'kShooterAngle'}, className="btn-secondary", size="sm"),
                dbc.Button("← kShooterRPM", id={'type': 'backtrack', 'index': 'kShooterRPM'}, className="btn-secondary", size="sm"),
                dbc.Button("← kExitVelocity", id={'type': 'backtrack', 'index': 'kExitVelocity'}, className="btn-secondary", size="sm"),
            ])
        ]),
        
        # Coefficient Interactions
        html.Div(className="card", children=[
            html.Div("Detected Coefficient Interactions", className="card-header"),
            html.P("Automatically detected dependencies between coefficients", style={'color': 'var(--text-secondary)'}),
            html.Div(id='interactions-display', children=[
                html.Table(className="table-github", children=[
                    html.Thead([
                        html.Tr([
                            html.Th("Coefficient 1"),
                            html.Th("Coefficient 2"),
                            html.Th("Interaction Strength"),
                            html.Th("Recommendation"),
                        ])
                    ]),
                    html.Tbody([
                        html.Tr([
                            html.Td("kShooterAngle"),
                            html.Td("kExitVelocity"),
                            html.Td(html.Div(style={'width': '100px', 'height': '20px', 'background': 'linear-gradient(to right, #1a7f37 80%, #e8e8e8 80%)'}, title="80% correlation")),
                            html.Td("Tune together")
                        ]),
                        html.Tr([
                            html.Td("kDragCoefficient"),
                            html.Td("kExitVelocity"),
                            html.Td(html.Div(style={'width': '100px', 'height': '20px', 'background': 'linear-gradient(to right, #FF8C00 60%, #e8e8e8 60%)'}, title="60% correlation")),
                            html.Td("Consider re-tuning")
                        ]),
                        html.Tr([
                            html.Td("kShotHeight"),
                            html.Td("kTargetHeight"),
                            html.Td(html.Div(style={'width': '100px', 'height': '20px', 'background': 'linear-gradient(to right, #9a6700 40%, #e8e8e8 40%)'}, title="40% correlation")),
                            html.Td("Monitor")
                        ]),
                    ])
                ])
            ])
        ]),
        
        # Tuning Session Management
        html.Div(className="card", children=[
            html.Div("Tuning Session Management", className="card-header"),
            html.Div([
                html.Label("Session Name:", style={'fontWeight': 'bold'}),
                dbc.Input(type="text", value=f"Tuning session {datetime.now().strftime('%m/%d/%Y at %H:%M')}", id='session-name', placeholder="Enter session name"),
                html.Br(),
                html.Label("Session Notes:", style={'fontWeight': 'bold'}),
                dbc.Textarea(id='session-notes', placeholder="Notes about this tuning session...", style={'height': '100px'}),
                html.Br(),
                html.Div(style={'display': 'flex', 'gap': '8px'}, children=[
                    dbc.Button("💾 Save Session", id='save-session-btn', className="btn-primary"),
                    dbc.Button("📁 Load Session", id='load-session-btn', className="btn-secondary"),
                    dbc.Button("📤 Export Session Data", id='export-session-btn', className="btn-secondary"),
                ])
            ])
        ]),
    ])


def create_settings_view():
    """Create simplified settings view with only essential options."""
    return html.Div([
        # Core Tuner Settings
        html.Div(className="card", children=[
            html.Div("Core Tuner Settings", className="card-header"),
            html.Div([
                dbc.Checklist(
                    id='tuner-toggles',
                    options=[
                        {'label': 'Enable Tuner', 'value': 'enabled'},
                        {'label': 'Auto-optimize', 'value': 'auto_optimize'},
                        {'label': 'Auto-advance', 'value': 'auto_advance'},
                    ],
                    value=['enabled'],
                    switch=True
                ),
                html.Small("Enable Tuner: Activate the Bayesian optimization system", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '4px'}),
                html.Small("Auto-optimize: Automatically run optimization after reaching shot threshold", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '2px'}),
                html.Small("Auto-advance: Automatically move to next coefficient when threshold reached", style={'color': 'var(--text-secondary)', 'display': 'block', 'marginTop': '2px'}),
                html.Hr(),
                html.Label("Shot Threshold", style={'fontWeight': 'bold'}),
                dbc.Input(type="number", value=10, id='auto-optimize-threshold', min=1, max=100),
                html.Small("Number of shots before optimization", style={'color': 'var(--text-secondary)'}),
            ])
        ]),
        
        # NetworkTables Configuration
        html.Div(className="card", children=[
            html.Div("NetworkTables Configuration", className="card-header"),
            html.Div([
                html.Label("Robot IP / Team Number", style={'fontWeight': 'bold'}),
                dbc.Input(type="text", value="10.TE.AM.2", id='robot-ip', placeholder="10.TE.AM.2 or roborio-TEAM-frc.local"),
                html.Br(),
                
                html.Label("Table Path", style={'fontWeight': 'bold'}),
                dbc.Input(type="text", value="/Tuning/BayesianTuner", id='nt-table-path'),
                html.Br(),
                
                dbc.Checklist(
                    id='nt-toggles',
                    options=[
                        {'label': 'Auto-reconnect on disconnect', 'value': 'auto_reconnect'},
                    ],
                    value=[],
                    switch=True
                ),
            ])
        ]),
        
        # Save/Load Configuration
        html.Div(className="card", children=[
            html.Div("Configuration Management", className="card-header"),
            html.Div(style={'display': 'flex', 'gap': '8px', 'flexWrap': 'wrap'}, children=[
                dbc.Button("💾 Save Settings", id='save-settings-btn', className="btn-primary"),
                dbc.Button("📁 Load Settings", id='load-settings-btn', className="btn-secondary"),
                dbc.Button("Reset to Defaults", id='reset-settings-btn', className="btn-secondary"),
            ])
        ])
    ])


def create_robot_status_view():
    """Create the robot status monitoring view."""
    return html.Div([
        # Breadcrumb navigation
        html.Div(className="breadcrumb", children=[
            html.Span("Home", className="breadcrumb-item"),
            html.Span("/", className="breadcrumb-separator"),
            html.Span("Robot Status", className="breadcrumb-item active"),
        ]),
        
        # Robot vital stats
        html.Div(className="card", children=[
            html.Div("Robot Vital Statistics", className="card-header"),
            html.P("Real-time monitoring of robot performance and health", style={'fontSize': '14px', 'color': 'var(--text-secondary)', 'marginBottom': '16px'}),
            html.Div(style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(200px, 1fr))', 'gap': '16px'}, children=[
                html.Div(className="card", style={'padding': '12px'}, children=[
                    html.Label("Battery Voltage", style={'fontSize': '12px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                    html.Div(id='robot-battery', children="12.4V", style={'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--success)'}),
                    html.Small("Healthy", style={'color': 'var(--text-secondary)'})
                ]),
                html.Div(className="card", style={'padding': '12px'}, children=[
                    html.Label("CPU Usage", style={'fontSize': '12px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                    html.Div(id='robot-cpu', children="34%", style={'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--info)'}),
                    html.Small("Normal", style={'color': 'var(--text-secondary)'})
                ]),
                html.Div(className="card", style={'padding': '12px'}, children=[
                    html.Label("Memory Usage", style={'fontSize': '12px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                    html.Div(id='robot-memory', children="128MB", style={'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--info)'}),
                    html.Small("Normal", style={'color': 'var(--text-secondary)'})
                ]),
                html.Div(className="card", style={'padding': '12px'}, children=[
                    html.Label("CAN Utilization", style={'fontSize': '12px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                    html.Div(id='robot-can', children="42%", style={'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--success)'}),
                    html.Small("Healthy", style={'color': 'var(--text-secondary)'})
                ]),
                html.Div(className="card", style={'padding': '12px'}, children=[
                    html.Label("Loop Time", style={'fontSize': '12px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                    html.Div(id='robot-loop-time', children="18ms", style={'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--success)'}),
                    html.Small("On target", style={'color': 'var(--text-secondary)'})
                ]),
                html.Div(className="card", style={'padding': '12px'}, children=[
                    html.Label("Connection", style={'fontSize': '12px', 'color': 'var(--text-secondary)', 'fontWeight': '600', 'textTransform': 'uppercase'}),
                    html.Div(id='robot-connection-time', children="Disconnected", style={'fontSize': '18px', 'fontWeight': '600', 'color': 'var(--danger)'}),
                    html.Small("No robot", style={'color': 'var(--text-secondary)'})
                ]),
            ])
        ]),
        
        # Robot performance graphs
        html.Div(className="card", children=[
            html.Div("Robot Performance Graphs", className="card-header"),
            html.P("Monitor robot-specific metrics over time", style={'fontSize': '14px', 'color': 'var(--text-secondary)', 'marginBottom': '16px'}),
            
            # Battery voltage over time
            dcc.Graph(
                id='robot-battery-graph',
                figure=go.Figure(
                    data=[],
                    layout=go.Layout(
                        title='Battery Voltage (Last 60s)',
                        xaxis={'title': 'Time (seconds ago)', 'autorange': 'reversed'},
                        yaxis={'title': 'Voltage (V)', 'range': [11, 13]},
                        template='plotly',
                        height=300,
                        annotations=[{
                            'text': 'No data available - Robot disconnected',
                            'xref': 'paper',
                            'yref': 'paper',
                            'x': 0.5,
                            'y': 0.5,
                            'showarrow': False,
                            'font': {'size': 14}
                        }]
                    )
                )
            ),
            
            # CPU and Memory usage
            dcc.Graph(
                id='robot-resources-graph',
                figure=go.Figure(
                    data=[],
                    layout=go.Layout(
                        title='CPU & Memory Usage (Last 60s)',
                        xaxis={'title': 'Time (seconds ago)', 'autorange': 'reversed'},
                        yaxis={'title': 'Usage (%)', 'range': [0, 100]},
                        template='plotly',
                        height=300,
                        annotations=[{
                            'text': 'No data available - Robot disconnected',
                            'xref': 'paper',
                            'yref': 'paper',
                            'x': 0.5,
                            'y': 0.5,
                            'showarrow': False,
                            'font': {'size': 14}
                        }]
                    )
                )
            ),
        ]),
        
        # Robot logs
        html.Div(className="card", children=[
            html.Div("Robot Logs", className="card-header"),
            html.P("Real-time logs from robot code", style={'fontSize': '14px', 'color': 'var(--text-secondary)', 'marginBottom': '16px'}),
            html.Div(
                id='robot-logs-display',
                style={
                    'backgroundColor': 'var(--bg-secondary)',
                    'padding': '16px',
                    'borderRadius': '6px',
                    'fontFamily': 'monospace',
                    'fontSize': '12px',
                    'maxHeight': '400px',
                    'overflowY': 'auto',
                    'whiteSpace': 'pre-wrap'
                },
                children=[
                    html.Div(f"[{datetime.now().strftime('%H:%M:%S')}] Robot code initialized"),
                    html.Div(f"[{datetime.now().strftime('%H:%M:%S')}] Subsystems ready"),
                    html.Div(f"[{datetime.now().strftime('%H:%M:%S')}] Awaiting connection..."),
                    html.Div(f"[{datetime.now().strftime('%H:%M:%S')}] NetworkTables not connected", style={'color': 'var(--warning)'}),
                ]
            )
        ]),
        
        # Robot diagnostics
        html.Div(className="card", children=[
            html.Div("🔧 Robot Diagnostics", className="card-header"),
            html.Table(className="table-github", children=[
                html.Thead([
                    html.Tr([
                        html.Th("Component"),
                        html.Th("Status"),
                        html.Th("Temperature"),
                        html.Th("Current Draw"),
                        html.Th("Errors"),
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td("Left Drive Motor"),
                        html.Td([html.Span("●", style={'color': 'var(--success)'}), " OK"]),
                        html.Td("42°C"),
                        html.Td("3.2A"),
                        html.Td("0"),
                    ]),
                    html.Tr([
                        html.Td("Right Drive Motor"),
                        html.Td([html.Span("●", style={'color': 'var(--success)'}), " OK"]),
                        html.Td("41°C"),
                        html.Td("3.1A"),
                        html.Td("0"),
                    ]),
                    html.Tr([
                        html.Td("Shooter Motor"),
                        html.Td([html.Span("●", style={'color': 'var(--warning)'}), " Warm"]),
                        html.Td("58°C"),
                        html.Td("12.4A"),
                        html.Td("0"),
                    ]),
                    html.Tr([
                        html.Td("Intake Motor"),
                        html.Td([html.Span("●", style={'color': 'var(--success)'}), " OK"]),
                        html.Td("38°C"),
                        html.Td("2.1A"),
                        html.Td("0"),
                    ]),
                    html.Tr([
                        html.Td("Pneumatics"),
                        html.Td([html.Span("●", style={'color': 'var(--danger)'}), " No Data"]),
                        html.Td("--"),
                        html.Td("--"),
                        html.Td("1"),
                    ]),
                ])
            ])
        ]),
    ])


def create_notes_view():
    """Create the notes and to-do view."""
    return html.Div([
        html.Div(className="card", children=[
            html.Div("Add Note", className="card-header"),
            dbc.Textarea(id='note-input', placeholder="Enter your observation..."),
            dbc.Button("Add Note", id='add-note-btn', className="btn-primary", style={'marginTop': '8px'})
        ]),
        
        html.Div(className="card", children=[
            html.Div("Add To-Do Item", className="card-header"),
            dbc.Input(id='todo-input', placeholder="Enter task..."),
            dbc.Button("Add To-Do", id='add-todo-btn', className="btn-primary", style={'marginTop': '8px'})
        ]),
        
        html.Div(className="card", children=[
            html.Div("Recent Notes", className="card-header"),
            html.Div(id='notes-list', children=[
                html.P("No notes yet", style={'fontStyle': 'italic', 'color': 'var(--text-secondary)'})
            ])
        ]),
        
        html.Div(className="card", children=[
            html.Div("To-Do List", className="card-header"),
            html.Div(id='todos-list', children=[
                html.P("No to-dos yet", style={'fontStyle': 'italic', 'color': 'var(--text-secondary)'})
            ])
        ])
    ])


def create_danger_zone_view():
    """Create the danger zone view for sensitive operations."""
    return html.Div([
        html.Div(className="card", style={'borderColor': 'var(--danger)'}, children=[
            html.Div("Danger Zone", className="card-header", style={'color': 'var(--danger)'}),
            html.P("These operations can significantly affect your tuning data. Use with caution."),
            
            html.Hr(),
            html.Div("Configuration Operations", style={'fontWeight': 'bold', 'marginBottom': '8px'}),
            dbc.Button("Reconfigure Base Point", id='reconfigure-base-btn', className="btn-secondary", style={'marginBottom': '8px', 'width': '100%'}),
            dbc.Button("Restore Factory Defaults", id='restore-defaults-btn', className="btn-secondary", style={'marginBottom': '8px', 'width': '100%'}),
            dbc.Button("🔐 Lock Configuration", id='lock-config-btn', className="btn-secondary", style={'marginBottom': '8px', 'width': '100%'}),
            
            html.Hr(),
            html.Div("Data Management", style={'fontWeight': 'bold', 'marginBottom': '8px'}),
            dbc.Button("📤 Export Configuration", id='export-config-btn', className="btn-secondary", style={'marginBottom': '8px', 'width': '100%'}),
            dbc.Button("📥 Import Configuration", id='import-config-btn', className="btn-secondary", style={'marginBottom': '8px', 'width': '100%'}),
            
            html.Hr(),
            html.Div("Destructive Operations", style={'fontWeight': 'bold', 'marginBottom': '8px', 'color': 'var(--danger)'}),
            dbc.Button("Reset All Tuning Data", id='reset-data-btn', className="btn-danger", style={'marginBottom': '8px', 'width': '100%'}),
            dbc.Button("🧹 Clear All Pinned Data", id='clear-pinned-btn', className="btn-danger", style={'marginBottom': '8px', 'width': '100%'}),
            
            html.Hr(),
            html.Div("Emergency Controls", style={'fontWeight': 'bold', 'marginBottom': '8px', 'color': 'var(--danger)'}),
            dbc.Button("🔥 Emergency Stop", id='emergency-stop-btn', className="btn-danger", style={'marginBottom': '8px', 'width': '100%'}),
            dbc.Button("Force Retune Coefficient", id='force-retune-btn', className="btn-danger", style={'marginBottom': '8px', 'width': '100%'}),
        ])
    ])


def create_logs_view():
    """Create the system logs view."""
    return html.Div([
        html.Div(className="card", children=[
            html.Div("System Logs", className="card-header"),
            html.Div(
                id='logs-display',
                style={
                    'backgroundColor': 'var(--bg-secondary)',
                    'padding': '16px',
                    'borderRadius': '6px',
                    'fontFamily': 'monospace',
                    'fontSize': '12px',
                    'maxHeight': '500px',
                    'overflowY': 'auto'
                },
                children=[
                    html.Div(f"[{datetime.now().strftime('%H:%M:%S')}] Dashboard initialized"),
                    html.Div(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for robot connection..."),
                ]
            )
        ])
    ])


def create_help_view():
    """Create the help and resources view."""
    return html.Div([
        # Summary
        html.Div(className="card", children=[
            html.Div("About MLtune", className="card-header"),
            html.P("MLtune Dashboard v1.0", style={'fontWeight': 'bold', 'fontSize': '16px'}),
            html.P("Comprehensive browser-based control system for Bayesian Optimization Tuner."),
            html.P("MLtune uses advanced machine learning to automatically tune FRC robot shooting parameters. This dashboard provides complete runtime control over the tuning process with an intuitive interface."),
            html.P("Features: GitHub-inspired design, two-level mode system, real-time monitoring, and complete control over all tuner settings.", style={'fontStyle': 'italic', 'color': 'var(--text-secondary)'})
        ]),
        
        # Documentation
        html.Div(className="card", children=[
            html.Div("📚 Documentation", className="card-header"),
            html.P("Complete guides and documentation for using MLtune:"),
            html.Ul([
                html.Li([
                    html.A("Getting Started Guide", href="https://github.com/Ruthie-FRC/MLtune/blob/main/docs/GETTING_STARTED.md", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                    " - First-time setup and installation"
                ]),
                html.Li([
                    html.A("Usage Guide", href="https://github.com/Ruthie-FRC/MLtune/blob/main/docs/USAGE.md", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                    " - How to use the tuner and dashboard"
                ]),
                html.Li([
                    html.A("Dashboard Guide", href="https://github.com/Ruthie-FRC/MLtune/blob/main/docs/dashboard/README.md", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                    " - Detailed dashboard features and controls"
                ]),
                html.Li([
                    html.A("Robot Integration", href="https://github.com/Ruthie-FRC/MLtune/blob/main/docs/ROBOT_INTEGRATION.md", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                    " - Integrate MLtune with your robot code"
                ]),
                html.Li([
                    html.A("Repository Structure", href="https://github.com/Ruthie-FRC/MLtune/blob/main/docs/REPO_STRUCTURE.md", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                    " - Understanding the codebase"
                ]),
            ])
        ]),
        
        # Get Help
        html.Div(className="card", children=[
            html.Div("💬 Get Help & Support", className="card-header"),
            html.P("Need help or have questions? Here's how to reach us:"),
            html.Div(style={'marginBottom': '16px'}, children=[
                html.Strong("ChiefDelphi (Recommended):"),
                html.Br(),
                html.A("Message @Ruthie-FRC on ChiefDelphi", href="https://www.chiefdelphi.com/u/ruthie-frc/summary", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                html.Br(),
                html.Small("Send a direct message for personalized help and support", style={'color': 'var(--text-secondary)'})
            ]),
            html.Div(style={'marginBottom': '16px'}, children=[
                html.Strong("GitHub Issues:"),
                html.Br(),
                html.A("Report bugs or request features", href="https://github.com/Ruthie-FRC/MLtune/issues", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                html.Br(),
                html.Small("For bug reports, feature requests, or technical issues", style={'color': 'var(--text-secondary)'})
            ]),
            html.Div(style={'marginBottom': '16px'}, children=[
                html.Strong("GitHub Discussions:"),
                html.Br(),
                html.A("Join the community discussion", href="https://github.com/Ruthie-FRC/MLtune/discussions", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                html.Br(),
                html.Small("Ask questions, share tips, and connect with other users", style={'color': 'var(--text-secondary)'})
            ])
        ]),
        
        # Troubleshooting
        html.Div(className="card", children=[
            html.Div("🔧 Troubleshooting", className="card-header"),
            html.P("Common issues and solutions:"),
            html.Div(style={'marginBottom': '12px'}, children=[
                html.Strong("Connection Issues:"),
                html.Ul([
                    html.Li("Verify robot is powered on and connected to network"),
                    html.Li("Check team number in configuration matches your robot"),
                    html.Li("Ensure NetworkTables is enabled on robot"),
                    html.Li("Check firewall settings if using wireless connection")
                ])
            ]),
            html.Div(style={'marginBottom': '12px'}, children=[
                html.Strong("Dashboard Not Loading:"),
                html.Ul([
                    html.Li("Ensure all dependencies are installed: pip install -r dashboard/requirements.txt"),
                    html.Li("Try a different web browser (Chrome or Firefox recommended)"),
                    html.Li("Clear browser cache and reload the page")
                ])
            ]),
            html.Div(style={'marginBottom': '12px'}, children=[
                html.Strong("For more help:"),
                html.Br(),
                html.A("View full troubleshooting guide", href="https://github.com/Ruthie-FRC/MLtune/blob/main/docs/USAGE.md#troubleshooting", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'})
            ])
        ]),
        
        # Contributing
        html.Div(className="card", children=[
            html.Div("🤝 Contributing", className="card-header"),
            html.P("Want to contribute to MLtune? We welcome contributions!"),
            html.Ul([
                html.Li([
                    html.A("Contributing Guide", href="https://github.com/Ruthie-FRC/MLtune/blob/main/docs/CONTRIBUTING.md", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                    " - Learn how to contribute code, documentation, or ideas"
                ]),
                html.Li([
                    html.A("View source on GitHub", href="https://github.com/Ruthie-FRC/MLtune", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                    " - Fork the repository and submit pull requests"
                ]),
                html.Li([
                    html.A("Code of Conduct", href="https://github.com/Ruthie-FRC/MLtune/blob/main/CODE_OF_CONDUCT.md", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                    " - Our community guidelines"
                ])
            ]),
            html.P("Contributions of all kinds are welcome: bug fixes, new features, documentation improvements, and more!", style={'marginTop': '12px', 'fontStyle': 'italic'})
        ]),
        
        # License & Credits
        html.Div(className="card", children=[
            html.Div("⚖️ License & Credits", className="card-header"),
            html.P([
                "MLtune is open source software licensed under the ",
                html.A("GNU General Public License v3.0", href="https://github.com/Ruthie-FRC/MLtune/blob/main/LICENSE", target="_blank", style={'color': 'var(--accent-primary)', 'textDecoration': 'none', 'fontWeight': '500'}),
                "."
            ]),
            html.P("Created and maintained by Ruthie-FRC", style={'fontWeight': '500'}),
            html.P("Copyright © 2025 Ruthie-FRC. All rights reserved.", style={'fontSize': '12px', 'color': 'var(--text-secondary)'})
        ]),
    ])


# Main layout
app.layout = html.Div(
    id='root-container',
    children=[
        dcc.Store(id='app-state', data=app_state),
        dcc.Interval(id='update-interval', interval=1000),  # Update every second
        
        create_top_nav(),
        create_sidebar(),
        
        html.Div(
            id='main-content',
            className="main-content",
            children=[create_dashboard_view()]
        ),
        
        # Bottom status bar with real-time info
        html.Div(className="status-bar", children=[
            html.Div(className="status-bar-item", children=[
                html.Span("Time: "),
                html.Span(id='status-bar-time', children=datetime.now().strftime('%I:%M:%S %p'))
            ]),
            html.Div(className="status-bar-separator"),
            html.Div(className="status-bar-item", children=[
                html.Span("Date: "),
                html.Span(id='status-bar-date', children=datetime.now().strftime('%B %d, %Y'))
            ]),
            html.Div(className="status-bar-separator"),
            html.Div(className="status-bar-item", children=[
                html.Span("Battery: "),
                html.Span(id='status-bar-battery', children="--V")
            ]),
            html.Div(className="status-bar-separator"),
            html.Div(className="status-bar-item", children=[
                html.Span("Connection: "),
                html.Span(id='status-bar-signal', children="Disconnected")
            ]),
            html.Div(className="status-bar-separator"),
            html.Div(className="status-bar-item", children=[
                html.Span("Shots: "),
                html.Span(id='status-bar-shots', children="0")
            ]),
            html.Div(className="status-bar-separator"),
            html.Div(className="status-bar-item", children=[
                html.Span("Success: "),
                html.Span(id='status-bar-success', children="0.0%")
            ]),
        ]),
    ]
)


# Callbacks
@app.callback(
    Output('main-content', 'children'),
    Output('main-content', 'className'),
    Output({'type': 'nav-btn', 'index': ALL}, 'className'),
    [Input({'type': 'nav-btn', 'index': ALL}, 'n_clicks')],
    [State('sidebar', 'className')]
)
def update_view(clicks, sidebar_class):
    """Update the main content view based on sidebar navigation and mark the active sidebar item."""
    ctx = callback_context
    # Default view is 'dashboard'
    default_view = 'dashboard'

    # Sidebar button indices in the same order as create_sidebar
    nav_indices = ['dashboard', 'coefficients', 'workflow', 'graphs', 'settings', 'robot', 'logs', 'help']

    if not ctx.triggered:
        content = create_dashboard_view()
        class_name = 'main-content expanded' if 'collapsed' in (sidebar_class or '') else 'main-content'
        nav_classes = ['sidebar-menu-item active' if idx == default_view else 'sidebar-menu-item' for idx in nav_indices]
        return content, class_name, nav_classes
    
    # Determine which button was clicked
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if triggered_id == '':
        content = create_dashboard_view()
        class_name = 'main-content expanded' if 'collapsed' in (sidebar_class or '') else 'main-content'
        nav_classes = ['sidebar-menu-item active' if idx == default_view else 'sidebar-menu-item' for idx in nav_indices]
        return content, class_name, nav_classes
    
    try:
        button_data = json.loads(triggered_id)
        view = button_data.get('index', default_view)
    except (json.JSONDecodeError, KeyError, TypeError):
        view = default_view
    
    # Map view to content - use lazy evaluation to avoid errors
    try:
        view_functions = {
            'dashboard': create_dashboard_view,
            'coefficients': create_coefficients_view,
            'workflow': create_workflow_view,
            'graphs': create_graphs_view,
            'settings': create_settings_view,
            'robot': create_robot_status_view,
            'notes': create_notes_view,
            'danger': create_danger_zone_view,
            'logs': create_logs_view,
            'help': create_help_view
        }
        
        view_func = view_functions.get(view, create_dashboard_view)
        content = view_func()
    except Exception as e:
        print(f"Error rendering view {view}: {e}")
        content = create_dashboard_view()
    
    class_name = 'main-content expanded' if 'collapsed' in (sidebar_class or '') else 'main-content'
    nav_classes = ['sidebar-menu-item active' if idx == view else 'sidebar-menu-item' for idx in nav_indices]

    return content, class_name, nav_classes


@app.callback(
    Output('sidebar', 'className'),
    [Input('sidebar-toggle', 'n_clicks')],
    [State('sidebar', 'className')]
)
def toggle_sidebar(n_clicks, current_class):
    """Toggle sidebar collapsed state."""
    if n_clicks:
        if current_class and 'collapsed' in current_class:
            return 'sidebar'
        else:
            return 'sidebar collapsed'
    return current_class or 'sidebar'


# ============================================================================
# Button Callback Functions
# ============================================================================

@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input('start-tuner-btn', 'n_clicks'),
     Input('stop-tuner-btn', 'n_clicks'),
     Input('run-optimization-btn', 'n_clicks'),
     Input('skip-coefficient-btn', 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_core_control_buttons(start_clicks, stop_clicks, run_clicks, skip_clicks, state):
    """Handle core control button clicks and actually control the tuner."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'start-tuner-btn':
        state['tuner_enabled'] = True
        print("✅ Tuner Started")
        if tuner_coordinator:
            try:
                tuner_coordinator.start()
                print("✓ Tuner coordinator thread started")
            except Exception as e:
                print(f"Error starting tuner: {e}")
        
    elif button_id == 'stop-tuner-btn':
        state['tuner_enabled'] = False
        print("⛔ Tuner Stopped")
        if tuner_coordinator:
            try:
                tuner_coordinator.stop()
                print("✓ Tuner coordinator thread stopped")
            except Exception as e:
                print(f"Error stopping tuner: {e}")
        
    elif button_id == 'run-optimization-btn':
        print("🔄 Running Optimization...")
        if tuner_coordinator:
            try:
                tuner_coordinator.trigger_optimization()
                print("✓ Optimization triggered")
            except Exception as e:
                print(f"Error triggering optimization: {e}")
        else:
            print("⚠️ Tuner not available - running in demo mode")
        
    elif button_id == 'skip-coefficient-btn':
        print("⏭️ Skipping to Next Coefficient")
        if tuner_coordinator and tuner_coordinator.optimizer:
            try:
                tuner_coordinator.optimizer.advance_to_next_coefficient()
                # Update state to reflect the new coefficient
                current_coeff = tuner_coordinator.optimizer.get_current_coefficient_name()
                if current_coeff:
                    state['current_coefficient'] = current_coeff
                print(f"✓ Advanced to next coefficient: {current_coeff}")
            except Exception as e:
                print(f"Error skipping coefficient: {e}")
        else:
            print("⚠️ Tuner not available - running in demo mode")
    
    return state


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input('prev-coeff-btn', 'n_clicks'),
     Input('next-coeff-btn', 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_coefficient_navigation(prev_clicks, next_clicks, state):
    """Handle coefficient navigation buttons."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    coefficients = ['kDragCoefficient', 'kGravity', 'kShotHeight', 'kTargetHeight', 
                    'kShooterAngle', 'kShooterRPM', 'kExitVelocity']
    current_idx = coefficients.index(state['current_coefficient']) if state['current_coefficient'] in coefficients else 0
    
    if button_id == 'prev-coeff-btn':
        new_idx = (current_idx - 1) % len(coefficients)
        state['current_coefficient'] = coefficients[new_idx]
        print(f"⬅️ Previous Coefficient: {state['current_coefficient']}")
    elif button_id == 'next-coeff-btn':
        new_idx = (current_idx + 1) % len(coefficients)
        state['current_coefficient'] = coefficients[new_idx]
        print(f"➡️ Next Coefficient: {state['current_coefficient']}")
    
    return state


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input('fine-tune-up-btn', 'n_clicks'),
     Input('fine-tune-down-btn', 'n_clicks'),
     Input('fine-tune-reset-btn', 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_fine_tuning_buttons(up_clicks, down_clicks, reset_clicks, state):
    """Handle fine tuning control buttons."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'fine-tune-up-btn':
        print("⬆️ Fine Tune Up")
    elif button_id == 'fine-tune-down-btn':
        print("⬇️ Fine Tune Down")
    elif button_id == 'fine-tune-reset-btn':
        print("🔄 Fine Tune Reset")
    
    return state


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input('record-hit-btn', 'n_clicks'),
     Input('record-miss-btn', 'n_clicks')],
    [State('app-state', 'data'),
     State({'type': 'coeff-slider', 'index': ALL}, 'value')],
    prevent_initial_call=True
)
def handle_shot_recording(hit_clicks, miss_clicks, state, coeff_values):
    """
    Handle HIT/MISS button clicks to record shot results.
    
    Records the shot outcome along with current coefficient values and sends
    to the tuner backend for Bayesian optimization.
    """
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Get current coefficient values
    coefficients = ['kDragCoefficient', 'kGravity', 'kShotHeight', 'kTargetHeight', 
                    'kShooterAngle', 'kShooterRPM', 'kExitVelocity']
    current_coeffs = {}
    for i, coeff_name in enumerate(coefficients):
        if i < len(coeff_values):
            current_coeffs[coeff_name] = coeff_values[i]
    
    # Determine if hit or miss
    hit = (button_id == 'record-hit-btn')
    
    # Update local state
    state['shot_count'] = state.get('shot_count', 0) + 1
    if hit:
        hits = state.get('total_hits', 0) + 1
        state['total_hits'] = hits
    else:
        hits = state.get('total_hits', 0)
    state['success_rate'] = hits / state['shot_count'] if state['shot_count'] > 0 else 0.0
    
    # Log to console
    result_str = "✓ HIT" if hit else "✗ MISS"
    print(f"{result_str} recorded! Shot #{state['shot_count']}")
    print(f"  Coefficients: {current_coeffs}")
    print(f"  Success Rate: {state['success_rate']:.1%}")
    
    # Send to tuner backend if available
    if tuner_coordinator and TUNER_AVAILABLE:
        try:
            # Create a ShotData object
            # In real implementation, robot would provide distance, velocity, etc.
            # For now, we create a minimal shot data with the hit/miss outcome
            shot_data = ShotData(
                hit=hit,
                distance=0.0,  # Would come from robot sensors
                shot_velocity=0.0,  # Would come from robot sensors
                timestamp=time.time()
            )
            
            # Record the shot with the tuner's optimizer
            if tuner_coordinator.optimizer:
                tuner_coordinator.optimizer.record_shot(shot_data, current_coeffs)
                print(f"✓ Shot data sent to tuner backend")
            
            # Log the shot data
            if tuner_coordinator.data_logger:
                tuner_coordinator.data_logger.log_shot(shot_data, current_coeffs)
                print(f"✓ Shot data logged")
                
        except Exception as e:
            print(f"Error recording shot with tuner: {e}")
    else:
        print("⚠️ Tuner not available - shot recorded locally only")
    
    return state


@app.callback(
    Output('export-status', 'children'),
    [Input('export-current-coeffs-btn', 'n_clicks'),
     Input('export-all-logs-btn', 'n_clicks')],
    [State({'type': 'coeff-slider', 'index': ALL}, 'value'),
     State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_export_buttons(export_current_clicks, export_logs_clicks, coeff_values, state):
    """
    Handle export button clicks to generate CSV files.
    
    Creates CSV files with coefficient data that can be easily used in robot code.
    """
    ctx = callback_context
    if not ctx.triggered:
        return ""
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Get current coefficient values
    coefficients = ['kDragCoefficient', 'kGravity', 'kShotHeight', 'kTargetHeight', 
                    'kShooterAngle', 'kShooterRPM', 'kExitVelocity']
    current_coeffs = {}
    for i, coeff_name in enumerate(coefficients):
        if i < len(coeff_values):
            current_coeffs[coeff_name] = coeff_values[i]
    
    try:
        if button_id == 'export-current-coeffs-btn':
            # Export current coefficients to CSV
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"current_coefficients_{timestamp_str}.csv"
            filepath = os.path.join(os.getcwd(), filename)
            
            with open(filepath, 'w') as f:
                f.write("Coefficient,Value\n")
                for coeff_name, value in current_coeffs.items():
                    f.write(f"{coeff_name},{value}\n")
            
            print(f"✓ Exported current coefficients to: {filename}")
            return f"✓ Exported to: {filename}"
            
        elif button_id == 'export-all-logs-btn':
            # Export all coefficient logs with timestamps
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"coefficient_logs_{timestamp_str}.csv"
            filepath = os.path.join(os.getcwd(), filename)
            
            # Try to get logs from tuner if available
            if tuner_coordinator and tuner_coordinator.data_logger:
                try:
                    # Get log directory from tuner
                    log_dir = tuner_coordinator.config.LOG_DIRECTORY if hasattr(tuner_coordinator.config, 'LOG_DIRECTORY') else 'tuner_logs'
                    
                    # Export from existing logs
                    with open(filepath, 'w') as f:
                        f.write("Timestamp,ShotNumber,Hit,")
                        f.write(",".join(coefficients))
                        f.write(",Distance,Velocity,SuccessRate\n")
                        
                        # Get shot history from tuner if available
                        if hasattr(tuner_coordinator.optimizer, 'evaluation_history'):
                            for i, entry in enumerate(tuner_coordinator.optimizer.evaluation_history):
                                timestamp = entry.get('timestamp', datetime.now().isoformat())
                                shot_num = i + 1
                                hit = entry.get('hit', False)
                                
                                f.write(f"{timestamp},{shot_num},{hit},")
                                
                                # Write coefficient values
                                coeffs = entry.get('coefficient_values', current_coeffs)
                                for coeff_name in coefficients:
                                    f.write(f"{coeffs.get(coeff_name, 0.0)},")
                                
                                # Write additional data
                                additional = entry.get('additional_data', {})
                                distance = additional.get('distance', 0.0)
                                velocity = additional.get('velocity', 0.0)
                                success_rate = entry.get('success_rate', 0.0)
                                f.write(f"{distance},{velocity},{success_rate}\n")
                    
                    print(f"✓ Exported all logs to: {filename}")
                    return f"✓ Exported logs to: {filename}"
                    
                except Exception as e:
                    print(f"Error exporting from tuner logs: {e}")
                    # Fallback to basic export
            
            # Fallback: export current state
            with open(filepath, 'w') as f:
                f.write("Timestamp,ShotNumber,Hit,")
                f.write(",".join(coefficients))
                f.write(",Distance,Velocity,SuccessRate\n")
                
                # Write current state as a single entry
                f.write(f"{datetime.now().isoformat()},{state.get('shot_count', 0)},True,")
                for coeff_name in coefficients:
                    f.write(f"{current_coeffs.get(coeff_name, 0.0)},")
                f.write(f"0.0,0.0,{state.get('success_rate', 0.0)}\n")
            
            print(f"✓ Exported current state to: {filename}")
            return f"✓ Exported to: {filename}"
            
    except Exception as e:
        error_msg = f"Error exporting data: {e}"
        print(error_msg)
        return f"✗ {error_msg}"
    
    return ""


@app.callback(
    [Output({'type': 'coeff-slider', 'index': 'kDragCoefficient'}, 'value'),
     Output({'type': 'coeff-slider', 'index': 'kGravity'}, 'value'),
     Output({'type': 'coeff-slider', 'index': 'kShotHeight'}, 'value'),
     Output({'type': 'coeff-slider', 'index': 'kTargetHeight'}, 'value'),
     Output({'type': 'coeff-slider', 'index': 'kShooterAngle'}, 'value'),
     Output({'type': 'coeff-slider', 'index': 'kShooterRPM'}, 'value'),
     Output({'type': 'coeff-slider', 'index': 'kExitVelocity'}, 'value'),
     Output('app-state', 'data', allow_duplicate=True)],
    [Input('increase-all-btn', 'n_clicks'),
     Input('decrease-all-btn', 'n_clicks'),
     Input('reset-all-coeff-btn', 'n_clicks'),
     Input('copy-coeff-btn', 'n_clicks')],
    [State({'type': 'coeff-slider', 'index': 'kDragCoefficient'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kGravity'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kShotHeight'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kTargetHeight'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kShooterAngle'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kShooterRPM'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kExitVelocity'}, 'value'),
     State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_coefficient_bulk_actions(increase_clicks, decrease_clicks, reset_clicks, copy_clicks,
                                    drag_val, grav_val, shot_val, target_val, angle_val, rpm_val, velocity_val,
                                    state):
    """Handle bulk coefficient action buttons."""
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Current values in the same order as COEFFICIENT_NAMES
    current_values = [drag_val, grav_val, shot_val, target_val, angle_val, rpm_val, velocity_val]
    
    if button_id == 'increase-all-btn':
        print("⬆️ Increasing All Coefficients by 10%")
        # Increase all coefficient values by 10%, clamping to max
        new_values = [clamp_coefficient_value(v * 1.1, name) for v, name in zip(current_values, COEFFICIENT_NAMES)]
        return new_values + [state]
        
    elif button_id == 'decrease-all-btn':
        print("⬇️ Decreasing All Coefficients by 10%")
        # Decrease all coefficient values by 10%, clamping to min
        new_values = [clamp_coefficient_value(v * 0.9, name) for v, name in zip(current_values, COEFFICIENT_NAMES)]
        return new_values + [state]
        
    elif button_id == 'reset-all-coeff-btn':
        print("🔄 Resetting All Coefficients to Defaults")
        # Reset all coefficients to defaults using COEFFICIENT_NAMES for consistent ordering
        state['coefficient_values'] = {}
        default_values = [COEFFICIENT_DEFAULTS[name] for name in COEFFICIENT_NAMES]
        return default_values + [state]
        
    elif button_id == 'copy-coeff-btn':
        print("📋 Copied Current Coefficient Values")
        # Log current values (in real implementation, would copy to clipboard)
        for name, value in zip(COEFFICIENT_NAMES, current_values):
            print(f"  {name}: {value}")
        return current_values + [state]
    
    return current_values + [state]


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input({'type': 'coeff-slider', 'index': ALL}, 'value')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_coefficient_sliders(slider_values, state):
    """Handle coefficient slider changes."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    # Extract which slider was changed
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if triggered_id:
        try:
            slider_data = json.loads(triggered_id)
            coeff_name = slider_data.get('index')
            if coeff_name:
                # Get the value from the triggered slider
                new_value = ctx.triggered[0]['value']
                if 'coefficient_values' not in state:
                    state['coefficient_values'] = {}
                state['coefficient_values'][coeff_name] = new_value
                print(f"📊 {coeff_name} = {new_value}")
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    
    return state


@app.callback(
    [Output({'type': 'coeff-slider', 'index': 'kDragCoefficient'}, 'value', allow_duplicate=True),
     Output({'type': 'coeff-slider', 'index': 'kGravity'}, 'value', allow_duplicate=True),
     Output({'type': 'coeff-slider', 'index': 'kShotHeight'}, 'value', allow_duplicate=True),
     Output({'type': 'coeff-slider', 'index': 'kTargetHeight'}, 'value', allow_duplicate=True),
     Output({'type': 'coeff-slider', 'index': 'kShooterAngle'}, 'value', allow_duplicate=True),
     Output({'type': 'coeff-slider', 'index': 'kShooterRPM'}, 'value', allow_duplicate=True),
     Output({'type': 'coeff-slider', 'index': 'kExitVelocity'}, 'value', allow_duplicate=True),
     Output('app-state', 'data', allow_duplicate=True)],
    [Input({'type': 'fine-inc', 'index': ALL}, 'n_clicks'),
     Input({'type': 'fine-dec', 'index': ALL}, 'n_clicks'),
     Input({'type': 'fine-inc-large', 'index': ALL}, 'n_clicks'),
     Input({'type': 'fine-dec-large', 'index': ALL}, 'n_clicks'),
     Input({'type': 'reset-coeff', 'index': ALL}, 'n_clicks')],
    [State({'type': 'coeff-slider', 'index': 'kDragCoefficient'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kGravity'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kShotHeight'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kTargetHeight'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kShooterAngle'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kShooterRPM'}, 'value'),
     State({'type': 'coeff-slider', 'index': 'kExitVelocity'}, 'value'),
     State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_coefficient_fine_adjustments(inc_clicks, dec_clicks, inc_large_clicks, dec_large_clicks, reset_clicks, 
                                        drag_val, grav_val, shot_val, target_val, angle_val, rpm_val, velocity_val, state):
    """Handle fine adjustment buttons for individual coefficients."""
    ctx = callback_context
    if not ctx.triggered:
        return no_update

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Get coefficient name from the triggered button ID
    try:
        button_data = json.loads(triggered_id)
        coeff_name = button_data.get('index')
    except (json.JSONDecodeError, KeyError, TypeError):
        return no_update

    # Validate coefficient name before using it
    if not coeff_name:
        return no_update
    
    # Get current values in order
    current_slider_values = [drag_val, grav_val, shot_val, target_val, angle_val, rpm_val, velocity_val]
    
    # Find the index of this coefficient
    if coeff_name not in COEFFICIENT_NAMES:
        return no_update
    
    coeff_index = COEFFICIENT_NAMES.index(coeff_name)
    current_value = current_slider_values[coeff_index]
    
    # Use module-level configuration constants
    coeff_config = COEFFICIENT_CONFIG.get(coeff_name, {'step': 0.1, 'min': 0, 'max': 100})
    step = coeff_config['step']
    min_val = coeff_config['min']
    max_val = coeff_config['max']
    
    try:
        button_type = button_data.get('type')

        new_value = current_value

        if button_type == 'fine-inc':
            new_value = min(current_value + step, max_val)
            print(f"➕ {coeff_name}: {current_value:.4f} → {new_value:.4f} (+{step})")
        elif button_type == 'fine-dec':
            new_value = max(current_value - step, min_val)
            print(f"➖ {coeff_name}: {current_value:.4f} → {new_value:.4f} (-{step})")
        elif button_type == 'fine-inc-large':
            new_value = min(current_value + (step * 10), max_val)
            print(f"➕➕ {coeff_name}: {current_value:.4f} → {new_value:.4f} (+{step * 10})")
        elif button_type == 'fine-dec-large':
            new_value = max(current_value - (step * 10), min_val)
            print(f"➖➖ {coeff_name}: {current_value:.4f} → {new_value:.4f} (-{step * 10})")
        elif button_type == 'reset-coeff':
            new_value = COEFFICIENT_DEFAULTS.get(coeff_name, current_value)
            print(f"🔄 Reset {coeff_name}: {current_value:.4f} → {new_value:.4f} (default)")
        
        # Update the specific coefficient value
        new_slider_values = current_slider_values.copy()
        new_slider_values[coeff_index] = new_value
        
        # Store the new value in state
        if 'coefficient_values' not in state:
            state['coefficient_values'] = {}
        state['coefficient_values'][coeff_name] = new_value
        
        # Return all slider values plus state
        return new_slider_values + [state]
        
    except Exception as e:
        print(f"Error in coefficient fine adjustment: {e}")
        return no_update


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input({'type': 'jump-to-btn', 'index': ALL}, 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_jump_to_buttons(clicks, state):
    """Handle jump to coefficient buttons."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if triggered_id:
        try:
            button_data = json.loads(triggered_id)
            coeff_name = button_data.get('index')
            state['current_coefficient'] = coeff_name
            print(f"⤵️ Jumped to {coeff_name}")
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    
    return state


@app.callback(
    Output({'type': 'coeff-card', 'index': MATCH}, 'style'),
    [Input('app-state', 'data')],
    [State({'type': 'coeff-card', 'index': MATCH}, 'id')],
    prevent_initial_call=False
)
def update_coefficient_card_highlight(state, card_id):
    """Update coefficient card background to highlight the currently active coefficient."""
    if not card_id or not isinstance(card_id, dict):
        return {'marginBottom': '12px'}
    
    coeff_name = card_id.get('index')
    if not coeff_name:
        return {'marginBottom': '12px'}
    
    current_coeff = state.get('current_coefficient', 'kDragCoefficient')
    
    if coeff_name == current_coeff:
        # Highlight the current coefficient
        return {'marginBottom': '12px', 'backgroundColor': 'var(--accent-subtle)'}
    else:
        # Default background
        return {'marginBottom': '12px', 'backgroundColor': 'var(--bg-primary)'}


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input('export-graphs-btn', 'n_clicks'),
     Input('refresh-graphs-btn', 'n_clicks'),
     Input('pause-graphs-btn', 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_graph_controls(export_clicks, refresh_clicks, pause_clicks, state):
    """Handle graph control buttons."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'export-graphs-btn':
        print("📥 Exporting All Graphs...")
    elif button_id == 'refresh-graphs-btn':
        print("🔄 Refreshing Graph Data...")
    elif button_id == 'pause-graphs-btn':
        print("⏸️ Toggling Graph Auto-Update")
    
    return state


@app.callback(
    [Output('graph-success-rate', 'style'),
     Output('graph-coefficient-history', 'style'),
     Output('graph-optimization-progress', 'style'),
     Output('graph-shot-distribution', 'style'),
     Output('graph-algorithm-comparison', 'style'),
     Output('graph-convergence', 'style'),
     Output('graph-heatmap', 'style'),
     Output('graph-velocity-dist', 'style')],
    [Input('graph-toggles', 'value')]
)
def toggle_graph_visibility(selected_graphs):
    """Toggle visibility of graphs based on checklist."""
    graph_ids = [
        'success_rate',
        'coefficient_history',
        'optimization_progress',
        'shot_distribution',
        'algorithm_comparison',
        'convergence',
        'heatmap',
        'velocity_dist'
    ]
    
    styles = []
    for graph_id in graph_ids:
        if graph_id in selected_graphs:
            styles.append({'display': 'block'})
        else:
            styles.append({'display': 'none'})
    
    return styles


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input('start-workflow-btn', 'n_clicks'),
     Input('skip-workflow-btn', 'n_clicks'),
     Input('prev-workflow-btn', 'n_clicks'),
     Input('reset-workflow-btn', 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_workflow_controls(start_clicks, skip_clicks, prev_clicks, reset_clicks, state):
    """Handle workflow control buttons."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'start-workflow-btn':
        print("▶️ Starting Workflow from Beginning")
    elif button_id == 'skip-workflow-btn':
        print("⏭️ Skipping to Next in Workflow")
    elif button_id == 'prev-workflow-btn':
        print("⏮️ Going to Previous in Workflow")
    elif button_id == 'reset-workflow-btn':
        print("🔄 Resetting Workflow Progress")
    
    return state


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input({'type': 'backtrack', 'index': ALL}, 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_backtrack_buttons(clicks, state):
    """Handle backtrack coefficient buttons."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if triggered_id:
        try:
            button_data = json.loads(triggered_id)
            coeff_name = button_data.get('index')
            print(f"⏪ Backtracking to {coeff_name}")
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    
    return state


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input('save-session-btn', 'n_clicks'),
     Input('load-session-btn', 'n_clicks'),
     Input('export-session-btn', 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_session_management(save_clicks, load_clicks, export_clicks, state):
    """Handle session management buttons."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'save-session-btn':
        print("💾 Saving Session...")
    elif button_id == 'load-session-btn':
        print("📁 Loading Session...")
    elif button_id == 'export-session-btn':
        print("📤 Exporting Session Data...")
    
    return state


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input('save-settings-btn', 'n_clicks'),
     Input('load-settings-btn', 'n_clicks'),
     Input('reset-settings-btn', 'n_clicks'),
     Input('set-baseline-btn', 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_settings_buttons(save_clicks, load_clicks, reset_clicks, baseline_clicks, state):
    """Handle settings management buttons."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'save-settings-btn':
        print("💾 Saving Settings...")
    elif button_id == 'load-settings-btn':
        print("📁 Loading Settings...")
    elif button_id == 'reset-settings-btn':
        print("🔄 Resetting Settings to Defaults...")
    elif button_id == 'set-baseline-btn':
        print("⭐ Setting Current Values as Baseline")
    
    return state


@app.callback(
    [Output('notes-list', 'children'),
     Output('note-input', 'value')],
    [Input('add-note-btn', 'n_clicks')],
    [State('note-input', 'value'),
     State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_add_note(clicks, note_text, state):
    """Handle adding a new note."""
    if not clicks or not note_text:
        return dash.no_update, dash.no_update
    
    timestamp = datetime.now().strftime('%I:%M:%S %p')
    new_note = html.Div(
        className="card",
        style={'marginBottom': '8px', 'padding': '12px'},
        children=[
            html.Div(f"[{timestamp}]", style={'fontSize': '12px', 'color': 'var(--text-secondary)'}),
            html.P(note_text, style={'margin': '4px 0 0 0'})
        ]
    )
    
    # Get current notes
    if 'notes' not in state:
        state['notes'] = []
    
    state['notes'].insert(0, {'time': timestamp, 'text': note_text})
    
    # Create list of note elements
    notes_elements = [
        html.Div(
            className="card",
            style={'marginBottom': '8px', 'padding': '12px'},
            children=[
                html.Div(f"[{note['time']}]", style={'fontSize': '12px', 'color': 'var(--text-secondary)'}),
                html.P(note['text'], style={'margin': '4px 0 0 0'})
            ]
        ) for note in state['notes']
    ]
    
    print(f"📝 Added Note: {note_text}")
    
    return notes_elements if notes_elements else [html.P("No notes yet", style={'fontStyle': 'italic', 'color': 'var(--text-secondary)'})], ""


@app.callback(
    [Output('todos-list', 'children'),
     Output('todo-input', 'value')],
    [Input('add-todo-btn', 'n_clicks')],
    [State('todo-input', 'value'),
     State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_add_todo(clicks, todo_text, state):
    """Handle adding a new to-do item."""
    if not clicks or not todo_text:
        return dash.no_update, dash.no_update
    
    if 'todos' not in state:
        state['todos'] = []
    
    state['todos'].append({'text': todo_text, 'done': False})
    
    # Create list of todo elements
    todos_elements = [
        html.Div(
            className="card",
            style={'marginBottom': '8px', 'padding': '12px', 'display': 'flex', 'alignItems': 'center'},
            children=[
                dbc.Checklist(
                    options=[{'label': todo['text'], 'value': 'done'}],
                    value=['done'] if todo.get('done', False) else [],
                    inline=True
                )
            ]
        ) for todo in state['todos']
    ]
    
    print(f"✅ Added To-Do: {todo_text}")
    
    return todos_elements if todos_elements else [html.P("No to-dos yet", style={'fontStyle': 'italic', 'color': 'var(--text-secondary)'})], ""


@app.callback(
    Output('app-state', 'data', allow_duplicate=True),
    [Input('reconfigure-base-btn', 'n_clicks'),
     Input('restore-defaults-btn', 'n_clicks'),
     Input('lock-config-btn', 'n_clicks'),
     Input('export-config-btn', 'n_clicks'),
     Input('import-config-btn', 'n_clicks'),
     Input('reset-data-btn', 'n_clicks'),
     Input('clear-pinned-btn', 'n_clicks'),
     Input('emergency-stop-btn', 'n_clicks'),
     Input('force-retune-btn', 'n_clicks')],
    [State('app-state', 'data')],
    prevent_initial_call=True
)
def handle_danger_zone_buttons(reconfig_clicks, restore_clicks, lock_clicks, export_clicks,
                                import_clicks, reset_clicks, clear_clicks, emergency_clicks,
                                retune_clicks, state):
    """Handle danger zone buttons with appropriate warnings."""
    ctx = callback_context
    if not ctx.triggered:
        return state
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'reconfigure-base-btn':
        print("⚙️ Reconfiguring Base Point...")
    elif button_id == 'restore-defaults-btn':
        print("🔄 Restoring Factory Defaults...")
    elif button_id == 'lock-config-btn':
        state['config_locked'] = not state.get('config_locked', False)
        status = "Locked" if state['config_locked'] else "Unlocked"
        print(f"🔐 Configuration {status}")
    elif button_id == 'export-config-btn':
        print("📤 Exporting Configuration...")
    elif button_id == 'import-config-btn':
        print("📥 Importing Configuration...")
    elif button_id == 'reset-data-btn':
        print("⚠️ Resetting All Tuning Data...")
        state['coefficient_values'] = {}
        state['shot_count'] = 0
        state['success_rate'] = 0.0
    elif button_id == 'clear-pinned-btn':
        print("🧹 Clearing All Pinned Data...")
        state['pinned_values'] = {}
    elif button_id == 'emergency-stop-btn':
        print("🔥 EMERGENCY STOP!")
        state['tuner_enabled'] = False
    elif button_id == 'force-retune-btn':
        print("🔄 Forcing Retune of Current Coefficient...")
    
    return state


@app.callback(
    [Output('coeff-display', 'children'),
     Output('shot-display', 'children'),
     Output('success-display', 'children')],
    [Input('app-state', 'data')]
)
def update_dashboard_displays(state):
    """Update the dashboard display values."""
    coeff = state.get('current_coefficient', 'kDragCoefficient')
    shots = state.get('shot_count', 0)
    success = state.get('success_rate', 0.0)
    
    return coeff, str(shots), f"{success:.1%}"


@app.callback(
    [Output('robot-battery', 'children'),
     Output('robot-battery', 'style'),
     Output('robot-cpu', 'children'),
     Output('robot-cpu', 'style'),
     Output('robot-memory', 'children'),
     Output('robot-memory', 'style'),
     Output('robot-can', 'children'),
     Output('robot-can', 'style'),
     Output('robot-loop-time', 'children'),
     Output('robot-loop-time', 'style')],
    [Input('app-state', 'data')]
)
def update_robot_status_displays(state):
    """Update robot status displays - clear when disconnected."""
    connection_status = state.get('connection_status', 'disconnected')
    
    if connection_status == 'disconnected' or not connection_status or connection_status == '':
        # Robot is disconnected - show N/A for all values
        na_style = {'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--text-secondary)'}
        return (
            "N/A", na_style,
            "N/A", na_style,
            "N/A", na_style,
            "N/A", na_style,
            "N/A", na_style
        )
    else:
        # Robot is connected - show actual values (placeholder for now)
        return (
            "12.4V", {'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--success)'},
            "34%", {'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--info)'},
            "128MB", {'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--info)'},
            "42%", {'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--success)'},
            "18ms", {'fontSize': '24px', 'fontWeight': '600', 'color': 'var(--success)'}
        )


@app.callback(
    [Output('status-bar-time', 'children'),
     Output('status-bar-date', 'children'),
     Output('status-bar-shots', 'children'),
     Output('status-bar-success', 'children')],
    [Input('update-interval', 'n_intervals')],
    [State('app-state', 'data')]
)
def update_status_bar(n_intervals, state):
    """Update the status bar with current time and stats."""
    # Use JavaScript on client side for accurate local time
    # For now, we'll return empty and handle with clientside callback
    shots = str(state.get('shot_count', 0))
    success = f"{state.get('success_rate', 0.0):.1%}"
    
    # Return placeholders for time/date - will be updated by clientside callback
    return no_update, no_update, shots, success


# Clientside callback to update time/date with user's local timezone
app.clientside_callback(
    """
    function(n_intervals) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
        const dateStr = now.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
        return [timeStr, dateStr];
    }
    """,
    [Output('status-bar-time', 'children', allow_duplicate=True),
     Output('status-bar-date', 'children', allow_duplicate=True)],
    [Input('update-interval', 'n_intervals')],
    prevent_initial_call=True
)


@app.callback(
    [Output({'type': 'coeff-current-display', 'index': 'kDragCoefficient'}, 'children'),
     Output({'type': 'coeff-current-display', 'index': 'kGravity'}, 'children'),
     Output({'type': 'coeff-current-display', 'index': 'kShotHeight'}, 'children'),
     Output({'type': 'coeff-current-display', 'index': 'kTargetHeight'}, 'children'),
     Output({'type': 'coeff-current-display', 'index': 'kShooterAngle'}, 'children'),
     Output({'type': 'coeff-current-display', 'index': 'kShooterRPM'}, 'children'),
     Output({'type': 'coeff-current-display', 'index': 'kExitVelocity'}, 'children')],
    [Input({'type': 'coeff-slider', 'index': 'kDragCoefficient'}, 'value'),
     Input({'type': 'coeff-slider', 'index': 'kGravity'}, 'value'),
     Input({'type': 'coeff-slider', 'index': 'kShotHeight'}, 'value'),
     Input({'type': 'coeff-slider', 'index': 'kTargetHeight'}, 'value'),
     Input({'type': 'coeff-slider', 'index': 'kShooterAngle'}, 'value'),
     Input({'type': 'coeff-slider', 'index': 'kShooterRPM'}, 'value'),
     Input({'type': 'coeff-slider', 'index': 'kExitVelocity'}, 'value')],
    prevent_initial_call=False
)
def update_coefficient_current_displays(drag_val, grav_val, shot_val, target_val, angle_val, rpm_val, velocity_val):
    """Update the 'Current:' value displays in coefficient headers when sliders change."""
    # Format each value appropriately based on its type
    def format_value(val, coeff_name):
        config = COEFFICIENT_CONFIG.get(coeff_name, {})
        step = config.get('step', 0.1)
        # If step is very small, show more decimal places
        if step < 0.01:
            return f"{val:.4f}"
        elif step < 1:
            return f"{val:.2f}"
        else:
            return f"{val:.0f}"
    
    return (
        format_value(drag_val, 'kDragCoefficient'),
        format_value(grav_val, 'kGravity'),
        format_value(shot_val, 'kShotHeight'),
        format_value(target_val, 'kTargetHeight'),
        format_value(angle_val, 'kShooterAngle'),
        format_value(rpm_val, 'kShooterRPM'),
        format_value(velocity_val, 'kExitVelocity')
    )


if __name__ == '__main__':
    import webbrowser, threading, time
    import os

    print("=" * 60)
    print("MLtune Dashboard Starting")
    print("=" * 60)
    print(f"Opening browser to: http://localhost:8050")
    print("=" * 60)
    print(f"Tuner integration: {'Available' if TUNER_AVAILABLE else 'Demo mode'}")

    # Open browser after a short delay to ensure server is ready
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://localhost:8050')

    # Start the browser in a background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Use debug mode only in development, not in production
    debug_mode = os.environ.get('DASH_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=8050)
    

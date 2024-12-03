from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')
DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', 8050))

# Initialize Dash app with external stylesheets
app = Dash(
    __name__,
    title="DroneFleet Dashboard",
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
    ]
)

# Define CSS variables and global styles
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            :root {
                --primary-color: #00A4EF;
                --success-color: #7FBA00;
                --warning-color: #FFB900;
                --danger-color: #F25022;
                --neutral-color: #737373;
                --maintenance-color: #FF8C00;
                --background-color: #f8f9fa;
            }
            body {
                margin: 0;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: var(--background-color);
            }
        </style>
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

def create_map_component(drones_data):
    """Create the map visualization component."""
    
    # Convert drone data to DataFrame
    df = pd.DataFrame([{
        'id': drone['id'],
        'lat': drone['position'][0],
        'lon': drone['position'][1],
        'status': drone['status'],
        'battery': drone['battery_level'],
        'altitude': drone['altitude']
    } for drone in drones_data])

    # Create the map
    fig = go.Figure()

    # Add drone markers
    status_colors = {
        'idle': '#7FBA00',
        'in_transit': '#00A4EF',
        'delivering': '#FFB900',
        'returning': '#F25022',
        'charging': '#737373',
        'maintenance': '#FF8C00'
    }

    for status in df['status'].unique():
        mask = df['status'] == status
        fig.add_trace(go.Scattermapbox(
            lat=df[mask]['lat'],
            lon=df[mask]['lon'],
            mode='markers+text',
            marker=dict(
                size=10,
                color=status_colors.get(status, '#000000'),
                symbol='circle'
            ),
            text=df[mask]['id'].apply(lambda x: x[:8]),
            name=status.capitalize(),
            hovertemplate=(
                "<b>Drone %{text}</b><br>" +
                "Status: " + status + "<br>" +
                "Battery: %{customdata[0]}%<br>" +
                "Altitude: %{customdata[1]}m<br>" +
                "Position: (%{lat:.4f}, %{lon:.4f})<extra></extra>"
            ),
            customdata=df[mask][['battery', 'altitude']].values
        ))

    # Update layout
    fig.update_layout(
        mapbox=dict(
            style="carto-positron",
            zoom=12,
            center=dict(
                lat=df['lat'].mean(),
                lon=df['lon'].mean()
            )
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)"
        ),
        showlegend=True,
        uirevision=True
    )

    return html.Div([
        html.Div([
            html.H2("Fleet Map", className="section-title"),
            html.P(f"Tracking {len(drones_data)} drones")
        ], className="map-header"),
        dcc.Graph(
            figure=fig,
            style={'height': '70vh'},
            config={'displayModeBar': True}
        )
    ])

def create_stats_component(fleet_data):
    """Create statistics components."""
    drones = fleet_data.get("drones", [])
    analytics = fleet_data.get("analytics", {})
    
    # Calculate statistics
    total_drones = len(drones)
    active_drones = len([d for d in drones if d['status'] not in ['charging', 'maintenance']])
    battery_levels = [d['battery_level'] for d in drones]
    avg_battery = sum(battery_levels) / len(battery_levels) if battery_levels else 0
    maintenance_scores = [d['maintenance_score'] for d in drones]
    avg_maintenance = sum(maintenance_scores) / len(maintenance_scores) if maintenance_scores else 0
    
    # Create battery gauge
    battery_gauge = dcc.Graph(
        figure=go.Figure(go.Indicator(
            mode="gauge+number",
            value=avg_battery,
            title={'text': "Average Battery Level"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#00A4EF"},
                'steps': [
                    {'range': [0, 20], 'color': "#F25022"},
                    {'range': [20, 40], 'color': "#FFB900"},
                    {'range': [40, 100], 'color': "#7FBA00"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 20
                }
            }
        )),
        config={'displayModeBar': False}
    )

    return html.Div([
        html.Div([
            html.Div([
                html.H4("Total Drones", className="stat-title"),
                html.P(str(total_drones), className="stat-value")
            ], className="stat-card"),
            html.Div([
                html.H4("Active Drones", className="stat-title"),
                html.P(str(active_drones), className="stat-value")
            ], className="stat-card"),
            html.Div([
                html.H4("Fleet Health", className="stat-title"),
                html.P(f"{avg_maintenance:.1f}%", className="stat-value")
            ], className="stat-card"),
            html.Div([
                html.H4("Average Battery", className="stat-title"),
                html.P(f"{avg_battery:.1f}%", className="stat-value")
            ], className="stat-card")
        ], className="stat-cards"),
        
        html.Div(battery_gauge, className="battery-gauge-container")
    ])

# Layout setup
app.layout = html.Div([
    # Header
    html.Header([
        html.Div([
            html.H1("DroneFleet Management Dashboard", className="header-title"),
            html.P(id="last-updated", className="header-timestamp"),
        ], className="header-content")
    ], className="header"),

    # Main content
    html.Main([
        # Left panel - Map and drone status
        html.Div([
            html.Section(id="map-container", className="map-container"),
            html.Section([
                html.H2("Active Drones", className="section-title"),
                html.Div(id="drone-list", className="drone-list"),
            ], className="drone-section"),
        ], className="left-panel"),

        # Right panel - Stats and controls
        html.Div([
            # Fleet Statistics
            html.Section([
                html.H2("Fleet Statistics", className="section-title"),
                html.Div(id="fleet-stats", className="stats-container"),
            ], className="stats-panel"),

            # Weather Information
            html.Section([
                html.H2("Weather Conditions", className="section-title"),
                html.Div(id="weather-info", className="weather-container"),
            ], className="weather-panel"),
        ], className="right-panel"),
    ], className="main-content"),

    # Update interval
    dcc.Interval(
        id='interval-component',
        interval=5*1000,  # Update every 5 seconds
        n_intervals=0
    ),
], className="app-container")

@app.callback(
    Output("map-container", "children"),
    Input("interval-component", "n_intervals")
)
def update_map(n):
    try:
        response = requests.get(f"{API_BASE_URL}/fleet/status")
        if response.status_code == 200:
            fleet_data = response.json()
            return create_map_component(fleet_data["drones"])
        return html.Div("Error loading map", className="error-message")
    except Exception as e:
        return html.Div(f"Error: {str(e)}", className="error-message")

@app.callback(
    Output("fleet-stats", "children"),
    Input("interval-component", "n_intervals")
)
def update_fleet_stats(n):
    try:
        response = requests.get(f"{API_BASE_URL}/fleet/status")
        if response.status_code == 200:
            fleet_data = response.json()
            return create_stats_component(fleet_data)
        return html.Div("Error loading statistics", className="error-message")
    except Exception as e:
        return html.Div(f"Error: {str(e)}", className="error-message")

@app.callback(
    Output("drone-list", "children"),
    Input("interval-component", "n_intervals")
)
def update_drone_list(n):
    try:
        response = requests.get(f"{API_BASE_URL}/drones")
        if response.status_code == 200:
            drones = response.json()
            return html.Div([
                html.Div([
                    html.H3([
                        html.I(className=f"fas fa-drone {drone['status']}-status"),
                        f"Drone {drone['id'][:8]}"
                    ], className="drone-title"),
                    html.Div([
                        html.P([
                            html.I(className="fas fa-battery-three-quarters"),
                            f"Battery: {drone['battery_level']}%"
                        ], className=f"drone-battery {'low-battery' if drone['battery_level'] < 20 else ''}"),
                        html.P([
                            html.I(className="fas fa-info-circle"),
                            f"Status: {drone['status'].replace('_', ' ').title()}"
                        ], className=f"{drone['status']}-status"),
                        html.P([
                            html.I(className="fas fa-wrench"),
                            f"Maintenance: {drone['maintenance_score']}%"
                        ], className=f"{'maintenance-warning' if drone['maintenance_score'] < 70 else ''}")
                    ], className="drone-details")
                ], className="drone-card")
                for drone in drones
            ])
        return html.Div([
            html.I(className="fas fa-exclamation-triangle"),
            " Error loading drone list"
        ], className="error-message")
    except Exception as e:
        return html.Div([
            html.I(className="fas fa-exclamation-circle"),
            f" Error: {str(e)}"
        ], className="error-message")

@app.callback(
    Output("weather-info", "children"),
    Input("interval-component", "n_intervals")
)
def update_weather(n):
    try:
        response = requests.get(f"{API_BASE_URL}/fleet/weather")
        if response.status_code == 200:
            weather_data = response.json()
            return html.Div([
                html.Div([
                    html.I(className=f"fas fa-{get_weather_icon(weather_data)}"),
                    html.P([
                        html.I(className="fas fa-wind"),
                        f"Wind: {weather_data['conditions']['wind_speed']} m/s"
                    ]),
                    html.P([
                        html.I(className="fas fa-eye"),
                        f"Visibility: {weather_data['conditions']['visibility']} km"
                    ]),
                    html.P([
                        html.I(className="fas fa-check-circle" if weather_data['is_safe_for_flight'] else "fas fa-times-circle"),
                        f"Safe for flight: {'Yes' if weather_data['is_safe_for_flight'] else 'No'}"
                    ], className="flight-status")
                ], className="weather-info")
            ])
        return html.Div("Error loading weather information", className="error-message")
    except Exception as e:
        return html.Div(f"Error: {str(e)}", className="error-message")

@app.callback(
    Output("last-updated", "children"),
    Input("interval-component", "n_intervals")
)
def update_timestamp(n):
    return f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

def get_weather_icon(weather_data):
    """Return appropriate weather icon based on conditions."""
    conditions = weather_data['conditions']
    if conditions['precipitation'] > 0:
        return "cloud-rain"
    elif conditions['wind_speed'] > 10:
        return "wind"
    elif conditions['visibility'] < 5:
        return "cloud"
    return "sun"

if __name__ == '__main__':
    app.run_server(
        debug=True,
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT
    )
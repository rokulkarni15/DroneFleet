from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List

def create_stat_card(title: str, value: str) -> html.Div:
    """Create a statistics card component."""
    return html.Div([
        html.H4(title, className="stat-title"),
        html.P(value, className="stat-value")
    ], className="stat-card")

def create_battery_gauge(battery_levels: List[float]) -> dcc.Graph:
    """Create a gauge chart for average battery level."""
    avg_battery = sum(battery_levels) / len(battery_levels) if battery_levels else 0
    
    return dcc.Graph(
        figure=go.Figure(data=[go.Indicator(
            mode="gauge+number",
            value=avg_battery,
            title={'text': "Average Battery Level"},
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [None, 100]},
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
        )]),
        config={'displayModeBar': False},
        className="battery-gauge"
    )

def create_status_distribution(drones: List[Dict]) -> dcc.Graph:
    """Create a pie chart showing drone status distribution."""
    status_counts = pd.DataFrame(drones)['status'].value_counts()
    
    return dcc.Graph(
        figure=go.Figure(data=[go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            hole=.3,
            marker=dict(colors=[
                '#7FBA00',  # idle
                '#00A4EF',  # in_transit
                '#FFB900',  # delivering
                '#F25022',  # returning
                '#737373',  # charging
                '#FF8C00'   # maintenance
            ])
        )]),
        config={'displayModeBar': False},
        className="status-distribution"
    )

def create_maintenance_histogram(maintenance_scores: List[float]) -> dcc.Graph:
    """Create a histogram of maintenance scores."""
    return dcc.Graph(
        figure=px.histogram(
            pd.DataFrame({'scores': maintenance_scores}),
            x="scores",
            nbins=10,
            title="Maintenance Score Distribution",
            labels={"scores": "Maintenance Score", "count": "Number of Drones"},
            color_discrete_sequence=["#00A4EF"]
        ).update_layout(
            showlegend=False,
            margin=dict(l=10, r=10, t=30, b=10)
        ),
        config={'displayModeBar': False},
        className="maintenance-histogram"
    )

def create_stats_component(fleet_data: Dict) -> html.Div:
    """Create the complete statistics component."""
    drones = fleet_data.get("drones", [])
    analytics = fleet_data.get("analytics", {})
    active_deliveries = fleet_data.get("active_deliveries", 0)
    
    # Extract drone statistics
    battery_levels = [drone["battery_level"] for drone in drones]
    maintenance_scores = [drone["maintenance_score"] for drone in drones]
    
    return html.Div([
        # Summary Statistics
        html.Div([
            create_stat_card("Total Drones", str(len(drones))),
            create_stat_card("Active Drones", str(analytics.get("active_drones", 0))),
            create_stat_card("Active Deliveries", str(active_deliveries)),
            create_stat_card("Fleet Utilization", f"{analytics.get('fleet_utilization', 0)*100:.1f}%")
        ], className="stat-cards"),

        # Battery and Status Section
        html.Div([
            html.Div([
                html.H3("Battery Status"),
                create_battery_gauge(battery_levels)
            ], className="battery-section"),
            
            html.Div([
                html.H3("Drone Status Distribution"),
                create_status_distribution(drones)
            ], className="status-section")
        ], className="battery-status-container"),

        # Maintenance Section
        html.Div([
            html.H3("Maintenance Overview"),
            create_maintenance_histogram(maintenance_scores),
            html.Div([
                create_stat_card(
                    "Average Maintenance Score",
                    f"{sum(maintenance_scores)/len(maintenance_scores):.1f}%" if maintenance_scores else "N/A"
                )
            ], className="maintenance-summary")
        ], className="maintenance-section"),

        # Weather Status
        html.Div([
            html.H3("Weather Conditions"),
            html.Div([
                create_stat_card(
                    "Wind Speed",
                    f"{fleet_data.get('weather_conditions', {}).get('base', {}).get('wind_speed', 0):.1f} m/s"
                ),
                create_stat_card(
                    "Visibility",
                    f"{fleet_data.get('weather_conditions', {}).get('base', {}).get('visibility', 0):.1f} km"
                ),
                create_stat_card(
                    "Safe for Flight",
                    "Yes" if fleet_data.get('weather_conditions', {}).get('is_safe', False) else "No"
                )
            ], className="weather-cards")
        ], className="weather-section")
    ], className="stats-container")
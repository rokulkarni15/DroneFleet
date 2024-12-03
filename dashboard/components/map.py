from dash import html
import plotly.graph_objects as go
import pandas as pd
import dash_core_components as dcc

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
    for status in df['status'].unique():
        mask = df['status'] == status
        fig.add_trace(go.Scattermapbox(
            lat=df[mask]['lat'],
            lon=df[mask]['lon'],
            mode='markers+text',
            marker=dict(
                size=10,
                color=get_status_color(status),
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
        uirevision=True  # Preserve zoom/pan state on updates
    )

    return html.Div([
        html.Div([
            html.H2("Fleet Map"),
            html.P(f"Tracking {len(drones_data)} drones")
        ], className="map-header"),
        dcc.Graph(
            figure=fig,
            style={'height': '70vh'},
            config={'displayModeBar': True}
        )
    ])

def get_status_color(status):
    """Return color based on drone status."""
    status_colors = {
        'idle': '#7FBA00',      # Green
        'in_transit': '#00A4EF', # Blue
        'delivering': '#FFB900', # Yellow
        'returning': '#F25022',  # Red
        'charging': '#737373',   # Grey
        'maintenance': '#FF8C00' # Orange
    }
    return status_colors.get(status, '#000000')
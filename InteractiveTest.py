import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_leaflet as dl

# Load datasets
desinventar = pd.read_csv("GhanaDesInventar.csv")
emdat = pd.read_csv("Romania+Ghana_EMDAT.csv")
dartmouth = pd.read_csv("DartmouthFlood.csv")

# desinventar = pd.read_csv("desinventar.csv")
desinventar_data = desinventar[['Location', 'latitude', 'longitude', 'Date', 'Event']].copy()
desinventar_data = desinventar_data.rename(columns={'Date': 'Year'})
desinventar_data['Database'] = "DesInventar"

# Load EM-DAT Data
# emdat = pd.read_csv("emdat.csv")
emdat_data = emdat[['Location', 'Latitude', 'Longitude', 'Start Year', 'Disaster Type']].copy()
emdat_data = emdat_data.rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude', 'Start Year': 'Year'})
emdat_data['Database'] = "EM-DAT"

# Load Dartmouth Data
# dartmouth = pd.read_csv("dartmouth.csv")
dartmouth_data = dartmouth[['Country', 'lat', 'long', 'Began', 'MainCause']].copy()
dartmouth_data = dartmouth_data.rename(columns={'lat': 'latitude', 'long': 'longitude', 'Began': 'Year'})
dartmouth_data['Database'] = "Dartmouth"

# # Add a source column to distinguish datasets
# desinventar['Source'] = 'DesInventar'
# emdat['Source'] = 'EM-DAT'
# dartmouth['Source'] = 'Dartmouth'

# Combine datasets
data = pd.concat([desinventar_data, emdat_data, dartmouth_data], ignore_index=True)

# Ensure valid dates and drop rows with invalid coordinates
data['Year'] = pd.to_datetime(data['Year'], errors='coerce').dt.year

# data = data.dropna(subset=['latitude', 'longitude', 'Date'])

# Extract unique event types for each dataset
desinventar_events = desinventar_data['Event'].unique()
emdat_events = emdat_data['Disaster Type'].unique()
dartmouth_events = dartmouth_data['MainCause'].drop_duplicates().dropna().unique()

# Define Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Interactive Disaster Map", style={'text-align': 'center'}),

    # Year filter
    html.Label("Select Year:"),
    dcc.Dropdown(
        id='year_filter',
        options=[{"label": str(int(year)), "value": int(year)} for year in sorted(data['Year'].dropna().unique())],
        value=sorted(data['Year'].unique())[0],  # Default to the earliest year
        style={'width': '40%', 'margin': 'auto'}
    ),

    html.Div(id='event_count', style={'text-align': 'center', 'margin-top': '10px'}),

    # Dropdown menus for event selection
    html.Div([
        html.Label("DesInventar Events"),
        dcc.Dropdown(
            id='desinventar_events',
            options=[{"label": event, "value": event} for event in desinventar_events] + [{"label": "Select All", "value": "all"}],
            multi=True,
            value=["all"]
        ),

        html.Label("EM-DAT Events"),
        dcc.Dropdown(
            id='emdat_events',
            options=[{"label": event, "value": event} for event in emdat_events] + [{"label": "Select All", "value": "all"}],
            multi=True,
            value=["all"]
        ),

        html.Label("Dartmouth Events"),
        dcc.Dropdown(
            id='dartmouth_events',
            options=[{"label": event, "value": event} for event in dartmouth_events] + [{"label": "Select All", "value": "all"}],
            multi=True,
            value=["all"]
        )
    ], style={'width': '40%', 'margin': 'auto'}),

    # Zoom-to-City Buttons
    html.Div([
        html.Button("Zoom to Akuse, Ghana", id="zoom_akuse"),
        html.Button("Zoom to Timisoara, Romania", id="zoom_timisoara")
    ], style={'text-align': 'center', 'margin-top': '20px'}),

    # Map
    dl.Map(
        id='disaster_map',
        center=[0, 0],
        zoom=2,
        children=[
            dl.TileLayer(),
            dl.LayerGroup(id='layer_desinventar'),
            dl.LayerGroup(id='layer_emdat'),
            dl.LayerGroup(id='layer_dartmouth')
        ],
        style={'width': '100%', 'height': '600px', 'margin': 'auto'}
    )
])

@app.callback(
    [Output('layer_desinventar', 'children'),
     Output('layer_emdat', 'children'),
     Output('layer_dartmouth', 'children'),
     Output('event_count', 'children')],
    [Input('year_filter', 'value'),
     Input('desinventar_events', 'value'),
     Input('emdat_events', 'value'),
     Input('dartmouth_events', 'value')]
)
def update_map(selected_year, desinventar_selected, emdat_selected, dartmouth_selected):
    # Filter data by year and selected events
    filtered_desinventar = desinventar[desinventar['Year'] == selected_year]
    if "all" not in desinventar_selected:
        filtered_desinventar = filtered_desinventar[filtered_desinventar['Event'].isin(desinventar_selected)]

    filtered_emdat = emdat[emdat['Year'] == selected_year]
    if "all" not in emdat_selected:
        filtered_emdat = filtered_emdat[filtered_emdat['Disaster Type'].isin(emdat_selected)]

    filtered_dartmouth = dartmouth[dartmouth['Year'] == selected_year]
    if "all" not in dartmouth_selected:
        filtered_dartmouth = filtered_dartmouth[filtered_dartmouth['MainCause'].isin(dartmouth_selected)]

    # Create map layers
    desinventar_markers = [dl.Marker(position=[row['latitude'], row['longitude']], children=dl.Popup(row['Event'])) for _, row in filtered_desinventar.iterrows()]
    emdat_markers = [dl.Marker(position=[row['Lat'], row['Long']], children=dl.Popup(row['Disaster Type'])) for _, row in filtered_emdat.iterrows()]
    dartmouth_markers = [dl.Marker(position=[row['lat'], row['long']], children=dl.Popup(row['MainCause'])) for _, row in filtered_dartmouth.iterrows()]

    # Count events
    total_events = len(filtered_desinventar) + len(filtered_emdat) + len(filtered_dartmouth)

    return desinventar_markers, emdat_markers, dartmouth_markers, f"Visible Events: {total_events}"

@app.callback(
    Output('disaster_map', 'center'),
    [Input('zoom_akuse', 'n_clicks'), Input('zoom_timisoara', 'n_clicks')]
)
def zoom_to_city(zoom_akuse_clicks, zoom_timisoara_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [0, 0]
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'zoom_akuse':
        return [6.1088, 0.1281]  # Coordinates for Akuse, Ghana
    elif button_id == 'zoom_timisoara':
        return [45.7489, 21.2087]  # Coordinates for Timișoara, Romania

    return [0, 0]

if __name__ == '__main__':
    app.run_server(debug=True)

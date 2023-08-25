# Standard Library Imports
import os
import time
from datetime import datetime as dt
from datetime import timedelta

# Dash and Plotly Imports
from dash import dcc, html, Dash, Input, Output, State, callback_context, no_update
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Data Handling Imports
import pandas as pd
import sqlite3
from sqlite3 import Error

# Image and Requests Imports
import requests
from PIL import Image
from io import BytesIO
import base64

# Custom Libraries Imports
from database import Database
from PLC_kumlib import ConfigPLC, init_plcs, generate_status_indicators,connect_plcs

# Environment Variables Imports
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
USER_NAME = os.getenv("USER_NAME")
PASSWORD = os.getenv("PASSWORD")
BASE_URL = os.getenv("BASE_URL")

# Define Constants
IP_ADDRESSES = ["192.168.0.11", "192.168.0.12", "192.168.0.13", "192.168.0.14", "192.168.0.15", "192.168.0.16"]
IP_ADDRESS_MULTIPLEXER = "192.168.0.100"
COMMANDS_KUM = {'open': 0b0000011, 'close': 0b0000101, 'estop': 0b0010000, 'none': 0b0000000}
STATUS_BITS_KUM = {0: "Estop Trigged", 1: "Motor Dir", 2: "Motor run", 3: "Warning buzzer", 4: "Open endstop", 5: "Close endstop"}
COMMANDS_MULTIPLEXER = {'kum1': 0b01000001, 'kum2': 0b01000010, 'kum3': 0b01000100, 'kum4': 0b01001000, 'kum5': 0b01010000, 'kum6': 0b01100000, 'POW': 0b01000111, 'off': 0b00000000}
STATUS_BITS_MULTIPLEXER = {0: "CH1", 1: "CH2", 2: "CH3", 3: "CH4", 4: "CH5", 5: "CH6", 7: "Pumpe"}

# Initialize PLCS
PLCS = init_plcs(IP_ADDRESSES,"KUM", COMMANDS_KUM,STATUS_BITS_KUM,  "V1")
# Add PLC_multiplexer to PLCS
PLCS['multiplexer'] = ConfigPLC(IP_ADDRESS_MULTIPLEXER, COMMANDS_MULTIPLEXER,STATUS_BITS_MULTIPLEXER,"V1")
connect_plcs(PLCS)

# Initialize Global Variable
LAST_FETCHED_TIME = dt(1970, 1, 1)  # Initialized to UNIX epoch time

# Split PLCS into COLUMNS for the layout
N_COLUMNS = 3
PLCS_IDS = list(PLCS.keys())
COLUMNS = [PLCS_IDS[i::N_COLUMNS] for i in range(N_COLUMNS)]

# Initialize Database object
db = Database('my_database.sqlite')

app = Dash(__name__)


def generate_html_status(status_indicators):
    html_elements = []

    for indicator in status_indicators:
        html_elements.append(html.Div(indicator['text'], style={'color': indicator['color']}))

    return html_elements


def generate_plc_div(PLCS, COLUMNS):
    return html.Div(
        [html.Div(
            [
                html.P(
                    f"PLC{plc_id.split('plc')[-1]}: {'Connected' if PLCS[plc_id].connected else 'Unreachable'}"),
                html.Div([html.Button(f'{cmd}', id=f'button-{plc_id}-{cmd}', n_clicks=0) for cmd in
                          PLCS[plc_id].commands.keys()]),
                html.Div(id=f'status-indicator-{plc_id}'),
                html.Div(id=f'output-{plc_id}')
            ], style={'margin-right': '50px'}
        )

            for plc_id in [id for col in COLUMNS for id in col if "multiplexer" not in id]

        ], style={'display': 'flex', 'justify-content': 'space-around'}
    )


def generate_multiplex_div(PLCS):
    return html.Div([
        html.P("PLC Multiplexer: Connected" if PLCS['multiplexer'].connected else "PLC Multiplexer: NOT Connected"),
        html.Div([html.Button(f'{cmd}', id=f'button-multiplexer-{cmd}', n_clicks=0) for cmd in
                  PLCS['multiplexer'].commands.keys()]),
        html.Div(id=f'status-indicator-multiplexer'),
        html.Div(id=f'output-multiplexer')
    ], style={'margin-right': '50px'})


def create_layout(PLCS, COLUMNS, graph_interval=10 * 1000):
    return html.Div(
        [
            html.Img(id='live-feed', src='')  # camera feed
            ,
            dcc.Graph(id='live-update-graph')   # live graph
            ,
            dcc.Interval( id='interval-component',interval=graph_interval,n_intervals=0)
            ,
            dcc.Store(id='stored-data', storage_type='session')
            ,
            generate_plc_div(PLCS, COLUMNS)
            ,
            generate_multiplex_div(PLCS)
            ,
            html.Button("Download CSV", id="btn_csv")
            ,
            dcc.Download(id="download-dataframe-csv")
            ,
        ]
    )


app.layout = create_layout(PLCS, COLUMNS)


@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn_csv", "n_clicks"),
    State('stored-data', 'data'),
    prevent_initial_call=True
)
def func(n_clicks, stored_data):
    if n_clicks:
        df = pd.DataFrame(stored_data)
        timestamp = dt.now().strftime('%Y-%m-%d_%H-%M-%S')
        return dcc.send_data_frame(df.to_csv, f"data_{timestamp}.csv")


@app.callback(
    [Output(f'status-indicator-{plc_id}', 'children') for plc_id in PLCS.keys()],
    Input('interval-component', 'n_intervals')
)
def update_status(n):
    return [generate_html_status(generate_status_indicators(PLCS[plc_id])) for plc_id in PLCS.keys()]

# Creating separate callbacks for each PLC
for plc_id in PLCS.keys():
    @app.callback(
        Output(f'output-{plc_id}', 'children'),
        [Input(f'button-{plc_id}-{cmd}', 'n_clicks') for cmd in PLCS[plc_id].commands.keys()],
        [State(f'button-{plc_id}-{cmd}', 'n_clicks') for cmd in PLCS[plc_id].commands.keys()],
    )
    def send_command(*args):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        else:
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            plc_id, cmd = button_id.split('-')[1:]
            n_clicks = ctx.states[f'{button_id}.n_clicks']
            if n_clicks > 0:
                PLCS[plc_id].write_command("V0", PLCS[plc_id].commands[cmd])
                return f"Command {cmd} sent to {plc_id}"


@app.callback(Output('live-feed', 'src'),
              Input('interval-component', 'n_intervals'))
def update_image(n):
    try:
        # Create the URL using environment variables
        url = f"{BASE_URL}&user={USER_NAME}&password={PASSWORD}&width=640&height=480"
        unique_url = f"{url}&t={time.time()}"  # append a unique timestamp to the URL

        # Get the image from the URL with a timeout
        response = requests.get(unique_url, timeout=10)

        # Validate the response
        response.raise_for_status()
        if "image" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Invalid content received, expected an image")

        # Open and process the image
        img = Image.open(BytesIO(response.content))
        top, bottom, left = 190, 200, 250
        width, height = img.size
        img_cropped = img.crop((left, top, width, height - bottom))

        # Convert to JPEG and encode
        buffered = BytesIO()
        img_cropped.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return 'data:image/jpeg;base64,{}'.format(img_str)
    except (requests.RequestException, ValueError, IOError) as e:
        # Log the error for debugging
        print(f"An error occurred: {e}")
        return None  # return a default image or error message


@app.callback(Output('live-update-graph', 'figure'),
              [Input('interval-component', 'n_intervals')],
              [State('stored-data', 'data')])  # Use State to get the current data from dcc.Store
def update_graph_live(n, stored_data, lim=3600):
    # Query all data from the database
    new_data = pd.DataFrame( db.query_data(None, lim), columns=['time', 'N2O ppm', 'CO2 ppm', 'CH4 ppm', 'NH3 ppb'])

    # if there's no stored data, store the new data
    if stored_data is None:
        df = new_data
    else:
        # If there's stored data, append new data to it
        df = pd.concat([pd.DataFrame(stored_data), new_data])

    # Limit the data to the last 1000 records
    df = df.tail(lim)

    if df.empty:
        return go.Figure()  # Return an empty figure

    # Create the graph
    fig = make_subplots(rows=4, cols=1, vertical_spacing=0.05)
    fig.update_layout(height=800)

    for i, col in enumerate(df.columns[1:]):
        fig.add_trace(go.Scatter(x=df['time'], y=df[col], name=col), row=i + 1, col=1)

    # Update xaxis properties
    fig.update_xaxes(range=[min(df['time']), max(df['time'])])

    # Add annotations with the latest values
    annotations = []
    for i, col in enumerate(df.columns[1:]):
        latest_value = df[col].iloc[1]  # Get the last value
        latest_time = pd.to_datetime(df['time'].iloc[1])  # Converts 'time' string to datetime object
        latest_time_with_offset = latest_time + timedelta(seconds=1)  # Adds a 1 minute offset

        # Adjust yref to point to the correct yaxis (e.g., y2, y3, ...)
        annotations.append(
            dict(xref='x', yref=f'y{i + 1}', x=latest_time_with_offset, y=latest_value, xanchor='left',
                 yanchor='middle',
                 text=str(latest_value), showarrow=False, font=dict(size=15)))

    # Update layout with annotations and move the legend below the graph
    fig.update_layout(
        annotations=annotations,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig


@app.callback(Output('stored-data', 'data'),
              [Input('live-update-graph', 'figure')],
              [State('stored-data', 'data')])
def update_stored_data(_, stored_data, lim=1000):
    if stored_data:
        last_plotted_time = max(row['time'] for row in stored_data)
    else:
        last_plotted_time = None

    new_data = pd.DataFrame(db.query_data(last_plotted_time, lim),
                            columns=['time', 'N2O ppm', 'CO2 ppm', 'CH4 ppm', 'NH3 ppb'])

    if stored_data is None:
        df = new_data
    else:
        df = pd.concat([pd.DataFrame(stored_data), new_data])

    df = df.sort_values('time')
    df = df.tail(lim)

    return df.to_dict('records')


if __name__ == '__main__':
    app.run_server(port=8051, host="0.0.0.0", debug=True)

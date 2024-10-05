import pandas as pd
from dash import Dash, html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import threading
import time
import random
from datetime import datetime, timedelta
import requests
from lxml import html as p_html
import dash

color_map = {
    "BJP": "#FF5722",
    "INC": "#1976D2",
    "INLD": "#4CAF50",
    "AAP": "#FFC107",
    "JJP": "#E91E63",
    "Others": "#CCCCCC"
}

class Data:
    def __init__(self, location='statewiseS071', check_interval=10):
        self.data = pd.DataFrame()
        self.last_modified = None
        self.location = location
        self.check_interval = check_interval
        self.update()  # Initial data load
        self.running = True  # Flag to control thread execution
        self.thread = threading.Thread(target=self.run_check, daemon=True)
        self.thread.start()  # Start the thread

    def run_check(self):
        while self.running:
            self.update()
            time.sleep(self.check_interval)

    def update(self):
        self.get_data()
        if not self.data.empty and all(self.data["Status"] == "Result Declared-"):
            self.running = False  # Stop the thread

    def get_data(self):
        if self.last_modified is not None:
            self.simulate_data()
            return
        else:
            df = self.fetch(self.location)
            if not df.empty:
                self.data = self.clean(df)
                self.data = self.data.sort_values(by="Margin", ascending=False)
                self.data["Seat"] = "X" + self.data["Const. No."].astype(str)
                self.last_modified = time.time()  # Update last modified time

    def simulate_data(self):
        if not self.data.empty:
            self.data.at[random.randint(0, len(self.data) - 1), "Margin"] = random.randint(2000, 120000)
            self.data.at[random.randint(0, len(self.data) - 1), "Leading Party"] = random.choice(["BJP", "INC", "INLD", "AAP", "Others"])
            self.data = self.data.sort_values(by="Margin", ascending=False)
            self.data["Seat"] = "X" + self.data["Const. No."].astype(str)
            self.last_modified = time.time()  # Update last modified time

    def fetch(self, location):
        try:
            page = requests.get(
                "https://results.eci.gov.in/PcResultGenJune2024/%s.htm" % location,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
                }
            )
            page.raise_for_status()  # Raise an error for bad responses
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()  # Return an empty DataFrame on error
        
        tree = p_html.fromstring(page.text)
        table = tree.xpath('/html/body/main/div/div[3]/div/table/tbody')[0]

        headers = [
            'Constituency',
            'Const. No.',
            'Leading Candidate',
            'Leading Party',
            'Trailing Candidate',
            'Trailing Party',
            'Margin',
            "Status"
        ]

        stack = []
        for row in table.findall(".//tr"):
            txt = [r.text for r in row.findall(".//td")]
            if len(txt) == 30:
                final_row = txt[:3] + txt[4:5] + txt[15:16] + txt[17:18] + txt[-2:]
                stack.append(final_row)

        df = pd.DataFrame(data=stack, columns=headers)
        return df

    def clean(self, df):
        df["Margin"] = df["Margin"].replace("-", "0").astype(int)
        df["Leading Party"] = df["Leading Party"].apply(lambda x: "".join(r[0] for r in x.split(" ")))
        df["Label"] = df["Margin"].astype("str") + " <> " + df["Constituency"] + " <> " + df['Leading Candidate']
        return df

data = Data(check_interval=15)

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div(
    style={'padding': '2rem'},
    children=[
        html.H1(
            children=[
                html.A(
                    "Haryana Election Results: 2024",
                    href="https://www.youtube.com/@HaryanaAurHaryanvi?sub_confirmation=1",
                    target="_blank",
                    style={'textDecoration': 'none', 'color': 'inherit'}
                )
            ],
            className="text-center",
            style={'marginBottom': '0.1rem', 'fontSize': '3rem'}
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(id='timestamp', style={'textAlign': 'center', 'marginBottom': '1px'}),
                        html.Div(
                            children=[dcc.Graph(id='party-pie-chart', config={'displayModeBar': False})],
                            style={'width': '100%'}
                        ),
                        html.Div(
                            children=[dcc.Graph(id='least-margin-bar-chart', config={'displayModeBar': False})],
                            style={'width': '100%'}
                        ),
                    ],
                    width=12,
                    xs=12,
                    sm=12,
                    md=6,  # Half width on medium devices
                ),
                dbc.Col(
                    [
                        dcc.Dropdown(
                            data.data["Constituency"].sort_values(),
                            multi=True,
                            id='seat-selector',
                            placeholder="Filter for Assembly",
                            style={'width': '100%', 'margin': '0.1em'}
                        ),
                        html.Div(
                            id="loading",
                            children=[dcc.Graph(id='election-graph', config={
                                'displayModeBar': False,
                                'editable': False,
                                'scrollZoom': False,
                                'doubleClick': 'reset',  # Change this as needed
                                'modeBarButtonsToRemove': ['lasso2d', 'select2d'], })],
                            style={'width': '100%'}
                        ),
                    ],
                    width=8,
                    xs=12,
                    sm=12,
                    md=6,  # Half width on medium devices
                ),
            ],
            style={'margin': '0'}
        ),
        html.Footer(
            style={'textAlign': 'center', 'padding': '1rem', 'backgroundColor': '#f8f9fa'},
            children=[
                html.A(
                    children=html.P(
                        "Haryana Elections 2024 | © HaryanaAurHaryanvi",
                        style={'margin': '0'}
                    ),
                    href="https://www.youtube.com/@HaryanaAurHaryanvi?sub_confirmation=1",
                    target="_blank",
                    style={'textDecoration': 'none', 'color': '#555'}
                )
            ]
        ),
        dcc.Interval(id='interval-component', interval=5 * 1000, n_intervals=0),
        dcc.Store(id='intermediate-value', data={"total": 0})
    ]
)

def create_least_margin_bar_chart(df):
    least_margin_df = df.nsmallest(5, 'Margin')
    colors = [color_map.get(party, "#CCCCCC") for party in least_margin_df['Leading Party']]

    bar_chart = {
        'data': [{
            'y': least_margin_df['Seat'],
            'x': least_margin_df['Margin'],
            'text': least_margin_df['Margin'].astype("str") + " <> " + least_margin_df["Constituency"],
            'type': 'bar',
            'name': 'Least Margin',
            "orientation": 'h',
            'marker': {'color': colors}
        }],
        'layout': {
            'title': 'Top 5 Seats with Least Margin',
            'height': 400,
            'width': 400,
            "margin": {'l': 0},
            'titlefont': {'size': 18},
            'font': {
                'size': 12  # Set the size for the text labels
            },
            'dragmode': False ,
            'xaxis': {
                'title': 'Margin'
            },
            'yaxis': {
                'title': '',
                'showticklabels': False,
            },
            
        }
    }
    return bar_chart

def stack_data(df, existing_texts=None):
    stack = []
    existing_colors = set(color_map.values())

    if existing_texts is None:
        existing_texts = {}

    for party in df["Leading Party"].unique():
        if party not in color_map:
            color_map[party] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            existing_colors.add(color_map[party])

        temp = df[df["Leading Party"] == party]
        item = {
            "y": temp["Seat"].to_list(),
            "x": temp["Margin"].to_list(),
            'text': temp["Label"],
            'type': 'bar',
            'name': party,
            'marker': {'color': color_map[party]},
            "orientation": 'h',
            "config": {
                'displayModeBar': False,  # Disable the display mode bar
                'scrollZoom': False,       # Disable zooming with scroll
                'displaylogo': False       # Hide the plotly logo
            }
        }

        stack.append(item)

    data = {
        'data': stack,
        'layout': {
            "title": "Election Margin by Constituency",
            "transition": {'duration': 1500},
            "height": max(len(df) * 80, 400),
            "width": 350,
            "margin": {'l': 0.00, 'r': 0},
            'font': {
                'size': 14  # Set the size for the text labels
            },
            'dragmode': False ,
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.0,
                "xanchor": "center",
                "x": 0.5
            },
            'yaxis': {
                'title': '',
                'showticklabels': False,
            }
        },
    }

    return data, existing_texts


def create_pie_chart(df):
    pie_data = df['Leading Party'].value_counts()
    pie_chart = {
        'data': [{
            'labels': pie_data.index,
            'values': pie_data.values,
            'type': 'pie',
            'textinfo': 'label+value',
            'marker': {'colors': [color_map.get(party, "#CCCCCC") for party in pie_data.index]},
        }],
        'layout': {
            'title': '',
            'height': 400,
            'width': 400,  # Set width to 100% for responsiveness
            "margin": {'l': 0},
            'titlefont': {'size': 18},
            'showlegend': False,
            'font': {
                'size': 20  # Set the size for the text labels
            },
            "legend": {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': 1.05,
                'xanchor': 'center',
                'x': 0.5
            }
        }
    }
    return pie_chart

@callback(
    Output('election-graph', 'figure'),
    Output('party-pie-chart', 'figure'),
    Output('least-margin-bar-chart', 'figure'),
    Output('timestamp', 'children'),
    Output('intermediate-value', 'data'),
    Input('seat-selector', 'value'),
    Input('intermediate-value', 'data'),
    Input('interval-component', 'n_intervals'),
)
def update_graphs(selected_seats, store, n):
    df = data.data.copy()

    if selected_seats is not None and len(selected_seats) > 0:
        filtered_df = df[df['Constituency'].isin(selected_seats)]
    else:
        filtered_df = df

    india_time = utc_now + timedelta(hours=5, minutes=30)  # Adjust to UTC +5:30
    timestamp = india_time.strftime('%Y-%m-%d %H:%M:%S')

    if filtered_df.Margin.sum() == store["total"]:
        return dash.no_update, dash.no_update, dash.no_update, timestamp, {"total": store["total"]}

    election_fig, existing_texts = stack_data(filtered_df)
    party_pie_fig = create_pie_chart(df)
    least_margin_fig = create_least_margin_bar_chart(df)

    return election_fig, party_pie_fig, least_margin_fig, timestamp, {"total": filtered_df.Margin.sum()}

if __name__ == '__main__':
    app.run_server(debug=True, host="0.0.0.0", port=18081)

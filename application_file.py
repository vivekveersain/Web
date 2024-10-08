import pandas as pd
from dash import Dash, html, dcc, callback, Output, Input
import threading
import time
import random
from datetime import datetime, timedelta
import requests
from lxml import html as p_html
from flask import Flask
import dash

party_colors = {
    "BJP": "#FF5722",
    "INC": "#1976D2",
    "INLD": "#4CAF50",
    "AAP": "#FFC107",
    "JJP": "#E91E63",
    "Others": "#CCCCCC",
}

class Data:
    def __init__(self, check_interval=10):
        self.data = pd.DataFrame()
        self.last_df = pd.DataFrame()
        self.last_modified = None
        self.location = ['statewiseS071', 'statewiseS072', 'statewiseS073', 'statewiseS074', 'statewiseS075']
        self.dfs = {}
        self.headers = ['Constituency','Const. No.','Leading Candidate', 'Leading Party',
            'Trailing Candidate','Trailing Party','Margin', "Round","Status"]
        self.check_interval = check_interval
        self.update()  # Initial data load
        self.running = True  # Flag to control thread execution
        self.thread = threading.Thread(target=self.run_check, daemon=True)
        self.thread.start()  # Start the thread
        self.page = None

    def run_check(self):
        while self.running:
            self.update()
            time.sleep(self.check_interval)

    def update(self):
        self.get_data()
        if not self.data.empty and all(self.data["Status"] == "Result Declared"):
            self.running = False  # Stop the thread

    def get_data(self):
        for location in self.location: self.fetch(location)
        df = pd.concat(self.dfs.values()).fillna("")
        df["Leading Party"] = df["Leading Party"].fillna("X")
        if not df.empty:
            self.data = self.clean(df)
            #self.data = self.data.sort_values(by="Margin", ascending=False)
            if not self.data.equals(self.last_df):
                print("UPDATED!!!", str(datetime.now()))
                self.last_modified = int(time.time())  # Update last modified time
                self.last_df = self.data.copy()
        
    def fetch(self, location):
        try:
            page = requests.get(
                "https://results.eci.gov.in/AcResultGenOct2024/%s.htm" % location,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "DNT": "1",
                    "Priority": "u=1",
                    "Referer": "https://results.eci.gov.in/AcResultGenOct2024/%s.htm" % location,
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-User": "?1",
                    "Sec-GPC": "1",
                    "TE": "trailers",
                    "Upgrade-Insecure-Requests": "1",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0"
                }
            )
            #page.raise_for_status()  # Raise an error for bad responses
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
        
        tree = p_html.fromstring(page.text)
        table = tree.xpath('/html/body/main/div/div[3]/div/table/tbody')[0]

        stack = []
        for row in table.findall(".//tr"):
            txt = [r.text for r in row.findall(".//td")]
            if len(txt) == 31:
                final_row = txt[:3] + txt[4:5] + txt[15:16] + txt[17:18] + txt[-3:]
                stack.append(final_row)

        df = pd.DataFrame(data=stack, columns=self.headers)
        self.dfs[location] = df

    def clean(self, df):
        df["Margin"] = df["Margin"].replace("-", "0").astype(int)
        df["Leading Party"] = df["Leading Party"].replace("", "X").apply(lambda x: "".join(r[0] for r in x.split(" ")))
        df["Label"] = df["Constituency"].astype("str") + df["Status"].apply(lambda x: " (Declared)" if x == "Result Declared" else "") + " | " + df["Margin"].apply(lambda x: format_margin_indian_style(x)).astype("str") + " (" + df["Round"] + ") |  "  + df['Leading Candidate'] + " | " + df['Leading Party']
        return df
    
def format_margin_indian_style(margin):
    margin = str(margin)
    rev = margin[:-1][::-1]
    return ",".join([rev[e*2:e*2+2] for e, r in enumerate(rev[::2])])[::-1]+margin[-1]

data = Data(check_interval=5)

# Initialize Flask app
server = Flask(__name__)

# Initialize Dash app
app = Dash(__name__, server=server)

# Define layout for Dash
app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#f4f4f4', 'padding': '10px'}, children=[
    html.H1(
        html.A("Haryana Elections Results", href="https://www.youtube.com", target="_blank", style={'color': 'black', 'textDecoration': 'none'}),
        style={'textAlign': 'center', 'marginBottom': '5px', 'fontSize': '28px', 'fontWeight': 'bold'}
    ),
    html.Div(
        html.A(
            "Subscribe on YouTube for support!",
            href="https://www.youtube.com/@HaryanaAurHaryanvi?sub_confirmation=1",
            target="_blank",
            style={
                'padding': '10px 20px',
                'backgroundColor': '#1976D2',
                'color': 'white',
                'borderRadius': '5px',
                'textDecoration': 'none',
                'transition': 'background-color 0.3s',
                'fontSize': '1.2rem',
                'textAlign': 'center',
                'display': 'inline-block',
                'margin': '10px auto'
            }
        ),
        style={'textAlign': 'center', 'marginBottom': '20px'}
    ),
    html.Div(id='last-update', style={'textAlign': 'center', 'marginTop': '10px', 'fontSize': '14px', 'color': '#555'}),
    dcc.Graph(id='donut-chart', config={'displayModeBar': False}),
    dcc.Dropdown(
        id='constituency-dropdown',
        options=[{'label': c, 'value': c} for c in data.data["Constituency"].sort_values()],
        multi=True,
        placeholder="Select Constituencies",
        style={'width': '100%', 'padding': '1px', 'margin': '0 auto', 'marginBottom': '1px'}
    ),
    dcc.Graph(id='bar-graph', config={'staticPlot': True, 'scrollZoom': False, 'displayModeBar': False}),
    dcc.Interval(
        id='interval-component',
        interval=5 * 1000,
        n_intervals=0
    ),
    dcc.Store(id='intermediate-value', data=""),
    dcc.Store(id='intermediate-value2', data=""),
    html.Footer(style={'textAlign': 'center', 'marginTop': '20px', 'fontSize': '14px', 'color': '#777'}, children=[
        html.A("© HaryanaAurHaryanvi - An initiative by Aacharya Veer Sain Shastri", 
            href="https://www.youtube.com/@HaryanaAurHaryanvi?sub_confirmation=1", 
            target="_blank", 
            style={'color': '#777', 'textDecoration': 'none'})
    ])

])

@app.callback(
    [Output('bar-graph', 'figure'),
     Output('donut-chart', 'figure'),
     Output('last-update', 'children')],
     Output('intermediate-value', 'data'),
     Output('intermediate-value2', 'data'),
    [Input('interval-component', 'n_intervals'),
     Input('constituency-dropdown', 'value'),
     Input('intermediate-value', 'data'),
     Input('intermediate-value2', 'data')]
)
def update_graph(n, selected_constituencies, last_modified, last_selection):
    # Update the DataFrame
    df = data.data.copy()
    if selected_constituencies is None: selected_constituencies = []

    # Get the current time in UTC+5:30
    current_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    last_update_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
    last_update_text = f"Last updated: {last_update_time} IST"

    #print(str(last_modified), str(data.last_modified))
    #print(int(time.time() - int(data.last_modified)))
    #print(data.data["Leading Party"].value_counts())
    #print(data.last_df["Leading Party"].value_counts())

    if str(last_modified) == str(data.last_modified) and selected_constituencies == last_selection:
        #print("No update")
        return dash.no_update, dash.no_update, last_update_text, dash.no_update, dash.no_update
    
    # Filter for the selected constituencies for the bar graph only
    if selected_constituencies:
        filtered_df = df[df['Constituency'].isin(selected_constituencies)].copy()
    else:
        filtered_df = df.copy()  # Show all data if no constituency is selected

    # Create a text label combining margin, constituency name, candidate name, and party name
    #filtered_df.loc[:, 'Label'] = filtered_df.apply(lambda row: f"{row['Constituency']} | {row['Margin']} | {row['Leading Candidate']} | {row['Leading Party']}", axis=1)

    # Sort by Leading Party and then by Margin in descending order
    filtered_df.sort_values(by=['Leading Party', 'Margin'], ascending=[False, False], inplace=True)

    # Calculate the maximum margin for the filtered DataFrame
    max_margin = filtered_df['Margin'].max() if not filtered_df.empty else 0

    if max_margin == 0: max_margin = 1
    # Handle case when selected_constituencies is None
    if selected_constituencies is None:
        selected_constituencies = []

    # Determine bar height based on selection
    num_selected = len(selected_constituencies) if selected_constituencies else len(df)
    bar_height = max(150, num_selected * 30)  # Adjust height dynamically

    # Determine the text position based on the margin condition
    text_positions = [
        'inside' if margin >= 0.55 * max_margin else 'outside'
        for margin in filtered_df['Margin']
    ]

    # Create a horizontal bar chart using Plotly
    bar_figure = {
        'data': [{
            'x': filtered_df['Margin'],
            'y': filtered_df['Constituency'],
            'type': 'bar',
            'orientation': 'h',
            'marker': {
                'color': filtered_df['Leading Party'].apply(lambda x: party_colors.get(x, "#CCCCCC")),
                'line': {'width': 0}  # Remove the border
            },
            'text': filtered_df['Label'],
            'textposition': text_positions,
            #'hovertemplate': '%{text}<br>%{y} Constituency<br>Margin: %{x}<extra></extra>',
        }],
        'layout': {
            'height': bar_height,
            'xaxis': {
                'title': '',
                'range': [0, max_margin * 1.1],
                'autorange': False
            },
            'yaxis': {
                'title': '',
                'showticklabels': False
            },
            'bargap': 0.1,
            'transition': {'duration': 2500, 'easing': 'cubic-in-out'},
            'showlegend': False,
            'margin': {
                'l': 0,
                'r': 0,
                't': 0,
                'b': 0
            },
        }
    }

    # Create the donut chart using the complete DataFrame
    seat_counts = df['Leading Party'].value_counts()
    
    donut_figure = {
        'data': [{
            'values': seat_counts,
            'labels': seat_counts.index,
            'type': 'pie',
            'hole': 0.4,
            'marker': {
                'colors': [party_colors.get(party, "#CCCCCC") for party in seat_counts.index]
            },
            'hoverinfo': 'label+percent+value',
            'textinfo': 'label+value',
            'textfont': {
            'size': 16  # Adjust the font size here
        },
        }],
        'layout': {
            'showlegend': False,
        }
    }

    return bar_figure, donut_figure, last_update_text, str(data.last_modified), selected_constituencies

if __name__ == '__main__':
    app.title = "Haryana Elections!!!"  # Set the title of the tab
    app.run(host="0.0.0.0", debug=False, port = "18081")
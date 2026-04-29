import dash
from dash import dcc, html
import plotly.graph_objs as go
import pandas as pd
import numpy as np

# Sample data for demonstration purposes
data = {'Drug': ['Drug A', 'Drug B', 'Drug C', 'Drug D'],
         'Score': [10.5, 9.8, 12.3, 11.7],
         'LogP': [-2.4, -1.8, -1.2, -0.6],
         'HBA': [3, 2, 1, 4],
         'HBD': [5, 4, 3, 2]}

# Convert to DataFrame
df = pd.DataFrame(data)

app = dash.Dash()

app.layout = html.Div([    dcc.Graph(id='drug-score-plot', figure={        'data': [go.Scatter(x=df['Drug'], y=df['Score'], mode='lines+markers'))],
    dcc.Graph(id='logp-hba-graph', figure={        'data': [go.Bar(x=df['Drug'], y=df['LogP']), go.Bar(x=df['Drug'], y=df['HBA'])]    })])

if __name__ == '__main__':
    app.run_server(debug=True)
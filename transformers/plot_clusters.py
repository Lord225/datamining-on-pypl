import pandas as pd
from dask import dataframe as dd
from dask.diagnostics import ProgressBar # type: ignore
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# Enable progress bar
ProgressBar().register()

# Load the data
functions = dd.read_sql_table(
    'functions',  
    'postgresql://postgres:8W0MQwY4DINCoX@localhost:5432/data-mining',
    index_col='id',
    bytes_per_chunk='10000kb'
) # type: ignore

embeddings = pd.read_hdf('tsne_embeddings.h5', key='tsne_embeddings', mode='r')
clusters = pd.read_hdf('clusters.h5', key='clusters', mode='r')

# Prepare the data
embeddings.columns = ['x', 'y']
clusters.columns = ['cluster']
clusters_embed = pd.concat([embeddings, clusters], axis=1)
clusters_embed['cluster'] = clusters_embed['cluster'].astype('category')

function_dict = functions.set_index('id')['name'].compute().to_dict()
body_dict = functions.set_index('id')['body'].compute().to_dict()

function_dict = {k-1: v for k, v in function_dict.items()}
body_dict = {k-1: v for k, v in body_dict.items()}

clusters_embed['function'] = clusters_embed.index.map(function_dict.get)
clusters_embed['body'] = clusters_embed.index.map(body_dict.get)

# Limit dataset to 50,000 samples for visualization
clusters_embed = clusters_embed[:250_000]

# Plotly figure
fig = px.scatter(
    clusters_embed, 
    x='x', 
    y='y', 
    color='cluster', 
    title='Cluster Plot',
    labels={'cluster': 'Cluster'},
    width=800,
    height=800,
    opacity=0.5,
)

# Initialize Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        dcc.Graph(id='scatter-plot', figure=fig, style={'flex': '1'}),
        html.Div(id='hover-data', style={'flex': '1', 'padding': '20px', 'border': '1px solid #ddd', 'margin-left': '20px'})
    ], style={'display': 'flex'})
])

# Callback to update hover data
@app.callback(
    Output('hover-data', 'children'),
    [Input('scatter-plot', 'hoverData')]
)
def display_hover_data(hoverData):
    if hoverData:
        # Get the point's index
        point_index = hoverData['points'][0]['pointIndex']
        
        # Retrieve the detailed function and body from clusters_embed for the hovered point
        function = clusters_embed.iloc[point_index]['function']
        body = clusters_embed.iloc[point_index]['body']
        
        return html.Div([
            html.H5(f"Function: {function}"),
            html.P(f"Body: {body}", style={'white-space': 'pre-wrap'})
        ])
    return "Hover over a point to see details."

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)

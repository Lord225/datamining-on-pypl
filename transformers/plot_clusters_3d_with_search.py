import pandas as pd
from dask import dataframe as dd
from dask.diagnostics import ProgressBar # type: ignore
import plotly.express as px # type: ignore
from dash import Dash, dcc, html, Input, Output # type: ignore
import torch 
from transformers import AutoModel

# Enable progress bar
ProgressBar().register()

CLUSTERS = 'clusters_3.h5'

EMBEDDINGS = 'embeddings_3.h5'


from torch import nn
import torch.nn.functional as F
import torch.utils
import torch.distributions
import torch
device = torch.device("cpu")

model = AutoModel.from_pretrained('jinaai/jina-embeddings-v2-base-code', trust_remote_code=True)

class VariationalEncoder(nn.Module):
    def __init__(self, latent_dims):
        super(VariationalEncoder, self).__init__()
        self.linear1 = nn.Linear(768, 512)
        self.linear11 = nn.Linear(512, 512)
        self.linear2 = nn.Linear(512, latent_dims)
        self.linear3 = nn.Linear(512, latent_dims)

        self.N = torch.distributions.Normal(0, 1)
        self.N.loc = self.N.loc # hack to get sampling on the GPU
        self.N.scale = self.N.scale
        self.kl = 0

    def forward(self, x):
        x = torch.flatten(x, start_dim=1)
        x = F.relu(self.linear1(x))
        x = F.relu(self.linear11(x))
        mu =  self.linear2(x)
        sigma = torch.exp(self.linear3(x))
        z = mu + sigma*self.N.sample(mu.shape)
        self.kl = (sigma**2 + mu**2 - torch.log(sigma) - 1/2).sum()
        return z
    
class Decoder(nn.Module):
    def __init__(self, latent_dims):
        super(Decoder, self).__init__()
        self.linear1 = nn.Linear(latent_dims, 512)
        self.linear11 = nn.Linear(512, 512)
        self.linear2 = nn.Linear(512, 768)

    def forward(self, z):
        z = F.elu(self.linear1(z))
        z = F.elu(self.linear11(z))
        z = F.elu(self.linear2(z))
        return z
class VariationalAutoencoder(nn.Module):
    def __init__(self, latent_dims):
        super(VariationalAutoencoder, self).__init__()
        self.encoder = VariationalEncoder(latent_dims)
        self.decoder = Decoder(latent_dims)

    def forward(self, x):
        z = self.encoder(x)
        return self.decoder(z)

# load VAE model (model.pth)
vae = VariationalAutoencoder(3)
vae.load_state_dict(torch.load('model.pth', map_location=device))
vae.to(device)
vae.eval()

def prep_data_body(row):
    func_name = row['name']
    func_args = row['args']
    func_body = row['body']

    def format_args(args):
        return ', '.join(args.replace('{', '').replace('}', '').split())
    
    def format_body(body):
        return body.replace('\n', ' ').replace('\r', ' ')
    
    func = f"def {func_name}({format_args(func_args)}):\n {format_body(func_body)}"

    return func

def prep_body_with_docstring(row):
    func_name = row['name']
    func_args = row['args']
    func_body = row['body']
    func_docstring = row['docstring']

    def format_args(args):
        return ', '.join(args.split())
    
    def format_body(body):
        return body.replace('\n', ' ').replace('\r', ' ')

    # rebuild function
    func = f"def {func_name}({format_args(func_args)}):\n {format_body(func_body)}\n\n{func_docstring}"

    return func



def encode_vae(embeddings):
    with torch.no_grad():
        embeddings_latent = vae.encoder(embeddings)

    return embeddings_latent

def encode_embeddings(text):
    text_cap = [t[:4096] for t in text]

    embeddings = model.encode(text_cap, convert_to_tensor=True, batch_size=1, max_length=4096, device=device)

    return embeddings

def generate_latent_space_of_text(text):
    embeddings = encode_embeddings(text)
    embeddings = embeddings.cpu().numpy()

    embeddings = embeddings.reshape(embeddings.shape[0], 1, 768)
    embeddings = torch.tensor(embeddings, dtype=torch.float32)
    embeddings_latent = encode_vae(embeddings)

    return embeddings_latent


functions = dd.read_sql_table(  # type: ignore
    'functions',  
    'postgresql://postgres:8W0MQwY4DINCoX@localhost:5432/data-mining',
    index_col='id',
    bytes_per_chunk='10000kb'
)

embeddings = pd.read_hdf(EMBEDDINGS, key='embeddings_3', mode='r')
clusters = pd.read_hdf(CLUSTERS, key='clusters', mode='r')

embeddings.columns = ['x', 'y', 'z']
clusters.columns = ['cluster']
clusters_embed = pd.concat([embeddings, clusters], axis=1)
clusters_embed['cluster'] = clusters_embed['cluster'].astype('category')

function_dict = functions.set_index('id')['name'].compute().to_dict()
body_dict = functions.set_index('id')['body'].compute().to_dict()

function_dict = {k-1: v for k, v in function_dict.items()}
body_dict = {k-1: v for k, v in body_dict.items()}

clusters_embed['function'] = clusters_embed.index.map(function_dict.get)
clusters_embed['body'] = clusters_embed.index.map(body_dict.get)
clusters_embed['index'] = clusters_embed.index

clusters_embed = clusters_embed[:100_000]

x_min, x_max = clusters_embed['x'].min(), clusters_embed['x'].max()
y_min, y_max = clusters_embed['y'].min(), clusters_embed['y'].max()
z_min, z_max = clusters_embed['z'].min(), clusters_embed['z'].max()

fig = px.scatter_3d(
    clusters_embed, 
    x='x', 
    y='y', 
    z='z',
    color='cluster',
    custom_data='index',
    title='Cluster Plot',
    labels={'cluster': 'Cluster'},
    width=800,
    height=800,
    
)


fig.update_layout(
    scene=dict(
        aspectmode='cube',
        xaxis=dict(range=[x_min, x_max]),
        yaxis=dict(range=[y_min, y_max]),
        zaxis=dict(range=[z_min, z_max])
    )
)

app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        dcc.Graph(id='scatter-plot', figure=fig, style={'flex': '1'}),
        html.Div(id='hover-data', style={'flex': '1', 'padding': '20px', 'border': '1px solid #ddd', 'margin-left': '20px'})
    ], style={'display': 'flex'}),
    html.Div([
        dcc.Input(id='search-input', type='text', placeholder='Search for function...'),
        html.Button('Search', id='search-button', n_clicks=0),
        html.Div(id='search-results')
    ])
])

@app.callback(
    Output('hover-data', 'children'),
    [Input('scatter-plot', 'hoverData')]
)
def display_hover_data(hoverData):
    if hoverData:
        print(hoverData)
        point_index = hoverData['points'][0]['customdata'][0]
        
        function = clusters_embed.iloc[point_index]['function']
        body = clusters_embed.iloc[point_index]['body']
        
        return html.Div([
            html.H5(f"Function: {function}"),
            html.P(f"Body: {body}", style={'white-space': 'pre-wrap'})
        ])
    return "Hover over a point to see details."

@app.callback(
    Output('scatter-plot', 'figure'),
    [Input('search-button', 'n_clicks')],
    [Input('search-input', 'value')]
)
def search_function(n_clicks, search_input):
    if n_clicks and search_input:
        search_input = search_input.lower()

        if not search_input or search_input.isspace():
            return fig
        
        embeddings_latent = generate_latent_space_of_text([search_input])

        # Calculate distances to the search input embedding
        distances = torch.cdist(embeddings_latent, torch.tensor(clusters_embed[['x', 'y', 'z']].values, dtype=torch.float32))
        closest_indices = distances.argsort(dim=1)[0][:500].numpy()  

        filtered_clusters_embed = clusters_embed.iloc[closest_indices]

        fig_new = px.scatter_3d(
            filtered_clusters_embed, 
            x='x', 
            y='y', 
            z='z',
            color='cluster',
            custom_data='index',
            title='Cluster Plot',
            labels={'cluster': 'Cluster'},
            width=800,
            height=800,
        )


        fig_new.update_layout(
            scene=dict(
                aspectmode='cube',
                xaxis=dict(range=[x_min, x_max]),
                yaxis=dict(range=[y_min, y_max]),
                zaxis=dict(range=[z_min, z_max])
            )
        )


        return fig_new

    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)

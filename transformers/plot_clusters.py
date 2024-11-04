import pandas as pd
from dask import dataframe as dd 
from dask import array as da
from dask.diagnostics import ProgressBar # type: ignore

# enable progress bar
ProgressBar().register()

functions = dd.read_sql_table('functions',   # type: ignore
                            'postgresql://postgres:8W0MQwY4DINCoX@localhost:5432/data-mining', 
                            index_col='id', 
                            bytes_per_chunk='10000kb')



# Load embeddings and clusters data from HDF5 files
embeddings = pd.read_hdf('tsne_embeddings.h5', key='tsne_embeddings', mode='r')
clusters = pd.read_hdf('clusters.h5', key='clusters', mode='r')

# Name columns and combine embeddings with cluster labels
embeddings.columns = ['x', 'y']
clusters.columns = ['cluster']
clusters_embed = pd.concat([embeddings, clusters], axis=1)

# Set cluster column as a categorical data type for efficient processing
clusters_embed['cluster'] = clusters_embed['cluster'].astype('category')

# Create a dictionary to map function IDs to function names
function_dict = functions.set_index('id')['name'].compute().to_dict()
body_dict = functions.set_index('id')['body'].compute().to_dict()

# offset all ids by 1
function_dict = {k-1: v for k, v in function_dict.items()}
body_dict = {k-1: v for k, v in body_dict.items()}

# Map function names to clusters_embed using the dictionary
clusters_embed['function'] = clusters_embed.index.map(function_dict.get)
clusters_embed['body'] = clusters_embed.index.map(body_dict.get)


# Wrap the function body text to 50 characters
clusters_embed['body'] = clusters_embed['body'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)

print(clusters_embed.head())

clusters_embed = clusters_embed[:50_000]

import plotly.express as px

# Create a scatter plot using Plotly
fig = px.scatter(clusters_embed, 
                 x='x', 
                 y='y', 
                 color='cluster', 
                 title='Cluster Plot',
                 labels={'cluster': 'Cluster'},
                 )

# on hover show: cluster label, function name 
fig.update_traces(
    hovertemplate='<b>Cluster:</b> %{color} <br><b>Function:</b> %{customdata[0]} <br><b>Body:</b> %{customdata[1]}',
    customdata=[clusters_embed['function'], clusters_embed['body']]
)



# Show the plot
fig.show()

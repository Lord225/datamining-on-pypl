import logging
import common
from sqlalchemy import text
import ast
import pandas as pd
from dask import dataframe as dd 
from sqlalchemy.engine.url import make_url
from dask.diagnostics import ProgressBar # type: ignore

logging.basicConfig(level=logging.INFO)

ProgressBar().register()

conn = common.get_postgres()

class PythonCodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self.classes = []
    
    def visit_FunctionDef(self, node):
        function_info = {
            "name": node.name,
            "args": [arg.arg for arg in node.args.args], 
            "args_types": [ast.unparse(arg.annotation) for arg in node.args.args if arg.annotation],
            "args_defaults": [ast.unparse(default) for default in node.args.defaults],
            "body": ast.unparse(node.body),  # type: ignore
            "lineno": node.lineno
        }
        self.functions.append(function_info)
        self.generic_visit(node)
    


    def analyze(self, code):
        try:
            # remove null bytes
            if not isinstance(code, str):
                return
            
            code = code.replace('\x00', '')

            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError as e:
            logging.error(f"SyntaxError: {e}")

def analyze_python_code(code):    
    try:
        analyzer = PythonCodeAnalyzer()
        analyzer.analyze(code)
    
        return {
            "functions": analyzer.functions,
        }
    except Exception as e:
        logging.error(f"Error: {e}")
        return {
            "functions": [],
        }

if __name__ == '__main__':
    url = make_url(conn.engine.url)
    conn_str = f"postgresql://{url.username}:{url.password}@{url.host}:{url.port}/{url.database}"

    files = dd.read_sql_table('files',   # type: ignore
                              conn_str, 
                              index_col='id', 
                              bytes_per_chunk='100kb', 
                              # limits=(1000,1500)
                            )
    def analyze_code(row):
        code = row['content']
        result = analyze_python_code(code)
        result['file_id'] = row.name
        return pd.Series(result) 

    querry = files.map_partitions(lambda chunk: chunk.apply(analyze_code, axis=1))
    querry = querry.map_partitions(lambda chunk: chunk.explode('functions'))
    querry = querry.assign(
        repo=files['repo'],
    )
    
    querry = querry.dropna(subset=['functions'])
    
    querry = querry.assign(
        name=querry['functions'].apply(lambda x: x['name'], meta=('name', 'str')),
        args=querry['functions'].apply(lambda x: x['args'], meta=('args', 'str')),
        args_types=querry['functions'].apply(lambda x: x['args_types'], meta=('args_types', 'str')),
        args_defaults=querry['functions'].apply(lambda x: x['args_defaults'], meta=('args_defaults', 'str')),
        body=querry['functions'].apply(lambda x: x['body'], meta=('body', 'str')),
    ).drop(columns=['functions'])

    results = querry.compute(scheduler='processes', num_workers=16, optimize_graph=True)

    # set column max width
    # pd.set_option('display.max_colwidth', 1000)
    # pd.set_option('display.max_columns', None)
    # pd.set_option('display.width', 1000)
    # pd.set_option('display.max_rows', 10)
    # print(results[results['args_defaults'].apply(lambda x: len(x) > 0)][['args_defaults', 'args', 'args_types']])

    print('args_types are defined', results[results['args_types'].apply(lambda x: len(x) > 0)].shape)
    print('args_defaults are defined', results[~results['args_defaults'].apply(lambda x: len(x) > 0)].shape)
    print('total', results.shape)
    print('columns', results.columns)
    print('head', results.head())

    results.to_sql('functions', conn_str, if_exists='replace', index=False)

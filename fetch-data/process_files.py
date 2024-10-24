import chunk
from pathlib import Path
from zipfile import ZipFile, BadZipFile
import tqdm
import common
from sqlalchemy import text
import argparse
import ast
import pandas as pd
from dask import dataframe as dd 
import psycopg2
from sqlalchemy.engine.url import make_url
from dask.diagnostics import ProgressBar
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
            "body": ast.unparse(node.body),  
            "lineno": node.lineno
        }
        self.functions.append(function_info)
        self.generic_visit(node)
    
    # def visit_ClassDef(self, node):
    #     class_info = {
    #         "name": node.name,
    #         "methods": [],
    #         "lineno": node.lineno
    #     }
        
    #     for child in node.body:
    #         if isinstance(child, ast.FunctionDef):
    #             method_info = {
    #                 "name": child.name,
    #                 "args": [arg.arg for arg in child.args.args],
    #                 "body": ast.unparse(child.body),
    #                 "lineno": child.lineno
    #             }
    #             class_info["methods"].append(method_info)
        
    #     self.classes.append(class_info)
    #     self.generic_visit(node)


    def analyze(self, code):
        try:
            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError as e:
            print(f"SyntaxError: {e}")

def analyze_python_code(code):    
    try:
        analyzer = PythonCodeAnalyzer()
        analyzer.analyze(code)
    
        return {
            "functions": analyzer.functions,
        }
    except Exception as e:
        return {
            "functions": [],
        }

if __name__ == '__main__':
    url = make_url(conn.engine.url)
    conn_str = f"postgresql://{url.username}:{url.password}@{url.host}:{url.port}/{url.database}"

    files = dd.read_sql_table('files', conn_str, index_col='id', bytes_per_chunk='100kb') # type: ignore
    def analyze_code(row):
        code = row['content']
        result = analyze_python_code(code)
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
        body=querry['functions'].apply(lambda x: x['body'], meta=('body', 'str')),
    ).drop(columns=['functions'])

    results = querry.compute(
        scheduler='processes', num_workers=16, interleave=True, optimize_graph=True, resources={'processes': 16}
    )

    print(results.columns)    
    print(results)

    results.to_sql('functions', conn_str, if_exists='replace', index=False)

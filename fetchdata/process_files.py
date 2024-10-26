import logging
import common
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

import re

def extract_docstring(body):
    """
    Extract the first comment line as a pseudo-docstring or a traditional docstring if it exists.
    Return the modified function body without the pseudo-docstring or docstring and the extracted text.
    """
    try:
        # Check if there's a docstring in the AST
        tree = ast.parse(body)
        docstring = ast.get_docstring(tree)
        
        # If a docstring exists, remove it
        if docstring:
            for node in tree.body:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
                    tree.body.remove(node)
                    break
            body_without_docstring = ast.unparse(tree)
        else:
            # If no docstring, look for a first-line comment as a pseudo-docstring
            lines = body.splitlines()
            pseudo_docstring = None
            body_start = 0

            # Check if the first line is a comment
            if lines and re.match(r'^\s*#', lines[0]):
                pseudo_docstring = lines[0].lstrip('#').strip()  # Extract the comment text
                body_start = 1  # Start body after the first comment line
            
            # Join remaining lines to reconstruct the body without the first-line comment
            body_without_docstring = "\n".join(lines[body_start:]).strip()
            docstring = pseudo_docstring if pseudo_docstring else None
        body_without_docstring = body_without_docstring.replace('\x00', '')
        docstring = docstring.replace('\x00', '') if docstring else None

        return body_without_docstring, docstring
    except Exception as e:
        logging.error(f"Error extracting docstring: {e}")
        return body, None
        

if __name__ == '__main__':
    url = make_url(conn.engine.url)
    conn_str = f"postgresql://{url.username}:{url.password}@{url.host}:{url.port}/{url.database}"

    files = dd.read_sql_table('files',   # type: ignore
                              conn_str, 
                              index_col='id', 
                              bytes_per_chunk='100kb', 
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
        body_and_docstring=querry['functions'].apply(lambda x: extract_docstring(x['body']), meta=('body_and_docstring', 'object'))
    )

    querry = querry.assign(
        body=querry['body_and_docstring'].apply(lambda x: x[0] if x else None, meta=('body', 'str')),
        docstring=querry['body_and_docstring'].apply(lambda x: x[1] if x else None, meta=('docstring', 'str'))
    ).drop(columns=['functions', 'body_and_docstring'])

    querry = querry.drop_duplicates(subset=['body', 'name'])

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

import os
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv()


TOKEN = os.getenv("GITHUB_TOKEN")

def get_auth_headers():
    return {
        "Authorization": f"token {TOKEN}"
    }


def get_postgres():
    engine = sa.create_engine('postgresql://postgres:8W0MQwY4DINCoX@localhost:5432/data-mining')
    return engine.connect()
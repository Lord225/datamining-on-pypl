import os
from dotenv import load_dotenv

load_dotenv()


TOKEN = os.getenv("GITHUB_TOKEN")

def get_auth_headers():
    return {
        "Authorization": f"token {TOKEN}"
    }
import os
from pathlib import Path
from dotenv import load_dotenv
import pyTigerGraph as tg

# Project root
ROOT_DIR = Path(__file__).resolve().parent

# Load .env
env_file = ROOT_DIR / ".env"
print("ENV FILE =", env_file)
print("ENV EXISTS =", env_file.exists())

load_dotenv(env_file)

host = os.getenv("TG_HOST")
graph = os.getenv("TG_GRAPH")
user = os.getenv("TIGERGRAPH_USER")
password = os.getenv("TIGERGRAPH_PASSWORD")

print("HOST =", repr(host))
print("GRAPH =", repr(graph))
print("USER =", repr(user))
print("PASSWORD SET =", password is not None)

conn = tg.TigerGraphConnection(
    host=host,
    graphname=graph,
    username=user,
    password=password
)

print("Connected successfully!")
print(conn.getVertexCount("*"))
"""
test_falkordb_connection.py
Quick test to verify FalkorDB connection
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from falkordb import FalkorDB

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

HOST     = os.getenv("FALKORDB_HOST", "localhost")
PORT     = int(os.getenv("FALKORDB_PORT", 6379))
PASSWORD = os.getenv("FALKORDB_PASSWORD")          # can be None
USERNAME = os.getenv("FALKORDB_USERNAME")          # optional
GRAPH    = os.getenv("FALKORDB_GRAPH", "SocialGraph")

def main():
    print(f"Connecting to FalkorDB → {HOST}:{PORT}")
    
    try:
        db = FalkorDB(
            host=HOST,
            port=PORT,
            password=PASSWORD,
            username=USERNAME
        )
        g = db.select_graph(GRAPH)

        # Simple test query
        result = g.query("RETURN 'FalkorDB connection successful!' AS message")
        print(result.result_set[0][0])

        # Show existing graphs
        graphs = db.list_graphs()
        print(f"Existing graphs: {graphs}")

        print("\n Connection successful!")

    except Exception as e:
        print(f"\n Connection failed: {e}")

if __name__ == "__main__":
    main()
import os
import time
import csv
from pathlib import Path
from dotenv import load_dotenv
from pyTigerGraph import TigerGraphConnection

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

HOST = os.getenv("TG_HOST")
GRAPH = os.getenv("TG_GRAPH")
SECRET = os.getenv("TG_SECRET")

NODES_FILE = ROOT_DIR / "datasets" / "nodes.csv"
RELS_FILE  = ROOT_DIR / "datasets" / "relationships.csv"

BATCH_SIZE = 200   # TigerGraph handles larger batches well

def main():
    print("Connecting to TigerGraph...")
    conn = TigerGraphConnection(host=HOST, graphname=GRAPH, gsqlSecret=SECRET)
    conn.getToken(SECRET)
    print("✅ Connected\n")

# ---------- Create Schema ----------
    print("Creating schema...")

    # Drop the graph and types if they already exist
    drop_commands = f"""
    USE GLOBAL
    DROP GRAPH {GRAPH}
    DROP EDGE KNOWS
    DROP VERTEX User
    """

    try:
        print(conn.gsql(drop_commands))
    except Exception as e:
        print("Drop (expected if first time):", e)

    # Now create fresh
    schema = f"""
    USE GLOBAL
    CREATE VERTEX User (PRIMARY_ID id STRING) WITH primary_id_as_attribute="true"
    CREATE UNDIRECTED EDGE KNOWS (FROM User, TO User)
    CREATE GRAPH {GRAPH}(User, KNOWS)
    """

    result = conn.gsql(schema)
    print(result)
    print("Schema created.\n")

    # Switch to the new graph
    conn.graphname = GRAPH
    conn.getToken(SECRET)

    # ---------- Load Nodes ----------
    print("Loading nodes...")
    start_nodes = time.perf_counter()
    nodes_loaded = 0
    batch = []

    with open(NODES_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vid = row["id:ID"]
            batch.append((vid, {}))               # ← correct format: (id, attributes)
            if len(batch) >= BATCH_SIZE:
                conn.upsertVertices("User", batch)
                nodes_loaded += len(batch)
                print(f"  Nodes: {nodes_loaded:,}", end="\r")
                batch = []

        if batch:
            conn.upsertVertices("User", batch)
            nodes_loaded += len(batch)

    nodes_time = time.perf_counter() - start_nodes
    print(f"\nNodes loaded: {nodes_loaded:,} in {nodes_time:.2f}s")

    # ---------- Load Relationships ----------
    print("Loading relationships...")
    start_rels = time.perf_counter()
    rels_loaded = 0
    batch = []

    with open(RELS_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            batch.append((row[":START_ID"], row[":END_ID"], {}))
            if len(batch) >= BATCH_SIZE:
                conn.upsertEdges("User", "KNOWS", "User", batch)
                rels_loaded += len(batch)
                print(f"  Relationships: {rels_loaded:,}", end="\r")
                batch = []

        if batch:
            conn.upsertEdges("User", "KNOWS", "User", batch)
            rels_loaded += len(batch)

    rels_time = time.perf_counter() - start_rels
    total_time = nodes_time + rels_time

    print("\n\n========== INGEST RESULTS (TigerGraph) ==========")
    print(f"Nodes loaded        : {nodes_loaded:,}")
    print(f"Relationships loaded: {rels_loaded:,}")
    print(f"Total wall time     : {total_time:.2f} sec")
    print(f"Nodes / second      : {nodes_loaded / nodes_time:,.1f}")
    print(f"Rels / second       : {rels_loaded / rels_time:,.1f}")
    print("=================================================")
if __name__ == "__main__":
    main()
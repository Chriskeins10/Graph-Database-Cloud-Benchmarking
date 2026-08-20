"""
loaders/falkordb_loader.py
Load the same Pokec dataset into FalkorDB
"""

import os
import time
import csv
from pathlib import Path
from dotenv import load_dotenv
from falkordb import FalkorDB

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ====================== CONFIG ======================
HOST     = os.getenv("FALKORDB_HOST", "localhost")
PORT     = int(os.getenv("FALKORDB_PORT", 6379))
PASSWORD = os.getenv("FALKORDB_PASSWORD")
USERNAME = os.getenv("FALKORDB_USERNAME")
GRAPH    = os.getenv("FALKORDB_GRAPH", "SocialGraph")

NODES_CSV = ROOT_DIR / "datasets" / "nodes.csv"
RELS_CSV  = ROOT_DIR / "datasets" / "relationships.csv"

BATCH_SIZE = 200          # adjust if needed
# ====================================================


def get_graph():
    db = FalkorDB(
        host=HOST,
        port=PORT,
        password=PASSWORD,
        username=USERNAME
    )
    return db.select_graph(GRAPH)


def load_nodes(g):
    print("Loading nodes...")
    start = time.perf_counter()
    count = 0
    batch = []

    with open(NODES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Adjust column names if your CSV is different
            node_id = row.get("id") or row.get("node_id") or list(row.values())[0]
            batch.append({"id": int(node_id)})

            if len(batch) >= BATCH_SIZE:
                g.query(
                    """
                    UNWIND $batch AS row
                    CREATE (n:User {id: row.id})
                    """,
                    {"batch": batch}
                )
                count += len(batch)
                print(f"  Nodes: {count:,}", end="\r")
                batch = []

        # remaining
        if batch:
            g.query(
                """
                UNWIND $batch AS row
                CREATE (n:User {id: row.id})
                """,
                {"batch": batch}
            )
            count += len(batch)

    elapsed = time.perf_counter() - start
    print(f"\nNodes loaded: {count:,} in {elapsed:.2f}s")
    return count, elapsed


def load_relationships(g):
    print("Loading relationships...")
    start = time.perf_counter()
    count = 0
    batch = []

    with open(RELS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Adjust column names according to your relationships.csv
            src = row.get("start") or row.get("source") or row.get("from") or list(row.values())[0]
            dst = row.get("end")   or row.get("target") or row.get("to")   or list(row.values())[1]
            batch.append({"src": int(src), "dst": int(dst)})

            if len(batch) >= BATCH_SIZE:
                g.query(
                    """
                    UNWIND $batch AS row
                    MATCH (a:User {id: row.src}), (b:User {id: row.dst})
                    CREATE (a)-[:KNOWS]->(b)
                    """,
                    {"batch": batch}
                )
                count += len(batch)
                print(f"  Relationships: {count:,}", end="\r")
                batch = []

        if batch:
            g.query(
                """
                UNWIND $batch AS row
                MATCH (a:User {id: row.src}), (b:User {id: row.dst})
                CREATE (a)-[:KNOWS]->(b)
                """,
                {"batch": batch}
            )
            count += len(batch)

    elapsed = time.perf_counter() - start
    print(f"\nRelationships loaded: {count:,} in {elapsed:.2f}s")
    return count, elapsed


def main():
    print(f"Connecting to FalkorDB → {HOST}:{PORT}")
    g = get_graph()

    # Optional: clear existing graph
    try:
        g.delete()
        print("Old graph deleted.")
    except Exception:
        pass

    g = get_graph()   # re-select after delete

    # Create index for faster lookups
    print("Creating index on User.id ...")
    g.query("CREATE INDEX FOR (u:User) ON (u.id)")

    total_start = time.perf_counter()

    nodes_count, nodes_time = load_nodes(g)
    rels_count, rels_time = load_relationships(g)

    total_time = time.perf_counter() - total_start

    print("\n========== INGEST RESULTS (FalkorDB) ==========")
    print(f"Nodes loaded       : {nodes_count:,}")
    print(f"Relationships loaded: {rels_count:,}")
    print(f"Total wall time    : {total_time:.2f} sec")
    print(f"Nodes / second     : {nodes_count / nodes_time:,.1f}")
    print(f"Rels / second      : {rels_count / rels_time:,.1f}")
    print("================================================")


if __name__ == "__main__":
    main()
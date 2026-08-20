import os
import time
import csv
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ========== CONFIG (Memgraph Cloud) ==========
URI = os.getenv("MEMGRAPH_URI")
USER = os.getenv("MEMGRAPH_USER")
PASSWORD = os.getenv("MEMGRAPH_PASSWORD")

NODES_FILE = ROOT_DIR / "datasets" / "nodes.csv"
RELS_FILE  = ROOT_DIR / "datasets" / "relationships.csv"

BATCH_SIZE = 200

def get_session(driver):
    return driver.session()

def load_data():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD), max_connection_lifetime=300)

    # ---------- Clear + Index ----------
    with get_session(driver) as session:
        print("Clearing existing data...")
        session.run("MATCH (n) DETACH DELETE n")
        print("Creating index...")
        session.run("CREATE INDEX ON :User(id)")

    # ---------- Load Nodes ----------
    print("Loading nodes...")
    start_nodes = time.perf_counter()
    nodes_loaded = 0

    with open(NODES_FILE, "r") as f:
        reader = csv.DictReader(f)
        batch = []

        for row in reader:
            batch.append(row["id:ID"])
            if len(batch) >= BATCH_SIZE:
                with get_session(driver) as session:
                    session.run("UNWIND $batch AS id CREATE (n:User {id: id})", batch=batch)
                nodes_loaded += len(batch)
                print(f"  Nodes: {nodes_loaded:,}", end="\r")
                batch = []

        if batch:
            with get_session(driver) as session:
                session.run("UNWIND $batch AS id CREATE (n:User {id: id})", batch=batch)
            nodes_loaded += len(batch)

    nodes_time = time.perf_counter() - start_nodes
    print(f"\nNodes loaded: {nodes_loaded:,} in {nodes_time:.2f}s")

    # ---------- Load Relationships ----------
    print("Loading relationships...")
    start_rels = time.perf_counter()
    rels_loaded = 0

    with open(RELS_FILE, "r") as f:
        reader = csv.DictReader(f)
        batch = []

        for row in reader:
            batch.append({
                "source": row[":START_ID"],
                "target": row[":END_ID"]
            })

            if len(batch) >= BATCH_SIZE:
                success = False
                for attempt in range(3):
                    try:
                        with get_session(driver) as session:
                            session.run("""
                                UNWIND $batch AS row
                                MATCH (a:User {id: row.source})
                                MATCH (b:User {id: row.target})
                                CREATE (a)-[:KNOWS]->(b)
                            """, batch=batch)
                        success = True
                        break
                    except ServiceUnavailable:
                        print(f"\n  Connection lost. Retrying... (attempt {attempt+1})")
                        time.sleep(2)
                        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

                if not success:
                    print("Failed after retries. Stopping.")
                    break

                rels_loaded += len(batch)
                print(f"  Relationships: {rels_loaded:,}", end="\r")
                batch = []

        if batch:
            with get_session(driver) as session:
                session.run("""
                    UNWIND $batch AS row
                    MATCH (a:User {id: row.source})
                    MATCH (b:User {id: row.target})
                    CREATE (a)-[:KNOWS]->(b)
                """, batch=batch)
            rels_loaded += len(batch)

    rels_time = time.perf_counter() - start_rels
    total_time = nodes_time + rels_time

    print("\n\n========== INGEST RESULTS (Memgraph Cloud) ==========")
    print(f"Nodes loaded        : {nodes_loaded:,}")
    print(f"Relationships loaded: {rels_loaded:,}")
    print(f"Total wall time     : {total_time:.2f} sec")
    print(f"Nodes / second      : {nodes_loaded / nodes_time:,.1f}")
    print(f"Rels / second       : {rels_loaded / rels_time:,.1f}")
    print("=====================================================")

    driver.close()

if __name__ == "__main__":
    load_data()
"""
workloads/falkordb/falkordb_aggregations.py
Aggregation queries on FalkorDB
"""

import os
import time
import statistics
from pathlib import Path
from dotenv import load_dotenv
from falkordb import FalkorDB

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

HOST     = os.getenv("FALKORDB_HOST", "localhost")
PORT     = int(os.getenv("FALKORDB_PORT", 6379))
PASSWORD = os.getenv("FALKORDB_PASSWORD")
USERNAME = os.getenv("FALKORDB_USERNAME")
GRAPH    = os.getenv("FALKORDB_GRAPH", "SocialGraph")

ITERATIONS = 80
WARMUP     = 10


def get_graph():
    db = FalkorDB(host=HOST, port=PORT, password=PASSWORD, username=USERNAME)
    return db.select_graph(GRAPH)


def run_query(g, query):
    start = time.perf_counter()
    g.query(query)
    return (time.perf_counter() - start) * 1000


def percentile(data, p):
    if len(data) < 2:
        return data[0] if data else 0.0
    return statistics.quantiles(data, n=100)[p - 1]


def main():
    g = get_graph()
    print(f"Connected to FalkorDB → {HOST}:{PORT} | Graph: {GRAPH}\n")

    queries = {
        "Count all nodes": "MATCH (n:User) RETURN count(n)",
        
        "Count all relationships": "MATCH ()-[r:KNOWS]->() RETURN count(r)",
        
        "Group by degree (top 10)": """
            MATCH (n:User)-[r:KNOWS]->()
            WITH n, count(r) AS degree
            RETURN n.id AS id, degree
            ORDER BY degree DESC
            LIMIT 10
        """
    }

    results = {}

    for name, query in queries.items():
        print(f"Running: {name}...")
        latencies = []

        for _ in range(WARMUP):
            run_query(g, query)

        for _ in range(ITERATIONS):
            latency = run_query(g, query)
            latencies.append(latency)

        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)
        results[name] = {"p50": p50, "p95": p95}
        print(f"  → p50: {p50:.2f} ms | p95: {p95:.2f} ms")

    print("\n========== AGGREGATION RESULTS (FalkorDB) ==========")
    for name, res in results.items():
        print(f"{name:30} | p50: {res['p50']:7.2f} ms | p95: {res['p95']:7.2f} ms")
    print("====================================================")


if __name__ == "__main__":
    main()
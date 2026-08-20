"""
workloads/falkordb/falkordb_traversals.py
"""

import os
import time
import random
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

ITERATIONS = 120
WARMUP     = 20


def get_graph():
    db = FalkorDB(host=HOST, port=PORT, password=PASSWORD, username=USERNAME)
    return db.select_graph(GRAPH)


def get_random_node_ids(g, count=200):
    result = g.query(
        "MATCH (n:User) RETURN n.id AS id LIMIT $count",
        {"count": count}
    )
    return [row[0] for row in result.result_set]


def run_query(g, query, params):
    start = time.perf_counter()
    g.query(query, params)
    return (time.perf_counter() - start) * 1000


def percentile(data, p):
    if len(data) < 2:
        return data[0] if data else 0.0
    return statistics.quantiles(data, n=100)[p - 1]


def main():
    g = get_graph()
    print(f"Connected to FalkorDB → {HOST}:{PORT} | Graph: {GRAPH}")
    print("Collecting random start nodes...")

    node_ids = get_random_node_ids(g)
    print(f"Got {len(node_ids)} nodes\n")

    queries = {
        "1-hop": """
            MATCH (n:User {id: $id})-[:KNOWS]->(m)
            RETURN count(m)
        """,
        "2-hop": """
            MATCH (n:User {id: $id})-[:KNOWS*2]->(m)
            RETURN count(m)
        """,
        "3-hop": """
            MATCH (n:User {id: $id})-[:KNOWS*3]->(m)
            RETURN count(m)
        """
    }

    results = {}

    for name, query in queries.items():
        print(f"Running {name} queries...")
        latencies = []

        for _ in range(WARMUP):
            run_query(g, query, {"id": random.choice(node_ids)})

        for _ in range(ITERATIONS):
            latency = run_query(g, query, {"id": random.choice(node_ids)})
            latencies.append(latency)

        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)
        results[name] = {"p50": p50, "p95": p95}
        print(f"  {name} → p50: {p50:.2f} ms | p95: {p95:.2f} ms")

    print("\n========== TRAVERSAL RESULTS (FalkorDB) ==========")
    for name, res in results.items():
        print(f"{name:6} | p50: {res['p50']:7.2f} ms | p95: {res['p95']:7.2f} ms")
    print("==================================================")


if __name__ == "__main__":
    main()
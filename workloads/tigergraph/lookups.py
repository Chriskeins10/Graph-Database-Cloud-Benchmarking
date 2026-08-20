"""
workloads/tigergraph/tigergraph_lookups.py
Point Lookup + Filtered Lookup latency on TigerGraph
"""

import os
import time
import random
import statistics
from pathlib import Path
from dotenv import load_dotenv
import pyTigerGraph as tg

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

# ====================== CONFIG ======================
HOST        = os.getenv("TG_HOST")
GRAPH       = os.getenv("TG_GRAPH", "SocialGraph")
USERNAME    = os.getenv("TIGERGRAPH_USER", "tigergraph")
PASSWORD    = os.getenv("TIGERGRAPH_PASSWORD")
SECRET      = os.getenv("TG_SECRET")

VERTEX_TYPE = "User"      # ← change if needed
ID_ATTR     = "id"        # ← change if needed

ITERATIONS = 120
WARMUP     = 20
# ====================================================


def get_connection():
    conn = tg.TigerGraphConnection(
        host=HOST,
        graphname=GRAPH,
        username=USERNAME,
        password=PASSWORD,
    )
    if SECRET:
        token = conn.getToken(SECRET)[0]
        conn.apiToken = token
    return conn


def get_random_node_ids(conn, count=300):
    vertices = conn.getVertices(VERTEX_TYPE, limit=count)
    ids = []
    for v in vertices:
        if ID_ATTR in v:
            ids.append(v[ID_ATTR])
        elif "v_id" in v:
            ids.append(v["v_id"])
        elif "id" in v:
            ids.append(v["id"])
        else:
            ids.append(list(v.values())[0])
    return ids


def run_query(conn, query: str) -> float:
    start = time.perf_counter()
    conn.gsql(query)
    return (time.perf_counter() - start) * 1000


def percentile(data, p):
    if len(data) < 2:
        return data[0] if data else 0.0
    return statistics.quantiles(data, n=100)[p - 1]


def main():
    conn = get_connection()
    print(f"Connected to {HOST} | Graph: {GRAPH}")
    print("Collecting random node IDs...")

    node_ids = get_random_node_ids(conn, count=300)
    print(f"Got {len(node_ids)} nodes\n")

    if not node_ids:
        print("ERROR: No vertices found.")
        return

    results = {}

    # ---------- Point Lookup ----------
    print("Running Point Lookup...")
    latencies = []

    for i in range(WARMUP + ITERATIONS):
        nid = random.choice(node_ids)

        query = f"""
        USE GRAPH {GRAPH}
        INTERPRET QUERY () {{
          result = SELECT s FROM {VERTEX_TYPE}:s WHERE s.{ID_ATTR} == {nid};
          PRINT result;
        }}
        """

        latency = run_query(conn, query)
        if i >= WARMUP:
            latencies.append(latency)

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    results["Point Lookup"] = {"p50": p50, "p95": p95}
    print(f"  Point Lookup → p50: {p50:.2f} ms | p95: {p95:.2f} ms")

    # ---------- Filtered Lookup ----------
    print("Running Filtered Lookup...")
    latencies = []

    for i in range(WARMUP + ITERATIONS):
        # Take first 2 characters of a random id as prefix
        prefix = str(random.choice(node_ids))[:2]

        query = f"""
        USE GRAPH {GRAPH}
        INTERPRET QUERY () {{
          result = SELECT s FROM {VERTEX_TYPE}:s 
                   WHERE to_string(s.{ID_ATTR}) LIKE "{prefix}%";
          PRINT result.size() AS cnt;
        }}
        """

        latency = run_query(conn, query)
        if i >= WARMUP:
            latencies.append(latency)

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    results["Filtered Lookup"] = {"p50": p50, "p95": p95}
    print(f"  Filtered Lookup → p50: {p50:.2f} ms | p95: {p95:.2f} ms")

    # ---------- Results ----------
    print("\n========== LOOKUP RESULTS (TigerGraph) ==========")
    for name, res in results.items():
        print(f"{name:18} | p50: {res['p50']:7.2f} ms | p95: {res['p95']:7.2f} ms")
    print("=================================================")
    print(f"Indexed property: {VERTEX_TYPE}.{ID_ATTR}")


if __name__ == "__main__":
    main()
"""
workloads/tigergraph/tigergraph_aggregations.py
Aggregation queries latency on TigerGraph
"""

import os
import time
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
EDGE_TYPE   = "KNOWS"     # ← change if needed
ID_ATTR     = "id"        # ← change if needed

ITERATIONS = 80
WARMUP     = 10
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
    print(f"Connected to {HOST} | Graph: {GRAPH}\n")

    queries = {
        "Count all nodes": f"""
            USE GRAPH {GRAPH}
            INTERPRET QUERY () {{
              result = SELECT s FROM {VERTEX_TYPE}:s;
              PRINT result.size() AS cnt;
            }}
        """,

        "Count all relationships": f"""
            USE GRAPH {GRAPH}
            INTERPRET QUERY () {{
              result = SELECT s FROM {VERTEX_TYPE}:s -({EDGE_TYPE}:e)- {VERTEX_TYPE}:t;
              PRINT result.size() AS cnt;
            }}
        """,

        "Group by degree (top 10)": f"""
            USE GRAPH {GRAPH}
            INTERPRET QUERY () {{
              result = SELECT s FROM {VERTEX_TYPE}:s -({EDGE_TYPE}:e)- {VERTEX_TYPE}:t
                       ACCUM s.@degree += 1
                       ORDER BY s.@degree DESC
                       LIMIT 10;
              PRINT result[ID_ATTR], result.@degree;
            }}
        """
    }

    # Note: The "Group by degree" query uses an accumulator.
    # If your TigerGraph version complains about @degree,
    # we can switch to a simpler version.

    results = {}

    for name, query in queries.items():
        print(f"Running: {name}...")
        latencies = []

        for i in range(WARMUP + ITERATIONS):
            latency = run_query(conn, query)
            if i >= WARMUP:
                latencies.append(latency)

        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)
        results[name] = {"p50": p50, "p95": p95}
        print(f"  → p50: {p50:.2f} ms | p95: {p95:.2f} ms")

    print("\n========== AGGREGATION RESULTS (TigerGraph) ==========")
    for name, res in results.items():
        print(f"{name:30} | p50: {res['p50']:7.2f} ms | p95: {res['p95']:7.2f} ms")
    print("=====================================================")


if __name__ == "__main__":
    main()
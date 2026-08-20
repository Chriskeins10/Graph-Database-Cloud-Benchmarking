"""
workloads/tigergraph_traversals.py
1-hop / 2-hop / 3-hop latency benchmark on TigerGraph
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

# Change these two if your schema uses different names
VERTEX_TYPE = "User"        # or "Person"
EDGE_TYPE   = "KNOWS"       # or "FRIEND"
ID_ATTR     = "id"          # the attribute that stores the node id

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


def get_random_node_ids(conn, count=200):
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
    conn.gsql(query)          # more reliable than runInterpretedQuery on some versions
    return (time.perf_counter() - start) * 1000


def percentile(data, p):
    if len(data) < 2:
        return data[0] if data else 0.0
    return statistics.quantiles(data, n=100)[p - 1]


def main():
    conn = get_connection()
    print(f"Connected to {HOST} | Graph: {GRAPH}")
    print("Collecting random start nodes...")

    node_ids = get_random_node_ids(conn, count=200)
    print(f"Got {len(node_ids)} nodes\n")

    if not node_ids:
        print("ERROR: No vertices found. Check VERTEX_TYPE.")
        return

    results = {}

    for hop in [1, 2, 3]:
        name = f"{hop}-hop"
        print(f"Running {name} ...")
        latencies = []

        for i in range(WARMUP + ITERATIONS):
            nid = random.choice(node_ids)

            if hop == 1:
                query = f"""
                USE GRAPH {GRAPH}
                INTERPRET QUERY () {{
                  start = SELECT s FROM {VERTEX_TYPE}:s WHERE s.{ID_ATTR} == {nid};
                  result = SELECT t FROM start:s -({EDGE_TYPE}:e)- {VERTEX_TYPE}:t;
                  PRINT result.size() AS cnt;
                }}
                """
            elif hop == 2:
                query = f"""
                USE GRAPH {GRAPH}
                INTERPRET QUERY () {{
                  start = SELECT s FROM {VERTEX_TYPE}:s WHERE s.{ID_ATTR} == {nid};
                  mid   = SELECT m FROM start:s -({EDGE_TYPE}:e)- {VERTEX_TYPE}:m;
                  result = SELECT t FROM mid:m -({EDGE_TYPE}:e)- {VERTEX_TYPE}:t;
                  PRINT result.size() AS cnt;
                }}
                """
            else:  # 3-hop
                query = f"""
                USE GRAPH {GRAPH}
                INTERPRET QUERY () {{
                  start = SELECT s FROM {VERTEX_TYPE}:s WHERE s.{ID_ATTR} == {nid};
                  mid1  = SELECT m FROM start:s -({EDGE_TYPE}:e)- {VERTEX_TYPE}:m;
                  mid2  = SELECT m FROM mid1:m -({EDGE_TYPE}:e)- {VERTEX_TYPE}:m;
                  result = SELECT t FROM mid2:m -({EDGE_TYPE}:e)- {VERTEX_TYPE}:t;
                  PRINT result.size() AS cnt;
                }}
                """

            latency = run_query(conn, query)

            if i >= WARMUP:
                latencies.append(latency)

        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)
        results[name] = {"p50": p50, "p95": p95}
        print(f"  {name} → p50: {p50:.2f} ms | p95: {p95:.2f} ms")

    print("\n========== TRAVERSAL RESULTS (TigerGraph) ==========")
    for name, res in results.items():
        print(f"{name:6} | p50: {res['p50']:7.2f} ms | p95: {res['p95']:7.2f} ms")
    print("====================================================")


if __name__ == "__main__":
    main()
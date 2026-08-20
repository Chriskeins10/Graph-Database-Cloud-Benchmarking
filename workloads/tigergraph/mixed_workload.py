"""
workloads/tigergraph/tigergraph_mixed_workload.py
Concurrent Read/Write mixed workload on TigerGraph
"""

import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv
import pyTigerGraph as tg
from concurrent.futures import ThreadPoolExecutor, as_completed

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

CONCURRENCY = 10          # Number of concurrent clients
DURATION_SEC = 30         # How long to run the test
READ_RATIO = 0.8          # 80% reads, 20% writes
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


def worker(node_ids, stop_time, stats):
    """Each worker gets its own connection."""
    conn = get_connection()
    reads = 0
    writes = 0

    while time.time() < stop_time:
        if random.random() < READ_RATIO:
            # Read: 1-hop count
            nid = random.choice(node_ids)
            query = f"""
            USE GRAPH {GRAPH}
            INTERPRET QUERY () {{
              start = SELECT s FROM {VERTEX_TYPE}:s WHERE s.{ID_ATTR} == {nid};
              result = SELECT t FROM start:s -({EDGE_TYPE}:e)- {VERTEX_TYPE}:t;
              PRINT result.size() AS cnt;
            }}
            """
            conn.gsql(query)
            reads += 1
        else:
            # Write: create a relationship between two random nodes
            id1 = random.choice(node_ids)
            id2 = random.choice(node_ids)
            if id1 == id2:
                continue

            # Using upsertEdge (safer and faster than raw GSQL for writes)
            try:
                conn.upsertEdge(VERTEX_TYPE, id1, EDGE_TYPE, VERTEX_TYPE, id2)
                writes += 1
            except Exception:
                # fallback to GSQL if upsertEdge fails
                query = f"""
                USE GRAPH {GRAPH}
                INTERPRET QUERY () {{
                  a = SELECT s FROM {VERTEX_TYPE}:s WHERE s.{ID_ATTR} == {id1};
                  b = SELECT t FROM {VERTEX_TYPE}:t WHERE t.{ID_ATTR} == {id2};
                  INSERT INTO {EDGE_TYPE} (FROM, TO) VALUES (a, b);
                }}
                """
                conn.gsql(query)
                writes += 1

    stats.append((reads, writes))


def main():
    print(f"Running mixed workload on TigerGraph...")
    print(f"Concurrency : {CONCURRENCY}")
    print(f"Duration    : {DURATION_SEC} seconds")
    print(f"Read ratio  : {int(READ_RATIO*100)}% reads / {int((1-READ_RATIO)*100)}% writes\n")

    # Pre-fetch node IDs once
    conn = get_connection()
    node_ids = get_random_node_ids(conn, count=300)
    print(f"Using {len(node_ids)} random nodes for the test\n")

    if not node_ids:
        print("ERROR: No nodes found.")
        return

    stats = []
    stop_time = time.time() + DURATION_SEC
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [
            executor.submit(worker, node_ids, stop_time, stats)
            for _ in range(CONCURRENCY)
        ]
        for f in as_completed(futures):
            f.result()

    total_time = time.perf_counter() - start

    total_reads = sum(r for r, w in stats)
    total_writes = sum(w for r, w in stats)
    total_queries = total_reads + total_writes
    qps = total_queries / total_time if total_time > 0 else 0

    print("========== MIXED WORKLOAD RESULTS (TigerGraph) ==========")
    print(f"Total queries     : {total_queries:,}")
    print(f"  Reads           : {total_reads:,}")
    print(f"  Writes          : {total_writes:,}")
    print(f"Duration          : {total_time:.2f} sec")
    print(f"Throughput        : {qps:.1f} queries/sec")
    print(f"Concurrency       : {CONCURRENCY}")
    print("=========================================================")


if __name__ == "__main__":
    main()
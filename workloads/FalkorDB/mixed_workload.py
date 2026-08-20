"""
workloads/falkordb/falkordb_mixed_workload.py
Concurrent Read/Write mixed workload on FalkorDB
"""

import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv
from falkordb import FalkorDB
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

HOST     = os.getenv("FALKORDB_HOST", "localhost")
PORT     = int(os.getenv("FALKORDB_PORT", 6379))
PASSWORD = os.getenv("FALKORDB_PASSWORD")
USERNAME = os.getenv("FALKORDB_USERNAME")
GRAPH    = os.getenv("FALKORDB_GRAPH", "SocialGraph")

CONCURRENCY  = 10
DURATION_SEC = 30
READ_RATIO   = 0.8


def get_graph():
    db = FalkorDB(host=HOST, port=PORT, password=PASSWORD, username=USERNAME)
    return db.select_graph(GRAPH)


def get_random_node_ids(g, count=200):
    result = g.query(
        "MATCH (n:User) RETURN n.id AS id LIMIT $count",
        {"count": count}
    )
    return [row[0] for row in result.result_set]


def worker(node_ids, stop_time, stats):
    """Each worker creates its own connection."""
    g = get_graph()
    reads = 0
    writes = 0

    while time.time() < stop_time:
        if random.random() < READ_RATIO:
            # Read: 1-hop count
            nid = random.choice(node_ids)
            g.query(
                "MATCH (n:User {id: $id})-[:KNOWS]->(m) RETURN count(m)",
                {"id": nid}
            )
            reads += 1
        else:
            # Write: create a relationship
            id1 = random.choice(node_ids)
            id2 = random.choice(node_ids)
            if id1 == id2:
                continue
            g.query(
                """
                MATCH (a:User {id: $id1}), (b:User {id: $id2})
                CREATE (a)-[:KNOWS]->(b)
                """,
                {"id1": id1, "id2": id2}
            )
            writes += 1

    stats.append((reads, writes))


def main():
    print(f"Running mixed workload on FalkorDB...")
    print(f"Concurrency : {CONCURRENCY}")
    print(f"Duration    : {DURATION_SEC} seconds")
    print(f"Read ratio  : {int(READ_RATIO*100)}% reads / {int((1-READ_RATIO)*100)}% writes\n")

    # Pre-fetch node IDs
    g = get_graph()
    node_ids = get_random_node_ids(g, count=300)
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

    total_reads  = sum(r for r, w in stats)
    total_writes = sum(w for r, w in stats)
    total_queries = total_reads + total_writes
    qps = total_queries / total_time if total_time > 0 else 0

    print("========== MIXED WORKLOAD RESULTS (FalkorDB) ==========")
    print(f"Total queries     : {total_queries:,}")
    print(f"  Reads           : {total_reads:,}")
    print(f"  Writes          : {total_writes:,}")
    print(f"Duration          : {total_time:.2f} sec")
    print(f"Throughput        : {qps:.1f} queries/sec")
    print(f"Concurrency       : {CONCURRENCY}")
    print("=======================================================")


if __name__ == "__main__":
    main()
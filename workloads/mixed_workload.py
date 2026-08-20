import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# PATH / ENVIRONMENT
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ------------------------------------------------------------
# Select database
# ------------------------------------------------------------

# CognoDB
URI = os.getenv("COGNODB_URI")
USER = "cognodb"
PASSWORD = os.getenv("COGNODB_PASSWORD")

# Neo4j AuraDB
# URI = os.getenv("NEO4J_URI")
# USER = os.getenv("NEO4J_USER")
# PASSWORD = os.getenv("NEO4J_PASSWORD")

# # Memgraph
# URI = os.getenv("MEMGRAPH_URI")
# USER = os.getenv("MEMGRAPH_USER")
# PASSWORD = os.getenv("MEMGRAPH_PASSWORD")


# ============================================================
# CONFIGURATION
# ============================================================

CONCURRENCY = 10
DURATION_SEC = 30

# Target workload mix
READ_RATIO = 0.80

# Number of node IDs loaded once before benchmark
NODE_POOL_SIZE = 10_000


# ============================================================
# GET NODE IDS
# ============================================================

def get_node_ids(driver, limit=NODE_POOL_SIZE):
    """
    Fetch node IDs once before the benchmark starts.

    This query is NOT included in the workload timing.
    """

    with driver.session() as session:
        result = session.run(
            """
            MATCH (n:User)
            RETURN n.id AS id
            LIMIT $limit
            """,
            limit=limit
        )

        node_ids = [record["id"] for record in result]

    if not node_ids:
        raise RuntimeError("No User nodes found in the database.")

    print(f"Node IDs collected : {len(node_ids):,}")

    return node_ids


# ============================================================
# WORKER
# ============================================================

def worker(driver, stop_time, node_ids, stats):
    """
    Execute the mixed read/write workload.

    Each worker gets its own Neo4j session.
    """

    reads = 0
    writes = 0

    with driver.session() as session:

        while time.perf_counter() < stop_time:

            # ------------------------------------------------
            # READ
            # ------------------------------------------------

            if random.random() < READ_RATIO:

                node_id = random.choice(node_ids)

                session.run(
                    """
                    MATCH (n:User {id: $id})-[:KNOWS]->(m)
                    RETURN count(m)
                    """,
                    id=node_id
                ).consume()

                reads += 1

            # ------------------------------------------------
            # WRITE
            # ------------------------------------------------

            else:

                id1, id2 = random.sample(node_ids, 2)

                session.run(
                    """
                    MATCH (a:User {id: $id1}),
                          (b:User {id: $id2})
                    CREATE (a)-[:KNOWS]->(b)
                    """,
                    id1=id1,
                    id2=id2
                ).consume()

                writes += 1

    stats.append((reads, writes))


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("MIXED WORKLOAD BENCHMARK")
    print("=" * 60)

    print(f"Concurrency       : {CONCURRENCY}")
    print(f"Target duration   : {DURATION_SEC} seconds")
    print(
        f"Target read/write : "
        f"{READ_RATIO:.0%} / {(1 - READ_RATIO):.0%}"
    )
    print(f"Node pool size    : {NODE_POOL_SIZE:,}")
    print()

    # --------------------------------------------------------
    # CONNECT
    # --------------------------------------------------------

    if not URI:
        raise RuntimeError("Database URI is not configured.")

    if not USER:
        raise RuntimeError("Database username is not configured.")

    if not PASSWORD:
        raise RuntimeError("Database password is not configured.")

    driver = GraphDatabase.driver(
        URI,
        auth=(USER, PASSWORD)
    )

    try:

        # ----------------------------------------------------
        # CONNECTION TEST
        # ----------------------------------------------------

        driver.verify_connectivity()

        print("Database connection : OK")
        print()

        # ----------------------------------------------------
        # COLLECT NODE IDs BEFORE TIMING
        # ----------------------------------------------------

        node_ids = get_node_ids(
            driver,
            NODE_POOL_SIZE
        )

        print()

        # ----------------------------------------------------
        # WARM-UP
        # ----------------------------------------------------

        print("Running warm-up...")

        with driver.session() as session:

            for _ in range(20):

                node_id = random.choice(node_ids)

                session.run(
                    """
                    MATCH (n:User {id: $id})-[:KNOWS]->(m)
                    RETURN count(m)
                    """,
                    id=node_id
                ).consume()

        print("Warm-up completed.")
        print()

        # ----------------------------------------------------
        # BENCHMARK
        # ----------------------------------------------------

        stats = []

        benchmark_start = time.perf_counter()

        stop_time = benchmark_start + DURATION_SEC

        with ThreadPoolExecutor(
            max_workers=CONCURRENCY
        ) as executor:

            futures = [
                executor.submit(
                    worker,
                    driver,
                    stop_time,
                    node_ids,
                    stats
                )
                for _ in range(CONCURRENCY)
            ]

            for future in as_completed(futures):
                future.result()

        total_time = time.perf_counter() - benchmark_start

        # ----------------------------------------------------
        # RESULTS
        # ----------------------------------------------------

        total_reads = sum(
            reads for reads, writes in stats
        )

        total_writes = sum(
            writes for reads, writes in stats
        )

        total_queries = total_reads + total_writes

        if total_queries == 0:
            raise RuntimeError(
                "No queries were executed."
            )

        throughput = total_queries / total_time

        actual_read_ratio = (
            total_reads / total_queries
        )

        actual_write_ratio = (
            total_writes / total_queries
        )

        # ----------------------------------------------------
        # PRINT RESULTS
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("MIXED WORKLOAD RESULTS")
        print("=" * 60)

        print(
            f"Total queries       : {total_queries:,}"
        )

        print(
            f"  Reads             : {total_reads:,}"
        )

        print(
            f"  Writes            : {total_writes:,}"
        )

        print(
            f"Actual read ratio   : {actual_read_ratio:.2%}"
        )

        print(
            f"Actual write ratio  : {actual_write_ratio:.2%}"
        )

        print(
            f"Target duration     : {DURATION_SEC:.2f} sec"
        )

        print(
            f"Actual duration     : {total_time:.2f} sec"
        )

        print(
            f"Throughput          : {throughput:.2f} queries/sec"
        )

        print(
            f"Concurrency         : {CONCURRENCY}"
        )

        print("=" * 60)

    finally:

        driver.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
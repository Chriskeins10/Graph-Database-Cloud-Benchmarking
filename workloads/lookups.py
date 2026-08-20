import os
import time
import random
import statistics
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# URI = os.getenv("COGNODB_URI")
# USER = "cognodb"
# PASSWORD = os.getenv("COGNODB_PASSWORD")

# URI = os.getenv("NEO4J_URI")
# USER = os.getenv("NEO4J_USER")
# PASSWORD = os.getenv("NEO4J_PASSWORD")

URI = os.getenv("MEMGRAPH_URI")
USER = os.getenv("MEMGRAPH_USER")
PASSWORD = os.getenv("MEMGRAPH_PASSWORD")

ITERATIONS = 120
WARMUP = 20

def get_random_node_ids(session, count=300):
    result = session.run("MATCH (n:User) RETURN n.id AS id LIMIT $count", count=count)
    return [record["id"] for record in result]

def run_query(session, query, params=None):
    start = time.perf_counter()
    session.run(query, params or {}).consume()
    return (time.perf_counter() - start) * 1000  # ms

def percentile(data, p):
    return statistics.quantiles(data, n=100)[p-1]

def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    with driver.session() as session:
        print("Collecting random node IDs...")
        node_ids = get_random_node_ids(session)
        print(f"Got {len(node_ids)} nodes\n")

        # Make sure index exists
        session.run("CREATE INDEX user_id IF NOT EXISTS FOR (u:User) ON (u.id)")

        queries = {
            "Point Lookup": {
                "query": "MATCH (n:User {id: $id}) RETURN n",
                "params": lambda: {"id": random.choice(node_ids)}
            },
            "Filtered Lookup": {
                "query": "MATCH (n:User) WHERE n.id STARTS WITH $prefix RETURN count(n)",
                "params": lambda: {"prefix": str(random.choice(node_ids))[:2]}
            }
        }

        results = {}

        for name, item in queries.items():
            print(f"Running {name}...")
            latencies = []

            # Warm-up
            for _ in range(WARMUP):
                run_query(session, item["query"], item["params"]())

            # Measurements
            for _ in range(ITERATIONS):
                latency = run_query(session, item["query"], item["params"]())
                latencies.append(latency)

            p50 = percentile(latencies, 50)
            p95 = percentile(latencies, 95)
            results[name] = {"p50": p50, "p95": p95}
            print(f"  {name} → p50: {p50:.2f} ms | p95: {p95:.2f} ms")

        print("\n========== LOOKUP RESULTS (CognoDB) ==========")
        for name, res in results.items():
            print(f"{name:18} | p50: {res['p50']:7.2f} ms | p95: {res['p95']:7.2f} ms")
        print("==============================================")
        print("Indexed property: User.id")

    driver.close()

if __name__ == "__main__":
    main()
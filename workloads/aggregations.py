import os
import time
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

ITERATIONS = 80
WARMUP = 10

def run_query(session, query):
    start = time.perf_counter()
    session.run(query).consume()
    return (time.perf_counter() - start) * 1000  # ms

def percentile(data, p):
    return statistics.quantiles(data, n=100)[p-1]

def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    with driver.session() as session:
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

            # Warm-up
            for _ in range(WARMUP):
                run_query(session, query)

            # Measurements
            for _ in range(ITERATIONS):
                latency = run_query(session, query)
                latencies.append(latency)

            p50 = percentile(latencies, 50)
            p95 = percentile(latencies, 95)
            results[name] = {"p50": p50, "p95": p95}
            print(f"  → p50: {p50:.2f} ms | p95: {p95:.2f} ms")

        print("\n========== AGGREGATION RESULTS (CognoDB) ==========")
        for name, res in results.items():
            print(f"{name:30} | p50: {res['p50']:7.2f} ms | p95: {res['p95']:7.2f} ms")
        print("===================================================")

    driver.close()

if __name__ == "__main__":
    main()
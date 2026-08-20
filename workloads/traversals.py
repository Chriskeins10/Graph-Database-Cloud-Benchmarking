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

# URI = os.getenv("MEMGRAPH_URI")
# USER = os.getenv("MEMGRAPH_USER")
# PASSWORD = os.getenv("MEMGRAPH_PASSWORD")

URI     = os.getenv("FALKORDB_HOST", "localhost")
PORT     = int(os.getenv("FALKORDB_PORT", 6379))
PASSWORD = os.getenv("FALKORDB_PASSWORD")
USER = os.getenv("FALKORDB_USERNAME")
GRAPH    = os.getenv("FALKORDB_GRAPH", "SocialGraph")

# How many times to run each query after warm-up
ITERATIONS = 120
WARMUP = 20

def get_random_node_ids(session, count=200):
    result = session.run("MATCH (n:User) RETURN n.id AS id LIMIT $count", count=count)
    return [record["id"] for record in result]

def run_query(session, query, params):
    start = time.perf_counter()
    session.run(query, params).consume()
    return (time.perf_counter() - start) * 1000  # ms

def percentile(data, p):
    return statistics.quantiles(data, n=100)[p-1]

def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    with driver.session() as session:
        print("Collecting random start nodes...")
        node_ids = get_random_node_ids(session)
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

            # Warm-up
            for _ in range(WARMUP):
                nid = random.choice(node_ids)
                run_query(session, query, {"id": nid})

            # Actual measurements
            for _ in range(ITERATIONS):
                nid = random.choice(node_ids)
                latency = run_query(session, query, {"id": nid})
                latencies.append(latency)

            p50 = percentile(latencies, 50)
            p95 = percentile(latencies, 95)
            results[name] = {"p50": p50, "p95": p95}

            print(f"  {name} → p50: {p50:.2f} ms | p95: {p95:.2f} ms")

        print("\n========== TRAVERSAL RESULTS (CognoDB) ==========")
        for name, res in results.items():
            print(f"{name:6} | p50: {res['p50']:7.2f} ms | p95: {res['p95']:7.2f} ms")
        print("=================================================")

    driver.close()

if __name__ == "__main__":
    main()
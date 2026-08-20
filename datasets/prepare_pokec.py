import csv
from pathlib import Path

RAW_FILE = Path("raw/soc-pokec-relationships.txt")
OUTPUT_DIR = Path(".")
MAX_RELATIONSHIPS = 100_000       # Change this if you want bigger/smaller

def main():
    nodes = set()
    relationships = []

    print("Reading relationships...")
    with open(RAW_FILE, "r") as f:
        for i, line in enumerate(f):
            if i >= MAX_RELATIONSHIPS:
                break
            parts = line.strip().split()
            if len(parts) >= 2:
                source = parts[0]
                target = parts[1]
                nodes.add(source)
                nodes.add(target)
                relationships.append((source, target))

    print(f"Total relationships sampled: {len(relationships):,}")
    print(f"Total unique nodes: {len(nodes):,}")

    # Write nodes.csv
    nodes_file = OUTPUT_DIR / "nodes.csv"
    with open(nodes_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id:ID"])          # Neo4j-style header
        for node in sorted(nodes, key=lambda x: int(x)):
            writer.writerow([node])

    # Write relationships.csv
    rels_file = OUTPUT_DIR / "relationships.csv"
    with open(rels_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([":START_ID", ":END_ID", "type"])
        for source, target in relationships:
            writer.writerow([source, target, "KNOWS"])

    print("\nFiles created successfully:")
    print(f"  → {nodes_file}")
    print(f"  → {rels_file}")
    print("\nYou can now use these two CSV files for all databases.")

if __name__ == "__main__":
    main()
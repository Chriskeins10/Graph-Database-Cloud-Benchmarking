# Graph Database Cloud Benchmarking

Benchmark of **CognoDB Cloud** against other managed graph database platforms on the same dataset and workloads.

**Goal**: Fair methodology, reproducible automation, and honest reporting — not crowning a winner.

**Platforms compared**:
1. CognoDB Cloud (Free c0)
2. Neo4j AuraDB Free
3. Memgraph Cloud
4. TigerGraph Cloud Classic Free
5. FalkorDB Free

---

## Dataset

| Property              | Value                          |
|-----------------------|--------------------------------|
| Source                | SNAP `soc-Pokec` social network (sampled) |
| Nodes                 | 49,683                         |
| Relationships         | 100,000                        |
| Node label            | `User`                         |
| Relationship type     | `KNOWS`                        |
| Files                 | `datasets/nodes.csv`, `datasets/relationships.csv` |

The identical CSV files were loaded into every platform.

---

## Instance Specs & Fairness

| Platform       | Tier                    | Advertised Resources              | Notes |
|----------------|-------------------------|-----------------------------------|-------|
| **CognoDB**    | Free (c0)               | 0.5 vCPU, 256 MB RAM, 1 GB disk   | Intentionally small free tier |
| **Neo4j AuraDB** | Free                  | Shared / limited                  | Auto-pause on inactivity |
| **Memgraph**   | Cloud free / trial      | Shared                            | — |
| **TigerGraph** | Cloud Classic Free      | ~2–4 vCPU, 7.5–8 GB RAM           | Significantly larger than CognoDB |
| **FalkorDB**   | Free                    | 100 MB RAM                        | Closest resource match to CognoDB |

> **Fairness note**: Free tiers are not equal. CognoDB’s free tier is the most constrained. TigerGraph’s free tier has substantially more memory and CPU. FalkorDB’s 100 MB free tier is the closest in scale to CognoDB. All results must be interpreted with these resource differences in mind. Comparing a free tier against a paid tier would be a methodology error; all platforms were kept on free / entry tiers.

---

## Methodology

- **Same dataset**, same logical queries, same client machine and region for every platform.
- Warm-up performed before every measured workload.
- Latency reported as **p50 and p95** (not averages).
- Mixed workload: 10 concurrent clients, ~30 seconds, ~80 % reads / 20 % writes.
- All secrets read from environment variables (never committed).
- Automation: one loader + one set of workload scripts per platform.

| Category        | Metrics                                      | Iterations              |
|-----------------|----------------------------------------------|-------------------------|
| Data loading    | Nodes/s, Rels/s, total wall-clock            | Single run              |
| Traversals      | 1-hop, 2-hop, 3-hop latency                  | 20 warm-up + 120        |
| Lookups         | Point lookup + filtered lookup               | 20 warm-up + 120        |
| Aggregations    | Count nodes, count relationships, top-10 degree | 10 warm-up + 80      |
| Mixed workload  | Concurrent read/write throughput (QPS)       | 10 clients, 30 s        |

Indexed property on all platforms: `User.id`.

---

## Results

### 1. Data Loading

| Metric                    | CognoDB   | AuraDB Free | Memgraph  | TigerGraph | FalkorDB  |
|---------------------------|-----------|-------------|-----------|------------|-----------|
| Nodes loaded              | 49,683    | 49,683      | 49,683    | 49,683     | 49,683    |
| Relationships loaded      | 100,000   | 100,000     | 100,000   | 100,000    | 100,000   |
| Total wall time (s)       | 506.05    | 162.91      | 319.73    | **125.74** | 289.64    |
| Nodes / second            | 303.1     | 821.1       | 476.9     | **1,114.3**| 541.2     |
| Relationships / second    | 292.3     | 976.5       | 463.9     | **1,232.3**| 505.5     |

### 2. Traversals – p50 / p95 (ms)

| Hop   | CognoDB         | AuraDB Free       | Memgraph          | TigerGraph        | FalkorDB          |
|-------|-----------------|-------------------|-------------------|-------------------|-------------------|
| 1-hop | 320.7 / 558.9   | **81.4 / 235.0**  | 409.3 / 1283.2    | 345.8 / 570.9     | 320.4 / 563.8     |
| 2-hop | 310.7 / 466.4   | **80.7 / 276.8**  | 371.0 / 683.3     | 354.7 / 559.4     | 332.7 / 511.0     |
| 3-hop | 417.6 / 1246.4  | **85.2 / 248.3**  | 409.0 / 614.9     | 353.5 / 534.2     | 331.8 / 522.8     |

### 3. Lookups – p50 / p95 (ms)

| Query            | CognoDB          | AuraDB Free       | Memgraph          | TigerGraph        | FalkorDB          |
|------------------|------------------|-------------------|-------------------|-------------------|-------------------|
| Point Lookup     | 464.8 / 1435.7   | **82.4 / 192.5**  | 307.5 / 552.8     | 320.6 / 533.3     | 320.2 / 520.5     |
| Filtered Lookup  | 580.0 / 1709.5   | **75.0 / 215.8**  | 408.9 / 585.8     | 333.6 / 552.7     | 324.1 / 509.0     |

### 4. Aggregations – p50 / p95 (ms)

| Query                    | CognoDB          | AuraDB Free        | Memgraph          | TigerGraph        | FalkorDB          |
|--------------------------|------------------|--------------------|-------------------|-------------------|-------------------|
| Count all nodes          | 389.6 / 660.6    | **127.8 / 550.6**  | 409.7 / 689.1     | 322.3 / 510.4     | 308.8 / 561.4     |
| Count all relationships  | 479.0 / 1306.9   | **91.3 / 268.9**   | 427.7 / 662.5     | 524.6 / 1640.6    | 321.3 / 526.6     |
| Group by degree (top 10) | 1030.3 / 1316.0  | **116.2 / 290.1**  | 411.0 / 748.2     | 352.8 / 733.8     | 409.8 / 567.1     |

### 5. Mixed Workload (10 clients, ~30 s, ~80 % reads / 20 % writes)

| Metric              | CognoDB | AuraDB Free | Memgraph | TigerGraph | FalkorDB |
|---------------------|---------|-------------|----------|------------|----------|
| Throughput (QPS)    | 4.7     | **37.1**    | 10.8     | 25.9       | 25.7     |
| Total queries       | 172     | 1,131       | 330      | 783        | 777      |
| Duration (s)        | 36.7    | 30.5        | 30.6     | 30.2       | 30.2     |

### 6. Footprint

| Platform     | Observable footprint                          |
|--------------|-----------------------------------------------|
| CognoDB      | Free tier limits (0.5 vCPU / 256 MB / 1 GB)   |
| AuraDB Free  | Not fully observable (managed)                |
| Memgraph     | Not fully observable (managed)                |
| TigerGraph   | Free-tier instance specs as advertised        |
| FalkorDB     | 100 MB RAM free tier                          |

---

## Analysis

**AuraDB Free** is the clear latency leader on this dataset and workload. It delivered the lowest p50 and p95 numbers across traversals, lookups and aggregations — often 3–5× faster than the other free tiers.

**TigerGraph** achieved the highest ingest throughput (1,114 nodes/s and 1,232 rels/s). Its loading pipeline is clearly optimized for bulk import. Latency numbers were measured with interpreted GSQL; installed (compiled) queries would likely improve them further.

**CognoDB** free tier (0.5 vCPU / 256 MB) is intentionally the most resource-constrained platform in the comparison. Higher latency and lower concurrent throughput are expected under these limits and should not be read as a pure algorithmic ranking against platforms that offer more memory and CPU on their free tiers.

**FalkorDB** (100 MB free tier) produced latency numbers very close to CognoDB and TigerGraph on most read queries while matching TigerGraph’s mixed-workload throughput (~26 QPS). Given its small memory footprint, this is a strong result.

**Memgraph** showed higher variance (especially 1-hop p95) and mid-range throughput on the mixed workload.

Overall, the dominant factors on free tiers are **available resources**, **query execution model**, and **platform throttling**, more than raw query-language differences. Cypher-compatible engines (CognoDB, Aura, Memgraph, FalkorDB) used essentially identical query text, making those four a cleaner head-to-head on the query engine itself.

---

## Caveats

- Free-tier throttling, auto-pause and noisy-neighbour effects are present on every managed service.
- Resource disparity is significant: CognoDB free is far smaller than TigerGraph free.
- Network latency from the client machine to each cloud region is included in every measurement.
- Mixed-workload writes permanently added relationships; later runs therefore operated on a slightly larger graph.
- All latency figures are post warm-up (no cold-start numbers reported).
- TigerGraph used interpreted queries rather than installed queries.
- Some platforms exhibit large p50–p95 gaps, indicating occasional slow queries under free-tier conditions.

These results are a **reproducible, honest comparison under free-tier constraints**, not a definitive ranking of production performance.

---

## Project Structure

```text
cognodb-benchmark/
├── datasets/
│   ├── raw/
│   ├── nodes.csv
│   ├── relationships.csv
│   └── prepare_pokec.py
├── loaders/
│   ├── cognodb_loader.py
│   ├── auradb_loader.py
│   ├── memgraph_loader.py
│   ├── tigergraph_loader.py
│   └── falkordb_loader.py
├── workloads/
│   ├── Common/                  # CognoDB / Aura / Memgraph
│   │   ├── traversals.py
│   │   ├── lookups.py
│   │   ├── aggregations.py
│   │   └── mixed_workload.py
│   ├── tigergraph/
│   │   ├── tigergraph_traversals.py
│   │   ├── tigergraph_lookups.py
│   │   ├── tigergraph_aggregations.py
│   │   └── tigergraph_mixed_workload.py
│   └── falkordb/
│       ├── falkordb_traversals.py
│       ├── falkordb_lookups.py
│       ├── falkordb_aggregations.py
│       └── falkordb_mixed_workload.py
├── .env.example
├── requirements.txt
└── README.md


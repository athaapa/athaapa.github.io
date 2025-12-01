---
layout: post
title: "Building Clamp: Git-Like Version Control for RAG Vector Databases"
date: 2025-11-30
categories: [rag, vector-databases, tooling]
---

Ever updated your RAG knowledge base and wished you could just hit undo? That's why I built [Clamp](https://github.com/athaapa/clamp) – a version control system for vector databases that works like Git.

## The Problem

When you're building RAG systems, your vector database is constantly evolving. You ingest new documents, update embeddings, tweak chunking strategies. But what happens when a change breaks your retrieval quality? Most teams either rebuild from scratch or maintain multiple collections, both of which waste storage and compute.

Traditional vector databases like Qdrant support basic CRUD operations, but they lack semantic versioning capabilities. You can upsert documents, but there's no native way to track what changed, when, or roll back to a known-good state without losing data.

## The Core Insight

The breakthrough came from realizing that version control doesn't require moving data – it just requires tracking state. Instead of duplicating entire collections or implementing complex diff algorithms, Clamp treats versions as metadata annotations on existing vector points.

Here's the exact metadata schema:

```json
{
  "commit_hash": "sha256:abcd1234...",
  "group_id": "my_group",
  "is_active": true,
  "timestamp": "2025-11-30T12:34:56Z",
  "source_doc_id": "doc_1234",
  "chunk_index": 2
}
```

Each document version is stored as a separate point in Qdrant with a unique commit hash. Rollbacks flip the `is_active` flag instead of copying or deleting vectors – this means rollbacks are instant, typically under 100ms for 1k points.

## Implementation Challenges

### Metadata Schema & Indexing

The trickiest part was designing a metadata structure that balances queryability with Qdrant's filtering capabilities. I needed `commit_hash`, `group_id`, `is_active`, and `timestamp` fields without bloating payloads or slowing down retrieval.

**Performance matters here**: Qdrant uses payload indexes for filtering, and without proper indexing, metadata filters can cause full scans. I recommend creating payload indexes on frequently filtered fields:

```python
qdrant.create_payload_index(
    collection="docs",
    field_name="is_active",
    field_schema="bool"
)
qdrant.create_payload_index(
    collection="docs",
    field_name="commit_hash",
    field_schema="keyword"
)
```

This drops filter latency from ~500ms to ~50ms on collections with 10k+ points. Without indexes, every search query that filters on `is_active=true` scans all payloads.

### State Consistency & Atomicity

When a rollback happens, multiple points need their active flags updated atomically. Qdrant doesn't have native transactions, so I implemented a two-phase commit pattern: SQLite log updates first, then Qdrant points are updated in batches with retry logic.

To handle partial failures, I added a durable pending-ops table in SQLite. When a rollback or commit is requested, the operation is first inserted as pending, Qdrant updates are applied in idempotent batches, and the pending row is cleared only after all batches succeed. This lets an operator restart the process safely if Qdrant updates fail mid-flight – the system resumes where it left off.

Recovery example: if a rollback to commit `abc123` writes to SQLite but crashes before updating all Qdrant points, running `clamp status --repair` scans the pending-ops table, identifies the incomplete rollback, and replays the Qdrant batch updates.

### Storage Tradeoffs & Garbage Collection

The biggest downside of this design is storage cost. Every commit stores full vectors for all modified points, even if embeddings barely changed. After three major revisions, you're paying 3× storage and index build times scale with total point count, not just active points.

Mitigations I'm exploring:
- **Delta policy**: only store a new version when embedding changed beyond a cosine similarity threshold (e.g., 0.02)
- **Deduplication**: hash embeddings and store identical vectors only once, with metadata pointing to the shared vector
- **Garbage collection**: `clamp gc --prune-age=30d` deletes inactive points older than 30 days or offloads them to cold storage

Right now inactive points accumulate indefinitely, which is fine for small KBs but breaks down at scale. A production system needs automated GC with configurable retention policies.

## CLI & API Design

I wanted Clamp to feel like Git from the command line:

```bash
pip install clamp-rag
clamp init
clamp commit -m "Initial docs ingested"
clamp commit -m "Updated chunking strategy"
clamp checkout sha256:abcd1234
clamp branch experiment-v2
clamp merge experiment-v2
```

The semantics of `checkout`/`rollback`: instead of flipping `is_active` flags on every point, I'm moving toward a per-group `active_commit` pointer that queries consult. This is cheaper at read time because you filter against a single commit ID rather than scanning every point's `is_active` field.

## Operational Considerations

### Concurrency

Concurrent writes are handled with optimistic locking on commit metadata versions. If two processes try to commit changes to the same group simultaneously, the second commit detects a version mismatch and retries. For production use, a central write-lock per group (via Redis or etcd) would be safer.

### Monitoring & Testing

Integration tests simulate partial failures: SQLite updated, Qdrant update fails halfway through. An operator-facing command like `clamp status --group my_group` shows pending ops, last commit, index size, and inactive point count.

Benchmarks on a local Qdrant instance:
- 1k points upserted: ~200ms
- Rollback (flip flags): ~100ms
- Storage overhead: 3× vectors after three major revisions

### Security

Manage Qdrant API keys carefully and back up the SQLite commit DB regularly. The SQLite log is essential for recovery – without it, you can't reconstruct which commit corresponds to which points. Consider encryption-at-rest for archived vectors if your documents are sensitive.

## What I Learned

Building Clamp taught me that **version control is fundamentally about tracking intent, not just changes**. Git stores commit messages and diffs because code is text. But vectors don't diff meaningfully – what matters is knowing *why* a version exists and being able to restore that decision point.

I also learned that vector databases need better primitives for versioning. Qdrant's metadata filtering is powerful, but it's not designed for temporal queries or complex state transitions. Production RAG systems need first-class versioning support, and the current generation of vector databases treats it as an afterthought.

## Next Steps

Clamp is in early alpha with ~7 stars on GitHub. It only supports Qdrant right now, and there are rough edges around concurrent writes and collection management. But it works for my use case: versioning small to medium RAG knowledge bases where rollback speed matters more than storage efficiency.

Planned features:
- Branching and merging (test experimental document sets without affecting production)
- Pinecone and Weaviate support
- Web UI for visualizing commit history and diff analysis
- Automated GC with configurable retention policies

Try it on a small KB and watch how fast rollbacks are compared to rebuilding:

```bash
pip install clamp-rag
clamp init
clamp commit -m "Ingested docs batch 1"
# break something
clamp checkout <previous-commit>
```

The code is on [GitHub](https://github.com/athaapa/clamp). Open an issue or PR if you want a plugin for Pinecone/Weaviate or a web UI prototype. I'd love your feedback – especially if you find bugs or have ideas for better versioning patterns in vector databases.

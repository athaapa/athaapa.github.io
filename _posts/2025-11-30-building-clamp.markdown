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

```bash
# Try it:
pip install clamp-rag
clamp init
clamp ingest docs my_group "Initial version"
clamp history my_group
clamp rollback my_group <commit-hash>
```

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

### State Consistency

Currently, Clamp uses a pragmatic update order: new points are upserted to Qdrant first, then previous vectors are deactivated, and finally the commit is saved to SQLite. This approach prioritizes availability – if SQLite fails, the vector data is already in Qdrant and can be manually recovered.

The tradeoff: partial failures between Qdrant and SQLite can leave the system in an inconsistent state. For example, if Qdrant updates succeed but SQLite commit recording fails, you have orphaned vectors with no commit history entry. Right now this requires manual intervention to reconcile.

**Future work**: A durable pending-ops table in SQLite would enable true two-phase commits and automatic recovery after crashes, but it's not implemented yet.

### Storage Tradeoffs

Every commit stores full vectors for all modified points, even if embeddings barely changed. After three major revisions, you're paying 3× storage and index build times scale with total point count, not just active points.

**Currently there is no garbage collection implemented.** Inactive points accumulate indefinitely, which is fine for small KBs (my use case) but breaks down at scale.

Future mitigations could include delta policies (only store versions when embeddings change significantly), deduplication of identical vectors, or a `clamp gc` command to prune old inactive points.

## CLI & API Design

I wanted Clamp to feel like Git from the command line:

```bash
pip install clamp-rag
clamp init
clamp ingest docs my_group "Initial docs"
clamp ingest docs my_group "Updated chunking"
clamp history my_group
clamp rollback my_group sha256:abcd1234
```

The semantics of `checkout`/`rollback`: instead of flipping `is_active` flags on every point, I'm moving toward a per-group `active_commit` pointer that queries consult. This is cheaper at read time because you filter against a single commit ID rather than scanning every point's `is_active` field.

## Operational Considerations

### Concurrency

**Concurrent writes are not currently handled** – two processes committing to the same group simultaneously can race and create inconsistent state. For single-user development workflows this is acceptable, but production use would need optimistic locking on commit metadata or a central write-lock per group (via Redis or etcd).

### Monitoring & Testing

**Testing**: The test suite covers basic ingest, rollback, and history operations. Future work includes integration tests for partial failure scenarios (Qdrant succeeds, SQLite fails).

### Security

Manage Qdrant API keys carefully and back up the SQLite commit DB regularly. The SQLite log is essential for recovery – without it, you can't reconstruct which commit corresponds to which points. Consider encryption-at-rest for archived vectors if your documents are sensitive.

## What I Learned

Building Clamp taught me that **version control is fundamentally about tracking intent, not just changes**. Git stores commit messages and diffs because code is text. But vectors don't diff meaningfully – what matters is knowing *why* a version exists and being able to restore that decision point.

I also learned that vector databases need better primitives for versioning. Qdrant's metadata filtering is powerful, but it's not designed for temporal queries or complex state transitions. Production RAG systems need first-class versioning support, and the current generation of vector databases treats it as an afterthought.

## Current Limitations

- No garbage collection (inactive vectors accumulate)
- No concurrency control (single-writer only)
- Storage grows linearly with versions (no deduplication)
- Manual recovery required for partial failures
- Qdrant-only (Pinecone/Weaviate planned)

## Next Steps

Clamp is in early alpha with ~7 stars on GitHub. It only supports Qdrant right now, and there are rough edges around concurrent writes and collection management. But it works for my use case: versioning small to medium RAG knowledge bases where rollback speed matters more than storage efficiency.

Planned features:
- Branching and merging (test experimental document sets without affecting production)
- Pinecone and Weaviate support
- Web UI for visualizing commit history and diff analysis
- Automated GC with configurable retention policies

The code is on [GitHub](https://github.com/athaapa/clamp). Open an issue or PR if you want a plugin for Pinecone/Weaviate or a web UI prototype. I'd love your feedback – especially if you find bugs or have ideas for better versioning patterns in vector databases.

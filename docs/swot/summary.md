# SWOT Summary

## Overview

The PoC proves the most important architectural point: Temporal can orchestrate document ingestion through conversion, enrichment, chunking, embedding, and indexing. The workflow shape is clear and the task-queue split is a strong foundation.

The main issue is not whether Temporal fits. It does. The main issue is that the current implementation still has PoC shortcuts in the places that matter most for production: idempotency, external side effects, artifact contracts, real storage/indexing integrations, batching, observability, and tests.

## Strengths

- Temporal is a strong fit for this ingestion pipeline.
- The pipeline stages are clear and mostly separated by responsibility.
- Task queues already separate workflow, document conversion, AI, and Elastic work.
- Pydantic payloads provide a useful baseline for contracts.
- The README states the right design principles around small outputs, external artifacts, idempotent activities, and side-effect-free workflows.
- The repo is compact enough to harden without a large migration.
- Ruff and Pyright pass.

See: `docs/swot/strength.md`

## Weaknesses

- Workflow starts are not idempotent because IDs include a random UUID.
- External side effects are not protected from Temporal retries.
- Artifacts grow across stages because prior payloads are copied forward.
- The S3 service is local disk, not shared durable storage.
- Real S3 input handling is incorrect.
- Elastic integration is currently a stub.
- CPU-heavy chunking runs inside async activity execution.
- Tokenizer loading happens per activity call.
- Chunk storage/fetching is serial.
- Embedding batching is too naive for large documents.
- Metadata extraction sends full document content to the LLM.
- Configuration is hardcoded.
- Error handling is thin.
- There are no behavior tests.

See: `docs/swot/weakness.md`

## Opportunities

- Turn the PoC into a reusable ingestion platform with shared conversion, chunking, metadata, and embedding activities.
- Use more of Temporal's operational model: activity-specific retries, heartbeats, search attributes, cancellation, and workflow versioning.
- Make artifact lineage explicit with manifests, checksums, model versions, prompt versions, and stage-owned outputs.
- Improve scale through bounded batching and per-resource worker sizing.
- Add observability now while the repo is still small.
- Build confidence with workflow replay tests, activity unit tests, and integration tests.
- Separate development mocks from production interfaces.
- Add document quality controls such as file validation, duplicate detection, OCR handling, language detection, access metadata, and PII controls.
- Improve AI cost and quality management with token counting, model/prompt versioning, output evaluation, and caching.

See: `docs/swot/opportunity.md`

## Threats

- Duplicate ingestion can corrupt downstream indexed state.
- Retry storms can overload Docling, AI providers, or Elastic.
- Local artifact storage blocks horizontal scaling.
- Large documents can exhaust memory, context windows, provider limits, or activity timeouts.
- Workflow replay compatibility can break after code changes.
- Real S3 and Elastic failure modes are still unknown because integrations are mocked or incomplete.
- Sensitive data may leak into logs or oversized artifacts.
- AI costs can grow unexpectedly through retries, duplicate runs, and large documents.
- Operational failures may be hard to diagnose without structured logs, metrics, and search attributes.
- Development stack issues can slow adoption.

See: `docs/swot/threat.md`

## Recommended Priority

1. Fix idempotency first: stable workflow IDs, deterministic artifact keys, and idempotent Elastic writes.
2. Replace misleading mocks with explicit storage/indexing interfaces and real implementations.
3. Redesign artifact contracts so each stage stores only its owned output and references prior artifacts.
4. Add activity-specific retry policies, timeouts, heartbeats, and error classification.
5. Add bounded batching for chunks and embeddings.
6. Move tokenizer/model/client initialization out of per-call paths.
7. Add workflow replay tests, activity tests, and integration tests for real service boundaries.
8. Add structured logging, metrics, and workflow search attributes.

## Bottom Line

This is a useful PoC and the architecture is directionally sound. The largest risks are concentrated around production semantics rather than the high-level pipeline idea. If idempotency, artifact contracts, storage, indexing, batching, and tests are addressed next, this can become a credible foundation for a shared document ingestion platform.

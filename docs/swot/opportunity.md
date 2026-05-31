# Opportunities

## Turn the PoC into a reusable ingestion platform

The current workflow already separates common ingestion stages from the Elastic-specific indexing destination. With clearer contracts, this can become a reusable platform for multiple document-consuming applications.

Potential direction:

- Keep conversion, chunking, metadata extraction, and embedding as shared activities.
- Let downstream applications own domain-specific workflows and final indexing/storage.
- Define stable artifact contracts between shared and application-specific stages.

Relevant files:

- `README.md:3-5`
- `src/queues.py`
- `src/workflows/ingest_document.py`

## Use Temporal for robust operational recovery

Temporal can provide much more than the current PoC uses. The workflow can become resilient to transient failures, worker restarts, and external API outages if retry policies, heartbeats, and idempotency are designed deliberately.

Potential direction:

- Configure activity-specific retry policies.
- Add heartbeat timeouts for long-running activities.
- Use cancellation handling in activities.
- Add workflow search attributes for document ID, source URI, status, and tenant/application.
- Add signals or updates for reindexing, cancellation, or priority changes.

## Make artifact lineage explicit

The pipeline currently has implicit lineage through artifact paths. That can become a strong feature if formalized.

Potential direction:

- Store a manifest artifact for each workflow run.
- Record source URI, source checksum, generated artifact URIs, model versions, chunking version, embedding model, and indexing destination.
- Use content-addressed artifact keys where possible.
- Keep stage outputs small and reference prior artifacts.

Benefits:

- Easier debugging.
- Reproducible indexing.
- Safer backfills.
- Better auditability.

## Improve scale with bounded batching

Chunking, storage, embedding, and indexing can all be made more scalable without changing the high-level workflow shape.

Potential direction:

- Batch embeddings by token count and provider limits.
- Fetch/store chunk artifacts with bounded concurrency.
- Consider chunk batch artifacts for large documents.
- Split very large documents into child workflows or paginated activity batches.
- Use separate worker deployments for CPU-heavy, AI-bound, and IO-bound queues.

Relevant files:

- `src/activities/docling_to_chunks.py`
- `src/activities/embed_texts.py`
- `src/activities/send_to_elastic.py`
- `worker.py`

## Add real observability early

The repo is still small, so this is a good time to add operational instrumentation before the workflow gets larger.

Potential direction:

- Replace `print` with structured logging.
- Log workflow ID, run ID, document ID, activity name, attempt, artifact URI, chunk count, batch size, latency, and external status code.
- Add metrics for conversion duration, chunk count, embedding token count, indexing duration, retry count, and failure category.
- Add dashboards around queue backlog and activity latency.

Benefits:

- Faster incident diagnosis.
- Capacity planning based on real document sizes.
- Better visibility into expensive AI operations.

## Harden contracts with tests

The code is compact and already passes Ruff and Pyright. This is a good moment to add tests before more behavior accumulates.

Potential direction:

- Unit-test each activity with fake services.
- Add workflow replay tests.
- Add integration tests for local Docling and object storage.
- Add contract tests for Elastic payload shape.
- Add regression fixtures for empty, small, large, scanned, and malformed documents.

Benefits:

- Safer refactoring.
- Faster confidence when changing workflow structure.
- Earlier detection of replay-breaking changes.

## Separate development mocks from production interfaces

The local `S3Service` and `ElasticApiService` stubs are useful for fast PoC iteration, but they should become explicit development implementations behind interfaces.

Potential direction:

- Define storage and indexing protocols/interfaces.
- Provide local filesystem and fake Elastic implementations for tests.
- Provide real S3-compatible storage and Elastic/API implementations for runtime.
- Select implementation through validated configuration.

Benefits:

- Cleaner tests.
- Less risk of accidentally deploying mock behavior.
- Easier transition from local demo to shared environment.

## Add document quality and policy controls

Document ingestion systems usually need controls beyond pure indexing.

Potential direction:

- File type and size validation.
- Virus/malware scanning before conversion.
- PII or confidential-data classification.
- Language detection.
- OCR/scanned-document handling.
- Duplicate detection by source checksum.
- Access-control metadata propagation into the index.

Benefits:

- Safer ingestion.
- Better search filtering.
- Stronger compliance posture.

## Improve AI cost and quality management

The current AI calls do not track token usage, model version, prompt version, or output quality.

Potential direction:

- Version prompts and schemas.
- Record model names and embedding dimensions in artifacts.
- Add token counting before calls.
- Cap document content sent to metadata extraction.
- Evaluate summary quality against a fixture set.
- Add fallback behavior for missing publication dates or low-confidence extraction.

Benefits:

- More predictable cost.
- Better repeatability.
- Easier model migrations.

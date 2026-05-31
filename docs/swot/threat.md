# Threats

## Duplicate ingestion can corrupt downstream state

Because workflow IDs include a random UUID, retries or repeated submissions can create multiple active ingestions for the same document.

Relevant file:

- `main.py:26`

Threat:

- Duplicate documents or chunks can appear in the index.
- Competing workflows can overwrite or mix artifacts for the same `document_id`.
- Operators may not know which run is authoritative.

Mitigation:

- Use stable workflow IDs.
- Use deterministic artifact keys that include source digest or run ID.
- Make final indexing idempotent.

## Retry storms can overload external services

Default activity retries combined with high worker concurrency can amplify outages.

Relevant files:

- `src/workflows/ingest_document.py`
- `worker.py:41-64`

Threat:

- Docling, LiteLLM, and Elastic/API services can be overwhelmed.
- Costs can spike from repeated AI calls.
- Incident recovery can be delayed by retry backlog.

Mitigation:

- Add per-activity retry policies.
- Add rate limits and bounded concurrency.
- Mark validation failures as non-retryable.
- Use circuit-breaker or backpressure behavior at service clients.

## Local artifact storage blocks horizontal scaling

`S3Service` uses local disk under `./storage`.

Relevant file:

- `src/services/s3.py`

Threat:

- A worker processing a later activity may not have the artifact written by an earlier activity.
- Container restarts can lose data.
- Scaling workers across hosts will fail unpredictably.

Mitigation:

- Use real shared object storage.
- Keep local storage only for tests and local development.
- Add integration tests that run multiple worker processes.

## Large documents can exhaust memory, context windows, or provider limits

The pipeline stores and copies large payloads, sends full markdown to the LLM, and embeds all chunks in one request.

Relevant files:

- `src/activities/docling_to_markdown.py:31`
- `src/activities/generate_document_meta.py:49-52`
- `src/activities/embed_texts.py:50-52`

Threat:

- Activities time out.
- Workers run out of memory.
- LLM/embedding requests fail due to context or batch limits.
- Retries repeat expensive work.

Mitigation:

- Add file size and page count limits.
- Stream or batch large artifacts.
- Batch embeddings by token count.
- Use chunk-level metadata extraction for large documents.

## Workflow replay compatibility can break silently

The workflow has no versioning strategy. Once workflows are running, changing activity names, order, or payload models can break replay.

Relevant file:

- `src/workflows/ingest_document.py`

Threat:

- Deployments can break in-flight workflows.
- Backfills may fail after code changes.
- Operational recovery becomes harder.

Mitigation:

- Add workflow replay tests.
- Use Temporal patch/versioning APIs for workflow changes.
- Keep payload contracts backward-compatible.

## Real external integrations are still unknown

Elastic and S3 behavior is mocked or incomplete.

Relevant files:

- `src/services/elastic_api.py`
- `src/services/s3.py`

Threat:

- The PoC may hide actual latency, failure modes, schema issues, auth issues, and rate limits.
- Production readiness may be overestimated.

Mitigation:

- Implement real clients behind interfaces.
- Add integration tests against realistic local or staging services.
- Capture service-specific error classification.

## Sensitive data may leak into logs or artifacts

The code prints full documents/responses in places:

- `src/services/docling.py:53-54`
- `src/services/elastic_api.py:25-26`

Artifacts can also carry more fields than intended because previous payloads are copied forward.

Threat:

- Sensitive document content can appear in logs.
- Downstream artifacts can expose data outside the intended stage.
- Compliance controls become harder.

Mitigation:

- Replace raw prints with structured, redacted logs.
- Avoid logging full document content or full external responses.
- Keep artifact schemas minimal and explicit.

## Cost can grow unexpectedly

AI calls are not budgeted, token-counted, batched safely, or deduplicated.

Relevant files:

- `src/services/ai.py`
- `src/activities/generate_document_meta.py`
- `src/activities/embed_texts.py`

Threat:

- Reprocessing the same document can repeat expensive AI calls.
- Large documents can trigger high embedding and summarization costs.
- Retry behavior can multiply spend during incidents.

Mitigation:

- Cache outputs by source checksum, prompt version, and model version.
- Track token usage and model version.
- Add budget limits and batch controls.

## Operational failures may be hard to diagnose

Logging is unstructured, metrics are absent, and activity errors are not classified.

Threat:

- Operators may see failed workflows without enough context.
- Queue backlog and external service latency may be invisible.
- Root cause analysis can require manual artifact inspection.

Mitigation:

- Add structured logs and metrics.
- Add workflow search attributes.
- Record artifact sizes, chunk counts, model names, and external service status codes.

## Development stack issues can slow adoption

The namespace creation script has a typo:

- `stack/scripts/create-namespace.sh:57`

Docker image versions depend on environment variables:

- `stack/docker-compose.yml`

Threat:

- New developers may fail to start the stack.
- Environment differences can produce inconsistent behavior.

Mitigation:

- Fix the script typo.
- Pin known-good local stack versions.
- Add a documented bootstrap path and smoke test.

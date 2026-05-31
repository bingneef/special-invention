# Weaknesses

## Workflow starts are not idempotent

`main.py` appends a random UUID to every workflow ID:

- `main.py:26`

Re-running the same document creates another ingestion instead of deduplicating or returning the existing workflow. This conflicts with the README's own idempotency guidance:

- `README.md:9-10`

Impact:

- Duplicate indexing is likely.
- Retries from callers can create multiple workflows.
- Operational cleanup becomes harder because workflow identity is not tied to document identity.

Recommended direction:

- Use stable workflow IDs derived from document ID, artifact URI, or source digest.
- Define duplicate behavior explicitly: reject, reuse, supersede, or version.

## External side effects are not protected from retries

Activities rely on Temporal's default retry behavior while using only `start_to_close_timeout`, for example:

- `src/workflows/ingest_document.py:26-30`
- `src/workflows/ingest_document.py:42-48`

`SendToElastic` performs an external write:

- `src/activities/send_to_elastic.py:63`

If the external write succeeds but the activity fails before completion is recorded, Temporal can retry and write again.

Impact:

- Duplicate documents or chunks can be indexed.
- Partial writes may become hard to recover from.
- Activity retries can amplify external API incidents.

Recommended direction:

- Make Elastic writes idempotent with deterministic document IDs and upsert semantics.
- Configure retry policies per activity.
- Classify non-retryable errors.
- Store external operation IDs or checksums where useful.

## Artifact payloads grow across pipeline stages

`AppendArtifact` allows extra fields:

- `src/models.py:4-6`

Later stages repeatedly spread previous payloads into new outputs:

- `src/activities/docling_to_markdown.py:31`
- `src/activities/generate_document_meta.py:55-60`
- `src/activities/embed_texts.py:54-59`

This can cause downstream artifacts to carry full Docling JSON, markdown, metadata, and embeddings together.

Impact:

- Artifact size grows unnecessarily.
- Serialization and object storage costs increase.
- Data contracts become implicit and fragile.
- Sensitive or irrelevant fields can leak into later stages.

Recommended direction:

- Make every artifact schema explicit.
- Store only the fields owned by that stage.
- Reference prior artifacts by URI instead of copying their full contents.

## The S3 abstraction is local disk

`S3Service` writes to `./storage`:

- `src/services/s3.py:12-13`
- `src/services/s3.py:20-26`

This is not shared durable storage. Multiple workers, containers, or hosts will not see the same artifacts.

`generate_presigned_url` also ignores the requested bucket/key and always returns a fixed URL:

- `src/services/s3.py:15-18`

Impact:

- Horizontal scaling will break.
- Worker restarts or deployment changes can lose artifacts.
- The code looks S3-compatible while not behaving like S3.

Recommended direction:

- Replace the mock with a real object store client or make the mock explicit.
- Parse `s3://bucket/key` properly.
- Keep local storage only behind a development profile.

## Real S3 input handling is broken

When `payload.artifact_uri` starts with `s3://`, `ConvertToDocling` passes the whole URI as `artifact_name` while hardcoding `bucket_name=\"my-bucket\"`:

- `src/activities/convert_to_docling.py:31-35`

Impact:

- Real S3 inputs will not map to their actual bucket/key.
- Presigned URL generation cannot work correctly.

Recommended direction:

- Parse the URI into bucket and key.
- Use the parsed bucket/key when generating the presigned URL.
- Validate unsupported URI schemes early.

## Elastic integration is a stub

`ElasticApiService.store_document` only prints and returns `True`:

- `src/services/elastic_api.py:25-26`

Impact:

- The PoC proves orchestration shape, not indexing correctness.
- There is no validation of mappings, response handling, duplicates, or partial failures.
- Performance and failure characteristics of the real indexing path are unknown.

Recommended direction:

- Implement the real API client.
- Add contract tests against a local Elastic or API test double.
- Validate response status and index result.

## Heavy synchronous work runs in async activities

`DoclingToChunks` calls synchronous chunking directly from an async activity:

- `src/activities/docling_to_chunks.py:40`

`chunk_document` loads and uses tokenizer/chunker synchronously:

- `src/services/docling.py:63-72`

Impact:

- The async event loop can be blocked by CPU-heavy work.
- Worker throughput can collapse under large documents.

Recommended direction:

- Move CPU-heavy work to sync activities, `asyncio.to_thread`, a process pool, or a CPU-sized worker pool.

## Tokenizer loading happens per activity call

`AutoTokenizer.from_pretrained` is called inside `chunk_document`:

- `src/services/docling.py:66`

Impact:

- Repeated initialization adds latency.
- Worker startup/cache behavior becomes unpredictable.
- Concurrent calls can contend on model cache.

Recommended direction:

- Initialize tokenizer/chunker once per worker process.
- Inject the initialized component into `DoclingService`.

## Chunk IO is serial

Chunk artifacts are stored one by one:

- `src/activities/docling_to_chunks.py:54-60`

Chunk artifacts are fetched one by one before indexing:

- `src/activities/send_to_elastic.py:39-42`

Impact:

- Large documents spend avoidable time on sequential IO.
- Indexing latency grows linearly with chunk count.

Recommended direction:

- Use bounded concurrency for fetch/store operations.
- Consider storing chunks as a single batch artifact if per-chunk artifacts are not required.

## Embedding batching is too naive

`EmbedTexts` sends all texts to the embedder in one call:

- `src/activities/embed_texts.py:50-52`

Impact:

- Large documents can exceed provider request limits.
- Retries become all-or-nothing.
- Rate limits are harder to respect.

Recommended direction:

- Add token counting and batch sizing.
- Add bounded concurrency and backoff.
- Persist partial progress if embedding large documents.

## Metadata extraction sends the full document to the LLM

The metadata activity sends full markdown content to the model:

- `src/activities/generate_document_meta.py:49-52`

Impact:

- Large documents can exceed context limits.
- Cost and latency can be high.
- Important metadata may be diluted in long prompts.

Recommended direction:

- Use first pages, structured Docling metadata, chunk-level extraction, or map-reduce summarization.

## Configuration is hardcoded

Several endpoints and names are hardcoded:

- Temporal: `worker.py:24-26`, `main.py:14-17`
- Docling: `src/services/docling.py:28`
- Elastic API: `src/services/elastic_api.py:22`
- Bucket: repeated `\"my-bucket\"` in activities

Impact:

- Deployment outside local development is fragile.
- Tests cannot easily substitute services.
- Environment-specific behavior is hidden in code.

Recommended direction:

- Centralize settings.
- Validate required configuration at startup.
- Inject service dependencies with configured clients.

## Error handling is thin

`DoclingService.convert_document` does not call `raise_for_status`, assumes JSON, prints the full response, and assumes `document.json_content` exists:

- `src/services/docling.py:50-56`

`_get_page_from_chunk` catches only `KeyError`:

- `src/services/docling.py:96-102`

Impact:

- Failures become unclear.
- Logs can contain huge payloads.
- Some normal malformed/empty cases will fail unexpectedly.

Recommended direction:

- Add explicit response validation.
- Raise typed exceptions.
- Distinguish retryable and non-retryable failures.
- Improve page extraction defensively.

## Dependency injection is inconsistent

`GenerateDocumentMeta` accepts an AI service but then constructs a new `AIService()` directly:

- `src/activities/generate_document_meta.py:35-39`
- `src/activities/generate_document_meta.py:49`

Impact:

- Tests and mocks are harder.
- Runtime configuration can be ignored.

Recommended direction:

- Use `self.ai_service`.
- Keep all external clients injectable.

## No tests cover behavior

There are no test files.

Missing coverage includes:

- Activity idempotency.
- Workflow replay determinism.
- Retry behavior around external side effects.
- Artifact schema compatibility.
- Malformed Docling responses.
- Empty and large documents.
- Documents without publication dates.
- Embedding batch failures.
- Elastic indexing failures and duplicate handling.

Impact:

- Refactors are risky.
- Temporal replay issues may only appear in running workflows.
- External service behavior is unverified.

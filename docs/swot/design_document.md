# Design Document: Reusable Temporal Ingestion Framework

## Purpose

This document captures the design direction that follows from the SWOT analysis and the high-level stack assessment.

The current document-ingestion PoC proves that Temporal can orchestrate a pipeline through conversion, enrichment, chunking, embedding, and indexing. The next step is not only to harden this specific workflow, but to turn the useful parts into a reusable Temporal framework for ingestion and transformation jobs.

The document pipeline is the first implementation of that framework, not the final abstraction.

## Decision Summary

Use Temporal as the orchestration foundation for shared ingestion and transformation workflows.

The main reason is not that every individual document must be processed perfectly on the first attempt. A failed document can often be rerun. The stronger reason is that the organization wants a common orchestration layer for multiple jobs, sources, and applications.

Temporal is justified because it gives the framework:

- Durable workflow execution.
- Explicit activity boundaries.
- Retries and timeout handling.
- Task queues for different resource classes.
- Operational visibility into failed and running jobs.
- A consistent place to model reruns, backfills, and external side effects.

This is heavier than a simple queue-based indexing pipeline, but the extra operational model is justified if the framework becomes shared infrastructure.

## Scope

The framework should provide reusable orchestration building blocks and conventions.

It should not try to become a fully generic workflow engine from day one. That would create abstractions before enough real workflows exist.

The primary unit of reuse should be:

- Activities.
- Contracts.
- Artifact conventions.
- Retry conventions.
- Task queue conventions.
- Observability standards.
- Worker registration patterns.

Complete workflows can exist for common cases, such as document ingestion, but workflows should not be the main reusable abstraction.

## Platform Boundary

The platform should own the common ingestion and orchestration capabilities. Applications should own their domain-specific requirements and serving behavior.

The framework should own:

- Document conversion.
- Chunking strategy defaults.
- Embedding model defaults.
- Metadata extraction defaults and prompt management.
- Artifact manifest format.
- Object storage implementation.
- External source connector framework and shared connectors.
- Failure visibility and operational dashboards.
- Access-control propagation conventions.
- Reprocessing and backfill policy.
- Activity registration and execution conventions.
- Workflow conventions.

Applications should own:

- Destination-specific requirements.
- Internal search/index application mappings and schema.
- Domain-specific enrichment requirements.
- Application-specific validation rules.
- Search relevance tuning.
- Serving and query behavior.

This split keeps Temporal as the shared orchestration layer without forcing every application into one rigid product model.

The current organization is small, and the same team is likely to build both the framework and the first applications. In that stage, central ownership is mostly a code organization choice. If the organization later splits into platform and application teams, ownership should evolve toward a hybrid model where application engineers can contribute workflow or activity changes to the framework under shared review and versioning rules.

## Chosen Stack

### Temporal

Temporal should be the orchestration layer.

Justification:

- The pipeline has multiple dependent stages.
- Work can be long-running and failure-prone.
- External systems can fail independently.
- Activities need different retry, timeout, and resource policies.
- Operators need to know which jobs failed and why.
- Failed jobs need safe rerun behavior.

Limitations:

- Temporal does not make non-idempotent code safe.
- Workflow replay means workflow changes require discipline.
- Teams must understand workflow determinism, activity idempotency, and versioning.
- Temporal is too heavy if the use case remains a single simple indexing flow.

### Docling

Docling is a reasonable document-conversion component.

Justification:

- It produces a structured intermediate representation.
- Later stages can use markdown, page information, document structure, and chunk provenance.
- It is a better foundation than immediately flattening all documents into plain text.

Limitations:

- Scanned documents, complex PDFs, tables, multi-column layouts, and embedded images can still fail or lose meaning.
- Conversion latency and memory usage may be significant for large files.
- Docling should be treated as a conversion engine with uncertain input quality, not as a guaranteed parser.

### Object Storage

Object storage should hold large artifacts.

Justification:

- Temporal workflow history should not contain full documents, Docling JSON, markdown, chunks, or embeddings.
- Artifact references keep workflow payloads small.
- External artifacts make reruns, debugging, and lineage possible.

Limitations:

- Object storage becomes part of the contract, not just a blob dump.
- The framework needs artifact ownership, deterministic keys, checksums, lifecycle rules, access control, cleanup, and manifest tracking.

### AI Services

AI services should be used for enrichment, not correctness.

Good uses:

- Summaries.
- Keywords.
- Metadata suggestions.
- Embeddings.
- Classification.
- Quality signals.

Limitations:

- LLM output is probabilistic.
- Full-document prompting is expensive and fragile.
- Model and prompt versions must be recorded.
- AI calls need batching, caching, timeout policy, and cost visibility.

### Internal Search/Index Application

The current "Elastic" destination should be understood as an internal application for document and chunk search, not as direct ownership of raw Elasticsearch from the ingestion framework. The naming is unfortunate because the application may be backed by Elasticsearch, but architecturally it is a destination application.

Justification:

- It provides the application-facing search and indexing behavior.
- It can support keyword search, filtering, faceting, metadata queries, chunk retrieval, and potentially vector search.
- It fits the current example workflow as an application-owned destination while hiding the underlying search implementation from the ingestion framework.

Limitations:

- The internal search/index application should not be the canonical source of truth.
- Mappings, schema, relevance tuning, and serving behavior are application-specific.
- Duplicate indexing and partial indexing must be handled explicitly.
- Strict access-control filtering must be designed from the beginning.

## Reusable Activity Contract

Activities are the primary reusable asset. Therefore each shared activity must have a strict contract.

Every reusable activity should define:

- Typed input model.
- Typed output model.
- Artifact ownership: what it reads and what it writes.
- Deterministic artifact key strategy.
- Idempotency behavior.
- Retryable and non-retryable error categories.
- Timeout and heartbeat expectations.
- Resource class: CPU-bound, IO-bound, AI-bound, index-bound, or mixed.
- Task queue.
- Required configuration.
- Structured logs and metrics.
- Test fixtures with fake service dependencies.

Justification:

Reusable activities without strict contracts are only shared code. They are not safe orchestration building blocks. The contract is what allows different workflows to compose activities predictably.

## Workflow Conventions

Workflows should be standardized more lightly than activities.

Teams should be free to compose activities in the order and branching structure their use case requires. The framework should still define conventions so workflows remain readable, observable, and operationally consistent.

Workflow conventions should cover:

- Workflow ID format.
- Workflow input envelope.
- Workflow result shape.
- Search attributes.
- Status reporting.
- Artifact manifest creation and updates.
- Error handling style.
- Parent and child workflow usage.
- Retry policy references.
- Cancellation behavior.
- Versioning and patching policy.
- Signal and update support, where needed.

Justification:

Workflows are where use-case logic lives. Over-standardizing them would make the framework rigid. Under-standardizing them would make operations inconsistent. The right split is strict activity contracts and lighter workflow conventions.

## Identity And Idempotency

The framework must define identity before it can safely support reruns, retries, or backfills.

The system needs clear answers for:

- What is a source item?
- What is a document?
- What is a document version?
- What is a workflow run?
- What happens when the same item is submitted again?
- Does reingestion reject, reuse, overwrite, append, or create a new version?

The current PoC has a major gap here: workflow IDs include a random UUID, so repeated submissions create new ingestions instead of deduplicating or intentionally versioning the work.

Design decision:

- Workflow IDs should be stable and derived from source identity, document identity, version, or source digest.
- Artifact keys should be deterministic or explicitly versioned.
- Final destination writes should use deterministic IDs or upsert/replacement semantics.

Justification:

Temporal retries activities. That is only safe when external side effects are idempotent. Without stable identity, retries and reruns can create duplicate artifacts, duplicate index entries, and ambiguous operational state.

## Artifact Model

Each stage should own its output.

The current PoC copies prior payload fields forward, which causes artifacts to grow across stages and makes contracts implicit. That is acceptable in a PoC, but not in the framework.

The framework should define explicit artifacts such as:

- Source artifact.
- Converted Docling artifact.
- Markdown artifact.
- Metadata artifact.
- Chunk manifest.
- Embedding artifact.
- Index manifest.

Each artifact should record:

- Artifact type.
- Producer activity.
- Producer version.
- Source artifact references.
- Checksums.
- Model and prompt versions where relevant.
- Created timestamp.
- Storage URI.

Justification:

Explicit artifact contracts make reruns, debugging, backfills, and audits possible. They also prevent oversized artifacts and accidental leakage of sensitive data across stages.

## Failure And Rerun Model

The framework should guarantee visible, classified failure states and safe reruns. It does not need to guarantee that every failed document or job is automatically fixed.

Automatic retries should handle transient failures. Persistent failures should be classified, exposed operationally, and rerunnable after the input, configuration, external service, or workflow logic has been corrected.

Failure categories should include:

- Validation failures.
- Conversion failures.
- Chunking failures.
- AI provider failures.
- Invalid AI output.
- Object storage failures.
- Indexing or destination write failures.
- Workflow compatibility failures after code changes.

Rerun behavior should depend on the failure category:

- Some failures can be retried as-is.
- Some require replacing or rewriting failed-stage artifacts.
- Some require changing configuration.
- Some require starting a new workflow version.

Justification:

The organization can tolerate individual job failures if they are visible and rerunnable. That makes idempotency, deterministic artifacts, and clear failure classification more important than trying to automatically recover every case.

## Workflow Change Strategy

Workflow changes are a production concern because Temporal replays workflow code from event history.

The framework should use this strategy:

- Keep workflow code thin and stable.
- Put changeable business logic in activities where possible.
- Treat activity implementation changes as safe only when names, inputs, outputs, and side-effect semantics remain compatible.
- Treat workflow control-flow changes as compatibility-sensitive.
- Add replay tests for existing workflow histories.
- Use explicit workflow versioning for incompatible changes.
- Keep old workers available until old in-flight workflows complete, are cancelled, continue-as-new, or are deliberately migrated.
- Prefer child workflows or continue-as-new boundaries for long-running jobs.

Justification:

Changing workflow activity order, branching, timers, signals, child workflows, or payload interpretation can break replay for in-flight workflows. Versioning must be designed into the framework before long-lived workflows are common.

## Scale And Resource Management

The architecture is sound for moderate scale, but it needs bounded work units before production use.

Current risks include:

- CPU-heavy chunking inside async activity execution.
- Tokenizer loading per activity call.
- Serial chunk storage and fetches.
- Embedding all chunks in one request.
- Full-document metadata prompting.
- Large artifacts copied across stages.

Design decisions:

- Split task queues by resource class.
- Move CPU-heavy work to sync activities, process pools, or CPU-sized worker pools.
- Initialize tokenizers, models, and clients once per worker process.
- Batch embeddings by token count and provider limits.
- Use bounded concurrency for artifact storage and fetches.
- Use child workflows or batch manifests for very large documents.

Justification:

The framework should support more than small demo documents. Large documents can exhaust memory, provider context windows, activity timeouts, and indexing throughput unless batching and resource isolation are designed explicitly.

## Observability

The framework should standardize structured logs, metrics, and search attributes.

At minimum, logs and metrics should include:

- Workflow ID.
- Run ID.
- Source identity.
- Document ID or job ID.
- Activity name.
- Activity attempt.
- Artifact URI.
- Artifact size.
- Chunk count.
- Batch size.
- Latency.
- External service status.
- Failure category.

Workflow search attributes should include:

- Source identifier.
- Document or job identifier.
- Application.
- Status.
- Failure category.
- Tenant or access domain, where relevant.

Justification:

The organization does not require every job to succeed automatically, but it does need to know what failed and why. Without standardized observability, failed jobs become manual forensic work.

## Testing Strategy

The current PoC has no behavior tests. That is the largest confidence gap after idempotency and artifact contracts.

The framework should add:

- Unit tests for each activity using fake service dependencies.
- Contract tests for artifact schemas.
- Workflow replay tests.
- Integration tests for real object storage boundaries.
- Integration tests for indexing destinations or destination test doubles.
- Regression fixtures for empty, malformed, large, scanned, and complex documents.
- Tests for retry behavior around external side effects.

Justification:

Temporal systems can fail in ways that static checks do not catch, especially around replay, retries, idempotency, and external side effects. Tests are required before the framework can be safely reused by multiple workflows.

## Alternatives Considered

### Simple Job Queue

Examples: Celery, RQ, BullMQ, Sidekiq.

This would reduce operational complexity for a single simple pipeline.

Rejected as the primary direction because the goal is a reusable orchestration framework, not only background processing. A simple queue would require the team to build orchestration, visibility, retry semantics, deduplication, and recovery conventions itself.

### Airflow, Dagster, Or Prefect

These are strong options for scheduled data pipelines and asset-oriented batch processing.

Rejected as the primary direction because this framework is more about per-item operational workflows, external service calls, retryable activities, and rerunnable jobs than scheduled analytical pipelines.

### Kafka Or Event-Driven Pipeline

Kafka is useful for high-throughput decoupled event processing.

Rejected as the primary orchestration layer because it makes per-job orchestration, end-to-end traceability, compensation, and rerun semantics harder. Kafka may complement the framework later for event ingress or fanout.

### Cloud-Native Orchestration

Examples: AWS Step Functions, Google Workflows, Azure Durable Functions.

These are reasonable if the organization wants cloud-native managed orchestration.

Rejected as the primary direction because Temporal gives stronger local development ergonomics, portability, and workflow expressiveness for this use case.

### Managed Search Or RAG Platform

Examples: Azure AI Search, OpenSearch ingestion pipelines, Pinecone-based ingestion, LlamaIndex, LangChain.

These can speed up delivery for standard RAG-style ingestion.

Rejected as the primary direction because the framework needs control over artifact lineage, contracts, failure handling, and application-specific workflows. Managed RAG platforms may still be useful as downstream destinations or internal implementation details.

## Implementation Priorities

1. Define workflow identity and rerun policy.
2. Define artifact manifest schemas and deterministic artifact keys.
3. Replace local/mock storage and indexing behavior with explicit interfaces and real implementations.
4. Define the reusable activity contract and retrofit existing activities to it.
5. Add activity-specific retry policies, timeouts, heartbeats, and error categories.
6. Add structured logs, metrics, and search attributes.
7. Add bounded batching for chunk storage, chunk fetches, embeddings, and indexing.
8. Move tokenizer, model, and client initialization out of per-call paths.
9. Add workflow replay tests, activity tests, artifact contract tests, and integration tests.
10. Define workflow versioning and deployment rules before long-running workflows become common.

## Conclusion

The architecture is directionally sound if it is treated as the foundation for a reusable Temporal ingestion framework.

The main production risks are not the high-level pipeline shape. The main risks are the semantics around identity, idempotency, artifacts, side effects, observability, workflow versioning, and tests.

The design should therefore focus on reusable activities and conventions first. Complete workflows can be provided for common cases, but the durable platform value is in the contracts that make activities composable, rerunnable, observable, and safe across multiple applications.

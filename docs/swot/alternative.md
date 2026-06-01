# High-Level Stack Assessment

## Short Answer

The stack is directionally correct, but mainly if the goal is to build a shared orchestration foundation for multiple ingestion and transformation jobs.

Temporal is a good fit for that foundation. The stack starts to break if the goal is only "simple document upload to searchable index" with low operational complexity.

## Core Question

The main question is not whether the implementation needs hardening. It does. The higher-level question is:

> Is Temporal + Docling + object storage + AI services + Elastic the right architectural shape for a reusable ingestion platform?

The answer is: yes, if this is meant to become the foundation for multiple jobs, sources, and application-specific ingestion workflows.

It is probably too heavy if this is only a lightweight document indexing pipeline.

The strongest argument for Temporal is not that every individual document must be processed perfectly on the first attempt. A missed or failed document can often be rerun. The stronger argument is that the organization wants a common orchestration layer with consistent retry behavior, task queues, worker isolation, operational visibility, and reusable activities across many ingestion use cases.

The right target is not a fully generic workflow engine from day one. The better target is a reusable Temporal workflow framework: shared conventions, task queues, storage contracts, observability, retry defaults, common activities, and platform-owned workflow implementations, with document ingestion as the first implementation.

The primary unit of reuse should be activities and conventions, not complete workflows. Complete workflows can exist for common patterns, but the durable platform value is in reusable activities, artifact contracts, queue conventions, retry conventions, observability standards, and worker registration patterns.

## Stack Fit

### Temporal

Temporal is the strongest architectural choice in the current stack if this repository is treated as the beginning of a shared orchestration platform.

It fits because document ingestion has several characteristics Temporal handles well:

- Multiple dependent stages.
- Long-running work.
- Expensive external calls.
- Partial failure.
- Retries.
- Asynchronous workers.
- Operational visibility.
- The need to track, rerun, and recover failed jobs in a consistent way.

The current workflow already shows the right shape: convert, branch into document and chunk processing, embed, then index.

Where Temporal is less ideal:

- Very high-volume tiny jobs where queue overhead matters.
- Simple request/response flows.
- Systems where developers are not prepared to learn workflow determinism, replay, activity idempotency, and versioning.
- Pipelines that mostly need analytical scheduling rather than durable business-process execution.

Temporal is powerful, but it imposes discipline. If the team does not adopt that discipline, it can create a false sense of safety. The platform value comes from standardizing orchestration and failure handling across jobs, not merely from wrapping a single document pipeline in workflows.

### Docling

Docling is a reasonable choice for document normalization and conversion. It gives the pipeline a structured intermediate document model instead of immediately flattening everything into text.

That is valuable because later stages can use:

- Markdown.
- Page information.
- Document structure.
- Chunk provenance.
- Tables and layout-derived metadata, depending on input quality.

Where this can break:

- Scanned documents and OCR quality.
- Complex PDFs.
- Tables, footnotes, multi-column layouts, and embedded images.
- Documents where legal or business meaning depends on formatting.
- Very large files.
- Conversion latency and memory pressure.

Docling should be treated as a conversion engine with uncertain input quality, not as a guaranteed parser. The architecture should expect conversion failures, low-confidence extraction, and fallback paths.

### Object Storage

Object storage is the correct boundary for large artifacts.

Temporal should not carry full document contents, Docling JSON, markdown, chunks, or embeddings in workflow history. The README already states this correctly.

The limitation is that object storage becomes part of the contract. The system needs to account for:

- Artifact ownership.
- Lifecycle and retention.
- Checksums.
- Versioning.
- Access control.
- Encryption.
- Cleanup.
- Reproducibility.

This is not just a blob dump. For production, artifact storage becomes the system of record for intermediate pipeline state.

### AI Services

AI is useful here, but should be treated as an unreliable and expensive enrichment layer, not as the foundation of correctness.

Good uses:

- Summaries.
- Keywords.
- Extracted metadata.
- Semantic embeddings.
- Classification.
- Quality signals.

Risky uses:

- Authoritative metadata extraction without validation.
- Full-document prompting.
- Retrying expensive calls blindly.
- Assuming deterministic output.
- Not recording model and prompt versions.

The AI layer needs cost control, batching, caching, versioning, and fallback behavior. Otherwise it becomes the most unpredictable part of the system.

### Elastic

Elastic is a reasonable indexing and search target, especially if the target is hybrid search over document metadata, chunks, and embeddings.

It fits when the system needs:

- Keyword search.
- Filtering.
- Faceting.
- Document metadata queries.
- Chunk retrieval.
- Potentially vector search.

Where it can break:

- If vector search quality is the primary product requirement.
- If relevance tuning becomes complex.
- If access-control filtering is strict and per-user.
- If the indexed schema changes frequently.
- If duplicate indexing is not solved.
- If chunk/document consistency matters strongly.

Elastic should be treated as a serving index, not the source of truth. The canonical state should live in object storage plus manifests plus source systems.

## Where The Architecture Breaks

### 1. Platform Boundary

The platform should own the common ingestion and orchestration capabilities, while applications should own their domain-specific serving/indexing behavior.

This should be a reusable framework rather than a rigid product. The platform should own the standardized workflow and activity patterns, while applications provide requirements, domain rules, and destination-specific intent.

In this model, applications do not freely add arbitrary final activities into the orchestration layer. Instead, the Temporal framework owns how final activities are implemented, registered, configured, observed, and retried. Applications may define what should happen, but the framework should define how it is executed.

The generic layer should own:

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

Applications should own:

- Destination-specific requirements.
- Elastic index mappings and schema.
- Domain-specific enrichment.
- Application-specific validation.
- Search relevance tuning.
- Serving/query behavior.

This boundary keeps Temporal as the shared orchestration layer without making the platform responsible for every application's product semantics. The platform can provide defaults, contracts, reusable activities, and owned workflow implementations, but applications still need controlled extension points for domain-specific requirements.

The risk of this stronger platform-ownership model is that the Temporal layer can become a bottleneck. If every application-specific change requires platform-team implementation, the framework may slow teams down or accumulate too much domain logic. The architecture should therefore define explicit extension mechanisms, not ad hoc exceptions.

This risk is lower while the same small team owns both the framework and the applications using it. In that stage, central ownership is mostly a code organization choice. If the organization later splits into separate platform and application teams, the model should evolve toward hybrid ownership: application engineers can contribute workflow or activity changes to the Temporal framework under shared review and versioning rules.

### 2. Reusable Activity Contract

Because activities and conventions are the primary unit of reuse, every shared activity should satisfy a clear contract.

Each reusable activity should define:

- Typed input model.
- Typed output model.
- Artifact ownership: which artifacts it reads and which artifacts it writes.
- Deterministic artifact key strategy.
- Idempotency behavior.
- Retryable and non-retryable error categories.
- Timeout and heartbeat expectations.
- Resource class: CPU-bound, IO-bound, AI-bound, index-bound, or mixed.
- Task queue.
- Required configuration.
- Structured logs and metrics.
- Test fixtures with fake service dependencies.

This contract is what makes activities composable across workflows. Without it, the platform only provides shared code, not reliable shared orchestration building blocks.

### 3. Workflow Conventions

Workflows should be standardized more lightly than activities.

Teams should be free to compose activities in the order and branching structure their use case requires. The framework should still define conventions so workflows remain understandable, observable, and operationally consistent.

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

This keeps workflows flexible while preventing each application from inventing its own operational model.

### 4. Failure And Rerun Model

The framework should guarantee visible, classified failure states and safe reruns. It does not need to guarantee that every failed document or job is automatically fixed.

Automatic retries should handle transient failures. Persistent failures should be classified, exposed operationally, and rerunnable after the input, configuration, external service, or workflow logic has been corrected.

The framework should distinguish at least:

- Validation failures, such as missing sources or unsupported file types.
- Conversion failures.
- Chunking failures.
- AI provider failures.
- Invalid AI output.
- Object storage failures.
- Indexing or destination write failures.
- Workflow compatibility failures after code changes.

Safe reruns depend on idempotency. Workflow IDs, artifact keys, manifest updates, object storage writes, and final destination writes should be deterministic or explicitly versioned. Rerunning a failed job should either reuse existing completed artifacts safely or replace them according to a defined policy.

The platform should provide a rerun mechanism based on failure category. Some failures can be retried as-is, some require rewriting or replacing artifacts, and some require starting a new workflow version.

### 5. Workflow Change Strategy

Workflow changes are a first-class production concern in Temporal because workflow code is replayed from event history.

The framework should use a tiered strategy:

- Prefer keeping workflow code thin and stable. Put most business logic in activities, where implementation changes are easier to deploy.
- Treat activity implementation changes as safe when activity names, input contracts, output contracts, and side-effect semantics remain compatible.
- Treat workflow control-flow changes as compatibility-sensitive. Changes to activity ordering, branching, child workflows, timers, signals, or payload interpretation can break replay for in-flight workflows.
- For small compatible workflow changes, keep payloads backward-compatible and add tests that replay existing workflow histories.
- For incompatible workflow changes, introduce explicit workflow versioning: a new workflow type/name, a version field in the input envelope, Temporal patching/versioning APIs, or worker/build versioning depending on the deployment model.
- Keep old workers available until old in-flight workflows have completed, been cancelled, continued-as-new, or deliberately migrated.
- For long-running workflows, prefer shorter workflow executions with child workflows or continue-as-new boundaries so deployments do not need to support old workflow code indefinitely.

The practical default should be conservative: avoid changing workflow control flow while executions are in flight unless there is a clear versioning plan.

### 6. Identity

If the same document can be ingested twice without a clear policy, the whole system becomes unreliable.

The system needs stable answers to:

- What is a document?
- What is a version of a document?
- What is a workflow run?
- What happens when the same document is submitted again?
- Is reingestion overwrite, reject, append, or version?

This is more important than the specific retry settings.

### 7. Artifact Contracts

Each stage must own its output.

The high-level problem is that artifacts are currently passed forward as evolving blobs. Production systems need explicit contracts:

- Source artifact.
- Converted Docling artifact.
- Markdown artifact.
- Metadata artifact.
- Chunk manifest.
- Embedding artifact.
- Index manifest.

The system should know which version of which stage produced which output.

### 8. External Side Effects

Temporal retries activities. That is good only if side effects are idempotent.

Writes to object storage, AI providers, and Elastic need deterministic keys or operation IDs. Otherwise the orchestration layer can amplify duplication instead of preventing it.

### 9. Scale

The architecture is fine for moderate scale, but it needs bounded work units.

Large documents stress every part of the stack:

- Conversion time.
- Memory.
- Artifact size.
- Chunk count.
- Embedding batch limits.
- LLM context windows.
- Indexing throughput.
- Workflow history and activity timeout design.

At high scale, the system probably needs child workflows or batch manifests rather than one workflow doing everything in one linear graph.

### 10. Operational Ownership

This stack has several moving parts:

- Temporal.
- Temporal workers.
- Object storage.
- Docling service.
- AI provider or gateway.
- Elastic.
- Application APIs.
- Monitoring and logging.

That is acceptable if ingestion orchestration is a platform capability. It is overkill if there is no team willing to operate it or if only one simple document pipeline will use it.

## Key Limitations To Keep In Mind

- Temporal does not make non-idempotent code safe.
- Temporal does not remove the need for schema and version management.
- Docling does not guarantee correct semantic interpretation of documents.
- LLM metadata extraction is probabilistic.
- Embeddings are model-specific and need migration planning.
- Elastic is an index, not canonical durable state.
- Object storage needs governance, not just paths.
- Large documents are a product and infrastructure risk.
- Access control must be designed into indexing from the beginning.
- Replay compatibility becomes a real concern once workflows are long-lived.

## Alternatives

### Simpler Job Queue

Examples: Celery, RQ, BullMQ, Sidekiq.

Good when:

- Ingestion is simple.
- Failures can be retried manually.
- Workflows are short.
- Exact recovery is less important.
- The team wants lower operational complexity.

Tradeoff:

- The team must build orchestration, visibility, retry semantics, deduplication, and recovery itself.

### Airflow, Dagster, Or Prefect

Good when:

- Ingestion is batch-oriented.
- Jobs are scheduled.
- Pipelines are data-engineering workflows.
- Lineage and data assets matter more than per-document durability.

Less ideal when:

- Each document is an independent business process.
- User-triggered ingestion needs durable status.
- Retries and partial recovery are central.

Temporal is usually better for per-document operational workflows. Dagster and Airflow are usually better for scheduled data pipelines.

### Kafka Or Event-Driven Pipeline

Good when:

- Throughput is very high.
- Stages are independently scalable.
- Eventual consistency is acceptable.
- The system needs decoupled consumers.

Tradeoff:

- Harder end-to-end traceability.
- Harder per-document orchestration.
- More custom handling for retries, poison messages, deduplication, and compensation.

Kafka can complement Temporal, but it should not replace Temporal unless throughput and decoupling dominate the requirements.

### Cloud-Native Orchestration

Examples: AWS Step Functions, Google Workflows, Azure Durable Functions.

Good when:

- The platform is already cloud-specific.
- Managed operations matter more than portability.
- Integrations are mostly cloud-native.

Tradeoff:

- Vendor lock-in.
- Less flexible local development.
- Often weaker developer ergonomics for complex workflows than Temporal.

### Managed Search Or RAG Platform

Examples: Azure AI Search, OpenSearch ingestion pipelines, Pinecone-based ingestion, LlamaIndex/LangChain pipelines.

Good when:

- Speed of delivery matters most.
- Customization is limited.
- Ingestion requirements are standard.

Tradeoff:

- Less control over artifact lineage.
- Harder to enforce domain-specific contracts.
- Less transparent failure behavior.
- Migration risk if the platform does not fit later.

## Recommendation

Keep the stack if the ambition is a shared ingestion and transformation platform.

Do not treat this as "Temporal around a script." Treat it as a production ingestion control plane:

- Temporal owns orchestration and recovery.
- Object storage owns artifacts.
- Manifests own lineage.
- Docling owns conversion.
- AI services own enrichment, with versioned outputs.
- Elastic owns serving and search indexes.
- Source systems remain authoritative for original documents and access metadata.

The biggest architectural decision to make next is not batching or retries. It is the boundary between the generic orchestration layer and application-owned workflow logic. Once that boundary is clear, the document identity and artifact lineage model can be designed in a way that supports more than this single PoC.

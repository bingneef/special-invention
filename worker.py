import asyncio

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from src.activities.convert_to_docling import ConvertToDocling
from src.activities.docling_to_chunks import DoclingToChunks
from src.activities.docling_to_markdown import DoclingToMarkdown
from src.activities.embed_texts import EmbedTexts
from src.activities.generate_document_meta import GenerateDocumentMeta
from src.activities.send_to_elastic import SendToElastic
from src.queues import AI_TASK_QUEUE, DOCUMENT_CONVERSION_TASK_QUEUE, ELASTIC_TASK_QUEUE, WORKFLOW_TASK_QUEUE
from src.workflows.ingest_document import (
    IngestDocumentWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )

    workflow_worker = Worker(
        client,
        task_queue=WORKFLOW_TASK_QUEUE,
        workflows=[IngestDocumentWorkflow],
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules(
                "pydantic_core", "pydantic_core._pydantic_core", "pydantic_core.core_schema", "numpy"
            )
        ),
        max_concurrent_activities=0,
    )

    document_conversion_worker = Worker(
        client,
        task_queue=DOCUMENT_CONVERSION_TASK_QUEUE,
        max_concurrent_activities=10,
        activities=[
            ConvertToDocling().convert_to_docling,
            DoclingToMarkdown().docling_to_markdown,
            DoclingToChunks().docling_to_chunks,
        ],
    )

    ai_worker = Worker(
        client,
        task_queue=AI_TASK_QUEUE,
        max_concurrent_activities=50,
        activities=[EmbedTexts().embed_texts, GenerateDocumentMeta().generate_document_meta],
    )

    elastic_worker = Worker(
        client,
        task_queue=ELASTIC_TASK_QUEUE,
        max_concurrent_activities=50,
        activities=[SendToElastic().send_to_elastic],
    )

    print("Workers started.")

    # Start all tasks if any 'completes', stop and raise
    tasks = [
        asyncio.create_task(workflow_worker.run()),
        asyncio.create_task(document_conversion_worker.run()),
        asyncio.create_task(ai_worker.run()),
        asyncio.create_task(elastic_worker.run()),
    ]

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    for task in pending:
        task.cancel()

    finished = done.pop()
    exc = finished.exception()
    if exc:
        raise exc

    raise RuntimeError("A worker exited unexpectedly")


if __name__ == "__main__":
    asyncio.run(main())

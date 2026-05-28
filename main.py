import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from src.workflows.contracts import ActivityDocumentPayload
from src.workflows.ingest_document import (
    IngestDocumentWorkflow,
)


async def start_job(document_id: str):
    client = await Client.connect(
        "localhost:7233",
        namespace="default",
        data_converter=pydantic_data_converter,
    )

    handle = await client.start_workflow(
        IngestDocumentWorkflow.run,
        ActivityDocumentPayload(
            document_id=document_id,
            artifact_uri=f"s3://my-bucket/documents/{document_id}/original.json",
        ),
        id=f"ingest-document-{document_id}-{uuid.uuid4()}",
        task_queue="workflows:elastic",
    )

    print(handle)


async def main():
    for i in range(1, 3):
        document_id = f"doc-{i}"
        print(f"Starting workflow for {document_id}")
        await start_job(document_id)


if __name__ == "__main__":
    asyncio.run(main())

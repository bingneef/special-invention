import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from src.workflows.contracts import ActivityDocumentPayload
from src.workflows.ingest_document import (
    IngestDocumentWorkflow,
)


async def start_job(document_id: str, artifact_uri: str):
    client = await Client.connect(
        "localhost:7233",
        namespace="default",
        data_converter=pydantic_data_converter,
    )

    handle = await client.start_workflow(
        IngestDocumentWorkflow.run,
        ActivityDocumentPayload(
            document_id=document_id,
            artifact_uri=artifact_uri,
        ),
        id=f"ingest-document-{document_id}-{uuid.uuid4()}",
        task_queue="workflows:elastic",
    )

    print(handle)


async def main():
    document_urls = [
        # "https://www.rekenkamer.nl/site/binaries/site-content/collections/documents/2026/02/04/focus-op-quantum-bij-de-rijksoverheid/rapport-focus-op-quantum-bij-de-rijksoverheid.pdf",
        # "https://www.rekenkamer.nl/site/binaries/site-content/collections/documents/2024/11/07/de-kracht-en-kwetsbaarheid-van-het-digitale-krijgsmachtnetwerk-nafin/PAC+Rapport+De+kracht+en+kwetsbaarheid+van+het+digitale+krijgsmachtnetwerk+NAFIN.pdf",
        "https://www.ciz.nl/test-download"
    ]

    for i, document_url in enumerate(document_urls):
        document_id = f"doc-{i + 1}"
        print(f"Starting workflow for {document_id}")
        await start_job(document_id, document_url)


if __name__ == "__main__":
    asyncio.run(main())

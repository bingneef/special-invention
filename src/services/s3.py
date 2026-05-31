import asyncio
from pathlib import Path, PurePosixPath
from typing import Type, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class S3Service:
    def __init__(self, storage_root: str | Path = "./storage") -> None:
        self.storage_root = Path(storage_root)

    async def generate_presigned_url(self, bucket_name: str, artifact_name: str, expires_in: int = 3600) -> str:
        # In a real implementation, this would generate a presigned URL for S3.
        # For this mock, we'll just return a URI that our service can understand.
        return "https://www.ciz.nl/test-download"

    async def store_artifact(self, bucket_name: str, artifact_name: str, artifact_data: BaseModel) -> str:
        path = self._path_for(bucket_name, artifact_name)
        content = artifact_data.model_dump_json(indent=2)

        await asyncio.to_thread(self._write_text, path, content)

        return f"s3://{bucket_name}/{artifact_name}"

    async def fetch_artifact(self, uri: str, model: Type[T]) -> T:
        bucket_name, artifact_name = self._parse_uri(uri)
        path = self._path_for(bucket_name, artifact_name)
        content = await asyncio.to_thread(path.read_text, encoding="utf-8")

        return model.model_validate_json(content)

    def _path_for(self, bucket_name: str, artifact_name: str) -> Path:
        if not bucket_name:
            raise ValueError("bucket_name must not be empty")
        if not artifact_name:
            raise ValueError("artifact_name must not be empty")

        bucket_path = PurePosixPath(bucket_name)
        artifact_path = PurePosixPath(artifact_name)
        if bucket_path.is_absolute() or artifact_path.is_absolute():
            raise ValueError("bucket_name and artifact_name must be relative paths")
        if ".." in bucket_path.parts or ".." in artifact_path.parts:
            raise ValueError("bucket_name and artifact_name must not contain '..'")

        return self.storage_root / Path(*bucket_path.parts) / Path(*artifact_path.parts)

    def _parse_uri(self, uri: str) -> tuple[str, str]:
        parsed = urlparse(uri)
        if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
            raise ValueError(f"Invalid S3 URI: {uri}")

        return parsed.netloc, parsed.path.lstrip("/")

    def _write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":

    async def main():
        class Model(BaseModel):
            field1: str
            field2: int

        s3_service = S3Service()

        artifact_uri = await s3_service.store_artifact(
            bucket_name="my-bucket",
            artifact_name="test/artifact.json",
            artifact_data=Model(field1="value1", field2=123),
        )
        print(f"Stored artifact at: {artifact_uri}")

        fetched_data = await s3_service.fetch_artifact(artifact_uri, model=Model)
        print(f"Fetched artifact data: {fetched_data}")

    asyncio.run(main())

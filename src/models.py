from pydantic import BaseModel, ConfigDict


class AppendArtifact(BaseModel):
    model_config = ConfigDict(extra="allow")

    artifact_name: str

from pydantic import BaseModel, Field


class DeleteDatasetRequest(BaseModel):
    confirmation: str
    force: bool = False


class DeleteModelRequest(BaseModel):
    confirmation: str


class ResetDatabaseRequest(BaseModel):
    scope: str = Field(pattern="^(training|synthetic|all)$")
    confirmation: str
    delete_files: bool = False

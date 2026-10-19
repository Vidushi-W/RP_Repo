from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetVersion, ImportJob, Recording


class DatasetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_datasets(self) -> list[Dataset]:
        return list(self.db.scalars(select(Dataset).order_by(Dataset.updated_at.desc())))

    def get_dataset(self, dataset_id: int) -> Dataset | None:
        return self.db.get(Dataset, dataset_id)

    def get_recording(self, dataset_id: int, recording_id: str) -> Recording | None:
        return self.db.scalars(
            select(Recording).where(Recording.dataset_id == dataset_id, Recording.recording_id == recording_id)
        ).first()

    def list_recordings(self, dataset_id: int) -> list[Recording]:
        return list(self.db.scalars(select(Recording).where(Recording.dataset_id == dataset_id).order_by(Recording.recording_id)))

    def list_import_jobs(self) -> list[ImportJob]:
        return list(self.db.scalars(select(ImportJob).order_by(ImportJob.created_at.desc()).limit(20)))

    def content_hash_exists(self, dataset_id: int, content_hash: str) -> bool:
        return (
            self.db.scalar(
                select(func.count()).select_from(Recording).where(
                    Recording.dataset_id == dataset_id, Recording.content_hash == content_hash
                )
            )
            or 0
        ) > 0

    def add_activity(self, event_type: str, message: str) -> None:
        from app.models.activity import ActivityLog

        self.db.add(ActivityLog(event_type=event_type, message=message))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ActivityLog, Dataset, EvaluationRun, MLModel, TrainingJob


class SystemRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_datasets(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Dataset)) or 0

    def count_models(self) -> int:
        return self.db.scalar(select(func.count()).select_from(MLModel)) or 0

    def count_training_jobs(self) -> int:
        return self.db.scalar(select(func.count()).select_from(TrainingJob)) or 0

    def count_evaluations(self) -> int:
        return self.db.scalar(select(func.count()).select_from(EvaluationRun)) or 0

    def latest_training_job(self) -> TrainingJob | None:
        return self.db.scalars(select(TrainingJob).order_by(TrainingJob.created_at.desc()).limit(1)).first()

    def latest_evaluation(self) -> EvaluationRun | None:
        return self.db.scalars(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1)).first()

    def active_model(self) -> MLModel | None:
        return self.db.scalars(
            select(MLModel).where(MLModel.status == "active").order_by(MLModel.created_at.desc()).limit(1)
        ).first()

    def recent_activity(self, limit: int = 8) -> list[ActivityLog]:
        return list(self.db.scalars(select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)))

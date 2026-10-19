from sqlalchemy.orm import Session

from app.repositories.system import SystemRepository
from app.schemas.system import (
    ActivityItem,
    EvaluationSummary,
    ModelSummary,
    SystemStatusResponse,
    TrainingJobSummary,
)
from app.sensors.base import HardwareGloveSource


class SystemService:
    def __init__(self, db: Session) -> None:
        self.repo = SystemRepository(db)

    def get_status(self) -> SystemStatusResponse:
        dataset_count = self.repo.count_datasets()
        model_count = self.repo.count_models()
        active = self.repo.active_model()
        latest_job = self.repo.latest_training_job()
        latest_eval = self.repo.latest_evaluation()
        activity = self.repo.recent_activity()

        return SystemStatusResponse(
            backend_healthy=True,
            database_ready=True,
            dataset_count=dataset_count,
            model_count=model_count,
            active_model=(
                ModelSummary(id=active.id, name=active.name, version=active.version, status=active.status)
                if active
                else None
            ),
            latest_training_job=(
                TrainingJobSummary(
                    id=latest_job.id,
                    name=latest_job.name,
                    status=latest_job.status,
                    message=latest_job.message,
                    updated_at=latest_job.updated_at,
                )
                if latest_job
                else None
            ),
            latest_evaluation=(
                EvaluationSummary(
                    id=latest_eval.id,
                    name=latest_eval.name,
                    status=latest_eval.status,
                    summary=latest_eval.summary,
                    sequence_accuracy=latest_eval.sequence_accuracy,
                    created_at=latest_eval.created_at,
                )
                if latest_eval
                else None
            ),
            recent_activity=[
                ActivityItem(
                    id=a.id,
                    event_type=a.event_type,
                    message=a.message,
                    created_at=a.created_at,
                )
                for a in activity
            ],
            setup_complete=dataset_count > 0 and model_count > 0,
            hardware_gloves_connected=HardwareGloveSource.is_available(),
            features={
                "dataset_import": "planned",
                "training": "planned",
                "evaluation": "planned",
                "playground_recognition": "planned",
                "hardware_gloves": "not_connected",
            },
        )

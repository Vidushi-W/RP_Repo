"""Recognition feedback — uncertainty messages and future hardware vibration routing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FeedbackEvent:
    event_type: str
    message: str
    routed_to_hardware: bool
    simulated: bool


class FeedbackService:
    """UI feedback today; same interface can route to glove vibration motor later."""

    UNCERTAIN_MESSAGE = "Recognition uncertain. Please repeat the sequence."

    @staticmethod
    def on_uncertain_recognition(decoder_score: float, threshold: float) -> FeedbackEvent:
        return FeedbackEvent(
            event_type="repeat_request",
            message=FeedbackService.UNCERTAIN_MESSAGE,
            routed_to_hardware=False,
            simulated=True,
        )

    @staticmethod
    def on_vibration_request() -> FeedbackEvent:
        return FeedbackEvent(
            event_type="vibration_request",
            message="Simulated repeat-request signal (no physical glove motor connected).",
            routed_to_hardware=False,
            simulated=True,
        )

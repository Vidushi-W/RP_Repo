"""Hands-free visual sign-practice demo with locked sequence feedback."""

from __future__ import annotations

import os
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from backend.metrics import compare_pose_sequences, joint_angle_degrees
from backend.normalization import normalize_landmarks
from backend.reference_loader import load_reference_sequences
from backend.ml_classifier import load_error_classifier, predict_sequence
from backend.remediation_engine import recommend_from_history
from frontend.api_client import load_recent_attempts, save_practice_result


PROMPT_SECONDS = 4.5
COUNTDOWN_SECONDS = 3.0
CAPTURE_SECONDS = 4.0
RESULT_SECONDS = 4.0
SAMPLE_EVERY_N_FRAMES = 2
MIN_VALID_FRAMES = 5
ANGLE_TOLERANCE_DEGREES = 20.0


def open_webcam() -> cv2.VideoCapture:
    """Open the default camera for the practice and data-collection screens."""
    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError("Could not open webcam. Check camera access or index.")
    return capture


def angle_error_status(error_degrees: float) -> str:
    """Classify a median absolute angle difference against its reference."""
    if not np.isfinite(error_degrees):
        return "N/A"
    return "OK" if error_degrees <= ANGLE_TOLERANCE_DEGREES else "Needs adjustment"


def draw_hand_landmarks(frame: np.ndarray, landmarks: list) -> None:
    """Draw one MediaPipe Tasks hand skeleton onto a BGR frame."""
    height, width = frame.shape[:2]
    for connection in vision.HandLandmarksConnections.HAND_CONNECTIONS:
        start, end = landmarks[connection.start], landmarks[connection.end]
        cv2.line(
            frame,
            (int(start.x * width), int(start.y * height)),
            (int(end.x * width), int(end.y * height)),
            (80, 220, 80), 2, cv2.LINE_AA,
        )
    for point in landmarks:
        cv2.circle(
            frame, (int(point.x * width), int(point.y * height)),
            4, (40, 80, 255), -1, cv2.LINE_AA,
        )


def draw_sign_picture(canvas: np.ndarray, sign: str, center: tuple[int, int], size: int = 150) -> None:
    """Draw a simple picture cue for the six practice signs without text labels."""
    cx, cy = center
    scale = size / 150.0

    def p(x: float, y: float) -> tuple[int, int]:
        return int(cx + (x - 75) * scale), int(cy + (y - 75) * scale)

    if "book" in sign:
        cv2.rectangle(canvas, p(25, 35), p(73, 112), (225, 150, 55), -1)
        cv2.rectangle(canvas, p(77, 35), p(125, 112), (245, 245, 238), -1)
        cv2.rectangle(canvas, p(25, 35), p(73, 112), (255, 255, 255), 2)
        cv2.rectangle(canvas, p(77, 35), p(125, 112), (255, 255, 255), 2)
        cv2.line(canvas, p(75, 35), p(75, 114), (40, 85, 145), 5)
        for y in (55, 70, 85):
            cv2.line(canvas, p(38, y), p(65, y), (185, 205, 220), 2)
            cv2.line(canvas, p(85, y), p(112, y), (185, 205, 220), 2)
    elif "house" in sign:
        roof = np.asarray([p(22, 65), p(75, 25), p(128, 65)], dtype=np.int32)
        cv2.fillPoly(canvas, [roof], (70, 105, 220))
        cv2.rectangle(canvas, p(34, 63), p(116, 120), (170, 190, 245), -1)
        cv2.rectangle(canvas, p(67, 87), p(88, 120), (70, 95, 165), -1)
        cv2.rectangle(canvas, p(43, 75), p(58, 90), (235, 245, 255), -1)
        cv2.rectangle(canvas, p(94, 75), p(108, 90), (235, 245, 255), -1)
    elif "pen" in sign:
        cv2.line(canvas, p(43, 112), p(103, 43), (60, 170, 230), 16, cv2.LINE_AA)
        cv2.line(canvas, p(39, 117), p(43, 112), (60, 60, 80), 9, cv2.LINE_AA)
        cv2.line(canvas, p(98, 39), p(108, 48), (245, 220, 120), 10, cv2.LINE_AA)
        cv2.line(canvas, p(28, 125), p(117, 125), (210, 210, 210), 3)
    elif "come" in sign:
        cv2.circle(canvas, p(75, 40), 15, (200, 190, 110), -1)
        cv2.line(canvas, p(75, 58), p(75, 112), (200, 190, 110), 12)
        cv2.line(canvas, p(75, 78), p(46, 98), (200, 190, 110), 9)
        cv2.line(canvas, p(75, 78), p(104, 98), (200, 190, 110), 9)
        cv2.arrowedLine(canvas, p(10, 75), p(43, 75), (80, 220, 110), 6, cv2.LINE_AA, tipLength=0.35)
    elif "go" in sign:
        cv2.circle(canvas, p(63, 40), 15, (200, 190, 110), -1)
        cv2.line(canvas, p(63, 58), p(63, 112), (200, 190, 110), 12)
        cv2.line(canvas, p(63, 78), p(36, 98), (200, 190, 110), 9)
        cv2.line(canvas, p(63, 78), p(89, 98), (200, 190, 110), 9)
        cv2.arrowedLine(canvas, p(96, 75), p(139, 75), (80, 220, 110), 6, cv2.LINE_AA, tipLength=0.35)
    elif "like" in sign:
        cv2.circle(canvas, p(57, 58), 24, (70, 75, 235), -1)
        cv2.circle(canvas, p(94, 58), 24, (70, 75, 235), -1)
        heart = np.asarray([p(33, 65), p(75, 119), p(118, 65)], dtype=np.int32)
        cv2.fillPoly(canvas, [heart], (70, 75, 235))
    else:
        cv2.circle(canvas, (cx, cy), int(size * 0.38), (180, 190, 210), -1)


def load_reference_cues(signs: list[str]) -> dict[str, np.ndarray]:
    """Load the real source image, or a first video frame, for each cue."""
    root = Path(__file__).resolve().parents[1] / "references"
    cues: dict[str, np.ndarray] = {}
    for sign in signs:
        folder = root / sign
        sources = sorted(
            path for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".mp4", ".mov", ".avi", ".mkv"}
        ) if folder.exists() else []
        for source in sources:
            if source.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                cue = cv2.imread(str(source))
            else:
                video = cv2.VideoCapture(str(source))
                ok, cue = video.read()
                video.release()
                if not ok:
                    cue = None
            if cue is not None:
                cues[sign] = cue
                break
    return cues


def _dominant_hand_count(frames: list[np.ndarray]) -> int:
    counts = [len(frame) for frame in frames]
    return max(set(counts), key=lambda count: (counts.count(count), count))


def summarize_sequence(
    live_frames: list[np.ndarray], reference_sequences: list[list[np.ndarray]]
) -> dict[str, float | str]:
    """DTW-align the captured clip with its closest reference video or image."""
    if len(live_frames) < MIN_VALID_FRAMES:
        return {
            "message": (
                f"Captured {len(live_frames)} hand sample(s); at least {MIN_VALID_FRAMES} are needed. "
                "Keep the signing hand(s) visible during the full capture."
            )
        }

    live_hand_count = _dominant_hand_count(live_frames)
    live_sequence = [frame for frame in live_frames if len(frame) == live_hand_count]
    if len(live_sequence) < MIN_VALID_FRAMES:
        return {
            "message": (
                f"Captured {len(live_sequence)} consistent sample(s) with {live_hand_count} hand(s); "
                f"at least {MIN_VALID_FRAMES} are needed. Keep the same hand(s) visible throughout."
            )
        }

    best: dict[str, object] | None = None
    best_reference: list[np.ndarray] | None = None
    for reference in reference_sequences:
        if not reference or len(reference[0]) != live_hand_count:
            continue
        compared = compare_pose_sequences(live_sequence, reference)
        if compared and (best is None or compared["similarity"] > best["similarity"]):
            best, best_reference = compared, reference

    if best is None or best_reference is None:
        reference_counts = sorted({len(sequence[0]) for sequence in reference_sequences if sequence})
        expected = ", ".join(map(str, reference_counts)) or "no"
        return {
            "message": (
                f"Camera sees {live_hand_count} hand(s); this reference needs {expected}. "
                "Keep the required hand(s) visible for the whole capture."
            )
        }

    thumb_errors: list[float] = []
    index_errors: list[float] = []
    for live_index, ref_index, hand_pairs in best["alignment"]:
        for live_hand, ref_hand in hand_pairs:
            live_pose = live_sequence[live_index][live_hand]
            ref_pose = best_reference[ref_index][ref_hand]
            thumb_live = joint_angle_degrees(live_pose, 2, 3, 4)
            thumb_ref = joint_angle_degrees(ref_pose, 2, 3, 4)
            index_live = joint_angle_degrees(live_pose, 5, 6, 7)
            index_ref = joint_angle_degrees(ref_pose, 5, 6, 7)
            if np.isfinite([thumb_live, thumb_ref]).all():
                thumb_errors.append(abs(thumb_live - thumb_ref))
            if np.isfinite([index_live, index_ref]).all():
                index_errors.append(abs(index_live - index_ref))

    thumb_error = float(np.median(thumb_errors)) if thumb_errors else float("nan")
    index_error = float(np.median(index_errors)) if index_errors else float("nan")
    return {
        "similarity": float(best["similarity"]),
        "dtw_distance": float(best["distance"]),
        "thumb_status": angle_error_status(thumb_error),
        "index_status": angle_error_status(index_error),
    }


def draw_frontend(
    camera_frame: np.ndarray,
    sign: str,
    state: str,
    seconds_left: float,
    hands_detected: int,
    result: dict[str, float | str] | None,
    sign_index: int,
    sign_count: int,
    cue_image: np.ndarray | None = None,
) -> np.ndarray:
    """Compose camera view, picture cue, phase instructions and locked score."""
    view_height, view_width, panel_width = 540, 720, 350
    camera = cv2.resize(camera_frame, (view_width, view_height))
    panel = np.full((view_height, panel_width, 3), (34, 37, 48), dtype=np.uint8)
    if cue_image is None:
        draw_sign_picture(panel, sign, (panel_width // 2, 135), 155)
    else:
        max_width, max_height = panel_width - 36, 185
        cue_height, cue_width = cue_image.shape[:2]
        scale = min(max_width / cue_width, max_height / cue_height)
        resized = cv2.resize(cue_image, (int(cue_width * scale), int(cue_height * scale)))
        y0 = 35 + (max_height - resized.shape[0]) // 2
        x0 = (panel_width - resized.shape[1]) // 2
        panel[y0:y0 + resized.shape[0], x0:x0 + resized.shape[1]] = resized
    cv2.putText(panel, f"Sign {sign_index + 1} of {sign_count}", (24, 258), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (190, 195, 210), 1, cv2.LINE_AA)

    if state == "prompt":
        lines = ["Look at the picture", "Signing starts automatically", f"Next in {seconds_left:.1f} sec"]
    elif state == "countdown":
        lines = ["Get ready", f"Starting in {seconds_left:.0f}"]
    elif state == "capture":
        lines = ["Sign now", f"Recording: {seconds_left:.1f} sec", f"Hands detected: {hands_detected}"]
    elif state == "analyze":
        lines = ["Matching the sign movement..."]
    elif state == "paused":
        lines = ["Paused", "Press P to continue"]
    else:
        lines = ["Result locked"]
        if result and "similarity" in result:
            lines += [f"DTW pose similarity: {result['similarity']:.1f}%", f"Thumb: {result['thumb_status']}", f"Index: {result['index_status']}"]
            diagnosis = result.get("ml_label", "unavailable")
            if diagnosis == "NORMAL":
                diagnosis = "No trained error detected"
            elif diagnosis.startswith("ERR_"):
                diagnosis = f"Provisional: {diagnosis}"
            elif diagnosis == "UNSUPPORTED_SIGN":
                diagnosis = "Not trained for this sign"
            elif diagnosis == "NO_SINGLE_HAND_DATA":
                diagnosis = "Needs one visible hand"
            lines.append(f"RF diagnosis: {diagnosis}")
            if result.get("ml_confidence") is not None:
                lines.append(f"RF vote confidence (not accuracy): {result['ml_confidence']:.0%}")
            if result.get("recommendation"):
                lines.append(f"Practice: {result['recommendation']}")
            if result.get("save_status"):
                lines.append(str(result["save_status"]))
        elif result:
            lines += [str(result.get("message", "No result available."))]
        lines += ["Next picture appears automatically"]

    y = 305
    for line in lines:
        wrapped_lines = textwrap.wrap(line, width=38) or [""]
        for wrapped_line in wrapped_lines:
            cv2.putText(panel, wrapped_line, (24, y), cv2.FONT_HERSHEY_SIMPLEX, 0.49, (245, 245, 245), 1, cv2.LINE_AA)
            y += 30
    cv2.putText(panel, "1-6 choose | P pause | R retry", (18, view_height - 42), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (190, 195, 210), 1, cv2.LINE_AA)
    cv2.putText(panel, "N next | Q quit", (18, view_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (190, 195, 210), 1, cv2.LINE_AA)

    combined = np.zeros((view_height, view_width + panel_width, 3), dtype=np.uint8)
    combined[:, :view_width] = camera
    combined[:, view_width:] = panel
    cv2.putText(combined, "Follow the picture and sign when recording starts", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)
    return combined


def main() -> None:
    references = load_reference_sequences()
    if not references:
        raise FileNotFoundError("No processed reference templates. Run python -m backend.process_references first.")
    labels = list(references)
    reference_cues = load_reference_cues(labels)
    model_path = Path(__file__).resolve().parents[1] / "kinematic_error_classifier.pkl"
    classifier = load_error_classifier(model_path)
    if classifier:
        evaluation = classifier.get("evaluation", {})
        print(
            "Loaded provisional kinematic classifier; labels:", classifier.get("labels"),
            "supported signs:", classifier.get("sign_ids"),
            "stored held-out frame score:", evaluation.get("test_frame_accuracy", "not recorded"),
        )
    else:
        if model_path.exists():
            print("Kinematic classifier is not approved by grouped validation; ML diagnosis is disabled.")
        else:
            print("Kinematic classifier artifact missing; ML diagnosis is unavailable.")
    user_id = os.getenv("SLSL_USER_ID", "student_01").strip() or "student_01"
    selected_index = 0
    state = "prompt"
    state_started = time.monotonic()
    paused_state = "prompt"
    paused_at = 0.0
    live_frames: list[np.ndarray] = []
    scoring_frames: list[np.ndarray] = []
    session_result: dict[str, float | str] | None = None
    frame_counter = 0

    hand_model_path = Path(__file__).resolve().parents[1] / "hand_landmarker.task"
    if not hand_model_path.exists():
        raise FileNotFoundError("Missing hand_landmarker.task; see README.md for setup.")
    capture = open_webcam()

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(hand_model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    try:
        with vision.HandLandmarker.create_from_options(options) as hands:
            timestamp_ms = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    print("Could not read a frame from the webcam.")
                    break
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp_ms += 33
                result = hands.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)

                live_poses: list[np.ndarray] = []
                scoring_poses: list[np.ndarray] = []
                for hand in result.hand_landmarks or []:
                    draw_hand_landmarks(frame, hand)
                    raw = np.asarray([[point.x, point.y, point.z] for point in hand], dtype=np.float32)
                    normalized = normalize_landmarks(raw)
                    live_poses.append(normalized)
                    reference_orientation = normalized.copy()
                    # The preview is mirrored for the signer; reference media is not.
                    reference_orientation[:, 0] *= -1.0
                    scoring_poses.append(reference_orientation)

                now = time.monotonic()
                elapsed = now - state_started
                if state == "prompt" and elapsed >= PROMPT_SECONDS:
                    state, state_started = "countdown", now
                elif state == "countdown" and elapsed >= COUNTDOWN_SECONDS:
                    state, state_started = "capture", now
                    live_frames = []
                    scoring_frames = []
                    frame_counter = 0
                elif state == "capture":
                    frame_counter += 1
                    if live_poses and frame_counter % SAMPLE_EVERY_N_FRAMES == 0:
                        live_frames.append(np.stack(live_poses))
                        scoring_frames.append(np.stack(scoring_poses))
                    if elapsed >= CAPTURE_SECONDS:
                        state, state_started = "analyze", now
                elif state == "analyze":
                    analysis_started = time.monotonic()
                    session_result = summarize_sequence(scoring_frames, references[labels[selected_index]])
                    prediction = predict_sequence(classifier, live_frames, labels[selected_index])
                    if prediction:
                        session_result["ml_label"] = prediction["label"]
                        session_result["ml_confidence"] = prediction.get("confidence")
                    if "similarity" in session_result:
                        error_codes = []
                        if prediction and str(prediction.get("label", "")).startswith("ERR_"):
                            error_codes = [prediction["label"]]
                        expected_hands = len(references[labels[selected_index]][0][0])
                        payload = {
                            "user_id": user_id,
                            "sign_id": labels[selected_index],
                            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                            "hands_detected": int(_dominant_hand_count(live_frames)),
                            "expected_hands": expected_hands,
                            "status": "COMPLETED",
                            "metrics": {
                                "dtw_distance": float(session_result["dtw_distance"]),
                                "similarity_score": float(session_result["similarity"]),
                                "analysis_latency_ms": max(0.0, (time.monotonic() - analysis_started) * 1000.0),
                                "ml_prediction": prediction.get("label") if prediction else None,
                                "ml_confidence": prediction.get("confidence") if prediction else None,
                            },
                            "detected_error_codes": error_codes,
                        }
                        if error_codes:
                            payload["kinematic_observation"] = {
                                "feature_schema": "wrist_origin_unit_scale_xyz_v1",
                                "frames": [
                                    {"frame_index": i, "hands": frame.astype(float).tolist()}
                                    for i, frame in enumerate(live_frames[:120])
                                ],
                            }
                        attempts, _ = load_recent_attempts(user_id, limit=4)
                        if attempts is not None:
                            recommendations = recommend_from_history([*attempts[:4], payload])
                            if recommendations:
                                session_result["recommendation"] = recommendations[0]["exercise"]
                        else:
                            session_result["recommendation"] = "History unavailable; no recurrence recommendation"
                        _, save_status = save_practice_result(payload)
                        session_result["save_status"] = save_status
                    state, state_started = "result", now
                elif state == "result" and elapsed >= RESULT_SECONDS:
                    selected_index = (selected_index + 1) % len(labels)
                    state, state_started = "prompt", now
                    session_result = None

                if state == "prompt":
                    seconds_left = max(0.0, PROMPT_SECONDS - (time.monotonic() - state_started))
                elif state == "countdown":
                    seconds_left = max(0.0, COUNTDOWN_SECONDS - (time.monotonic() - state_started))
                elif state == "capture":
                    seconds_left = max(0.0, CAPTURE_SECONDS - (time.monotonic() - state_started))
                else:
                    seconds_left = 0.0

                view = draw_frontend(
                    frame, labels[selected_index], state, seconds_left,
                    len(live_poses), session_result, selected_index, len(labels),
                    reference_cues.get(labels[selected_index]),
                )
                cv2.imshow("SLSL Sign Practice", view)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("p"):
                    if state == "paused":
                        state = paused_state
                        state_started += time.monotonic() - paused_at
                    else:
                        paused_state = state
                        paused_at = time.monotonic()
                        state = "paused"
                elif state != "paused" and key in (ord("r"), ord("R")):
                    state, state_started = "prompt", time.monotonic()
                    session_result = None
                elif state != "paused" and key in (ord("n"), ord("N")):
                    selected_index = (selected_index + 1) % len(labels)
                    state, state_started, session_result = "prompt", time.monotonic(), None
                elif state != "paused" and ord("1") <= key <= ord("8"):
                    requested_index = key - ord("1")
                    if requested_index < len(labels):
                        selected_index = requested_index
                        state, state_started, session_result = "prompt", time.monotonic(), None
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

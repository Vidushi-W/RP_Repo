"""Collect labeled single-hand kinematic examples from the webcam.

Press 1 for NORMAL, 2 for ERR_PINKY_FLEX, or 3 for ERR_INDEX_EXT. Each key
records one independent capture session; repeat each label in multiple
sessions for meaningful session-held-out evaluation. Press Q to quit.
"""

from __future__ import annotations

import argparse
import csv
import os
import time
import uuid
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from frontend.main import draw_hand_landmarks, open_webcam
from backend.ml_features import FEATURE_NAMES, extract_features
from backend.normalization import normalize_landmarks
from backend.dataset_schema import ensure_current_dataset_schema


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "kinematic_dataset.csv"
LABEL_KEYS = {
    ord("1"): "NORMAL",
    ord("2"): "ERR_PINKY_FLEX",
    ord("3"): "ERR_INDEX_EXT",
    ord("4"): "ERR_WRIST_ROTATION",
}


def collect(output: Path, target_frames: int, signer_id: str, sign_id: str) -> None:
    """Append per-frame examples; session_id supports leakage-aware splitting."""
    model_path = ROOT / "hand_landmarker.task"
    if not model_path.exists():
        raise FileNotFoundError(f"Missing {model_path.name}; see README.md for setup.")
    output.parent.mkdir(parents=True, exist_ok=True)
    ensure_current_dataset_schema(output)
    needs_header = not output.exists() or output.stat().st_size == 0
    camera = open_webcam()
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    print("Use one signing hand. Keys: 1 NORMAL | 2 pinky flex | 3 index extension | 4 wrist rotation error | Q quit")
    print(f"Each key capture saves up to {target_frames} frames as a separate session.")
    print("Repeat every label in at least six sessions; vary distance and slight hand tilt between sessions.")
    print("Keep each label true to the visible pose, and collect every label from multiple signer IDs.")
    try:
        with output.open("a", newline="", encoding="utf-8") as data_file, vision.HandLandmarker.create_from_options(options) as detector:
            writer = csv.DictWriter(data_file, fieldnames=["label", "sign_id", "signer_id", "session_id", "frame_index", *FEATURE_NAMES])
            if needs_header:
                writer.writeheader()
            active_label: str | None = None
            session_id = ""
            captured = 0
            rows_written = 0
            started = 0.0
            timestamp_ms = 0
            while True:
                ok, frame = camera.read()
                if not ok:
                    print("Webcam stopped providing frames.")
                    break
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp_ms += 33
                result = detector.detect_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms
                )
                hands = result.hand_landmarks or []
                for hand in hands:
                    draw_hand_landmarks(frame, hand)

                if active_label:
                    if hands:
                        hand = hands[0]
                        raw = np.asarray([[point.x, point.y, point.z] for point in hand], dtype=np.float32)
                        features = extract_features(normalize_landmarks(raw))
                        row = {
                            "label": active_label,
                            "sign_id": sign_id,
                            "signer_id": signer_id,
                            "session_id": session_id,
                            "frame_index": captured,
                        }
                        row.update(dict(zip(FEATURE_NAMES, features.tolist())))
                        writer.writerow(row)
                        captured += 1
                        rows_written += 1
                        if captured % 10 == 0:
                            data_file.flush()
                    elapsed = time.monotonic() - started
                    cv2.putText(frame, f"{active_label}: {captured}/{target_frames}", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (40, 240, 80), 2)
                    if captured >= target_frames:
                        data_file.flush()
                        print(f"Saved {captured} frames: {active_label}, session {session_id}")
                        active_label = None
                    elif elapsed > 30:
                        print(f"Capture timed out; saved {captured} frames for {active_label}.")
                        data_file.flush()
                        active_label = None
                else:
                    cv2.putText(frame, "1 NORMAL | 2 PINKY | 3 INDEX | 4 WRIST ROTATION | Q QUIT", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                    cv2.putText(frame, f"Label context: {sign_id} | signer: {signer_id}", (15, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

                cv2.imshow("SLSL Kinematic Data Collection", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q")):
                    break
                if not active_label and key in LABEL_KEYS:
                    active_label = LABEL_KEYS[key]
                    session_id = uuid.uuid4().hex
                    captured = 0
                    started = time.monotonic()
                    print(f"Recording {active_label}; keep the pose/movement clear and consistent.")
    finally:
        camera.release()
        cv2.destroyAllWindows()
    print(f"Dataset saved locally: {output.resolve()} ({rows_written} new rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--frames", type=int, default=50, help="Detected frames to save per capture")
    parser.add_argument("--signer-id", default=os.getenv("SLSL_SIGNER_ID", "signer_01"), help="Pseudonymous participant ID")
    parser.add_argument("--sign-id", default=os.getenv("SLSL_DATA_SIGN_ID", "like"), help="Sign being practiced during all captures")
    args = parser.parse_args()
    if args.frames < 1:
        parser.error("--frames must be at least 1")
    collect(args.output, args.frames, args.signer_id, args.sign_id)


if __name__ == "__main__":
    main()

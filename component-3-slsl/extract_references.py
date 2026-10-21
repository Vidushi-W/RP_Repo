"""Extract normalized MediaPipe hand poses from labeled image/video folders.

Input layout::

    references/<sign-label>/*.jpg
    references/<sign-label>/*.png
    references/<sign-label>/*.mp4

Outputs one ``.npz`` per sign in ``references/processed``. Each row is one
detected hand pose, with its source filename, frame number, and hand index.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from normalization import normalize_landmarks


ROOT = Path(__file__).parent
REFERENCES_DIR = ROOT / "references"
OUTPUT_DIR = REFERENCES_DIR / "processed"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
SAMPLE_EVERY_N_FRAMES = 2  # About 15 samples/second for 30 FPS source clips.


def landmarks_to_array(points: list) -> np.ndarray:
    """Convert a MediaPipe Tasks hand landmark list to normalized XYZ."""
    raw = np.asarray([[point.x, point.y, point.z] for point in points], dtype=np.float32)
    return normalize_landmarks(raw)


def main() -> None:
    model_path = ROOT / "hand_landmarker.task"
    if not model_path.exists():
        raise FileNotFoundError(f"MediaPipe model not found: {model_path}")
    if not REFERENCES_DIR.exists():
        raise FileNotFoundError(f"Reference input folder not found: {REFERENCES_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    labels = sorted(
        path for path in REFERENCES_DIR.iterdir()
        if path.is_dir() and path.name != OUTPUT_DIR.name
    )
    if not labels:
        raise RuntimeError(f"No sign folders found under {REFERENCES_DIR}")

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.3,
        min_hand_presence_confidence=0.3,
        min_tracking_confidence=0.3,
    )

    with vision.HandLandmarker.create_from_options(options) as landmarker:
        timestamp_ms = 0
        for label_dir in labels:
            poses: list[np.ndarray] = []
            sources: list[str] = []
            frame_numbers: list[int] = []
            hand_indices: list[int] = []
            media_files = sorted(
                file for file in label_dir.iterdir()
                if file.suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
            )

            for media_path in media_files:
                if media_path.suffix.lower() in IMAGE_EXTENSIONS:
                    image = cv2.imread(str(media_path))
                    if image is None:
                        print(f"Skipping unreadable image: {media_path}")
                        continue
                    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    timestamp_ms += 1
                    result = landmarker.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms
                    )
                    detections = [(0, result.hand_landmarks)]
                else:
                    detections = []
                    capture = cv2.VideoCapture(str(media_path))
                    if not capture.isOpened():
                        print(f"Skipping unreadable video: {media_path}")
                        continue
                    frame_number = 0
                    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
                    while True:
                        ok, frame = capture.read()
                        if not ok:
                            break
                        if frame_number % SAMPLE_EVERY_N_FRAMES == 0:
                            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            timestamp_ms += max(1, round(SAMPLE_EVERY_N_FRAMES * 1000.0 / fps))
                            result = landmarker.detect_for_video(
                                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                                timestamp_ms,
                            )
                            detections.append((frame_number, result.hand_landmarks))
                        frame_number += 1
                    capture.release()

                detected_count = 0
                for frame_number, detected_hands in detections:
                    for hand_index, hand in enumerate(detected_hands):
                        poses.append(landmarks_to_array(hand))
                        sources.append(media_path.name)
                        frame_numbers.append(frame_number)
                        hand_indices.append(hand_index)
                        detected_count += 1
                print(f"{label_dir.name}/{media_path.name}: extracted {detected_count} hand poses")

            if not poses:
                print(f"No hands detected for '{label_dir.name}'; no template saved.")
                continue

            output_path = OUTPUT_DIR / f"{label_dir.name}.npy"
            metadata_path = OUTPUT_DIR / f"{label_dir.name}.json"
            np.save(output_path, np.stack(poses))
            metadata_path.write_text(
                json.dumps(
                    {
                        "sign_label": label_dir.name,
                        "pose_count": len(poses),
                        "source_files": sources,
                        "frame_numbers": frame_numbers,
                        "hand_indices": hand_indices,
                        "normalization": "wrist-origin, unit maximum wrist distance",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(
                f"Saved {len(poses)} normalized poses -> "
                f"{output_path.relative_to(ROOT)}"
            )


if __name__ == "__main__":
    main()

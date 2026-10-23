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
from types import SimpleNamespace

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from backend.normalization import normalize_landmarks


ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = ROOT / "references"
OUTPUT_DIR = REFERENCES_DIR / "processed"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
SAMPLE_EVERY_N_FRAMES = 2  # About 15 samples/second for 30 FPS source clips.
EXPECTED_HANDS_PATH = REFERENCES_DIR / "sign_requirements.json"


def _square_crop(image: np.ndarray, x_start: int, x_end: int) -> tuple[np.ndarray, int, int]:
    """Crop a vertical image slice and pad it square without distorting its hands."""
    height, width = image.shape[:2]
    crop = image[:, x_start:x_end]
    side = max(height, crop.shape[1])
    pad_left = (side - crop.shape[1]) // 2
    pad_right = side - crop.shape[1] - pad_left
    padded = cv2.copyMakeBorder(
        crop, 0, 0, pad_left, pad_right, cv2.BORDER_CONSTANT, value=(0, 0, 0)
    )
    return padded, pad_left, side


def _restore_crop_hand(hand: list, x_start: int, pad_left: int, square_side: int,
                       width: int, height: int) -> list:
    """Map crop-normalized landmarks back to normalized full-frame coordinates."""
    return [
        SimpleNamespace(
            x=(x_start + float(point.x) * square_side - pad_left) / width,
            y=float(point.y) * square_side / height,
            z=float(point.z) * square_side / width,
        )
        for point in hand
    ]


def _recover_two_crop_hands(
    image: np.ndarray, landmarker, timestamp_ms: int, full_frame_hands: list | None = None
) -> list[list]:
    """Combine full-frame and overlapping crop detections, deduplicating hands."""
    height, width = image.shape[:2]
    split = width // 2
    overlap = max(1, round(width * 0.20))
    regions = (
        (0, min(width, split + overlap // 2)),
        (max(0, split - overlap // 2), width),
    )
    candidates: list[list] = []
    for hand in full_frame_hands or []:
        candidates.append(hand)
    for side, (x_start, x_end) in enumerate(regions):
        crop, pad_left, square_side = _square_crop(image, x_start, x_end)
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        result = landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms + side
        )
        for hand in result.hand_landmarks or []:
            # Convert crop-normalized coordinates back into the original
            # frame coordinate system before normalizing the hand. Without
            # this, square padding stretches x/y differently from a full
            # frame detection and makes the reference incomparable to webcam
            # landmarks.
            candidates.append(_restore_crop_hand(hand, x_start, pad_left, square_side, width, height))

    # A hand seen in the full frame and in both crops should contribute once.
    # Compare wrist/palm centers in original image coordinates, not crop units.
    unique: list[tuple[float, float, list]] = []
    for hand in candidates:
        center_x = float(np.mean([point.x for point in hand]))
        center_y = float(np.mean([point.y for point in hand]))
        if any(np.hypot(center_x - x, center_y - y) < 0.11 for x, y, _ in unique):
            continue
        unique.append((center_x, center_y, hand))
    if len(unique) < 2:
        return []

    # Two hands can be close together (as in HOUSE), so don't require a fixed
    # left/right ordering or distance. Prefer hands from distinct image areas.
    best_pair = max(
        ((first, second) for index, first in enumerate(unique) for second in unique[index + 1:]),
        key=lambda pair: np.hypot(pair[0][0] - pair[1][0], pair[0][1] - pair[1][1]),
    )
    if np.hypot(best_pair[0][0] - best_pair[1][0], best_pair[0][1] - best_pair[1][1]) < 0.06:
        return []
    return [item[2] for item in sorted(best_pair, key=lambda item: item[0])]


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
        min_hand_detection_confidence=0.15,
        min_hand_presence_confidence=0.15,
        min_tracking_confidence=0.15,
    )

    requirements = json.loads(EXPECTED_HANDS_PATH.read_text(encoding="utf-8")) if EXPECTED_HANDS_PATH.exists() else {}

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
                    image_hands = list(result.hand_landmarks or [])
                    expected_hands = requirements.get(label_dir.name, {}).get("expected_hands")
                    if expected_hands == 2 and len(image_hands) < 2:
                        image_hands = _recover_two_crop_hands(image, landmarker, timestamp_ms + 1)
                        timestamp_ms += 2
                        if len(image_hands) < 2:
                            print(f"Could not recover both hands in {media_path.name}; check the reference crop.")
                    detections = [(0, image_hands)]
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
                            video_hands = list(result.hand_landmarks or [])
                            expected_hands = requirements.get(label_dir.name, {}).get("expected_hands")
                            if expected_hands == 2 and len(video_hands) < 2:
                                video_hands = _recover_two_crop_hands(frame, landmarker, timestamp_ms + 1)
                                timestamp_ms += 2
                            detections.append((frame_number, video_hands))
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

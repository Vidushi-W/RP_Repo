"""Offline MP4 -> LankaSigns hand-animation schema v1. Never opens a camera."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

VERSION = "lankasigns-hands-1.0"
COMPONENT_ROOT = Path(__file__).resolve().parents[1]

def within_component(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(COMPONENT_ROOT):
        raise ValueError("All inputs, models and outputs must remain inside web/avatar-generation.")
    return resolved

def normalized_hand(landmarks):
    if len(landmarks) != 21:
        return None
    if any(not math.isfinite(p.x) or not math.isfinite(p.y) for p in landmarks):
        return None
    return [{"x": max(0.0, min(1.0, p.x)), "y": max(0.0, min(1.0, p.y))} for p in landmarks]

def extract(args):
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    source = within_component(args.input)
    model = within_component(args.model)
    output = within_component(args.output)
    if not source.is_file() or source.suffix.lower() != ".mp4":
        raise ValueError("Input must be an existing MP4 file, never a camera identifier.")
    if not model.is_file():
        raise ValueError("Supply an official local Hand Landmarker .task model.")
    if output.suffix.lower() != ".json" or output in (source, model):
        raise ValueError("Output must be a separate JSON file.")
    if output.exists():
        raise ValueError("Output exists. Choose a new path to preserve existing work.")
    if not re.fullmatch(r"[A-Z0-9_]{1,64}", args.sign_id):
        raise ValueError("Sign IDs must contain uppercase A-Z, digits or underscores.")
    if not math.isfinite(args.sample_fps) or not 1 <= args.sample_fps <= 60:
        raise ValueError("Sample FPS must be in [1, 60].")
    if not args.dataset_reference.strip():
        raise ValueError("Dataset provenance is required.")

    capture = cv2.VideoCapture(str(source))
    try:
        if not capture.isOpened():
            raise ValueError("OpenCV could not decode the MP4.")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("Source FPS is unavailable; repair the container first.")
        interval = 1000.0 / min(fps, args.sample_fps)
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=0.5, min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        frames, index, previous_ms, next_sample_ms = [], 0, -1, 0.0
        fallback_count = 0
        width = height = 0
        with vision.HandLandmarker.create_from_options(options) as detector:
            while True:
                ok, image = capture.read()
                if not ok:
                    break
                image_height, image_width = image.shape[:2]
                if not width:
                    width, height = image_width, image_height
                elif (width, height) != (image_width, image_height):
                    raise ValueError("Changing frame dimensions are not supported.")
                raw_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC))
                if not math.isfinite(raw_ms) or raw_ms < 0 or (index > 0 and raw_ms <= previous_ms):
                    raw_ms = index * 1000.0 / fps
                    fallback_count += 1
                timestamp_ms = max(previous_ms + 1, round(raw_ms))
                previous_ms = timestamp_ms
                index += 1
                if timestamp_ms + 0.5 < next_sample_ms:
                    continue
                while next_sample_ms <= timestamp_ms + 0.5:
                    next_sample_ms += interval
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                result = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)
                hands = {"leftHand": None, "rightHand": None}
                scores = {"leftHand": 0.0, "rightHand": 0.0}
                for landmarks, categories in zip(result.hand_landmarks, result.handedness):
                    if not categories:
                        continue
                    category = max(categories, key=lambda item: item.score)
                    name = category.category_name
                    if name not in ("Left", "Right") or category.score < args.handedness_threshold:
                        continue
                    if args.swap_handedness:
                        name = "Right" if name == "Left" else "Left"
                    key = "leftHand" if name == "Left" else "rightHand"
                    # Resolve same-side duplicates by score; never invent the other side.
                    if category.score > scores[key]:
                        hands[key] = normalized_hand(landmarks)
                        scores[key] = float(category.score)
                frames.append({"timestampMs": timestamp_ms, **hands})
        if not frames:
            raise ValueError("No decodable frames found.")
        output.parent.mkdir(parents=True, exist_ok=True)
        with model.open("rb") as handle:
            model_sha = hashlib.file_digest(handle, "sha256").hexdigest()
        animation = {
            "schemaVersion": 1, "signId": args.sign_id,
            "durationMs": max(frames[-1]["timestampMs"] + 1, previous_ms + round(1000.0 / fps)),
            "frames": frames,
            "metadata": {
                "sourceWidth": width, "sourceHeight": height,
                "sourceFile": source.name, "sourceFps": fps,
                "sampleIntervalMs": interval, "extractionVersion": VERSION,
                "mediapipeVersion": mp.__version__, "modelSha256": model_sha,
                "fixture": False, "datasetReference": args.dataset_reference,
                "timestampConvention": "OpenCV source timestamps with monotonic FPS fallback",
                "timestampFallbackFrames": fallback_count,
                "handednessConvention": "MediaPipe predictions; verify source mirroring manually",
                "handednessSwapped": args.swap_handedness,
                "coordinates": "full-frame normalized x,y; clipped to [0,1]; no mirroring",
                "reviewed": False,
            },
        }
        with output.open("x", encoding="utf-8") as handle:
            json.dump(animation, handle, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        print(f"Saved {len(frames)} frames to {output}. Review before registering a real sign.")
    finally:
        capture.release()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sign-id", required=True)
    parser.add_argument("--dataset-reference", required=True)
    parser.add_argument("--sample-fps", type=float, default=30)
    parser.add_argument("--handedness-threshold", type=float, default=0.65)
    parser.add_argument("--swap-handedness", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.handedness_threshold) or not 0 <= args.handedness_threshold <= 1:
        parser.error("Handedness threshold must be in [0,1].")
    try:
        extract(args)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Extraction failed: {error}\n")
if __name__ == "__main__":
    main()

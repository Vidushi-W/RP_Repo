"""Pure validation shared by offline processing and API registry resolution."""
import math


def validate_motion(data, expected_id=None):
    if data.get('schemaVersion') != 1 or (expected_id and data.get('signId') != expected_id):
        raise ValueError('Invalid animation identity')
    duration = data.get('durationMs')
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid duration')
    frames = data.get('frames')
    if not isinstance(frames, list) or not 1 <= len(frames) <= 200000:
        raise ValueError('Invalid frame count')
    previous = -1
    detections = {'hands': 0, 'pose': 0, 'face': 0}
    for frame in frames:
        timestamp = frame.get('timestampMs', -1)
        if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp) or not previous < timestamp <= duration:
            raise ValueError('Invalid frame timing')
        previous = timestamp
        for key, count in [('leftHand', 21), ('rightHand', 21), ('pose', 33), ('face', 478)]:
            points = frame.get(key)
            if points is None:
                continue
            if not isinstance(points, list) or len(points) != count:
                raise ValueError('Invalid landmark count: ' + key)
            for point in points:
                if point is None and key in ('pose', 'face'):
                    continue
                if not isinstance(point, dict) or any(not isinstance(point.get(axis), (float, int)) or not math.isfinite(point[axis]) or not 0 <= point[axis] <= 1 for axis in ('x', 'y')):
                    raise ValueError('Invalid landmark coordinates')
            if any(point is not None for point in points):
                detections['hands' if key.endswith('Hand') else key] += 1
    if not detections['hands']:
        raise ValueError('No hands detected; sign animation unavailable')
    return {'frames': len(frames), 'durationMs': duration, 'detections': detections}

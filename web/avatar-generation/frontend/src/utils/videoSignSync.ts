import type { SignSegment } from '../types/hands';
import { sequenceAt, sequenceDuration, type SequenceItem } from './signSequence';

export function videoSignPosition(segments: SignSegment[], items: SequenceItem[], timeMs: number, playing: boolean, speed=1) {
  if (!Number.isFinite(speed) || speed <= 0 || speed > 4) throw new Error('Invalid signing speed.');
  const index = Number.isFinite(timeMs) ? segments.findIndex(segment => segment.startMs <= timeMs && timeMs < segment.endMs) : -1;
  if (index < 0) return null;
  const segment = segments[index];
  const sequence = segment.signs.map(id => items.find(item => item.signId === id)).filter((item): item is SequenceItem => !!item);
  const elapsedMs = (timeMs-segment.startMs)*speed;
  const duration = sequenceDuration(sequence);
  return {
    segmentIndex:index,
    current: elapsedMs < duration ? sequenceAt(sequence,elapsedMs) : null,
    signs: segment.signs,
    playing: playing && elapsedMs < duration && duration > 0,
    progress: Math.min(1,(timeMs-segment.startMs)/(segment.endMs-segment.startMs)),
    clipped: duration / speed > segment.endMs-segment.startMs,
    elapsedMs, durationMs:duration,
  };
}

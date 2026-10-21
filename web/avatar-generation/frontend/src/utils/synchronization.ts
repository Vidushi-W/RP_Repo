import type { Cue, SyncState } from '../types';
export function validateCues(cues: Cue[]): Cue[] {
  const ids = new Set<string>();
  const sorted = [...cues].sort((a, b) => a.start - b.start);
  for (let i = 0; i < sorted.length; i++) {
    const cue = sorted[i];
    if (!cue.id || !cue.wordId || !cue.label || ids.has(cue.id) || !Number.isFinite(cue.start) || !Number.isFinite(cue.end) || cue.start < 0 || cue.end <= cue.start || (i > 0 && sorted[i - 1].end > cue.start)) throw new Error('Cues require unique IDs, valid non-overlapping time ranges, and word labels.');
    ids.add(cue.id);
  }
  return sorted;
}
export function synchronize(cues: Cue[], time: number, playing: boolean, speed = 1): SyncState {
  if (!Number.isFinite(speed) || speed <= 0) throw new Error('Signing speed must be positive.');
  const cue = Number.isFinite(time) ? cues.find(c => c.start <= time && time < c.end) ?? null : null;
  return { cue, animationTime: cue ? (time - cue.start) * speed : 0, playing: !!cue && playing };
}
export function formatTime(value: number) { const seconds = Math.max(0, Math.floor(Number.isFinite(value) ? value : 0)); return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`; }

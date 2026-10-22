import type { Hand, HandAnimation, HandFrame } from '../types/hands';

export function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
export function finite(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}
export function validSignId(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Z0-9_]{1,64}$/.test(value);
}
function parseHand(value: unknown): Hand {
  if (value === null) return null;
  if (!Array.isArray(value) || value.length !== 21) throw new Error('Each detected hand must contain exactly 21 landmarks; use null for a missing hand.');
  return value.map(point => {
    if (!record(point) || !finite(point.x) || !finite(point.y) || point.x < 0 || point.x > 1 || point.y < 0 || point.y > 1) throw new Error('Landmark x and y must be finite normalized coordinates in [0, 1].');
    return { x: point.x, y: point.y };
  });
}
function parseOptionalPoints(value:unknown,count:number):(HandFrame['pose']) {
  if(value===undefined)return undefined;
  if(value===null)return null;
  if(!Array.isArray(value)||value.length!==count)throw new Error('Invalid body or face landmark count.');
  return value.map(point=>{
    if(point===null)return null;
    if(!record(point)||!finite(point.x)||!finite(point.y)||point.x<0||point.x>1||point.y<0||point.y>1)throw new Error('Invalid body or face coordinates.');
    return {x:point.x,y:point.y};
  });
}
export function parseAnimation(value: unknown, expectedId?: string): HandAnimation {
  if (!record(value) || value.schemaVersion !== 1 || !validSignId(value.signId) || (expectedId && expectedId !== value.signId)) throw new Error('Invalid animation version or sign identifier.');
  if (!finite(value.durationMs) || value.durationMs <= 0) throw new Error('Animation duration must be positive milliseconds.');
  const metadata = value.metadata;
  if (!record(metadata) || !finite(metadata.sourceWidth) || !finite(metadata.sourceHeight) || metadata.sourceWidth <= 0 || metadata.sourceHeight <= 0 || metadata.sourceWidth > 40000 || metadata.sourceHeight > 40000 || typeof metadata.extractionVersion !== 'string') throw new Error('Source image dimensions and extraction version are required.');
  if (metadata.sampleIntervalMs !== undefined && (!finite(metadata.sampleIntervalMs) || metadata.sampleIntervalMs <= 0)) throw new Error('Invalid sample interval.');
  if (metadata.fixture !== undefined && typeof metadata.fixture !== 'boolean') throw new Error('Invalid fixture flag.');
  if (!Array.isArray(value.frames) || !value.frames.length || value.frames.length > 200000) throw new Error('Animation must contain 1–200000 timestamped frames.');
  let previous = -1;
  const frames: HandFrame[] = value.frames.map(frame => {
    if (!record(frame) || !finite(frame.timestampMs) || frame.timestampMs < 0 || frame.timestampMs <= previous || frame.timestampMs > (value.durationMs as number)) throw new Error('Frame timestamps must increase strictly and remain within duration.');
    previous = frame.timestampMs;
    const parsed:HandFrame={ timestampMs: frame.timestampMs, leftHand: parseHand(frame.leftHand), rightHand: parseHand(frame.rightHand) };
    if(frame.pose!==undefined)parsed.pose=parseOptionalPoints(frame.pose,33);
    if(frame.face!==undefined)parsed.face=parseOptionalPoints(frame.face,478);
    return parsed;
  });
  return { schemaVersion: 1, signId: value.signId, durationMs: value.durationMs, frames, metadata: metadata as HandAnimation['metadata'] };
}

// Select saved samples only. No invented interpolation across occlusion or gaps.
export function frameAt(animation: HandAnimation, elapsedMs: number): HandFrame | null {
  if (!Number.isFinite(elapsedMs) || elapsedMs < 0 || elapsedMs > animation.durationMs) return null;
  let low = 0, high = animation.frames.length - 1, index = -1;
  while (low <= high) {
    const middle = (low + high) >>> 1;
    if (animation.frames[middle].timestampMs <= elapsedMs) { index = middle; low = middle + 1; }
    else high = middle - 1;
  }
  if (index < 0) return null;
  const frame = animation.frames[index];
  const maxHold = Math.min(2000, Math.max(250, (animation.metadata.sampleIntervalMs || 33.34) * 1.5));
  return elapsedMs - frame.timestampMs > maxHold ? null : frame;
}

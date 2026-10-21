import type { AnimationManifest, HandAnimation } from '../types/hands';
import { loadAnimation } from '../services/animationLoader';
export interface SequenceItem { signId: string; animation: HandAnimation | null; durationMs: number; error?: string }
export const MISSING_SIGN_SLOT_MS = 800;
export async function loadSequence(signs: string[], manifest: AnimationManifest, signal?: AbortSignal): Promise<SequenceItem[]> {
  const promises = new Map<string,Promise<SequenceItem>>();
  return Promise.all(signs.map(signId => {
    if (!promises.has(signId)) promises.set(signId,loadAnimation(signId,manifest,signal)
      .then(animation => ({signId,animation,durationMs:animation.durationMs}))
      .catch(error => {
        if (signal?.aborted) throw error;
        return {signId,animation:null,durationMs:MISSING_SIGN_SLOT_MS,error:error instanceof Error ? error.message : 'Animation unavailable.'};
      }));
    return promises.get(signId)!;
  }));
}
export function sequenceDuration(items: SequenceItem[]) { return items.reduce((total,item) => total + item.durationMs,0); }
export function sequenceAt(items: SequenceItem[], elapsedMs: number) {
  if (!items.length || !Number.isFinite(elapsedMs) || elapsedMs < 0) return null;
  let start = 0;
  for (let index = 0; index < items.length; index++) {
    const item = items[index];
    if (elapsedMs < start + item.durationMs || index === items.length - 1) {
      return { item, index, localTimeMs: Math.min(item.durationMs,Math.max(0,elapsedMs-start)) };
    }
    start += item.durationMs;
  }
  return null;
}

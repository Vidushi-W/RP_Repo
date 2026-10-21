import { useEffect, useState } from 'react';
import { AnimationScheduler, type PlaybackSnapshot } from '../utils/animationScheduler';

export function useAnimationClock(durationMs: number, speed: number, enabled = true, resetKey = '') {
  const [clock, setClock] = useState<AnimationScheduler | null>(null);
  const [snapshot, setSnapshot] = useState<PlaybackSnapshot>({ elapsedMs: 0, durationMs, status: 'idle', speed });
  useEffect(() => {
    // Allocate in the effect: React StrictMode can mount/clean up/mount safely.
    const scheduler = new AnimationScheduler(durationMs);
    scheduler.setSpeed(speed);
    const unsubscribe = scheduler.subscribe(setSnapshot);
    setClock(scheduler);
    return () => { unsubscribe(); scheduler.dispose(); };
  }, [durationMs, resetKey]);
  useEffect(() => { clock?.setSpeed(speed); if (!enabled) clock?.pause(); }, [clock, speed, enabled]);
  return { ...snapshot, play: () => enabled && clock?.play(), pause: () => clock?.pause(), restart: () => clock?.restart(), replay: () => enabled && clock?.replay() };
}

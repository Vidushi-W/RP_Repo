import { useEffect, useState } from 'react';
import { loadManifest } from '../services/animationLoader';
import type { AnimationManifest } from '../types/hands';
export function useAnimationLibrary(fixture = false, enabled = true) {
  const [manifest,setManifest] = useState<AnimationManifest | null>(null);
  const [error,setError] = useState('');
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    setManifest(null); setError('');
    if (!enabled) return () => { active=false;controller.abort(); };
    loadManifest(fixture,controller.signal).then(value => { if(active) setManifest(value); }).catch(error => { if(active && !controller.signal.aborted) setError(error instanceof Error ? error.message : 'Library unavailable.'); });
    return () => { active=false; controller.abort(); };
  },[fixture,enabled]);
  return {manifest,error};
}

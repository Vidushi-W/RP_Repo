import { useEffect, useRef, useState } from 'react';
import type { Cue } from '../types';
import { synchronize } from '../utils/synchronization';
export function useVideoSync(cues: Cue[], speed: number) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let frame = 0;
    const sample = () => { setTime(video.currentTime); setPlaying(!video.paused && !video.ended && video.readyState >= 3 && !video.seeking); };
    const tick = () => { sample(); frame = requestAnimationFrame(tick); };
    const metadata = () => setDuration(Number.isFinite(video.duration) ? video.duration : 0);
    const events = ['play', 'pause', 'seeking', 'seeked', 'ended', 'timeupdate', 'waiting', 'playing'];
    events.forEach(event => video.addEventListener(event, sample));
    video.addEventListener('loadedmetadata', metadata);
    frame = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(frame); events.forEach(event => video.removeEventListener(event, sample)); video.removeEventListener('loadedmetadata', metadata); };
  }, []);
  return { videoRef, time, duration, playing, sync: synchronize(cues, time, playing, speed) };
}

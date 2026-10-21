export interface PlaybackSnapshot { elapsedMs: number; durationMs: number; status: 'idle' | 'playing' | 'paused' | 'ended'; speed: number }
export interface FrameDriver { now: () => number; request: (callback: FrameRequestCallback) => number; cancel: (id: number) => void }
const browserDriver: FrameDriver = { now: () => performance.now(), request: callback => requestAnimationFrame(callback), cancel: id => cancelAnimationFrame(id) };

export class AnimationScheduler {
  private snapshot: PlaybackSnapshot;
  private listeners = new Set<(value: PlaybackSnapshot) => void>();
  private pending: number | null = null;
  private previous = 0;
  private disposed = false;
  constructor(durationMs: number, private driver: FrameDriver = browserDriver) {
    if (!Number.isFinite(durationMs) || durationMs < 0) throw new Error('Invalid playback duration.');
    this.snapshot = { elapsedMs: 0, durationMs, status: 'idle', speed: 1 };
  }
  getSnapshot = () => ({ ...this.snapshot });
  subscribe = (callback: (value: PlaybackSnapshot) => void) => {
    this.listeners.add(callback); callback(this.getSnapshot());
    return () => { this.listeners.delete(callback); };
  };
  private emit() { this.listeners.forEach(callback => callback(this.getSnapshot())); }
  private cancel() { if (this.pending !== null) this.driver.cancel(this.pending); this.pending = null; }
  private advance() {
    const now = this.driver.now();
    this.snapshot.elapsedMs = Math.min(this.snapshot.durationMs, this.snapshot.elapsedMs + Math.max(0, now - this.previous) * this.snapshot.speed);
    this.previous = now;
    if (this.snapshot.elapsedMs >= this.snapshot.durationMs) this.snapshot.status = 'ended';
  }
  private tick = () => {
    this.pending = null;
    if (this.disposed || this.snapshot.status !== 'playing') return;
    this.advance(); this.emit();
    if (this.snapshot.status === 'playing') this.pending = this.driver.request(this.tick);
  };
  play() {
    if (this.disposed || !this.snapshot.durationMs || this.snapshot.status === 'playing' || this.snapshot.status === 'ended') return;
    this.snapshot.status = 'playing'; this.previous = this.driver.now(); this.emit();
    this.pending = this.driver.request(this.tick);
  }
  pause() {
    if (this.disposed || this.snapshot.status !== 'playing') return;
    this.advance(); this.cancel();
    if (this.snapshot.elapsedMs < this.snapshot.durationMs) this.snapshot.status = 'paused';
    this.emit();
  }
  restart() {
    if (this.disposed) return;
    this.cancel(); this.snapshot.elapsedMs = 0; this.snapshot.status = 'idle'; this.emit();
  }
  replay() { this.restart(); this.play(); }
  setSpeed(speed: number) {
    if (!Number.isFinite(speed) || speed <= 0 || speed > 4) throw new Error('Playback speed must be greater than zero and at most 4.');
    if (this.disposed) return;
    if (this.snapshot.status === 'playing') this.advance();
    this.snapshot.speed = speed; this.emit();
    if (this.snapshot.status === 'ended') this.cancel();
  }
  dispose() { this.cancel(); this.listeners.clear(); this.disposed = true; }
}

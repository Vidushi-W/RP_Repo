import type { AnimationStatus } from '../../types';
export function StatusBadge({ status }: { status: AnimationStatus }) { return <span className={`badge ${status}`}>{status}</span>; }

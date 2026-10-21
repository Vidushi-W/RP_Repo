import type { HandAnimation, HandFrame } from '../../types/hands';
import { HAND_CONNECTIONS } from '../../utils/handConnections';
export function HandSkeletonCanvas({ frame, metadata, label = 'Saved hand landmarks' }: { frame: HandFrame | null; metadata?: HandAnimation['metadata']; label?: string }) {
  const width = metadata?.sourceWidth || 640, height = metadata?.sourceHeight || 480;
  const radius = Math.min(width, height) * 0.007;
  const visible = !!(frame?.leftHand || frame?.rightHand);
  return <svg className="hand-canvas" role="img" aria-label={label} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
    <rect width={width} height={height} fill="#f3f7f2"/>
    {(['leftHand', 'rightHand'] as const).map(side => {
      const hand = frame?.[side];
      if (!hand) return null;
      const color = side === 'leftHand' ? '#1d7159' : '#a4532c';
      return <g key={side} data-hand={side}>{HAND_CONNECTIONS.map(([from,to]) => <line key={`${from}-${to}`} x1={hand[from].x * width} y1={hand[from].y * height} x2={hand[to].x * width} y2={hand[to].y * height} stroke={color} strokeWidth={radius * 0.65}/>)}{hand.map((point,index) => <circle key={index} data-landmark={index} cx={point.x * width} cy={point.y * height} r={radius} fill={color}/>)}</g>;
    })}
    {!visible && <text x={width / 2} y={height / 2} textAnchor="middle" fill="#586c5a" fontSize={width * 0.025}>No saved hand detections at this time</text>}
  </svg>;
}

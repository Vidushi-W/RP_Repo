import type { HandAnimation, HandFrame } from '../../types/hands';
import { HAND_CONNECTIONS } from '../../utils/handConnections';
export function HandSkeletonCanvas({ frame, metadata, label = 'Saved hand landmarks', showMissing=true }: { frame: HandFrame | null; metadata?: HandAnimation['metadata']; label?: string; showMissing?:boolean }) {
  const width = metadata?.sourceWidth || 640, height = metadata?.sourceHeight || 480;
  const radius = Math.min(width, height) * 0.007;
  const visible = !!(frame?.leftHand || frame?.rightHand);
  return <svg className="hand-canvas" role="img" aria-label={label} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
    <rect width={width} height={height} fill="#f3f7f2"/>
    {([[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24]] as const).map(([from,to])=>{
      const a=frame?.pose?.[from],b=frame?.pose?.[to];
      return a&&b?<line key={`pose-${from}-${to}`} x1={a.x*width} y1={a.y*height} x2={b.x*width} y2={b.y*height} stroke="#536d87" strokeWidth={radius*0.8}/>:null;
    })}
    {frame?.face&&<g data-face="recorded">{[10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109].map((id,index,ids)=>{
      const a=frame.face?.[id],b=frame.face?.[ids[(index+1)%ids.length]];
      return a&&b?<line key={id} x1={a.x*width} y1={a.y*height} x2={b.x*width} y2={b.y*height} stroke="#536d87" strokeWidth={radius*0.35}/>:null;
    })}</g>}
    {frame?.face&&<g data-expression="recorded">{([[61,146],[146,91],[91,181],[181,84],[84,17],[17,314],[314,405],[405,321],[321,375],[375,291],[61,185],[185,40],[40,39],[39,37],[37,0],[0,267],[267,269],[269,270],[270,409],[409,291],[33,7],[7,163],[163,144],[144,145],[145,153],[153,154],[154,155],[155,133],[33,246],[246,161],[161,160],[160,159],[159,158],[158,157],[157,173],[173,133],[263,249],[249,390],[390,373],[373,374],[374,380],[380,381],[381,382],[382,362],[263,466],[466,388],[388,387],[387,386],[386,385],[385,384],[384,398],[398,362]] as const).map(([from,to])=>{
      const a=frame.face?.[from],b=frame.face?.[to];return a&&b?<line key={`face-${from}-${to}`} x1={a.x*width} y1={a.y*height} x2={b.x*width} y2={b.y*height} stroke="#536d87" strokeWidth={radius*0.3}/>:null;
    })}</g>}
    {(['leftHand', 'rightHand'] as const).map(side => {
      const hand = frame?.[side];
      if (!hand) return null;
      const color = side === 'leftHand' ? '#1d7159' : '#a4532c';
      return <g key={side} data-hand={side}>{HAND_CONNECTIONS.map(([from,to]) => <line key={`${from}-${to}`} x1={hand[from].x * width} y1={hand[from].y * height} x2={hand[to].x * width} y2={hand[to].y * height} stroke={color} strokeWidth={radius * 0.65}/>)}{hand.map((point,index) => <circle key={index} data-landmark={index} cx={point.x * width} cy={point.y * height} r={radius} fill={color}/>)}</g>;
    })}
    {!visible && showMissing && <text x={width / 2} y={height / 2} textAnchor="middle" fill="#586c5a" fontSize={width * 0.025}>No saved hand detections at this time</text>}
  </svg>;
}

import { Component, Suspense, useEffect, useMemo, type ReactNode } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { ContactShadows, OrbitControls, useGLTF } from '@react-three/drei';
import { AnimationMixer, LoopOnce } from 'three';
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { SyncState, VocabularyEntry } from '../../types';
import { isPlayable } from '../../services/vocabulary';
class RenderBoundary extends Component<{ children: ReactNode }, { error: boolean }> {
  state = { error: false };
  static getDerivedStateFromError() { return { error: true }; }
  render() { return this.state.error ? <div className="render-fallback">3D preview unavailable. Timeline controls remain available.</div> : this.props.children; }
}
function Placeholder() {
  return <group position={[0, -0.9, 0]}>
    <mesh position={[0, 1.65, 0]}><sphereGeometry args={[0.25, 32, 32]}/><meshStandardMaterial color="#b8c6bd"/></mesh>
    <mesh position={[0, 1.05, 0]}><capsuleGeometry args={[0.3, 0.55, 8, 24]}/><meshStandardMaterial color="#467e70"/></mesh>
    {[-1, 1].map(side => <group key={side}><mesh position={[side * 0.46, 0.95, 0]} rotation={[0, 0, side * 0.14]}><capsuleGeometry args={[0.095, 0.68, 8, 16]}/><meshStandardMaterial color="#b8c6bd"/></mesh><mesh position={[side * 0.17, 0.22, 0]}><capsuleGeometry args={[0.12, 0.6, 8, 16]}/><meshStandardMaterial color="#344e48"/></mesh></group>)}
  </group>;
}
function RiggedAsset({ url, entry, sync }: { url: string; entry?: VocabularyEntry; sync: SyncState }) {
  const invalidate = useThree(state => state.invalidate);
  const asset = useGLTF(url);
  const model = useMemo(() => clone(asset.scene), [asset.scene]);
  const mixer = useMemo(() => new AnimationMixer(model), [model]);
  useEffect(() => () => { mixer.stopAllAction(); mixer.uncacheRoot(model); }, [mixer, model]);
  useEffect(() => {
    mixer.stopAllAction();
    invalidate();
    if (!isPlayable(entry) || !sync.cue) return;
    const clip = asset.animations.find(item => item.name === entry?.clipName);
    if (!clip) return;
    const action = mixer.clipAction(clip);
    action.setLoop(LoopOnce, 1); action.clampWhenFinished = true; action.play();
    // Video time is the only clock: pause, replay, and backwards seek are deterministic.
    mixer.setTime(Math.min(sync.animationTime, clip.duration));
    invalidate();
  }, [mixer, asset.animations, entry, sync.cue, sync.animationTime, invalidate]);
  return <primitive object={model}/>;
}
export function AvatarRenderer({ avatarUrl, entry, sync }: { avatarUrl?: string | null; entry?: VocabularyEntry; sync?: SyncState }) {
  const assetUrl = isPlayable(entry) ? entry?.animationUrl : avatarUrl;
  return <RenderBoundary key={assetUrl || 'placeholder'}><Canvas camera={{ position: [0, 1, 4.6], fov: 35 }} dpr={[1, 1.5]} frameloop="demand" fallback={<div className="render-fallback">WebGL unavailable · placeholder preview</div>} aria-label="3D avatar preview, placeholder until a validated asset is supplied">
    <color attach="background" args={['#e8efea']}/><ambientLight intensity={1.8}/><directionalLight position={[3, 4, 5]} intensity={3}/>
    <Suspense fallback={null}>{assetUrl ? <RiggedAsset url={assetUrl} entry={entry} sync={sync || { cue: null, animationTime: 0, playing: false }}/> : <Placeholder/>}<ContactShadows position={[0, -1.15, 0]} opacity={0.3} scale={6} blur={2}/></Suspense>
    <OrbitControls enableZoom={false} enablePan={false} minPolarAngle={1.1} maxPolarAngle={1.7} target={[0, 0.1, 0]}/>
  </Canvas></RenderBoundary>;
}

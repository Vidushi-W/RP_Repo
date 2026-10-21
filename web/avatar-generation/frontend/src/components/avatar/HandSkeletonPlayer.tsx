import type { AnimationManifest } from '../../types/hands';
import { SignSequencePlayer } from './SignSequencePlayer';
export function HandSkeletonPlayer({signId,manifest,speed=1}: {signId:string;manifest?:AnimationManifest;speed?:number}) {
  return <SignSequencePlayer signs={signId?[signId]:[]} manifest={manifest} speed={speed}/>;
}

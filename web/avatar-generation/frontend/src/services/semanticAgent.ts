import { parseAgentResult } from './agentAdapter';
import { parseManifest } from './animationLoader';
import { record } from './animationSchema';
import type { AgentResult, AnimationManifest } from '../types/hands';

export interface SemanticMatch { signId:string; canonicalLabel:string; evidence:string; explanation:string; method:string; animationFile:string; reviewStatus:string }
export interface SemanticConcept { concept:string; evidence:string; animationAvailable:boolean }
export interface SemanticInference { performed:boolean; model?:string; mode:string }
export interface SemanticResult extends AgentResult { matches:SemanticMatch[]; unsupported:string[]; manifest:AnimationManifest; researchPreview:boolean; concepts:SemanticConcept[]; inference?:SemanticInference }

export function parseSemanticResult(value:unknown, preview:boolean):SemanticResult {
  const base=parseAgentResult(value);
  if(!record(value)||value.researchPreview!==preview||!Array.isArray(value.matches)||!Array.isArray(value.unsupported)||!value.unsupported.every(v=>typeof v==='string'))throw new Error('Invalid semantic agent response.');
  const manifest=parseManifest(value.manifest,preview);
  if(manifest.fixture)throw new Error('Semantic agent cannot return coordinate fixtures.');
  if(manifest.signs.some(entry=>!entry.sha256))throw new Error('Semantic animations require a verified checksum.');
  const matches:SemanticMatch[]=value.matches.map((m:unknown)=>{
    if(!record(m)||!['signId','canonicalLabel','evidence','explanation','method','animationFile','reviewStatus'].every(k=>typeof m[k]==='string'))throw new Error('Invalid match metadata.');
    const entry=manifest.signs.find(e=>e.signId===m.signId);
    if(!entry||entry.animationUrl!==m.animationFile||(!preview&&m.reviewStatus!=='approved'))throw new Error('Animation is outside the validated registry.');
    return m as unknown as SemanticMatch;
  });
  if(JSON.stringify(matches.map(m=>m.signId))!==JSON.stringify(base.signs))throw new Error('Agent signs do not match validated animations.');
  const concepts:SemanticConcept[]=[];
  if(value.concepts!==undefined){
    if(!Array.isArray(value.concepts)||value.concepts.length>40)throw new Error('Invalid semantic concepts.');
    for(const c of value.concepts){
      if(!record(c)||typeof c.concept!=='string'||typeof c.evidence!=='string'||typeof c.animationAvailable!=='boolean')throw new Error('Invalid semantic concept.');
      concepts.push({concept:c.concept,evidence:c.evidence,animationAvailable:c.animationAvailable});
    }
  }
  let inference:SemanticInference|undefined;
  if(value.inference!==undefined){
    if(!record(value.inference)||typeof value.inference.performed!=='boolean'||typeof value.inference.mode!=='string'||(value.inference.model!==undefined&&typeof value.inference.model!=='string'))throw new Error('Invalid inference metadata.');
    inference={performed:value.inference.performed,mode:value.inference.mode,model:value.inference.model as string|undefined};
  }
  return {...base,matches,manifest,unsupported:value.unsupported as string[],researchPreview:preview,concepts,inference};
}

/** Speech-to-text adapters call this with their final English transcript. */
export async function processTranscript(text:string, researchPreview=false, signal?:AbortSignal):Promise<SemanticResult> {
  const response=await fetch('/api/agent/process',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,researchPreview}),signal});
  const body=await response.json();
  if(!response.ok)throw new Error(typeof body.detail==='string'?body.detail:'Semantic agent request failed.');
  return parseSemanticResult(body,researchPreview);
}

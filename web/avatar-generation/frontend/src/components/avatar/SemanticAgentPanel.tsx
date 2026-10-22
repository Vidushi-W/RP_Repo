import { useEffect, useRef, useState } from 'react';
import { processTranscript, type SemanticResult } from '../../services/semanticAgent';
import { SignSequencePlayer } from './SignSequencePlayer';

export function SemanticAgentPanel() {
  const [text,setText]=useState('');
  const [preview,setPreview]=useState(false);
  const [result,setResult]=useState<SemanticResult|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [run,setRun]=useState(0);
  const controller=useRef<AbortController|null>(null);
  useEffect(()=>()=>controller.current?.abort(),[]);
  function clear(){controller.current?.abort();controller.current=null;setResult(null);setBusy(false);setError('');}
  async function process(){
    clear();const request=new AbortController();controller.current=request;setBusy(true);
    try {const next=await processTranscript(text,preview,request.signal);if(!request.signal.aborted){setResult(next);setRun(v=>v+1);}}
    catch(e){if(!request.signal.aborted)setError(e instanceof Error?e.message:'Semantic selection failed.');}
    finally {if(!request.signal.aborted)setBusy(false);}
  }
  return <section className="panel local-video-panel" aria-label="Semantic sign selection agent">
    <span className="eyebrow">ENGLISH → SEMANTIC AGENT → SAVED ANIMATION</span>
    <h2>Select signs with the AI agent</h2>
    <p className="small muted">Local Qwen3 interprets context against registered meanings and queues only existing recordings in English mention order. This does not determine SLSL grammar.</p>
    <label className="field-label" htmlFor="semantic-transcript">English text or speech-to-text transcript</label>
    <textarea id="semantic-transcript" rows={3} maxLength={1000} value={text} onChange={e=>{clear();setText(e.target.value);}} placeholder="The nurse is working."/>
    <label className="fixture-toggle"><input type="checkbox" checked={preview} onChange={e=>{clear();setPreview(e.target.checked);}}/> Research preview: include pending recordings</label>
    {preview&&<p className="fixture-banner">Unreviewed research playback. NURSE sign correctness and handedness are pending expert review. Proposed synonyms are not verified SLSL mappings.</p>}
    <button className="button primary" disabled={busy||!text.trim()} onClick={()=>void process()}>Process with AI Agent</button>
    <p role="status" aria-live="polite">{busy?'Agent processing: checking vocabulary and context…':error?'Agent request failed':result?result.signs.length?'Validated selection · playing saved recordings':'Unsupported sign':'Ready'}</p>
    {error&&<p className="error" role="alert">{error}</p>}
    {result&&<>
      <p><strong>Transcript:</strong> {result.englishText}</p>
      <p><strong>Recognized concepts:</strong> {result.concepts.map(c=>c.concept+(c.animationAvailable?'':' (no playable animation)')).join(' → ')||'No supported concepts identified'}</p>
      <p><strong>Playback queue:</strong> {result.signs.join(' → ')||'Unsupported sign'}</p>
      {result.inference&&<p className="small muted">{result.inference.performed?`Local inference: ${result.inference.model} · ${result.inference.mode}`:'Standalone registry match; no model inference performed.'}</p>}
      <ul>{result.matches.map((m,i)=><li key={i}><strong>{m.canonicalLabel}</strong> · {m.method} · {m.reviewStatus}<br/>{m.explanation}<br/><code>{m.animationFile}</code></li>)}</ul>
      {!!result.unsupported.length&&<p className="fixture-banner" role="status">Unsupported vocabulary: {result.unsupported.join('; ')}</p>}
      <SignSequencePlayer key={run} signs={result.signs} manifest={result.manifest} autoPlay/>
    </>}
  </section>;
}

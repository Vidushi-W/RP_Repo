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
  return <section className="panel local-video-panel" aria-label="Text to supported signs">
    <span className="eyebrow">FROM WORDS TO SIGNS</span>
    <h2>Find signs for your text</h2>
    <p className="small muted">Find supported signs based on the meaning of your text. Available recordings play in mention order; this does not determine SLSL grammar.</p>
    <label className="field-label" htmlFor="semantic-transcript">English text or speech-to-text transcript</label>
    <textarea id="semantic-transcript" rows={3} maxLength={1000} value={text} onChange={e=>{clear();setText(e.target.value);}} placeholder="The nurse is working."/>
    <label className="fixture-toggle"><input type="checkbox" checked={preview} onChange={e=>{clear();setPreview(e.target.checked);}}/> Include recordings awaiting review</label>
    {preview&&<p className="fixture-banner">Unreviewed playback. NURSE sign correctness and handedness are pending expert review. Proposed synonyms are not verified SLSL mappings.</p>}
    <button className="button primary" disabled={busy||!text.trim()} onClick={()=>void process()}>Find Matching Signs</button>
    <p role="status" aria-live="polite">{busy?'Finding matching vocabulary and context…':error?'Could not find signs':result?result.signs.length?'Validated selection · playing saved recordings':'Unsupported sign':'Ready'}</p>
    {error&&<p className="error" role="alert">{error}</p>}
    {result&&<>
      <p><strong>Transcript:</strong> {result.englishText}</p>
      <p><strong>Recognized concepts:</strong> {result.concepts.map(c=>c.concept+(c.animationAvailable?'':' (no playable animation)')).join(' → ')||'No supported concepts identified'}</p>
      <p><strong>Playback queue:</strong> {result.signs.join(' → ')||'Unsupported sign'}</p>
      {result.inference&&<p className="small muted">{result.inference.performed?'Text meaning processed':'Matched from the available sign library.'}</p>}
      <ul>{result.matches.map((m,i)=><li key={i}><strong>{m.canonicalLabel}</strong> · {m.reviewStatus}<br/>{m.explanation}</li>)}</ul>
      {!!result.unsupported.length&&<p className="fixture-banner" role="status">Unsupported vocabulary: {result.unsupported.join('; ')}</p>}
      <SignSequencePlayer key={run} signs={result.signs} manifest={result.manifest} autoPlay/>
    </>}
  </section>;
}

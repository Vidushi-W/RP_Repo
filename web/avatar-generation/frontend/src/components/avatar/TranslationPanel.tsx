import type { AgentResult, AnimationManifest } from '../../types/hands';
import type { WordMatch } from '../../services/signMatcher';
export function TranslationPanel({result,words,missing,manifest,source,activeIndex=-1}: {result:AgentResult|null;words:WordMatch[];missing:string[];manifest:AnimationManifest|null;source:'resolver'|'agent'|'fixture';activeIndex?:number}) {
  const unavailable=result?.signs.filter(id=>!manifest?.signs.some(entry=>entry.signId===id))||[];
  let ordinal=-1;
  return <section className="panel translation-summary"><span className="eyebrow">YOUR MATCHING SIGNS</span><h2>From words to signs</h2>
    <dl className="state-list"><div><dt>Original English</dt><dd>{result?.englishText||'No input processed yet.'}</dd></div><div><dt>Sinhala translation</dt><dd lang={result?.sinhalaText ? 'si' : 'en'}>{result?.sinhalaText||'No Sinhala text supplied.'}</dd></div><div><dt>Sequence source</dt><dd>{source==='fixture' ? 'Synthetic coordinate timing test; not a linguistic sequence.' : source==='agent' ? 'Imported playback instructions; linguistic correctness is not verified here.' : 'Matching words in input order; not SLSL grammar.'}</dd></div></dl>
    {words.length>0 && <div className="matched-words" aria-label="English vocabulary matches">{words.map((word,index)=>{const active=!!word.signId && ++ordinal===activeIndex;return <span className={active?'matched current-word':word.signId?'matched':'unmatched'} aria-current={active?'true':undefined} key={index}>{word.text}</span>;})}</div>}
    <p className="small mt-4"><strong>Matching signs:</strong> {result?.signs.join(' → ')||'None'}</p>
    {missing.length>0 && <p className="small mt-4"><strong>Words without matching signs:</strong> {missing.join(', ')}</p>}
    {unavailable.length>0 && <p className="error"><strong>Missing saved signs:</strong> {[...new Set(unavailable)].join(', ')}. No substitute signs will be used.</p>}
  </section>;
}

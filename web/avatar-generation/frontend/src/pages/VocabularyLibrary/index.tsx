import { useState } from 'react';
import { Search, BookOpen, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAnimationLibrary } from '../../hooks/useAnimationLibrary';
export default function VocabularyLibrary() {
  const {manifest,error}=useAnimationLibrary();
  const [query,setQuery]=useState('');
  const signs=manifest?.signs||[];
  const filtered=signs.filter(entry=>entry.label.toLowerCase().includes(query.toLowerCase())||entry.signId.toLowerCase().includes(query.toLowerCase()));
  return <><div className="page-title"><div><span className="eyebrow">REVIEWED RECORDINGS</span><h1>Vocabulary library</h1><p>Dataset references for saved SLSL hand-coordinate animations.</p></div><span className="badge">{signs.length} registered signs</span></div>
    <div className="notice"><strong>Real signs stay separate from coordinate tests.</strong> This library reads the reviewed SLSL manifest. Synthetic diagnostics are available only through the explicit test-library switch in the studio.</div>
    <section className="panel mt-6"><div className="library-tools"><label className="search"><Search size={18}/><input aria-label="Search recorded signs" placeholder="Search sign labels or identifiers…" value={query} onChange={e=>setQuery(e.target.value)}/></label></div>
    {error&&<p role="alert" className="error">{error}</p>}
    {filtered.length?<div className="table-scroll"><table><thead><tr><th>Sign ID</th><th>Label</th><th>Dataset reference</th><th>Aliases</th><th>Status</th></tr></thead><tbody>{filtered.map(entry=><tr key={entry.signId}><td>{entry.signId}</td><td>{entry.label}</td><td>{entry.datasetReference}</td><td>{entry.aliases.join(', ')}</td><td><span className="badge">Reviewed recording</span></td></tr>)}</tbody></table></div>:<div className="empty-library"><span className="large-icon"><BookOpen size={32}/></span><h2>{signs.length?'No matching signs':'The first recordings start here.'}</h2><p>{manifest?'Extract landmarks from licensed SLSL videos, review the coordinates and handedness, then register each saved JSON animation. No SLSL dataset recordings are bundled.':'Loading the saved-animation manifest…'}</p><Link className="text-link" to="/translation">Open the hand animation studio <ArrowRight size={16}/></Link></div>}
    </section></>;
}

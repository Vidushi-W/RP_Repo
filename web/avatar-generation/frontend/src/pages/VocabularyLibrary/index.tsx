import { useState } from 'react';
import { Search, BookOpen, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAnimationLibrary } from '../../hooks/useAnimationLibrary';
export default function VocabularyLibrary() {
  const {manifest,error}=useAnimationLibrary();
  const [query,setQuery]=useState('');
  const signs=manifest?.signs||[];
  const filtered=signs.filter(entry=>entry.label.toLowerCase().includes(query.toLowerCase())||entry.signId.toLowerCase().includes(query.toLowerCase()));
  return <><div className="page-title"><div><span className="eyebrow">DISCOVER VISUAL COMMUNICATION</span><h1>Explore the Sign Library</h1><p>Browse the signs available in this playback library. Live audio uses a separate supported vocabulary.</p></div><span className="badge">{signs.length} library signs</span></div>
    <div className="notice"><strong>Every sign has a place.</strong> Availability here reflects this playback library. Shared-tab audio uses its own vocabulary, so this list may differ from the signs you see in the live studio.</div>
    <section className="panel mt-6"><div className="library-tools"><label className="search"><Search size={18}/><input aria-label="Search recorded signs" placeholder="Search signs…" value={query} onChange={e=>setQuery(e.target.value)}/></label></div>
    {error&&<p role="alert" className="error">{error}</p>}
    {filtered.length?<div className="sign-library-grid">{filtered.map(entry=><article className="library-sign-card" key={entry.signId}><span className="step-icon"><BookOpen size={25}/></span><span className="badge">Available recording</span><h2>{entry.label}</h2><p>{entry.aliases.join(', ')}</p><details><summary>Recording details</summary><p>{entry.signId}</p><p>{entry.datasetReference}</p></details></article>)}</div>:<div className="empty-library"><span className="large-icon"><BookOpen size={32}/></span><h2>{signs.length?'No matching signs':'No signs to browse yet.'}</h2><p>{manifest?'No matching entries are available in this library. You can still visit the live studio to explore its supported vocabulary.':'Loading the sign library…'}</p><Link className="text-link" to="/translation">Open Sign Language Studio <ArrowRight size={16}/></Link></div>}
    </section></>;
}

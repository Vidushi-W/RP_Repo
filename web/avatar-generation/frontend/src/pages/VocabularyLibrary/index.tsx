import { useState } from 'react';
import { Search, BookOpen, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { vocabulary } from '../../services/vocabulary';
import { StatusBadge } from '../../components/common/StatusBadge';
export default function VocabularyLibrary() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const filtered = vocabulary.filter(entry => entry.word.toLowerCase().includes(query.toLowerCase()) && (status === 'all' || entry.animationStatus === status));
  return <><div className="page-title"><div><span className="eyebrow">A GROWING SIGN COLLECTION</span><h1>Vocabulary library</h1><p>Reviewed dataset references and their avatar animation readiness.</p></div><span className="badge">{vocabulary.length} verified words</span></div>
    <div className="notice"><strong>10 words planned for PP1.</strong> No Kaggle dataset or reviewed word list has been supplied. The library stays empty until real references are added; timing markers do not count as SLSL words.</div>
    <section className="panel mt-6"><div className="library-tools"><label className="search"><Search size={18}/><input aria-label="Search vocabulary" placeholder="Search words…" value={query} onChange={e => setQuery(e.target.value)}/></label><label className="filter">Animation status <select value={status} onChange={e => setStatus(e.target.value)}><option value="all">All statuses</option><option value="available">Available</option><option value="processing">Processing</option><option value="unavailable">Unavailable</option></select></label></div>
    {filtered.length ? <div className="table-scroll"><table><thead><tr><th>Word</th><th>Dataset reference</th><th>Source video</th><th>Animation</th><th>Reviewed</th></tr></thead><tbody>{filtered.map(entry => <tr key={entry.id}><td>{entry.word}</td><td>{entry.datasetReference}</td><td>{entry.sourceVideo}</td><td><StatusBadge status={entry.animationStatus}/></td><td>{entry.validated ? 'Yes' : 'Pending'}</td></tr>)}</tbody></table></div> : <div className="empty-library"><span className="large-icon"><BookOpen size={32}/></span><h2>{vocabulary.length ? 'No matching words' : 'The first signs start here.'}</h2><p>{vocabulary.length ? 'Try another search or animation status.' : 'Add reviewed vocabulary and dataset references to the JSON manifest. Each sign will show its source and animation status here.'}</p><Link className="text-link" to="/translation">Explore the timing demo <ArrowRight size={16}/></Link></div>}
    <div className="legend"><StatusBadge status="available"/><span>Asset ready</span><StatusBadge status="processing"/><span>In preparation</span><StatusBadge status="unavailable"/><span>No animation</span></div></section>
  </>;
}

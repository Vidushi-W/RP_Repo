import { NavLink, Outlet } from 'react-router-dom';
import { Hand, LayoutDashboard, Clapperboard, Library, Settings, ArrowUpRight } from 'lucide-react';
import { usePreferences } from '../../hooks/usePreferences';
const links = [{ to: '/', label: 'Overview', icon: LayoutDashboard }, { to: '/translation', label: 'Video translation', icon: Clapperboard }, { to: '/vocabulary', label: 'Vocabulary library', icon: Library }, { to: '/settings', label: 'Settings', icon: Settings }];
export function AppLayout() {
  const { preferences } = usePreferences();
  return <div className={`app ${preferences.highContrast ? 'high-contrast' : ''} ${preferences.reducedMotion ? 'reduced-motion' : ''}`}>
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className="sidebar"><NavLink to="/" className="brand"><span className="brand-icon"><Hand size={25}/></span><span>LankaSigns<small>AVATAR STUDIO</small></span></NavLink>
      <p className="nav-label">WORKSPACE</p><nav aria-label="Main navigation">{links.map(({ to, label, icon: Icon }) => <NavLink end={to === '/'} key={to} to={to}><Icon size={19}/>{label}</NavLink>)}</nav>
      <div className="sidebar-note"><span className="dot"/> RESEARCH PROTOTYPE<p>Building a more accessible learning experience, one sign at a time.</p><span>PP1 · Vidushi’s component <ArrowUpRight size={14}/></span></div>
      <div className="profile"><span>V</span><div>Vidushi<small>Accessibility engine</small></div></div>
    </aside>
    <div className="workspace"><header className="topbar"><span>LankaSigns <span className="muted">/</span> Accessibility engine</span><span className="badge">Local research workspace</span></header><main id="main-content" tabIndex={-1}><Outlet/></main><footer>Sri Lankan Sign Language · Made for understanding.<span>Research prototype / v0.1</span></footer></div>
  </div>;
}

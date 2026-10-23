import { NavLink, Outlet } from 'react-router-dom';
import { Hand, Home, ScreenShare, Library, Settings, Heart } from 'lucide-react';
import { usePreferences } from '../../hooks/usePreferences';
const links = [{ to: '/', label: 'Home', icon: Home }, { to: '/translation', label: 'Sign Language Studio', icon: ScreenShare }, { to: '/vocabulary', label: 'Sign Library', icon: Library }, { to: '/settings', label: 'Settings', icon: Settings }];
export function AppLayout() {
  const { preferences } = usePreferences();
  return <div className={`app ${preferences.highContrast ? 'high-contrast' : ''} ${preferences.reducedMotion ? 'reduced-motion' : ''}`}>
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className="sidebar"><NavLink to="/" className="brand"><span className="brand-icon"><Hand size={25}/></span><span>LankaSigns<small>AVATAR STUDIO</small></span></NavLink>
      <p className="nav-label">EXPLORE LANKASIGNS</p><nav aria-label="Main navigation">{links.map(({ to, label, icon: Icon }) => <NavLink end={to === '/'} key={to} to={to}><Icon size={19}/>{label}</NavLink>)}</nav>
      <div className="sidebar-note"><Heart size={23}/><h3>Made for connection.</h3><p>A more visual way to experience the content you love.</p><NavLink to="/translation">Visit your studio &rarr;</NavLink></div>
      <div className="sidebar-bottom"><Hand size={16}/> A little closer, one sign at a time.</div>
    </aside>
    <div className="workspace"><header className="topbar"><span>LankaSigns <span className="muted">/</span> Avatar Studio</span><span className="badge"><Hand size={13}/> Designed for connection</span></header><main id="main-content" tabIndex={-1}><Outlet/></main><footer>Sri Lankan Sign Language &middot; Made for understanding.<span>LankaSigns Avatar Studio</span></footer></div>
  </div>;
}

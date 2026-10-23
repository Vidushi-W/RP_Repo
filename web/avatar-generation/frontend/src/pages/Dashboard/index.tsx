import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen, AudioLines, ScreenShare, Hand, ShieldCheck, Sparkles } from 'lucide-react';
const steps = [
  { icon: ScreenShare, title: 'Share Your Tab', text: 'Choose a browser tab with audio and give permission to share its audio.' },
  { icon: AudioLines, title: 'We Process the Audio', text: 'Speech is recognized, then matched to the supported sign language vocabulary.' },
  { icon: Hand, title: 'Watch the Avatar Sign', text: 'Follow the corresponding Sri Lankan Sign Language animations in your studio.' },
];
export default function Dashboard() {
  return <div className="home-page">
    <section className="home-hero" aria-labelledby="hero-title">
      <div className="home-hero-copy"><span className="hero-kicker"><span className="dot"/> SRI LANKAN SIGN LANGUAGE ACCESSIBILITY</span>
        <h1 id="hero-title">Share a Tab.<br/><span>See the Signs.</span></h1>
        <p className="hero-tagline">Turning Sound Into Signs.<br/>Connecting People Visually.</p>
        <p className="hero-description">Share a browser tab with audio and watch LankaSigns transform supported spoken content into Sri Lankan Sign Language avatar animations.</p>
        <div className="hero-buttons"><Link className="button primary" to="/translation"><ScreenShare size={20}/> Share Tab &amp; See Signs <ArrowRight size={17}/></Link><Link className="button secondary" to="/vocabulary"><BookOpen size={18}/> Explore Sign Library</Link></div>
        <p className="hero-footnote"><ShieldCheck size={16}/> Your content. Your screen. A more accessible experience.</p>
      </div>
      <div className="companion-card"><div className="preview-toolbar"><span className="window-dots" aria-hidden="true"><i/><i/><i/></span><span>Your signing companion</span><Hand size={17}/></div>
        <div className="companion-art" aria-hidden="true"><span className="art-orbit orbit-one"/><span className="art-orbit orbit-two"/><div className="companion-symbol"><Hand size={88} strokeWidth={1.2}/></div><div className="art-chip audio-chip"><AudioLines size={19}/> Shared tab audio</div><div className="art-chip sign-chip"><Sparkles size={17}/> Supported signs</div></div>
        <div className="companion-caption"><span className="eyebrow">SOUND MEETS VISUAL COMMUNICATION</span><h2>Meet Your Signing Companion</h2><p>Making spoken content easier to experience visually.</p><span className="preview-note">Illustration &middot; Open the studio to see the avatar.</span></div>
      </div>
    </section>
    <section className="how-section" aria-labelledby="how-title"><div className="home-section-heading"><span className="eyebrow">A LITTLE SHARING. A NEW PERSPECTIVE.</span><h2 id="how-title">How LankaSigns Works</h2><p>Three simple steps to a more accessible digital experience.</p></div><div className="steps-grid">{steps.map(({icon:Icon,title,text},i)=><article className="step-card" key={title}><div className="step-top"><span className="step-icon"><Icon size={25}/></span><span className="step-number">0{i+1}</span></div><h3>{title}</h3><p>{text}</p>{i<2&&<ArrowRight className="step-arrow" size={19} aria-hidden="true"/>}</article>)}</div></section>
    <section className="share-feature"><div><span className="eyebrow">YOUR CONTENT, MORE ACCESSIBLE</span><h2>Bring Your Content to Life.</h2><p>Watching a video or listening to an educational lesson? Share your browser tab with audio and follow matching sign animations in the studio.</p><Link className="button primary" to="/translation"><ScreenShare size={19}/> Share Tab &amp; See Signs</Link><p className="small">Choose a tab, then enable &ldquo;Share tab audio&rdquo; in your browser.</p></div><div className="sharing-diagram" aria-label="Browser tab audio connects to the signing avatar"><div className="diagram-browser"><span className="window-dots" aria-hidden="true"><i/><i/><i/></span><ScreenShare size={38}/><strong>Your browser tab</strong><span>Video &middot; Audio &middot; Learning</span></div><ArrowRight className="diagram-arrow" aria-hidden="true"/><div className="diagram-sign"><Hand size={36}/><strong>Your signing avatar</strong><span>Matching signs</span></div></div></section>
    <p className="coverage-note"><BookOpen size={18}/> LankaSigns plays supported vocabulary. Some spoken content may have no matching sign; animations do not provide a complete grammatical translation.</p>
    <section className="accessibility-banner"><Hand size={30}/><h2>Communication Should Have No Barriers.</h2><p>Technology should bring people closer together. LankaSigns helps make supported digital content more accessible through visual communication.</p></section>
    <section className="final-cta"><div><h2>Ready to See Sound Differently?</h2><p>Bring your browser tab into your signing studio.</p></div><Link className="button primary" to="/translation"><ScreenShare size={19}/> Share Tab &amp; See Signs <ArrowRight size={17}/></Link></section>
  </div>;
}

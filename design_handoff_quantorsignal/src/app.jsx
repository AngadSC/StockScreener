// ====== App shell — v3 Atelier ======

function App() {
  const [route, setRoute] = useState({ name: 'home' });
  const [cmdOpen, setCmdOpen] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => { window.scrollTo({ top: 0 }); }, [route]);

  const goStock    = (ticker) => setRoute({ name: 'stock', ticker });
  const goScreener = () => setRoute({ name: 'screener' });
  const goHome     = () => setRoute({ name: 'home' });
  const cmdK       = () => setCmdOpen(true);

  let page = null;
  if (route.name === 'home')          page = <Dashboard goStock={goStock} goScreener={goScreener} />;
  else if (route.name === 'screener') page = <Screener goStock={goStock} />;
  else if (route.name === 'stock')    page = <StockDetail ticker={route.ticker} goStock={goStock} goBack={goScreener} />;
  else if (route.name === 'ai')       page = <AIAnalyst goStock={goStock} />;
  else                                 page = <ComingSoon name={route.name} goHome={goHome} />;

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar route={route} setRoute={setRoute} onCmdK={cmdK} />
      <main style={{ flex: 1, minWidth: 0, background: 'transparent', borderLeft: '1px solid var(--line)' }}>
        {page}
      </main>
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onPick={goStock} />
    </div>
  );
}

function ComingSoon({ name, goHome }) {
  const labels = {
    watch:    { eyebrow:'Workspace', title: 'Watchlist',  desc: 'A focused set of high-conviction names with live prices, AI deltas, and one-tap alerts. Coming soon.' },
    backtest: { eyebrow:'Workspace', title: 'Backtester', desc: 'Compose a strategy from a canvas of indicators and rules; watch the equity curve render in real time.' },
    ai:       { eyebrow:'Workspace', title: 'Research',   desc: 'Generate a thesis brief in thirty seconds — bull case, bear case, catalysts, and a transparent confidence score.' },
    port:     { eyebrow:'Workspace', title: 'Portfolio',  desc: 'Holdings, performance, factor exposure, attribution, and risk — all in one quiet workspace.' },
  };
  const l = labels[name] || { eyebrow:'Workspace', title: name, desc: '' };
  return (
    <div className="page-enter">
      <PageHeader eyebrow={l.eyebrow} title={l.title} subtitle={l.desc} right={
        <button className="btn btn-primary btn-sm" onClick={goHome}>Back to markets <Icon name="arrow-r" size={13} /></button>
      } />
      <div style={{ padding:'80px 48px', display:'grid', placeItems:'center' }}>
        <div style={{ maxWidth:560, textAlign:'center' }}>
          <div className="divider" style={{ marginBottom: 14 }}>
            <span className="serif" style={{ fontStyle:'italic', fontSize:14, color:'var(--mute)' }}>In preparation</span>
          </div>
          <span className="smallcap-low" style={{ fontSize:11 }}>· Design preview · not yet wired ·</span>
        </div>
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);

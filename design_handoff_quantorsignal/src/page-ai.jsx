// ====== AI Analyst — v6 Batcave ======

function AIAnalyst({ goStock }) {
  // build ranked conviction ideas from the universe
  const ideas = useMemo(() => {
    const scored = STOCKS.map(s => {
      // synthesize a conviction score from momentum + growth + quality
      const mom = Math.max(Math.min(s.chg / 7, 1), -1);
      const growth = Math.min((s.rev_g ?? 0) / 0.5, 1);
      const quality = Math.min((s.roe ?? 0) / 1.5, 1);
      const raw = 50 + mom * 18 + growth * 20 + quality * 14;
      const score = Math.round(Math.max(20, Math.min(98, raw)));
      const rec = score >= 80 ? 'Strong buy' : score >= 65 ? 'Buy' : score >= 50 ? 'Hold' : score >= 38 ? 'Reduce' : 'Sell';
      return { ...s, score, rec };
    }).sort((a,b) => b.score - a.score);
    return scored.slice(0, 8);
  }, []);

  const [selected, setSelected] = useState(ideas[0].ticker);
  const [thinking, setThinking] = useState(false);
  const sel = STOCKS_BY_TICKER[selected];
  const selIdea = ideas.find(i => i.ticker === selected) || ideas[0];
  const report = AI_REPORT;

  const pick = (t) => {
    if (t === selected) return;
    setThinking(true);
    setSelected(t);
    setTimeout(() => setThinking(false), 480);
  };

  const recTone = (rec) => rec.includes('buy') || rec === 'Buy' ? 'var(--up)' : rec === 'Hold' ? 'var(--sapphire)' : 'var(--dn)';

  const suggestions = [
    'Semis with expanding margins',
    'Quality compounders under 30× P/E',
    'Oversold large-caps with positive flow',
    'Dividend growers, low beta',
  ];

  return (
    <div className="page-enter">
      <PageHeader
        title="AI Analyst"
        subtitle="A reasoning engine that reads the tape, the filings, and the wire — then writes the thesis. Ask in plain language, or review today's highest-conviction ideas."
      />

      {/* ask bar */}
      <div style={{ padding:'0 48px 32px' }}>
        <div className="glass hud hud-blue" style={{ padding:'8px 8px 8px 20px', display:'flex', alignItems:'center', gap:14 }}>
          <span className="hud-c1" /><span className="hud-c2" />
          <Icon name="sparkles" size={16} stroke={1.4} />
          <input className="ai-ask"
            placeholder="Ask the analyst to build a thesis or screen…"
            style={{ flex:1, background:'transparent', border:'none', outline:'none', color:'var(--ink)', fontSize:16, fontFamily:'Spectral', fontWeight:400 }} />
          <span className="kbd hide-md">⏎</span>
          <button className="btn btn-primary btn-sm" style={{ flexShrink:0 }}>Generate <Icon name="arrow-r" size={13} /></button>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:8, marginTop:14, flexWrap:'wrap' }}>
          <span className="smallcap-low" style={{ fontSize:10.5, marginRight:4 }}>Try</span>
          {suggestions.map(s => (
            <button key={s} className="suggest-chip" style={{
              fontFamily:'Spectral', fontStyle:'italic', fontSize:13, color:'var(--ink-2)',
              background:'var(--surface)', border:'1px solid var(--line)', borderRadius:999,
              padding:'7px 14px', cursor:'pointer', transition:'all 220ms var(--ease)',
            }}>{s}</button>
          ))}
        </div>
      </div>

      {/* main: conviction queue + brief */}
      <div style={{ padding:'0 48px 40px', display:'grid', gridTemplateColumns:'minmax(300px, 1fr) minmax(0, 1.5fr)', gap:24 }}>
        {/* conviction queue */}
        <div>
          <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:16 }}>
            <h3 className="serif-tight" style={{ fontSize:22 }}>Conviction queue</h3>
            <span className="smallcap-low" style={{ fontSize:10.5 }}>Ranked by edge</span>
          </div>
          <div className="card" style={{ overflow:'hidden' }}>
            {ideas.map((idea, i) => {
              const on = idea.ticker === selected;
              return (
                <div key={idea.ticker} onClick={() => pick(idea.ticker)} className="row-hover" style={{
                  display:'grid', gridTemplateColumns:'20px auto 1fr auto', gap:14, alignItems:'center',
                  padding:'14px 18px', borderTop: i === 0 ? 'none' : '1px solid var(--line)',
                  background: on ? 'var(--surface-2)' : 'transparent',
                  position:'relative',
                }}>
                  {on && <span style={{ position:'absolute', left:0, top:10, bottom:10, width:2, background:'var(--sapphire)', borderRadius:'0 2px 2px 0' }} />}
                  <span className="mono" style={{ fontSize:11, color: on ? 'var(--sapphire)' : 'var(--whisper)' }}>{(i+1).toString().padStart(2,'0')}</span>
                  <div style={{ minWidth:52 }}>
                    <div className="serif-tight" style={{ fontSize:16, color:'var(--ink)' }}>{idea.ticker}</div>
                    <div className="smallcap-low" style={{ fontSize:9.5, marginTop:1, color: recTone(idea.rec) }}>{idea.rec}</div>
                  </div>
                  <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                    <Bar pct={idea.score} accent={idea.score >= 65 ? 'var(--up)' : idea.score >= 50 ? 'var(--sapphire)' : 'var(--dn)'} />
                  </div>
                  <span className="readout" style={{ fontSize:20, color:'var(--ink)' }}>{idea.score}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* selected brief */}
        <div className="card-ivory hud" style={{ padding:'36px 40px', position:'relative', minHeight:560, opacity: thinking ? 0.4 : 1, transition:'opacity 360ms var(--ease)' }}>
          <span className="hud-c1" /><span className="hud-c2" />

          <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:24 }}>
            <div>
              <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:10 }}>
                <span className="smallcap-low" style={{ fontSize:11, color:'var(--forest)' }}>Generated brief</span>
                <span style={{ color:'var(--ghost)' }}>·</span>
                <span className="status">No. 4218</span>
              </div>
              <h2 className="serif-tight" style={{ fontSize:52, lineHeight:0.95, color:'var(--ink)', letterSpacing:'-0.03em' }}>{sel.ticker}</h2>
              <div className="serif" style={{ fontSize:18, color:'var(--ink-2)', marginTop:6, fontStyle:'italic', fontWeight:300 }}>{sel.name}</div>
            </div>
            <div style={{ textAlign:'right', flexShrink:0 }}>
              <div style={{ position:'relative', width:96, height:96, marginLeft:'auto' }}>
                <svg width="96" height="96" viewBox="0 0 96 96" style={{ transform:'rotate(-90deg)' }}>
                  <circle cx="48" cy="48" r="40" fill="none" stroke="rgba(216,210,192,0.10)" strokeWidth="5" />
                  <circle cx="48" cy="48" r="40" fill="none" stroke={recTone(selIdea.rec)} strokeWidth="5" strokeLinecap="round" strokeDasharray={`${(selIdea.score/100) * 251.3} 300`} style={{ transition:'stroke-dasharray 600ms var(--ease)' }} />
                </svg>
                <div style={{ position:'absolute', inset:0, display:'grid', placeItems:'center', flexDirection:'column' }}>
                  <span className="readout" style={{ fontSize:32, color:'var(--ink)' }}>{selIdea.score}</span>
                </div>
              </div>
              <div className="smallcap-low" style={{ fontSize:10, marginTop:6 }}>Conviction</div>
            </div>
          </div>

          {/* recommendation line */}
          <div style={{ display:'flex', alignItems:'center', gap:16, marginTop:24, padding:'16px 20px', background:'var(--surface)', borderRadius:12, border:'1px solid var(--line)' }}>
            <div>
              <div className="smallcap-low" style={{ fontSize:10 }}>Call</div>
              <div className="serif-tight" style={{ fontSize:24, color:recTone(selIdea.rec), lineHeight:1, marginTop:2 }}>{selIdea.rec}</div>
            </div>
            <div style={{ width:1, height:34, background:'var(--line)' }} />
            <div>
              <div className="smallcap-low" style={{ fontSize:10 }}>Last</div>
              <div className="serif-num" style={{ fontSize:20, marginTop:2 }}>{fmtPrice(sel.price)}</div>
            </div>
            <div style={{ width:1, height:34, background:'var(--line)' }} />
            <div>
              <div className="smallcap-low" style={{ fontSize:10 }}>Target</div>
              <div className="serif-num" style={{ fontSize:20, marginTop:2, color:'var(--up)' }}>{fmtPrice(sel.price * 1.16)}</div>
            </div>
            <div style={{ width:1, height:34, background:'var(--line)' }} />
            <div style={{ flex:1, minWidth:0 }}>
              <div className="smallcap-low" style={{ fontSize:10, marginBottom:5 }}>Trend · 90d</div>
              <div style={{ color: sel.chg >= 0 ? 'var(--up)' : 'var(--dn)' }}>
                <Sparkline values={sel.spark90} width={140} height={26} stroke="currentColor" fill />
              </div>
            </div>
          </div>

          {/* narrative */}
          <p className="serif" style={{ fontSize:16.5, lineHeight:1.6, color:'var(--ink-2)', marginTop:24, maxWidth:'62ch' }}>
            <span className="serif-tight" style={{ fontSize:34, float:'left', lineHeight:0.9, marginRight:10, marginTop:3, color:'var(--ink)' }}>{sel.name.charAt(0)}</span>
            {sel.ticker} screens in the top decile of our coverage on the convergence of momentum and quality. {sel.sector === 'Technology' ? 'Datacenter and platform demand remains the dominant driver' : 'Operating leverage and disciplined capital allocation underpin the call'}, with revenue growth of {((sel.rev_g ?? 0)*100).toFixed(0)}% and return on equity near {((sel.roe ?? 0)*100).toFixed(0)}%. The engine marks this an above-average setup with defined risk.
          </p>

          <div className="divider" style={{ marginTop:26, marginBottom:18 }}>
            <span className="serif" style={{ fontStyle:'italic', fontSize:13, color:'var(--mute)' }}>The two-sided case</span>
          </div>

          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:36 }}>
            <AIThesis title="The bull case" tone="up" items={report.thesis.bull} />
            <AIThesis title="The bear case" tone="dn" items={report.thesis.bear} />
          </div>

          <div style={{ display:'flex', gap:10, marginTop:30, alignItems:'center' }}>
            <button className="btn btn-primary btn-sm" onClick={() => goStock(sel.ticker)}>Open full detail <Icon name="arrow-r" size={13} /></button>
            <button className="btn btn-ghost btn-sm"><Icon name="replay" size={13} /> Regenerate</button>
            <button className="btn btn-ghost btn-sm"><Icon name="bookmark" size={13} /> Save</button>
            <span style={{ marginLeft:'auto', fontSize:11.5, color:'var(--mute)', fontStyle:'italic', fontFamily:'Spectral' }}>Synthesized in 1.8s · 42 sources</span>
          </div>
        </div>
      </div>

      {/* recent briefs */}
      <div style={{ padding:'0 48px 64px' }}>
        <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:18 }}>
          <h3 className="serif-tight" style={{ fontSize:24 }}>Recent briefs</h3>
          <span className="lnk" style={{ fontSize:12, color:'var(--mute)' }}>Archive →</span>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:18 }}>
          {[
            { t:'NVDA', h:'Datacenter re-acceleration confirmed; raising target', tone:'up', time:'09:38' },
            { t:'UNH',  h:'Healthcare leg-down setup forming at prior support', tone:'dn', time:'09:12' },
            { t:'COIN', h:'Volatility regime favors the derivatives expansion', tone:'up', time:'08:51' },
          ].map((b,i) => (
            <div key={i} onClick={() => goStock(b.t)} className="card card-hover" style={{ padding:'22px 24px' }}>
              <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:14 }}>
                <span className="serif-tight" style={{ fontSize:20 }}>{b.t}</span>
                <span className="mono" style={{ fontSize:10.5, color:'var(--mute)' }}>{b.time} ET</span>
              </div>
              <div className="serif" style={{ fontSize:16, lineHeight:1.4, color:'var(--ink)' }}>{b.h}</div>
              <div style={{ marginTop:16, display:'flex', alignItems:'center', gap:8 }}>
                <span className={`status ${b.tone === 'up' ? 'status-up' : 'status-dn'}`}>{b.tone === 'up' ? 'BULLISH' : 'BEARISH'}</span>
                <span className="row-arrow" style={{ marginLeft:'auto', color:'var(--mute)' }}><Icon name="arrow-tr" size={14} /></span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AIThesis({ title, tone, items }) {
  const isUp = tone === 'up';
  return (
    <div>
      <div className="smallcap-low" style={{ fontSize:10.5, marginBottom:14, color: isUp ? 'var(--up)' : 'var(--dn)' }}>{title}</div>
      <ul style={{ listStyle:'none', display:'flex', flexDirection:'column', gap:14 }}>
        {items.map((it, i) => (
          <li key={i} style={{ display:'flex', gap:12, fontSize:14, lineHeight:1.5, color:'var(--ink-2)' }}>
            <span className="serif" style={{ fontSize:14, color: isUp ? 'var(--up)' : 'var(--dn)', flexShrink:0, fontStyle:'italic', fontWeight:500, minWidth:18 }}>{i+1}.</span>
            <span className="serif" style={{ fontWeight:300 }}>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

Object.assign(window, { AIAnalyst });

// ====== Stock detail — v3 Atelier ======

function StockDetail({ ticker, goStock, goBack }) {
  const stock = STOCKS_BY_TICKER[ticker] || STOCKS[0];
  const [range, setRange] = useState('3M');
  const [tab, setTab] = useState('overview');
  const [watch, setWatch] = useState(false);

  const news = NEWS[ticker] || NEWS.NVDA;
  const report = AI_REPORT;
  const peers = useMemo(() => STOCKS.filter(s => s.sector === stock.sector && s.ticker !== ticker).slice(0, 5), [ticker, stock.sector]);

  const w52pos = ((stock.price - stock.w52l) / (stock.w52h - stock.w52l)) * 100;

  return (
    <div className="page-enter">
      {/* breadcrumb */}
      <div style={{ padding:'24px 48px 0', display:'flex', alignItems:'center', gap:10, color:'var(--mute)', fontSize:12 }}>
        <span className="lnk" onClick={goBack} style={{ borderColor:'transparent' }}>Markets</span>
        <span style={{ color:'var(--ghost)' }}>·</span>
        <span>{stock.sector}</span>
        <span style={{ color:'var(--ghost)' }}>·</span>
        <span style={{ color:'var(--ink)' }}>{ticker}</span>
      </div>

      {/* hero */}
      <div style={{ padding:'24px 48px 36px' }}>
        <div style={{ display:'grid', gridTemplateColumns:'minmax(0, 1.4fr) minmax(0, 1fr)', gap:48, alignItems:'flex-end' }}>
          <div>
            <div className="smallcap-low" style={{ fontSize:11, marginBottom:14 }}>Equity profile</div>
            <h1 className="serif-tight" style={{ fontSize:'clamp(64px, 8vw, 96px)', lineHeight:0.95, letterSpacing:'-0.035em', color:'var(--ink)' }}>{ticker}</h1>
            <div className="serif" style={{ fontSize:22, color:'var(--ink-2)', marginTop:8, fontStyle:'italic', fontWeight:300 }}>{stock.name}</div>
            <div className="smallcap-low" style={{ fontSize:11.5, marginTop:14 }}>
              {stock.industry} · NASDAQ · USD
            </div>
          </div>

          <div style={{ display:'flex', flexDirection:'column', alignItems:'flex-end', gap:14 }}>
            <div className="smallcap-low" style={{ fontSize:11, display:'inline-flex', alignItems:'center', gap:8 }}>
              <span className="dot dot-up pulse" />
              Live · {new Date().toLocaleTimeString('en-US',{ hour:'2-digit', minute:'2-digit' })} ET
            </div>
            <div className="readout" style={{ fontSize:'clamp(48px, 7vw, 90px)', color:'var(--ink)' }}>{stock.price.toFixed(2)}</div>
            <div style={{ display:'flex', alignItems:'center', gap:14 }}>
              <Delta value={stock.chg} size="lg" />
              <span className="mono" style={{ fontSize:12, color:'var(--mute)' }}>{(stock.price * stock.chg / 100).toFixed(2)} today</span>
            </div>
            <div style={{ display:'flex', gap:8, marginTop:8 }}>
              <button className="btn btn-primary btn-sm"><Icon name="sparkles" size={13} /> AI analysis</button>
              <button className="btn btn-ghost btn-sm" onClick={() => setWatch(!watch)}>
                <Icon name={watch ? 'bookmark-f' : 'bookmark'} size={13} />
                {watch ? 'Saved' : 'Save'}
              </button>
            </div>
          </div>
        </div>

        {/* 52w range — elegant */}
        <div style={{ marginTop:36, padding:'24px 28px', background:'var(--surface)', borderRadius:14, boxShadow:'var(--shadow-1)' }}>
          <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:14 }}>
            <span className="smallcap-low" style={{ fontSize:11 }}>52 week range</span>
            <span className="serif" style={{ fontSize:14, color:'var(--mute)', fontStyle:'italic' }}>{w52pos.toFixed(0)}% of range</span>
          </div>
          <div style={{ position:'relative', height:4, background:'var(--ghost)', borderRadius:999 }}>
            <div style={{ position:'absolute', left:0, top:0, bottom:0, width:'100%', background:'linear-gradient(90deg, rgba(194,90,58,0.30), rgba(174,185,199,0.30), rgba(91,168,121,0.30))', borderRadius:999 }} />
            <div style={{ position:'absolute', left:`${w52pos}%`, top:'50%', transform:'translate(-50%, -50%)', width:14, height:14, background:'var(--forest)', borderRadius:999, border:'3px solid var(--surface)', boxShadow:'var(--shadow-2)' }} />
          </div>
          <div style={{ display:'flex', justifyContent:'space-between', marginTop:10 }}>
            <span className="serif-num" style={{ fontSize:13, color:'var(--dn)' }}>${stock.w52l.toFixed(2)}</span>
            <span className="serif-num" style={{ fontSize:13, color:'var(--up)' }}>${stock.w52h.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* key stats — refined */}
      <div style={{ padding:'0 48px 36px' }}>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(8, minmax(0, 1fr))', borderTop:'1px solid var(--line)', borderBottom:'1px solid var(--line)' }}>
          {[
            { l:'Market cap',  v: fmtMcap(stock.mcap) },
            { l:'Volume',      v: fmtVol(stock.vol) },
            { l:'P/E',         v: stock.pe?.toFixed(1) ?? '—' },
            { l:'ROE',         v: (stock.roe * 100).toFixed(0) + '%' },
            { l:'Beta',        v: stock.beta.toFixed(2) },
            { l:'Dividend',    v: stock.divy > 0 ? (stock.divy*100).toFixed(2)+'%' : '—' },
            { l:'Revenue',     v: (stock.rev_g*100).toFixed(1)+'%', tone: stock.rev_g > 0 ? 'up' : 'dn' },
            { l:'EPS TTM',     v: '$2.78' },
          ].map((s,i) => (
            <div key={i} style={{ padding:'20px 18px', borderRight: i < 7 ? '1px solid var(--line)' : 'none' }}>
              <div className="smallcap-low" style={{ fontSize:10.5, marginBottom:8 }}>{s.l}</div>
              <div className="serif-num" style={{ fontSize:22, color: s.tone === 'up' ? 'var(--up)' : s.tone === 'dn' ? 'var(--dn)' : 'var(--ink)' }}>{s.v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* tabs */}
      <div style={{ padding:'0 48px', display:'flex', alignItems:'center', gap:32, borderBottom:'1px solid var(--line)' }}>
        {['overview','fundamentals','research','news','peers','filings'].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            background:'none', border:'none', cursor:'pointer',
            padding:'18px 0', fontFamily:'Geist', fontSize:13, fontWeight: tab === t ? 500 : 400,
            color: tab === t ? 'var(--ink)' : 'var(--mute)',
            position:'relative', textTransform:'capitalize',
            transition:'all 200ms',
          }}>
            {t}
            {tab === t && <span style={{ position:'absolute', left:0, right:0, bottom:-1, height:1.5, background:'var(--ink)' }} />}
          </button>
        ))}
      </div>

      {/* main grid */}
      <div style={{ padding:'28px 48px 64px', display:'grid', gridTemplateColumns:'minmax(0, 1.55fr) minmax(0, 1fr)', gap:32 }}>
        {/* left column */}
        <div style={{ display:'flex', flexDirection:'column', gap:28 }}>

          {/* chart */}
          <div className="card hud hud-blue" style={{ padding:'28px 32px' }}>
            <span className="hud-c1" /><span className="hud-c2" />
            <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:18 }}>
              <h3 className="serif-tight" style={{ fontSize:22 }}>Price history</h3>
              <div className="seg">
                {['1D','5D','1M','3M','YTD','1Y','5Y'].map(p => (
                  <button key={p} onClick={() => setRange(p)} className={`seg-btn ${range === p ? 'active' : ''}`}>{p}</button>
                ))}
              </div>
            </div>
            <div className="scan-host">
              <AreaChart values={stock.spark90} height={320} accent={stock.chg >= 0 ? '#5ba879' : '#c25a3a'} />
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(6, 1fr)', marginTop:24, paddingTop:18, borderTop:'1px solid var(--line)' }}>
              {[
                { l:'Open',  v: fmtPrice(stock.price * 0.992) },
                { l:'High',  v: fmtPrice(stock.price * 1.013) },
                { l:'Low',   v: fmtPrice(stock.price * 0.988) },
                { l:'Close', v: fmtPrice(stock.price * 0.997) },
                { l:'VWAP',  v: fmtPrice(stock.price * 0.998) },
                { l:'Volume',v: fmtVol(stock.vol) },
              ].map((s,i) => (
                <div key={i} style={{ paddingRight: i < 5 ? 18 : 0 }}>
                  <div className="smallcap-low" style={{ fontSize:10.5, marginBottom:5 }}>{s.l}</div>
                  <div className="serif-num" style={{ fontSize:15, color:'var(--ink)' }}>{s.v}</div>
                </div>
              ))}
            </div>
          </div>

          {/* research / AI brief — editorial */}
          <div className="card-ivory" style={{ padding:'36px 40px' }}>
            <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:18 }}>
              <div>
                <div className="smallcap-low" style={{ fontSize:11, color:'var(--forest)', marginBottom:8 }}>Research brief · No. 4218</div>
                <h3 className="serif-tight" style={{ fontSize:32 }}>The case for {ticker}</h3>
              </div>
              <div style={{ textAlign:'right' }}>
                <div className="readout" style={{ fontSize:48, color:'var(--forest)' }}>{report.score}</div>
                <div className="smallcap-low" style={{ fontSize:10.5, marginTop:4 }}>Conviction</div>
              </div>
            </div>

            <p className="serif" style={{ fontSize:17, lineHeight:1.6, color:'var(--ink-2)', marginTop:10, maxWidth:'58ch' }}>
              <span className="serif-tight" style={{ fontSize:34, float:'left', lineHeight:0.9, marginRight:10, marginTop:4, color:'var(--ink)' }}>T</span>
              he position synthesizes three trends now converging at unusual amplitude. Datacenter revenue is reaccelerating after a one-quarter pause; sovereign AI commitments add a third durable demand vector; and gross-margin expansion is now visible through FY27 consensus. The recommendation reads <em>buy</em> with above-average conviction.
            </p>

            <div className="divider" style={{ marginTop:28, marginBottom:18 }}>
              <span className="serif" style={{ fontStyle:'italic', fontSize:13, color:'var(--mute)' }}>The thesis</span>
            </div>

            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:36 }}>
              <ThesisCol title="The bull case" tone="up" items={report.thesis.bull} />
              <ThesisCol title="The bear case" tone="dn" items={report.thesis.bear} />
            </div>

            <div className="divider" style={{ marginTop:32, marginBottom:18 }}>
              <span className="serif" style={{ fontStyle:'italic', fontSize:13, color:'var(--mute)' }}>Catalysts</span>
            </div>

            <div style={{ display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:24 }}>
              {report.catalysts.map(c => (
                <div key={c.label}>
                  <div className="smallcap-low" style={{ fontSize:11, marginBottom:6, color:'var(--forest)' }}>{c.date}</div>
                  <div className="serif" style={{ fontSize:15, lineHeight:1.3, color:'var(--ink)' }}>{c.label}</div>
                  <div style={{ fontSize:11, color:'var(--mute)', marginTop:4, fontStyle:'italic', fontFamily:'Spectral' }}>{c.weight.toLowerCase()} impact</div>
                </div>
              ))}
            </div>

            <div style={{ display:'flex', gap:10, marginTop:30 }}>
              <button className="btn btn-primary btn-sm">Read full report <Icon name="arrow-r" size={13} /></button>
              <span style={{ marginLeft:'auto', fontSize:12, color:'var(--mute)', alignSelf:'center', fontStyle:'italic', fontFamily:'Spectral' }}>Updated 09:38 ET · refreshes hourly</span>
            </div>
          </div>

          {/* factor scores */}
          <div className="card" style={{ padding:'28px 32px' }}>
            <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:24 }}>
              <h3 className="serif-tight" style={{ fontSize:22 }}>Factor scores</h3>
              <span className="serif" style={{ fontSize:12, color:'var(--mute)', fontStyle:'italic' }}>vs. {stock.sector}</span>
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'18px 40px' }}>
              {report.factors.map(f => (
                <div key={f.label}>
                  <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:8 }}>
                    <span style={{ fontSize:13.5, fontWeight:500 }}>{f.label}</span>
                    <span className="serif-num" style={{ fontSize:15 }}>{f.score}</span>
                  </div>
                  <div className="bar">
                    <div className="bar-fill" style={{
                      width:`${f.score}%`,
                      background: f.score >= 70 ? 'var(--up)' : f.score >= 40 ? 'var(--forest)' : 'var(--dn)',
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* right column */}
        <div style={{ display:'flex', flexDirection:'column', gap:28 }}>
          {/* signal snapshot — AI analyst readout */}
          <div className="card hud" style={{ padding:'24px 28px' }}>
            <span className="hud-c1" /><span className="hud-c2" />
            <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:18 }}>
              <h3 className="serif-tight" style={{ fontSize:22 }}>Signal snapshot</h3>
              <span className="status">OBS-4218</span>
            </div>

            {/* conviction dial */}
            <div style={{ display:'flex', alignItems:'center', gap:18 }}>
              <div style={{ position:'relative', flexShrink:0 }}>
                <svg width="72" height="72" viewBox="0 0 72 72" style={{ transform:'rotate(-90deg)' }}>
                  <circle cx="36" cy="36" r="30" fill="none" stroke="var(--surface-2)" strokeWidth="5" />
                  <circle cx="36" cy="36" r="30" fill="none" stroke="var(--up)" strokeWidth="5" strokeLinecap="round" strokeDasharray={`${(report.score/100) * 188.5} 200`} />
                </svg>
                <div style={{ position:'absolute', inset:0, display:'grid', placeItems:'center' }}>
                  <span className="readout" style={{ fontSize:24, color:'var(--ink)' }}>{report.score}</span>
                </div>
              </div>
              <div>
                <div className="smallcap-low" style={{ fontSize:10.5, marginBottom:4 }}>Recommendation</div>
                <div className="serif-tight" style={{ fontSize:24, color:'var(--up)', lineHeight:1 }}>{report.recommendation}</div>
                <div style={{ fontSize:11.5, color:'var(--mute)', marginTop:6, fontStyle:'italic', fontFamily:'Spectral' }}>9 buy · 2 hold · 1 sell</div>
              </div>
            </div>

            {/* key levels */}
            <div style={{ marginTop:20, paddingTop:18, borderTop:'1px solid var(--line)', display:'flex', flexDirection:'column', gap:12 }}>
              {[
                { l:'Entry zone',  v: fmtPrice(stock.price * 0.985), c:'var(--ink)' },
                { l:'Price target',v: fmtPrice(stock.price * 1.16),  c:'var(--up)' },
                { l:'Protective stop', v: fmtPrice(stock.price * 0.92), c:'var(--dn)' },
                { l:'Risk / reward', v: '1 : 2.4', c:'var(--sapphire)' },
              ].map((r,i) => (
                <div key={i} style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between' }}>
                  <span style={{ fontSize:12.5, color:'var(--mute)' }}>{r.l}</span>
                  <span className="serif-num" style={{ fontSize:16, color:r.c }}>{r.v}</span>
                </div>
              ))}
            </div>

            <button className="btn btn-primary" style={{ width:'100%', marginTop:20, justifyContent:'center' }}>
              <Icon name="sparkles" size={13} /> Open AI Analyst
            </button>
          </div>

          {/* news */}
          <div>
            <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:14 }}>
              <h3 className="serif-tight" style={{ fontSize:22 }}>Recent dispatches</h3>
              <span className="lnk" style={{ fontSize:12, color:'var(--mute)' }}>All →</span>
            </div>
            {news.map((n, i) => (
              <div key={i} className="row-hover" style={{ padding:'14px 4px', borderTop: i === 0 ? '1px solid var(--line)' : '1px solid var(--line)' }}>
                <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:5 }}>
                  <span className="smallcap-low" style={{ fontSize:10.5 }}>{n.source}</span>
                  <span style={{ color:'var(--ghost)' }}>·</span>
                  <span className="mono" style={{ fontSize:11, color:'var(--mute)' }}>{n.time}</span>
                </div>
                <div className="serif" style={{ fontSize:15, lineHeight:1.42, color:'var(--ink)' }}>{n.title}</div>
              </div>
            ))}
          </div>

          {/* peers — elegant row */}
          <div>
            <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:14 }}>
              <h3 className="serif-tight" style={{ fontSize:22 }}>Peers</h3>
              <span className="serif" style={{ fontSize:12, color:'var(--mute)', fontStyle:'italic' }}>{stock.sector}</span>
            </div>
            {peers.map((p, i) => (
              <div key={p.ticker} onClick={() => goStock(p.ticker)} className="row-hover" style={{
                display:'grid', gridTemplateColumns:'auto 1fr auto auto', gap:14, alignItems:'center',
                padding:'12px 4px', borderTop:'1px solid var(--line)',
              }}>
                <div style={{ minWidth:54 }}>
                  <div className="serif-tight" style={{ fontSize:15, color:'var(--ink)' }}>{p.ticker}</div>
                </div>
                <div style={{ fontSize:12, color:'var(--mute)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{p.name}</div>
                <Sparkline values={p.spark} width={48} height={20} stroke={p.chg >= 0 ? 'var(--up)' : 'var(--dn)'} />
                <Delta value={p.chg} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ThesisCol({ title, tone, items }) {
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

function FieldLabel({ l, children }) {
  return (
    <div>
      <div className="smallcap-low" style={{ fontSize:10.5, marginBottom:6 }}>{l}</div>
      {children}
    </div>
  );
}

Object.assign(window, { StockDetail });

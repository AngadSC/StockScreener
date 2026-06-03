// ====== Markets dashboard — v3 Atelier ======

function Dashboard({ goStock, goScreener }) {
  const featured = useMemo(() => [...STOCKS].filter(s => s.mcap > 100e9).sort((a,b) => b.chg - a.chg)[0], []);

  const topGainers = useMemo(() => [...STOCKS].filter(s => s.chg > 0 && s.mcap > 5e9).sort((a,b) => b.chg - a.chg).slice(0, 5), []);
  const topLosers  = useMemo(() => [...STOCKS].filter(s => s.chg < 0 && s.mcap > 5e9).sort((a,b) => a.chg - b.chg).slice(0, 5), []);

  const indexes = [
    { name: 'S&P 500',       sym: 'SPX', price: 5891.42,  chg: 0.62 },
    { name: 'NASDAQ 100',    sym: 'NDX', price: 21086.34, chg: 1.18 },
    { name: 'Russell 2000',  sym: 'RUT', price: 2278.80,  chg: -0.42 },
    { name: 'Treasury 10Y',  sym: 'TNX', price: 4.34,     chg: 0.18 },
    { name: 'Gold',          sym: 'XAU', price: 2682.40,  chg: 0.34 },
    { name: 'WTI Crude',     sym: 'CL',  price: 71.20,    chg: 1.46 },
  ];

  // sector flow
  const sectorData = useMemo(() => {
    const map = {};
    STOCKS.forEach(s => {
      if (!map[s.sector]) map[s.sector] = { sector: s.sector, mcap: 0, weighted: 0, count: 0 };
      map[s.sector].mcap += s.mcap;
      map[s.sector].weighted += s.chg * s.mcap;
      map[s.sector].count++;
    });
    return Object.values(map).map(d => ({ ...d, chg: d.weighted / d.mcap })).sort((a,b) => b.chg - a.chg);
  }, []);

  const now = new Date();
  const dateStr = now.toLocaleDateString('en-US',{ weekday:'long', month:'long', day:'numeric', year:'numeric' });

  return (
    <div className="page-enter">
      {/* ===== top date strip ===== */}
      {/* ===== telemetry strip ===== */}
      <PageHeader
        title="Markets"
        subtitle="Three names crossed your thresholds overnight. Two have research briefs ready. The bond complex repriced quietly."
        right={
          <>
            <button className="btn btn-ghost btn-sm" onClick={goScreener}>Open screener</button>
            <button className="btn btn-primary btn-sm">View today's brief <Icon name="arrow-r" size={13} /></button>
          </>
        }
      />

      {/* ===== indexes — refined row, no boxes ===== */}
      <div style={{ padding:'8px 48px 32px' }}>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(6, minmax(0, 1fr))', gap:0, borderTop:'1px solid var(--line)', borderBottom:'1px solid var(--line)' }}>
          {indexes.map((ix, i) => (
            <div key={ix.sym} style={{ padding:'18px 22px', borderRight: i < 5 ? '1px solid var(--line)' : 'none' }}>
              <div className="smallcap-low" style={{ fontSize:11, marginBottom:8 }}>{ix.name}</div>
              <div className="serif-num" style={{ fontSize:'clamp(16px, 1.6vw, 22px)', color:'var(--ink)', lineHeight:1 }}>{ix.price.toLocaleString('en-US',{ minimumFractionDigits:2, maximumFractionDigits:2 })}</div>
              <div style={{ marginTop:6 }}><Delta value={ix.chg} /></div>
            </div>
          ))}
        </div>
      </div>

      {/* ===== featured + watchlist side-by-side ===== */}
      <div style={{ padding:'0 48px 32px', display:'grid', gridTemplateColumns:'minmax(0, 1.6fr) minmax(320px, 1fr)', gap:24 }}>
        {/* featured */}
        <div className="card hud" style={{ padding:'32px 36px' }}>
          <span className="hud-c1" /><span className="hud-c2" />
          <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:24, marginBottom:8 }}>
            <div>
              <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8 }}>
                <span className="smallcap-low" style={{ fontSize:11, color:'var(--forest)' }}>Today's spotlight</span>
                <span style={{ color:'var(--ghost)' }}>·</span>
                <span className="status">OBS-4218</span>
              </div>
              <h2 className="serif-tight" style={{ fontSize:48, color:'var(--ink)', lineHeight:1, letterSpacing:'-0.03em' }}>{featured.ticker}</h2>
              <div style={{ fontSize:14, color:'var(--mute)', marginTop:6 }}>{featured.name} · {featured.sector}</div>
            </div>
            <div style={{ textAlign:'right', minWidth:0 }}>
              <div className="readout" style={{ fontSize:'clamp(36px, 4.4vw, 56px)', color:'var(--ink)' }}>{featured.price.toFixed(2)}</div>
              <div style={{ display:'flex', alignItems:'center', justifyContent:'flex-end', gap:10, marginTop:8, flexWrap:'wrap' }}>
                <Delta value={featured.chg} size="lg" />
                <span className="mono" style={{ fontSize:11, color:'var(--mute)' }}>{(featured.price * featured.chg / 100).toFixed(2)} today</span>
              </div>
            </div>
          </div>

          {/* segment + chart */}
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginTop:24, marginBottom:6 }}>
            <div className="seg">
              {['1D','5D','1M','3M','YTD','1Y'].map((p,i) => (
                <button key={p} className={`seg-btn ${i === 3 ? 'active' : ''}`}>{p}</button>
              ))}
            </div>
            <div className="smallcap-low" style={{ fontSize:11 }}>3-month price</div>
          </div>
          <div className="scan-host" style={{ color:'var(--forest)' }}>
            <AreaChart values={featured.spark90} height={260} accent={featured.chg >= 0 ? '#5ba879' : '#c25a3a'} />
          </div>

          <div style={{ display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:0, marginTop:14, paddingTop:24, borderTop:'1px solid var(--line)' }}>
            {[
              { l:'Market cap', v: fmtMcap(featured.mcap) },
              { l:'Volume',     v: fmtVol(featured.vol) },
              { l:'P/E ratio',  v: featured.pe?.toFixed(1) ?? '—' },
              { l:'52w range',  v: `${featured.w52l.toFixed(0)} – ${featured.w52h.toFixed(0)}` },
            ].map((s,i) => (
              <div key={i}>
                <div className="smallcap-low" style={{ fontSize:11, marginBottom:6 }}>{s.l}</div>
                <div className="serif-num" style={{ fontSize:22, color:'var(--ink)' }}>{s.v}</div>
              </div>
            ))}
          </div>

          <div style={{ display:'flex', gap:8, marginTop:28 }}>
            <button className="btn btn-primary btn-sm" onClick={() => goStock(featured.ticker)}>Open detail <Icon name="arrow-r" size={13} /></button>
            <button className="btn btn-ghost btn-sm"><Icon name="bookmark" size={13} /> Save</button>
            <button className="btn btn-ghost btn-sm" style={{ marginLeft:'auto' }}><Icon name="sparkles" size={13} /> AI brief</button>
          </div>
        </div>

        {/* watchlist — refined, no boxes per row */}
        <div className="card hud hud-blue" style={{ padding:'8px 0 0' }}>
          <span className="hud-c1" /><span className="hud-c2" />
          <div style={{ padding:'24px 28px 12px', display:'flex', alignItems:'baseline', justifyContent:'space-between' }}>
            <div>
              <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:6 }}>
                <span className="smallcap-low" style={{ fontSize:11 }}>Watchlist</span>
                <span className="live-dot">LIVE</span>
              </div>
              <div className="serif-tight" style={{ fontSize:22 }}>Core six</div>
            </div>
            <button className="btn-bare" style={{ padding:'4px 8px' }}><Icon name="plus" size={14} /></button>
          </div>

          {topGainers.slice(0,5).map((s,i) => (
            <div key={s.ticker} onClick={() => goStock(s.ticker)} className="row-hover" style={{
              display:'grid', gridTemplateColumns:'auto 1fr auto', gap:14, alignItems:'center',
              padding:'14px 28px', borderTop:'1px solid var(--line)',
            }}>
              <div style={{ minWidth:64 }}>
                <div className="serif-tight" style={{ fontSize:16, color:'var(--ink)' }}>{s.ticker}</div>
                <div style={{ fontSize:11, color:'var(--mute)', marginTop:1, maxWidth:'14ch', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{s.sector}</div>
              </div>
              <Sparkline values={s.spark} width={72} height={22} stroke={s.chg >= 0 ? 'var(--up)' : 'var(--dn)'} />
              <div style={{ textAlign:'right' }}>
                <div className="serif-num" style={{ fontSize:15, color:'var(--ink)' }}>{s.price.toFixed(2)}</div>
                <Delta value={s.chg} />
              </div>
            </div>
          ))}
          <div style={{ padding:'14px 28px 22px', borderTop:'1px solid var(--line)', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
            <span className="smallcap-low" style={{ fontSize:11 }}>Net position today</span>
            <span className="serif-num" style={{ fontSize:18, color:'var(--up)' }}>+$3,184.20</span>
          </div>
        </div>
      </div>

      {/* ===== editorial section: movers as inline lists ===== */}
      <div style={{ padding:'0 48px 32px' }}>
        <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:24 }}>
          <h2 className="serif-tight" style={{ fontSize:32, color:'var(--ink)' }}>Movers</h2>
          <div className="seg">
            <button className="seg-btn active">All</button>
            <button className="seg-btn">Holdings</button>
            <button className="seg-btn">Sector</button>
          </div>
        </div>

        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:48 }}>
          <MoverList title="Advancing" tone="up" stocks={topGainers} onPick={goStock} />
          <MoverList title="Declining" tone="dn" stocks={topLosers}  onPick={goStock} />
        </div>
      </div>

      {/* ===== sector flow — refined typography, no boxes ===== */}
      <div style={{ padding:'0 48px 48px' }}>
        <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:24 }}>
          <h2 className="serif-tight" style={{ fontSize:32 }}>Sector flow</h2>
          <span className="smallcap-low" style={{ fontSize:11 }}>Capitalization-weighted · today</span>
        </div>

        <div style={{ display:'grid', gridTemplateColumns:'repeat(2, 1fr)', gap:'0 64px' }}>
          {sectorData.map((s,i) => (
            <div key={s.sector} style={{
              display:'grid', gridTemplateColumns:'1fr 80px 100px', gap:18, alignItems:'center',
              padding:'14px 0', borderBottom:'1px solid var(--line)',
            }}>
              <div>
                <div className="serif" style={{ fontSize:17, color:'var(--ink)' }}>{s.sector}</div>
                <div className="smallcap-low" style={{ fontSize:10.5, marginTop:2 }}>{s.count} constituents · {fmtMcap(s.mcap)}</div>
              </div>
              <div>
                <div className="bar">
                  <div className="bar-fill" style={{
                    width: `${Math.min(Math.abs(s.chg) * 30, 100)}%`,
                    background: s.chg >= 0 ? 'var(--up)' : 'var(--dn)',
                  }} />
                </div>
              </div>
              <div style={{ textAlign:'right' }}>
                <span className="serif-num" style={{ fontSize:18, color: s.chg >= 0 ? 'var(--up)' : 'var(--dn)' }}>
                  {s.chg >= 0 ? '+' : ''}{s.chg.toFixed(2)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ===== editorial close: AI brief + market wire ===== */}
      <div style={{ padding:'0 48px 64px' }}>
        <div style={{ display:'grid', gridTemplateColumns:'minmax(0, 1.4fr) minmax(0, 1fr)', gap:32 }}>
          {/* brief */}
          <div className="card-ivory hud" style={{ padding:'40px 44px' }}>
            <span className="hud-c1" /><span className="hud-c2" />
            <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:14 }}>
              <span className="smallcap-low" style={{ fontSize:11, color:'var(--forest)' }}>Morning brief · No. 482</span>
              <span style={{ color:'var(--ghost)' }}>·</span>
              <span className="status">SYNTHESIZED · 09:32 ET</span>
            </div>
            <h3 className="serif-tight" style={{ fontSize:30, lineHeight:1.2, color:'var(--ink)', maxWidth:'28ch' }}>
              A measured tape; tech leads, healthcare lags, and the bond complex repriced quietly overnight.
            </h3>
            <p style={{ fontSize:15, lineHeight:1.7, color:'var(--ink-2)', marginTop:20, maxWidth:'52ch' }}>
              Three observations: the Blackwell shipment data beat whisper numbers and is being received as a re-acceleration signal rather than a normalization. Mortgage data at 10:30 carries asymmetric risk into the long end. And the rotation out of staples is now seven sessions deep — uncrowded enough to be interesting.
            </p>
            <div style={{ marginTop:28, display:'flex', alignItems:'center', gap:14 }}>
              <button className="btn btn-primary btn-sm">Continue reading <Icon name="arrow-r" size={13} /></button>
              <span className="smallcap-low" style={{ fontSize:11 }}>4 min read · by AI Analyst</span>
            </div>
          </div>

          {/* wire */}
          <div>
            <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:18 }}>
              <h3 className="serif-tight" style={{ fontSize:22 }}>Market wire</h3>
              <span className="lnk" style={{ fontSize:12, color:'var(--mute)' }}>All →</span>
            </div>
            {[
              { time:'09:41', src:'Reuters',   title:'NVIDIA hits intraday record as hyperscaler orders accelerate' },
              { time:'09:32', src:'Bloomberg', title:'Services revenue trajectory points to $100B run-rate at Apple' },
              { time:'09:18', src:'WSJ',       title:'Tesla cuts Model Y pricing 4% across US lineup' },
              { time:'09:02', src:'FT',        title:'Yields back up as Treasury auction tail surprises bond desks' },
            ].map((n,i) => (
              <div key={i} className="row-hover" style={{ padding:'14px 4px', borderBottom:'1px solid var(--line)' }}>
                <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:5 }}>
                  <span className="mono" style={{ fontSize:11, color:'var(--mute)' }}>{n.time}</span>
                  <span style={{ color:'var(--ghost)' }}>·</span>
                  <span className="smallcap-low" style={{ fontSize:10.5 }}>{n.src}</span>
                </div>
                <div className="serif" style={{ fontSize:15.5, lineHeight:1.4, color:'var(--ink)' }}>{n.title}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ===== footer line ===== */}
      <div style={{ padding:'0 48px 48px' }}>
        <div className="divider">
          <span className="serif" style={{ fontStyle:'italic', fontSize:14, color:'var(--mute)' }}>QuantorSignal · A daily research workspace</span>
        </div>
      </div>
    </div>
  );
}

// ---- mover list — refined, no boxes per row ----
function MoverList({ title, tone, stocks, onPick }) {
  return (
    <div>
      <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:14 }}>
        <h3 className="serif-tight" style={{ fontSize:22, color:'var(--ink)' }}>{title}</h3>
        <span className="smallcap-low" style={{ fontSize:11 }}>Top five</span>
      </div>
      <div>
        {stocks.map((s,i) => (
          <div key={s.ticker} onClick={() => onPick(s.ticker)} className="row-hover" style={{
            display:'grid', gridTemplateColumns:'24px 1fr auto auto', gap:16, alignItems:'center',
            padding:'16px 4px', borderTop:'1px solid var(--line)',
          }}>
            <span className="mono" style={{ fontSize:11, color:'var(--whisper)' }}>{(i+1).toString().padStart(2,'0')}</span>
            <div style={{ minWidth:0 }}>
              <div style={{ display:'flex', alignItems:'baseline', gap:10 }}>
                <span className="serif-tight" style={{ fontSize:18, color:'var(--ink)' }}>{s.ticker}</span>
                <span style={{ fontSize:12, color:'var(--mute)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{s.name}</span>
              </div>
              <div className="smallcap-low" style={{ fontSize:10.5, marginTop:2 }}>{s.sector}</div>
            </div>
            <Sparkline values={s.spark} width={60} height={22} stroke={s.chg >= 0 ? 'var(--up)' : 'var(--dn)'} />
            <div style={{ textAlign:'right', minWidth:96 }}>
              <div className="serif-num" style={{ fontSize:17, color:'var(--ink)' }}>{s.price.toFixed(2)}</div>
              <Delta value={s.chg} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { Dashboard });

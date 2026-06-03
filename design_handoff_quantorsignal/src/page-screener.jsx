// ====== Screener — v3 Atelier ======

function Screener({ goStock }) {
  const [search, setSearch] = useState('');
  const [sectorFilter, setSectorFilter] = useState(new Set());
  const [priceRange, setPriceRange] = useState([0, 1500]);
  const [minMcap, setMinMcap] = useState(1);
  const [maxPe, setMaxPe] = useState(300);
  const [minRoe, setMinRoe] = useState(0);
  const [dividendOnly, setDividendOnly] = useState(false);
  const [profitableOnly, setProfitableOnly] = useState(false);
  const [sortBy, setSortBy] = useState('mcap');
  const [sortDir, setSortDir] = useState('desc');
  const [savedView, setSavedView] = useState('Quality');
  const [selected, setSelected] = useState(new Set());

  const filtered = useMemo(() => {
    let rows = STOCKS.filter(s => {
      if (search) {
        const q = search.toLowerCase();
        if (!s.ticker.toLowerCase().includes(q) && !s.name.toLowerCase().includes(q)) return false;
      }
      if (sectorFilter.size > 0 && !sectorFilter.has(s.sector)) return false;
      if (s.price < priceRange[0] || s.price > priceRange[1]) return false;
      if (s.mcap < minMcap * 1e9) return false;
      if (s.pe != null && s.pe > maxPe) return false;
      if (s.roe < minRoe / 100) return false;
      if (dividendOnly && (s.divy ?? 0) <= 0) return false;
      if (profitableOnly && (s.pe == null || s.pe <= 0)) return false;
      return true;
    });
    rows.sort((a,b) => {
      const av = a[sortBy] ?? -Infinity;
      const bv = b[sortBy] ?? -Infinity;
      return sortDir === 'desc' ? bv - av : av - bv;
    });
    return rows;
  }, [search, sectorFilter, priceRange, minMcap, maxPe, minRoe, dividendOnly, profitableOnly, sortBy, sortDir]);

  const toggleSector = (s) => {
    const next = new Set(sectorFilter);
    next.has(s) ? next.delete(s) : next.add(s);
    setSectorFilter(next);
  };
  const reset = () => {
    setSearch(''); setSectorFilter(new Set()); setPriceRange([0,1500]); setMinMcap(1); setMaxPe(300); setMinRoe(0); setDividendOnly(false); setProfitableOnly(false);
  };
  const toggleSort = (k) => {
    if (sortBy === k) setSortDir(d => d === 'desc' ? 'asc' : 'desc');
    else { setSortBy(k); setSortDir('desc'); }
  };
  const toggleSelect = (t) => {
    const next = new Set(selected);
    next.has(t) ? next.delete(t) : next.add(t);
    setSelected(next);
  };

  const views = [
    { name: 'Quality',     desc: 'High ROE, low debt' },
    { name: 'Deep value',  desc: 'P/E under fifteen' },
    { name: 'Growth',      desc: 'Revenue above twenty' },
    { name: 'Dividend',    desc: 'Yield above two point five' },
    { name: 'Mega tech',   desc: 'Technology, $500B+' },
  ];

  const activeFilterCount = (search ? 1 : 0) + sectorFilter.size + (priceRange[0] > 0 || priceRange[1] < 1500 ? 1 : 0) + (minMcap > 1 ? 1 : 0) + (maxPe < 300 ? 1 : 0) + (minRoe > 0 ? 1 : 0) + (dividendOnly ? 1 : 0) + (profitableOnly ? 1 : 0);

  return (
    <div className="page-enter">
      <PageHeader
        title="Screener"
        subtitle="Adjust the criteria on the left. The table updates in place. Save the screens you'd return to."
        right={
          <>
            <button className="btn btn-ghost btn-sm"><Icon name="arrow-tr" size={13} /> Export</button>
            <button className="btn btn-primary btn-sm"><Icon name="plus" size={13} /> Save screen</button>
          </>
        }
      />

      {/* saved views — refined chips */}
      <div style={{ padding:'0 48px 28px', display:'flex', alignItems:'center', gap:8, flexWrap:'wrap' }}>
        <span className="smallcap-low" style={{ fontSize:11, marginRight:8 }}>Saved screens</span>
        {views.map(v => (
          <button key={v.name} onClick={() => setSavedView(v.name)} style={{
            display:'flex', alignItems:'baseline', gap:8,
            padding:'8px 14px', borderRadius:999, cursor:'pointer',
            background: savedView === v.name ? 'var(--ink)' : 'var(--surface)',
            color: savedView === v.name ? 'var(--ivory)' : 'var(--ink)',
            border:'1px solid', borderColor: savedView === v.name ? 'var(--ink)' : 'var(--line)',
            transition:'all 240ms var(--ease)',
            fontFamily: 'Geist', fontSize: 12.5, fontWeight: 500,
          }}>
            {v.name}
            <span style={{ fontSize: 10.5, opacity: savedView === v.name ? 0.7 : 0.5, fontStyle: 'italic', fontFamily: 'Spectral' }}>{v.desc}</span>
          </button>
        ))}
      </div>

      {/* body */}
      <div style={{ padding:'0 48px 48px', display:'grid', gridTemplateColumns:'280px minmax(0, 1fr)', gap:32 }}>
        {/* ===== filter rail ===== */}
        <aside style={{ position:'sticky', top:24, alignSelf:'flex-start' }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:18 }}>
            <h3 className="serif-tight" style={{ fontSize:22 }}>Criteria</h3>
            {activeFilterCount > 0 && (
              <button onClick={reset} className="btn-bare" style={{ fontSize:11.5, padding:'4px 0', color:'var(--dn)' }}>Reset</button>
            )}
          </div>

          <FilterField label="Ticker or company">
            <div style={{ position:'relative' }}>
              <span style={{ position:'absolute', left:14, top:'50%', transform:'translateY(-50%)', color:'var(--mute)' }}>
                <Icon name="search" size={13} />
              </span>
              <input className="input" style={{ paddingLeft:36 }} value={search} onChange={e => setSearch(e.target.value)} placeholder="e.g. NVDA" />
            </div>
          </FilterField>

          <FilterField label="Price range" value={`$${priceRange[0]} – $${priceRange[1]}`}>
            <div style={{ display:'flex', gap:6 }}>
              <input className="input" type="number" value={priceRange[0]} onChange={e => setPriceRange([+e.target.value, priceRange[1]])} placeholder="Min" />
              <input className="input" type="number" value={priceRange[1]} onChange={e => setPriceRange([priceRange[0], +e.target.value])} placeholder="Max" />
            </div>
          </FilterField>

          <FilterField label="Minimum market cap" value={minMcap >= 1000 ? `$${(minMcap/1000).toFixed(1)}T` : `$${minMcap}B`}>
            <input className="rng" type="range" min="1" max="3500" step="1" value={minMcap} onChange={e => setMinMcap(+e.target.value)} />
            <div style={{ display:'flex', justifyContent:'space-between', marginTop:8 }}>
              <span className="mono" style={{ fontSize:10, color:'var(--whisper)' }}>1B</span>
              <span className="mono" style={{ fontSize:10, color:'var(--whisper)' }}>3.5T</span>
            </div>
          </FilterField>

          <FilterField label="Maximum P/E" value={maxPe === 300 ? 'Any' : maxPe}>
            <input className="rng" type="range" min="5" max="300" step="1" value={maxPe} onChange={e => setMaxPe(+e.target.value)} />
          </FilterField>

          <FilterField label="Minimum ROE" value={`${minRoe}%`}>
            <input className="rng" type="range" min="0" max="100" step="1" value={minRoe} onChange={e => setMinRoe(+e.target.value)} />
          </FilterField>

          <FilterField label="Sectors" value={sectorFilter.size > 0 ? `${sectorFilter.size} of ${SECTORS.length}` : 'Any'}>
            <div style={{ display:'flex', flexDirection:'column' }}>
              {SECTORS.map(s => {
                const on = sectorFilter.has(s);
                return (
                  <label key={s} onClick={() => toggleSector(s)} className="row-hover" style={{
                    display:'flex', alignItems:'center', justifyContent:'space-between',
                    padding:'7px 0', cursor:'pointer',
                  }}>
                    <span style={{ fontSize:13, color: on ? 'var(--ink)' : 'var(--ink-2)', fontWeight: on ? 500 : 400 }}>{s}</span>
                    <span className={`check ${on ? 'on' : ''}`}>
                      {on && <span style={{ color:'var(--ivory)', display:'inline-flex' }}><Icon name="check-sm" size={10} /></span>}
                    </span>
                  </label>
                );
              })}
            </div>
          </FilterField>

          <div style={{ display:'flex', flexDirection:'column', gap:14, paddingTop:18, marginTop:8, borderTop:'1px solid var(--line)' }}>
            <Toggle label="Dividend payers only" checked={dividendOnly} onChange={setDividendOnly} />
            <Toggle label="Profitable only (P/E > 0)" checked={profitableOnly} onChange={setProfitableOnly} />
          </div>

          <div style={{ marginTop:20, padding:'12px 14px', display:'flex', alignItems:'center', gap:10, background:'var(--ivory)', borderRadius:10, border:'1px solid var(--line)' }}>
            <span className="dot dot-forest pulse" />
            <span style={{ fontSize:11.5, color:'var(--mute)' }}>Auto-runs as you adjust</span>
          </div>
        </aside>

        {/* ===== results ===== */}
        <div>
          {/* toolbar */}
          <div style={{ display:'flex', alignItems:'flex-end', justifyContent:'space-between', marginBottom:18 }}>
            <div>
              <div className="smallcap-low" style={{ fontSize:11, marginBottom:6 }}>{filtered.length === STOCKS.length ? 'Universe' : 'Result set'} · {savedView}</div>
              <div style={{ display:'flex', alignItems:'baseline', gap:10 }}>
                <span className="readout" style={{ fontSize:42, color:'var(--ink)' }}>{filtered.length.toString().padStart(3,'0')}</span>
                <span className="serif" style={{ fontSize:14, color:'var(--mute)', fontStyle:'italic' }}>matches of {STOCKS.length}</span>
              </div>
            </div>
            <div style={{ display:'flex', gap:10, alignItems:'center' }}>
              {selected.size > 0 && (
                <>
                  <span className="smallcap-low" style={{ fontSize:11 }}>{selected.size} selected</span>
                  <button className="btn btn-quiet btn-sm"><Icon name="bookmark" size={13} /> Save selection</button>
                  <button className="btn btn-quiet btn-sm"><Icon name="replay" size={13} /> Backtest</button>
                  <button className="btn-bare" onClick={() => setSelected(new Set())}><Icon name="x" size={13} /></button>
                </>
              )}
              <button className="btn btn-quiet btn-sm"><Icon name="sliders" size={13} /> Columns</button>
            </div>
          </div>

          {/* table */}
          <div className="card" style={{ overflow:'hidden' }}>
            <div style={{ overflowX:'auto' }}>
              <table style={{ width:'100%', borderCollapse:'separate', borderSpacing:0, minWidth:1080 }}>
                <thead>
                  <tr>
                    <Th style={{ width:36 }}>
                      <span className={`check ${selected.size === filtered.length && filtered.length > 0 ? 'on' : ''}`} onClick={() => {
                        if (selected.size === filtered.length) setSelected(new Set());
                        else setSelected(new Set(filtered.map(s => s.ticker)));
                      }}>
                        {selected.size === filtered.length && filtered.length > 0 && <span style={{ color:'var(--ivory)', display:'inline-flex' }}><Icon name="check-sm" size={10} /></span>}
                      </span>
                    </Th>
                    <Th sortKey="ticker" current={sortBy} dir={sortDir} onSort={toggleSort}>Symbol</Th>
                    <Th sortKey="price"  current={sortBy} dir={sortDir} onSort={toggleSort} align="right">Last</Th>
                    <Th sortKey="chg"    current={sortBy} dir={sortDir} onSort={toggleSort} align="right">Day</Th>
                    <Th align="center">Trend</Th>
                    <Th sortKey="mcap"   current={sortBy} dir={sortDir} onSort={toggleSort} align="right">Market cap</Th>
                    <Th sortKey="pe"     current={sortBy} dir={sortDir} onSort={toggleSort} align="right">P/E</Th>
                    <Th sortKey="roe"    current={sortBy} dir={sortDir} onSort={toggleSort} align="right">ROE</Th>
                    <Th sortKey="divy"   current={sortBy} dir={sortDir} onSort={toggleSort} align="right">Yield</Th>
                    <Th sortKey="vol"    current={sortBy} dir={sortDir} onSort={toggleSort} align="right">Volume</Th>
                    <Th>Sector</Th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s, i) => {
                    const isSel = selected.has(s.ticker);
                    return (
                      <tr key={s.ticker} className="row-hover" style={{ background: isSel ? 'var(--forest-soft)' : 'transparent' }} onClick={() => goStock(s.ticker)}>
                        <Td onClick={(e) => { e.stopPropagation(); toggleSelect(s.ticker); }}>
                          <span className={`check ${isSel ? 'on' : ''}`}>
                            {isSel && <span style={{ color:'var(--ivory)', display:'inline-flex' }}><Icon name="check-sm" size={10} /></span>}
                          </span>
                        </Td>
                        <Td>
                          <div className="serif-tight" style={{ fontSize:17, color:'var(--ink)', lineHeight:1.15 }}>{s.ticker}</div>
                          <div style={{ fontSize:11.5, color:'var(--mute)', marginTop:2, maxWidth:'22ch', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{s.name}</div>
                        </Td>
                        <Td align="right"><span className="serif-num" style={{ fontSize:15, color:'var(--ink)' }}>{s.price.toFixed(2)}</span></Td>
                        <Td align="right"><Delta value={s.chg} /></Td>
                        <Td align="center">
                          <div style={{ display:'inline-flex', color: s.chg >= 0 ? 'var(--up)' : 'var(--dn)' }}>
                            <Sparkline values={s.spark} width={68} height={22} stroke="currentColor" />
                          </div>
                        </Td>
                        <Td align="right"><span className="serif-num" style={{ fontSize:14 }}>{fmtMcap(s.mcap)}</span></Td>
                        <Td align="right"><span className="serif-num" style={{ fontSize:14, color: s.pe == null ? 'var(--whisper)' : 'var(--ink)' }}>{s.pe != null ? s.pe.toFixed(1) : '—'}</span></Td>
                        <Td align="right"><span className="serif-num" style={{ fontSize:14 }}>{s.roe != null ? (s.roe*100).toFixed(0)+'%' : '—'}</span></Td>
                        <Td align="right"><span className="serif-num" style={{ fontSize:14, color: s.divy > 0 ? 'var(--ink)' : 'var(--whisper)' }}>{s.divy > 0 ? (s.divy*100).toFixed(2)+'%' : '—'}</span></Td>
                        <Td align="right"><span className="mono" style={{ fontSize:12, color:'var(--mute)' }}>{fmtVol(s.vol)}</span></Td>
                        <Td><span style={{ fontSize:12, color:'var(--mute)' }}>{s.sector}</span></Td>
                      </tr>
                    );
                  })}
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={11} style={{ padding:'90px 24px', textAlign:'center' }}>
                        <div className="serif-tight" style={{ fontSize:28, color:'var(--ink-2)' }}>No matches</div>
                        <div style={{ fontSize:13, color:'var(--mute)', marginTop:6 }}>Loosen a criterion to surface something.</div>
                        <button onClick={reset} className="btn btn-primary btn-sm" style={{ marginTop:20 }}>Reset criteria</button>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* pagination */}
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'20px 4px' }}>
            <span className="smallcap-low" style={{ fontSize:11 }}>{filtered.length === 0 ? '0' : `1 – ${Math.min(filtered.length, 50)}`} of {filtered.length}</span>
            <div style={{ display:'flex', gap:4, alignItems:'center' }}>
              <button className="btn-bare" style={{ padding:'6px 8px' }}><Icon name="chev-l" size={13} /></button>
              {[1,2,3].map(p => (
                <button key={p} style={{
                  background: p === 1 ? 'var(--ink)' : 'transparent',
                  color: p === 1 ? 'var(--ivory)' : 'var(--ink-2)',
                  border: '1px solid', borderColor: p === 1 ? 'var(--ink)' : 'var(--line)',
                  width: 30, height: 30, borderRadius: 6, cursor: 'pointer',
                  fontFamily: 'Spectral', fontSize: 13, fontWeight: 500,
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 200ms var(--ease)',
                }}>{p}</button>
              ))}
              <span className="mono" style={{ fontSize:11, color:'var(--whisper)', padding:'6px 4px' }}>…</span>
              <button className="btn-bare" style={{ padding:'6px 8px' }}><Icon name="chev-r" size={13} /></button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FilterField({ label, value, children }) {
  return (
    <div style={{ marginBottom:20 }}>
      <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', marginBottom:9 }}>
        <span style={{ fontSize:12.5, fontWeight:500, color:'var(--ink)' }}>{label}</span>
        {value && <span className="serif" style={{ fontSize:12.5, color:'var(--forest)', fontStyle:'italic' }}>{value}</span>}
      </div>
      {children}
    </div>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <label onClick={() => onChange(!checked)} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', cursor:'pointer' }}>
      <span style={{ fontSize:12.5, color:'var(--ink)' }}>{label}</span>
      <span style={{
        width:36, height:20, borderRadius:999, background: checked ? 'var(--ink)' : 'var(--ghost)',
        position:'relative', flexShrink:0, transition:'all 240ms var(--ease)',
      }}>
        <span style={{
          position:'absolute', top:2, left: checked ? 18 : 2, width:16, height:16, borderRadius:999,
          background:'var(--ivory)', transition:'left 240ms var(--ease)',
          boxShadow:'0 1px 2px rgba(0,0,0,0.2)',
        }} />
      </span>
    </label>
  );
}

function Th({ children, sortKey, current, dir, onSort, align = 'left', style }) {
  const active = sortKey && current === sortKey;
  return (
    <th onClick={sortKey ? () => onSort(sortKey) : undefined} style={{
      padding:'18px 18px 14px', textAlign:align, cursor: sortKey ? 'pointer' : 'default',
      userSelect:'none', borderBottom:'1px solid var(--line)',
      ...style,
    }}>
      <span className="smallcap-low" style={{ fontSize:11, color: active ? 'var(--ink)' : 'var(--mute)', display:'inline-flex', alignItems:'center', gap:5 }}>
        {children}
        {sortKey && <span style={{ opacity: active ? 1 : 0.3, transform: active && dir === 'asc' ? 'rotate(180deg)' : 'none', display:'inline-flex', transition: 'transform 240ms var(--ease)' }}><Icon name="chev-d" size={10} /></span>}
      </span>
    </th>
  );
}

function Td({ children, align = 'left', onClick }) {
  return <td onClick={onClick} style={{ padding:'14px 18px', textAlign:align, verticalAlign:'middle', borderBottom:'1px solid var(--line)' }}>{children}</td>;
}

Object.assign(window, { Screener });

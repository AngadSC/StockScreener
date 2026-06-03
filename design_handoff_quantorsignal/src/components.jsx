// ====== shared components — v3 Atelier ======

const { useState, useEffect, useMemo, useRef } = React;

// ---- formatters ----
const fmtPrice = (n) => n == null ? '—' : `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtPct = (n, withSign = true) => {
  if (n == null) return '—';
  const sign = withSign ? (n >= 0 ? '+' : '') : '';
  return `${sign}${n.toFixed(2)}%`;
};
const fmtMcap = (n) => {
  if (n == null) return '—';
  if (n >= 1e12) return `$${(n/1e12).toFixed(2)}T`;
  if (n >= 1e9)  return `$${(n/1e9).toFixed(1)}B`;
  if (n >= 1e6)  return `$${(n/1e6).toFixed(0)}M`;
  return `$${n.toLocaleString()}`;
};
const fmtVol = (n) => {
  if (n == null) return '—';
  if (n >= 1e9) return `${(n/1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n/1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n/1e3).toFixed(1)}K`;
  return String(n);
};

// ---- icons (thinner strokes — 1.4) ----
function Icon({ name, size = 16, stroke = 1.4 }) {
  const props = {
    width: size, height: size, viewBox: '0 0 24 24',
    fill: 'none', stroke: 'currentColor', strokeWidth: stroke,
    strokeLinecap: 'round', strokeLinejoin: 'round',
    style: { display: 'block', flexShrink: 0 },
  };
  switch (name) {
    case 'search':    return <svg {...props}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>;
    case 'arrow-r':   return <svg {...props}><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>;
    case 'arrow-tr':  return <svg {...props}><path d="M7 17 17 7"/><path d="M8 7h9v9"/></svg>;
    case 'arrow-up':  return <svg {...props}><path d="m6 9 6-6 6 6"/><path d="M12 3v18"/></svg>;
    case 'arrow-dn':  return <svg {...props}><path d="m6 15 6 6 6-6"/><path d="M12 3v18"/></svg>;
    case 'chev-d':    return <svg {...props}><path d="m6 9 6 6 6-6"/></svg>;
    case 'chev-r':    return <svg {...props}><path d="m9 6 6 6-6 6"/></svg>;
    case 'chev-l':    return <svg {...props}><path d="m15 6-6 6 6 6"/></svg>;
    case 'plus':      return <svg {...props}><path d="M12 5v14M5 12h14"/></svg>;
    case 'minus':     return <svg {...props}><path d="M5 12h14"/></svg>;
    case 'check':     return <svg {...props} strokeWidth="1.6"><path d="m4 12 5 5L20 6"/></svg>;
    case 'check-sm':  return <svg width={size} height={size} viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{display:'block'}}><path d="m2.5 6.5 2.5 2.5L9.5 3.5"/></svg>;
    case 'bookmark':  return <svg {...props}><path d="M6 4h12v17l-6-4-6 4z"/></svg>;
    case 'bookmark-f': return <svg {...props} fill="currentColor"><path d="M6 4h12v17l-6-4-6 4z"/></svg>;
    case 'star':      return <svg {...props}><path d="M12 3 14.5 9l6 .5-4.6 4 1.4 6L12 16.5 6.7 19.5l1.4-6L3.5 9.5l6-.5L12 3z"/></svg>;
    case 'home':      return <svg {...props}><path d="M3 11 12 3l9 8"/><path d="M5 10v10h14V10"/></svg>;
    case 'filter':    return <svg {...props}><path d="M3 6h18M6 12h12M10 18h4"/></svg>;
    case 'chart':     return <svg {...props}><path d="M3 21V8m0 13h18M8 17v-6m4 6V5m4 12V11m4 6V8"/></svg>;
    case 'sliders':   return <svg {...props}><path d="M4 6h7M15 6h5M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="13" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/></svg>;
    case 'sparkles':  return <svg {...props}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6 8.5 8.5M15.5 15.5l2.9 2.9M5.6 18.4 8.5 15.5M15.5 8.5l2.9-2.9"/></svg>;
    case 'replay':    return <svg {...props}><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>;
    case 'wallet':    return <svg {...props}><path d="M3 7a2 2 0 0 1 2-2h13v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M16 12h3"/><path d="M3 8h15"/></svg>;
    case 'pie':       return <svg {...props}><path d="M21 12A9 9 0 1 1 12 3v9z"/></svg>;
    case 'bell':      return <svg {...props}><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10 21a2 2 0 0 0 4 0"/></svg>;
    case 'cmd':       return <svg {...props}><path d="M9 6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V6Z"/></svg>;
    case 'gear':      return <svg {...props}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/></svg>;
    case 'x':         return <svg {...props}><path d="m6 6 12 12M18 6 6 18"/></svg>;
    case 'globe':     return <svg {...props}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>;
    case 'briefcase': return <svg {...props}><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V4h6v3"/></svg>;
    default: return null;
  }
}

// ====== Quantor mark — faceted vault crest, brass on obsidian ======
function Mark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" style={{ display:'block', flexShrink:0 }}>
      <defs>
        <linearGradient id="brass" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#c8d2de" />
          <stop offset="0.5" stopColor="#aeb9c7" />
          <stop offset="1" stopColor="#8a96a6" />
        </linearGradient>
        <radialGradient id="crestFill" cx="0.5" cy="0.38" r="0.7">
          <stop offset="0" stopColor="#1a1822" />
          <stop offset="1" stopColor="#0c0b0e" />
        </radialGradient>
      </defs>
      {/* hexagonal crest plate */}
      <path d="M18 2.2 L31 9.5 V26.5 L18 33.8 L5 26.5 V9.5 Z"
            fill="url(#crestFill)" stroke="url(#brass)" strokeWidth="1" strokeLinejoin="round" />
      {/* inner bevel line */}
      <path d="M18 5.4 L28.2 11.1 V24.9 L18 30.6 L7.8 24.9 V11.1 Z"
            fill="none" stroke="#aeb9c7" strokeOpacity="0.22" strokeWidth="0.7" strokeLinejoin="round" />
      {/* Q serif */}
      <text x="18" y="24.4" textAnchor="middle" fontFamily="Spectral, serif" fontWeight="500" fontSize="18" fill="url(#brass)" letterSpacing="-0.04em">Q</text>
    </svg>
  );
}

// ====== sparkline — thinner stroke, no glow ======
function Sparkline({ values, width = 80, height = 24, stroke = 'currentColor', strokeWidth = 1.25, fill = false }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values), max = Math.max(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => [
    (i / (values.length - 1)) * (width - 4) + 2,
    height - 2 - ((v - min) / range) * (height - 4),
  ]);
  const d = pts.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(' ');
  const area = `${d} L${pts[pts.length-1][0]},${height} L${pts[0][0]},${height}Z`;
  const last = pts[pts.length-1];
  return (
    <svg className="spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {fill && <path d={area} fill={stroke} opacity="0.10" />}
      <path d={d} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r="1.6" fill={stroke} />
    </svg>
  );
}

// ====== area chart — noir grid ======
function AreaChart({ values, height = 280, accent = '#aeb9c7', baseline = true, vWidth = 1000 }) {
  const padL = 0, padR = 60, padT = 20, padB = 30;
  if (!values || values.length < 2) return null;
  const min = Math.min(...values), max = Math.max(...values);
  const range = max - min || 1;
  const w = vWidth, h = height;
  const pts = values.map((v, i) => [
    padL + (i / (values.length - 1)) * (w - padL - padR),
    h - padB - ((v - min) / range) * (h - padT - padB),
  ]);
  const d = pts.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(' ');
  const area = `${d} L${pts[pts.length-1][0]},${h - padB} L${pts[0][0]},${h - padB}Z`;
  const last = pts[pts.length-1];

  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const monthIdx = new Date().getMonth();
  const xTicks = [0, 0.25, 0.5, 0.75, 1].map((t,i) => ({
    x: padL + t * (w - padL - padR),
    label: months[(monthIdx - 3 + i + 12) % 12],
  }));
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map(t => ({
    y: h - padB - t * (h - padT - padB),
    v: min + t * range,
  }));

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none" style={{ display:'block' }}>
      <defs>
        <linearGradient id="aGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={accent} stopOpacity="0.28" />
          <stop offset="100%" stopColor={accent} stopOpacity="0" />
        </linearGradient>
      </defs>
      {baseline && yTicks.map((t,i) => (
        <g key={i}>
          <line x1={padL} x2={w-padR} y1={t.y} y2={t.y} stroke="rgba(232,222,198,0.07)" strokeWidth="0.75" />
          <text x={w - padR + 10} y={t.y + 3} fontSize="11" fontFamily="Spectral" fill="#7d7666" fontWeight="400">
            {t.v.toFixed(2)}
          </text>
        </g>
      ))}
      <path d={area} fill="url(#aGrad)" />
      <path d={d} fill="none" stroke={accent} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <line x1={last[0]} x2={last[0]} y1={padT} y2={h - padB} stroke={accent} strokeWidth="0.6" strokeDasharray="2 4" opacity="0.4" />
      <circle cx={last[0]} cy={last[1]} r="3" fill={accent} />
      {xTicks.map((t,i) => (
        <text key={i} x={t.x} y={h - 8} fontSize="11" fontFamily="Spectral" fill="#7d7666" fontWeight="400"
              textAnchor={i===0?'start':i===xTicks.length-1?'end':'middle'}>
            {t.label}
        </text>
      ))}
    </svg>
  );
}

// ====== delta indicator — restrained, no triangles ======
function Delta({ value, size = 'sm' }) {
  if (value == null) return <span style={{ color: 'var(--whisper)' }}>—</span>;
  const up = value >= 0;
  const px = size === 'lg' ? 15 : 12.5;
  return (
    <span className="mono" style={{
      color: up ? 'var(--up)' : 'var(--dn)',
      fontSize: px,
      display: 'inline-flex',
      alignItems: 'center',
      gap: 3,
    }}>
      <span style={{ fontSize: px - 5, lineHeight: 1, transform: up ? 'translateY(-0.5px)' : 'translateY(0.5px)' }}>{up ? '↑' : '↓'}</span>
      {fmtPct(value, false)}
    </span>
  );
}

// ====== left sidebar nav ======
function Sidebar({ route, setRoute, onCmdK }) {
  const items = [
    { id: 'home',     label: 'Markets',     icon: 'home' },
    { id: 'screener', label: 'Screener',    icon: 'filter' },
    { id: 'watch',    label: 'Watchlist',   icon: 'bookmark' },
    { id: 'ai',       label: 'AI Analyst',  icon: 'sparkles' },
    { id: 'backtest', label: 'Backtester',  icon: 'replay' },
  ];

  return (
    <aside style={{ width: 248, flexShrink: 0, padding: '28px 24px', position: 'sticky', top: 0, height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 13, paddingBottom: 8 }}>
        <Mark size={34} />
        <span className="serif-tight" style={{ fontSize: 21, color: 'var(--ink)', letterSpacing:'-0.02em' }}>Quantor<span style={{ fontStyle: 'italic', fontWeight: 400, color:'var(--forest)' }}>signal</span></span>
      </div>

      <div style={{ height: 28 }} />

      {/* search trigger */}
      <button onClick={onCmdK} className="btn btn-quiet btn-sm" style={{ width: '100%', justifyContent:'flex-start', gap: 10, paddingLeft: 12, paddingRight: 10 }}>
        <Icon name="search" size={13} stroke={1.5} />
        <span style={{ color:'var(--whisper)', flex: 1, textAlign:'left' }}>Search</span>
        <span className="kbd">⌘K</span>
      </button>

      <div style={{ height: 28 }} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {items.map(it => {
          const active = route.name === it.id || (it.id === 'home' && route.name === 'stock');
          return (
            <button key={it.id} onClick={() => setRoute({ name: it.id })} className={`nav-item ${active ? 'active' : ''}`}>
              <Icon name={it.icon} size={15} stroke={1.4} />
              {it.label}
            </button>
          );
        })}
      </div>

      <div style={{ flex: 1 }} />

      {/* Pro card — quieter, more refined */}
      <div style={{ padding: '20px 18px', borderRadius: 14, background: 'var(--ivory)', border: '1px solid var(--line)', position: 'relative' }}>
        <div style={{ display:'flex', alignItems:'center', gap: 6 }}>
          <span className="dot dot-forest" />
          <span className="smallcap" style={{ fontSize: 10, color: 'var(--forest)' }}>Quantor Pro</span>
        </div>
        <div className="serif-tight" style={{ fontSize: 18, marginTop: 8, lineHeight: 1.25 }}>
          Unlimited screens, AI research, live feed.
        </div>
        <button className="btn btn-forest btn-xs" style={{ width: '100%', marginTop: 14, justifyContent:'center' }}>
          Upgrade — $29/mo
        </button>
      </div>

      <div style={{ height: 16 }} />

      {/* user row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 4px' }}>
        <div style={{ width: 32, height: 32, borderRadius: 999, background: 'var(--ink)', display: 'grid', placeItems: 'center', color: 'var(--ivory)', fontFamily: 'Spectral', fontSize: 14, fontWeight: 400 }}>J</div>
        <div style={{ flex: 1, minWidth: 0, lineHeight: 1.3 }}>
          <div style={{ fontSize: 12.5, fontWeight: 500 }}>Jordan Vance</div>
          <div style={{ fontSize: 11, color: 'var(--mute)' }}>jvance@quantor</div>
        </div>
        <button className="btn-bare" style={{ padding: 4 }}><Icon name="gear" size={14} /></button>
      </div>
    </aside>
  );
}

// ====== page header — title + subtle subtitle, optional right ======
function PageHeader({ eyebrow, title, subtitle, right }) {
  return (
    <div style={{ padding: '40px 48px 24px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
      <div style={{ flex: '1 1 320px', minWidth: 0 }}>
        {eyebrow && <div className="smallcap" style={{ marginBottom: 14 }}>{eyebrow}</div>}
        <h1 className="serif-tight" style={{ fontSize: 'clamp(36px, 4vw, 52px)', lineHeight: 1.02, color: 'var(--ink)' }}>{title}</h1>
        {subtitle && <div style={{ fontSize: 15, color: 'var(--mute)', marginTop: 12, maxWidth: '56ch', lineHeight: 1.5 }}>{subtitle}</div>}
      </div>
      {right && <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', justifyContent:'flex-end' }}>{right}</div>}
    </div>
  );
}

// ====== command palette ======
function CommandPalette({ open, onClose, onPick }) {
  const [q, setQ] = useState('');
  const inputRef = useRef(null);
  useEffect(() => {
    if (open) { setQ(''); setTimeout(() => inputRef.current?.focus(), 30); }
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return STOCKS.slice(0, 7);
    return STOCKS.filter(s => s.ticker.toLowerCase().includes(term) || s.name.toLowerCase().includes(term)).slice(0, 8);
  }, [q]);

  if (!open) return null;
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(10px)', zIndex: 100, display: 'grid', placeItems: 'start center', paddingTop: '14vh' }}>
      <div onClick={e => e.stopPropagation()} className="card" style={{ width: 'min(640px, 92vw)', overflow: 'hidden', boxShadow: 'var(--shadow-3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '18px 22px', borderBottom: '1px solid var(--line)' }}>
          <Icon name="search" size={15} />
          <input ref={inputRef} value={q} onChange={e => setQ(e.target.value)} placeholder="Search by ticker or company"
            style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: 'var(--ink)', fontSize: 15, fontFamily: 'Spectral', fontWeight: 400 }} />
          <span className="kbd">ESC</span>
        </div>
        <div style={{ padding: 10, maxHeight: '52vh', overflowY: 'auto' }}>
          <div className="smallcap" style={{ padding: '12px 16px 8px', fontSize: 9.5 }}>{q ? 'Matches' : 'Suggested'}</div>
          {results.map(s => (
            <button key={s.ticker} onClick={() => { onPick(s.ticker); onClose(); }}
              style={{
                display: 'flex', alignItems: 'center', gap: 14, width: '100%', padding: '12px 16px',
                background: 'transparent', border: 'none', color: 'var(--ink)', cursor: 'pointer',
                borderRadius: 8, textAlign: 'left', transition: 'background 200ms var(--ease)',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <span className="serif-tight" style={{ fontSize: 16, width: 60, color: 'var(--ink)' }}>{s.ticker}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: 'var(--ink-2)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{s.name}</div>
                <div style={{ fontSize: 11, color: 'var(--mute)', marginTop: 1 }}>{s.sector}</div>
              </div>
              <span className="mono" style={{ fontSize: 12.5 }}>{fmtPrice(s.price)}</span>
              <Delta value={s.chg} />
            </button>
          ))}
          {results.length === 0 && <div style={{ padding: 28, textAlign: 'center', color: 'var(--mute)' }}>No matches.</div>}
        </div>
      </div>
    </div>
  );
}

// ====== bar ======
function Bar({ pct, accent = 'var(--forest)' }) {
  return (
    <div className="bar" style={{ flex: 1 }}>
      <div className="bar-fill" style={{ width: `${pct}%`, background: accent }} />
    </div>
  );
}

Object.assign(window, {
  fmtPrice, fmtPct, fmtMcap, fmtVol,
  Icon, Mark, Sparkline, AreaChart, Delta, Bar,
  Sidebar, PageHeader, CommandPalette,
});

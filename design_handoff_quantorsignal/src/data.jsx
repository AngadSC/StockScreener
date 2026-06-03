// ====== mock market data ======
// All data is fictional and for design purposes only.

const STOCKS = [
  { ticker: 'NVDA', name: 'NVIDIA Corp.',          sector: 'Technology',           industry: 'Semiconductors',         price: 1248.32, chg: 4.86,  mcap: 3.07e12, vol: 48.2e6,  pe: 76.4, roe: 0.91, divy: 0.0002, beta: 1.68, rev_g: 0.262, w52l: 412.50, w52h: 1268.04 },
  { ticker: 'AAPL', name: 'Apple Inc.',            sector: 'Technology',           industry: 'Consumer Electronics',   price: 232.14, chg: 0.42,   mcap: 3.52e12, vol: 52.4e6,  pe: 36.1, roe: 1.50, divy: 0.0046, beta: 1.25, rev_g: 0.061, w52l: 164.08, w52h: 237.49 },
  { ticker: 'MSFT', name: 'Microsoft Corp.',       sector: 'Technology',           industry: 'Software—Infrastructure',price: 438.92, chg: 1.18,   mcap: 3.26e12, vol: 18.7e6,  pe: 38.7, roe: 0.37, divy: 0.0069, beta: 0.88, rev_g: 0.155, w52l: 308.10, w52h: 468.35 },
  { ticker: 'TSLA', name: 'Tesla, Inc.',           sector: 'Consumer Cyclical',    industry: 'Auto Manufacturers',     price: 218.80, chg: -3.42,  mcap: 698.4e9, vol: 96.3e6,  pe: 64.2, roe: 0.23, divy: 0,      beta: 2.31, rev_g: 0.018, w52l: 138.80, w52h: 299.29 },
  { ticker: 'AMZN', name: 'Amazon.com, Inc.',      sector: 'Consumer Cyclical',    industry: 'Internet Retail',        price: 184.72, chg: 0.91,   mcap: 1.92e12, vol: 28.4e6,  pe: 49.6, roe: 0.18, divy: 0,      beta: 1.16, rev_g: 0.118, w52l: 118.35, w52h: 201.20 },
  { ticker: 'META', name: 'Meta Platforms',        sector: 'Communication Svc.',   industry: 'Internet Content',       price: 542.18, chg: 2.04,   mcap: 1.37e12, vol: 12.8e6,  pe: 28.4, roe: 0.34, divy: 0.0037, beta: 1.21, rev_g: 0.221, w52l: 313.66, w52h: 559.84 },
  { ticker: 'GOOG', name: 'Alphabet Inc. (Class C)',sector: 'Communication Svc.',  industry: 'Internet Content',       price: 175.20, chg: -0.18,  mcap: 2.15e12, vol: 18.2e6,  pe: 24.6, roe: 0.30, divy: 0.0046, beta: 1.04, rev_g: 0.137, w52l: 121.46, w52h: 191.75 },
  { ticker: 'AVGO', name: 'Broadcom Inc.',         sector: 'Technology',           industry: 'Semiconductors',         price: 168.45, chg: 3.21,   mcap: 786.2e9, vol: 22.1e6,  pe: 65.2, roe: 0.16, divy: 0.0125, beta: 1.18, rev_g: 0.471, w52l: 79.74,  w52h: 185.16 },
  { ticker: 'AMD',  name: 'Advanced Micro Devices',sector: 'Technology',           industry: 'Semiconductors',         price: 158.32, chg: 2.78,   mcap: 256.4e9, vol: 32.4e6,  pe: 195.4,roe: 0.03, divy: 0,      beta: 1.69, rev_g: 0.179, w52l: 116.37, w52h: 227.30 },
  { ticker: 'JPM',  name: 'JPMorgan Chase & Co.',  sector: 'Financial Services',   industry: 'Banks—Diversified',      price: 218.94, chg: 0.62,   mcap: 624.8e9, vol: 8.2e6,   pe: 12.4, roe: 0.16, divy: 0.0235, beta: 1.10, rev_g: 0.072, w52l: 144.41, w52h: 225.48 },
  { ticker: 'V',    name: 'Visa Inc.',             sector: 'Financial Services',   industry: 'Credit Services',        price: 286.74, chg: 0.34,   mcap: 568.1e9, vol: 6.4e6,   pe: 32.1, roe: 0.51, divy: 0.0073, beta: 0.95, rev_g: 0.098, w52l: 227.84, w52h: 290.96 },
  { ticker: 'MA',   name: 'Mastercard Inc.',       sector: 'Financial Services',   industry: 'Credit Services',        price: 478.31, chg: 0.89,   mcap: 449.2e9, vol: 3.1e6,   pe: 39.8, roe: 1.74, divy: 0.0055, beta: 1.04, rev_g: 0.106, w52l: 359.77, w52h: 490.00 },
  { ticker: 'LLY',  name: 'Eli Lilly & Co.',       sector: 'Healthcare',           industry: 'Drug Manufacturers',     price: 932.65, chg: -1.24,  mcap: 886.4e9, vol: 4.2e6,   pe: 121.6,roe: 0.57, divy: 0.0058, beta: 0.42, rev_g: 0.358, w52l: 561.43, w52h: 972.53 },
  { ticker: 'UNH',  name: 'UnitedHealth Group',    sector: 'Healthcare',           industry: 'Healthcare Plans',       price: 538.22, chg: -0.42,  mcap: 496.3e9, vol: 3.8e6,   pe: 29.4, roe: 0.25, divy: 0.0156, beta: 0.55, rev_g: 0.082, w52l: 436.38, w52h: 630.73 },
  { ticker: 'XOM',  name: 'Exxon Mobil Corp.',     sector: 'Energy',               industry: 'Oil & Gas Integrated',   price: 118.65, chg: 1.36,   mcap: 510.7e9, vol: 12.4e6,  pe: 14.2, roe: 0.18, divy: 0.0316, beta: 0.96, rev_g: 0.013, w52l: 95.77,  w52h: 126.34 },
  { ticker: 'CVX',  name: 'Chevron Corp.',         sector: 'Energy',               industry: 'Oil & Gas Integrated',   price: 162.40, chg: 0.94,   mcap: 295.6e9, vol: 7.1e6,   pe: 14.8, roe: 0.13, divy: 0.0425, beta: 1.05, rev_g: -0.011,w52l: 138.75, w52h: 167.11 },
  { ticker: 'COST', name: 'Costco Wholesale',      sector: 'Consumer Defensive',   industry: 'Discount Stores',        price: 894.18, chg: 1.74,   mcap: 396.4e9, vol: 1.8e6,   pe: 56.7, roe: 0.32, divy: 0.0050, beta: 0.78, rev_g: 0.063, w52l: 631.65, w52h: 920.20 },
  { ticker: 'PG',   name: 'Procter & Gamble',      sector: 'Consumer Defensive',   industry: 'Household Products',     price: 168.45, chg: 0.21,   mcap: 397.1e9, vol: 5.6e6,   pe: 27.6, roe: 0.31, divy: 0.0241, beta: 0.39, rev_g: 0.029, w52l: 142.50, w52h: 171.84 },
  { ticker: 'NFLX', name: 'Netflix, Inc.',         sector: 'Communication Svc.',   industry: 'Entertainment',          price: 712.30, chg: 2.18,   mcap: 304.8e9, vol: 4.3e6,   pe: 47.9, roe: 0.31, divy: 0,      beta: 1.27, rev_g: 0.146, w52l: 411.04, w52h: 736.86 },
  { ticker: 'DIS',  name: 'Walt Disney Co.',       sector: 'Communication Svc.',   industry: 'Entertainment',          price: 98.42,  chg: -1.84,  mcap: 178.5e9, vol: 11.2e6,  pe: 38.7, roe: 0.04, divy: 0.0091, beta: 1.22, rev_g: 0.030, w52l: 83.91,  w52h: 123.74 },
  { ticker: 'COIN', name: 'Coinbase Global',       sector: 'Financial Services',   industry: 'Capital Markets',        price: 238.74, chg: 6.94,   mcap: 60.4e9,  vol: 14.8e6,  pe: 53.2, roe: 0.27, divy: 0,      beta: 3.61, rev_g: 0.823, w52l: 65.65,  w52h: 283.48 },
  { ticker: 'PLTR', name: 'Palantir Technologies', sector: 'Technology',           industry: 'Software—Infrastructure',price: 36.84,  chg: 5.12,   mcap: 82.6e9,  vol: 68.4e6,  pe: 254.6,roe: 0.10, divy: 0,      beta: 2.84, rev_g: 0.272, w52l: 13.68,  w52h: 39.41 },
  { ticker: 'SHOP', name: 'Shopify Inc.',          sector: 'Technology',           industry: 'Software—Application',   price: 78.94,  chg: -2.62,  mcap: 101.4e9, vol: 8.4e6,   pe: 88.6, roe: 0.13, divy: 0,      beta: 2.18, rev_g: 0.252, w52l: 48.56,  w52h: 90.32 },
  { ticker: 'SNOW', name: 'Snowflake Inc.',        sector: 'Technology',           industry: 'Software—Application',   price: 138.21, chg: -4.12,  mcap: 46.8e9,  vol: 6.2e6,   pe: null, roe: -0.41,divy: 0,      beta: 0.98, rev_g: 0.295, w52l: 107.13, w52h: 237.72 },
  { ticker: 'CRWD', name: 'CrowdStrike Holdings',  sector: 'Technology',           industry: 'Software—Infrastructure',price: 332.86, chg: 3.42,   mcap: 81.7e9,  vol: 4.1e6,   pe: 392.4,roe: 0.10, divy: 0,      beta: 1.06, rev_g: 0.331, w52l: 192.50, w52h: 398.33 },
  { ticker: 'UBER', name: 'Uber Technologies',     sector: 'Technology',           industry: 'Software—Application',   price: 71.32,  chg: 1.84,   mcap: 148.7e9, vol: 16.3e6,  pe: 84.4, roe: 0.31, divy: 0,      beta: 1.39, rev_g: 0.142, w52l: 41.10,  w52h: 87.00 },
  { ticker: 'BA',   name: 'Boeing Company',        sector: 'Industrials',          industry: 'Aerospace & Defense',    price: 144.86, chg: -2.48,  mcap: 109.4e9, vol: 8.7e6,   pe: null, roe: -1.20,divy: 0,      beta: 1.49, rev_g: -0.077,w52l: 137.03, w52h: 267.54 },
  { ticker: 'CAT',  name: 'Caterpillar Inc.',      sector: 'Industrials',          industry: 'Farm & Heavy Construction', price: 412.31, chg: 0.74, mcap: 198.4e9, vol: 2.4e6, pe: 18.4, roe: 0.61, divy: 0.0146, beta: 1.07, rev_g: -0.039,w52l: 245.60, w52h: 422.37 },
  { ticker: 'BRK.B',name: 'Berkshire Hathaway B',  sector: 'Financial Services',   industry: 'Insurance—Diversified',  price: 478.20, chg: 0.18,   mcap: 1.03e12, vol: 3.2e6,   pe: 18.7, roe: 0.13, divy: 0,      beta: 0.86, rev_g: 0.105, w52l: 360.55, w52h: 491.67 },
  { ticker: 'HD',   name: 'Home Depot Inc.',       sector: 'Consumer Cyclical',    industry: 'Home Improvement Retail',price: 412.74, chg: 0.42,   mcap: 410.6e9, vol: 2.8e6,   pe: 27.4, roe: 11.4, divy: 0.0237, beta: 1.03, rev_g: -0.022,w52l: 323.77, w52h: 423.42 },
];

// build deterministic-ish but pretty sparkline data for each ticker
function sparkFor(ticker, chg, n=24) {
  const seed = ticker.split('').reduce((s,c)=>s+c.charCodeAt(0),0);
  const out = [];
  let v = 100;
  const trend = chg / 100;
  for (let i = 0; i < n; i++) {
    const noise = (Math.sin(seed * 1.3 + i * 0.7) + Math.cos(seed * 0.4 + i * 1.1)) * 0.012;
    v *= 1 + noise + trend / n;
    out.push(v);
  }
  return out;
}

STOCKS.forEach(s => { s.spark = sparkFor(s.ticker, s.chg, 24); s.spark90 = sparkFor(s.ticker, s.chg * 4, 90); });

const SECTORS = [...new Set(STOCKS.map(s => s.sector))].sort();

const STOCKS_BY_TICKER = Object.fromEntries(STOCKS.map(s => [s.ticker, s]));

// ====== news + AI report mock content ======
const NEWS = {
  NVDA: [
    { time: '2h',  source: 'Reuters',         title: 'NVIDIA hits intraday record as hyperscaler orders accelerate into Q3' },
    { time: '5h',  source: 'Bloomberg',       title: 'Analyst: Datacenter ramp shows no sign of plateauing, raises PT to $1,400' },
    { time: '1d',  source: 'WSJ',             title: 'Blackwell platform shipments outpace internal forecasts by 18%' },
    { time: '2d',  source: 'Financial Times', title: 'Sovereign AI deals expand pipeline by $11B in trailing quarter' },
  ],
  AAPL: [
    { time: '3h',  source: 'Reuters',   title: 'Apple Intelligence rollout enters next phase in EU markets' },
    { time: '1d',  source: 'Bloomberg', title: 'Services revenue trajectory points to $100B run-rate' },
    { time: '3d',  source: 'WSJ',       title: 'Vision Pro 2 prototypes shown to select developers' },
  ],
  TSLA: [
    { time: '1h',  source: 'Reuters',         title: 'Tesla cuts Model Y pricing 4% across US lineup' },
    { time: '6h',  source: 'Bloomberg',       title: 'FSD v13 wide-release pushed to following quarter' },
    { time: '1d',  source: 'Financial Times', title: 'Energy storage deployments hit new quarterly high' },
  ],
};

const AI_REPORT = {
  score: 78,
  recommendation: 'Strong Buy',
  recDelta: 'Upgraded from Buy 2 weeks ago',
  thesis: {
    bull: [
      'Datacenter revenue growing 154% YoY with no near-term substitute platform',
      'Sovereign AI commitments add a third durable demand pillar beyond cloud + enterprise',
      'Gross margins expanding past 75% on Blackwell mix shift',
    ],
    bear: [
      'Concentration risk: top 4 customers represent 41% of bookings',
      'Multiple is rich at 76× — leaves no room for execution misses',
      'Geopolitical export-control overhang on China revenue stream',
    ],
  },
  catalysts: [
    { date: 'NOV 19', label: 'Q3 FY26 Earnings', weight: 'HIGH' },
    { date: 'NOV 30', label: 'GTC Tokyo Keynote', weight: 'MED' },
    { date: 'DEC 12', label: 'Investor Day', weight: 'HIGH' },
  ],
  factors: [
    { label: 'Growth',     score: 96 },
    { label: 'Profitability', score: 92 },
    { label: 'Quality',    score: 88 },
    { label: 'Momentum',   score: 71 },
    { label: 'Value',      score: 24 },
    { label: 'Low Risk',   score: 38 },
  ],
};

// expose globally
Object.assign(window, { STOCKS, STOCKS_BY_TICKER, SECTORS, NEWS, AI_REPORT });

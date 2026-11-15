import type { CommodityDef } from './types';

export const TOP_10_CRYPTO = [
  'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'DOGEUSD',
  'BNBUSD', 'AVAXUSD', 'NEARUSD', 'SUIUSD', 'LINKUSD',
];

export const MOMENTUM_CRYPTO = [
  'RLCUSD', 'STRKUSD', 'XAUTUSD', 'PAXGUSD', 'TAOUSD',
  'ONDOUSD', 'SAGAUSD', 'APTUSD', 'AAVEUSD', 'FILUSD',
];

export const POPULAR_INDIAN_STOCKS = [
  // Nifty 50 & Heavyweights
  'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'SBIN',
  'ICICIBANK', 'TATAMOTORS', 'BHARTIARTL', 'ITC', 'LT',
  'AXISBANK', 'WIPRO', 'HCLTECH', 'KOTAKBANK', 'ADANIENT',
  'ADANIPORTS', 'BAJFINANCE', 'BAJAJFINSV', 'MARUTI', 'SUNPHARMA',
  'NTPC', 'POWERGRID', 'ONGC', 'COALINDIA', 'JSWSTEEL',
  'TATASTEEL', 'TITAN', 'ULTRACEMCO', 'M&M', 'HEROMOTOCO',
  'TECHM', 'INDUSINDBK', 'NESTLEIND', 'ASIANPAINT', 'GRASIM',
  'BPCL', 'CIPLA', 'DIVISLAB', 'EICHERMOT', 'DRREDDY',
  'BRITANNIA', 'APOLLOHOSP', 'TATACONSUM', 'SBILIFE', 'HDFCLIFE',
  'SHRIRAMFIN',
  // High-Volume Midcaps & Trending Stocks
  'CUPID', 'SUZLON', 'ZOMATO', 'PAYTM', 'JIOFIN',
  'TATACHEM', 'IRFC', 'RVNL', 'BSE', 'CDSL',
  'HAL', 'BEL', 'MAZDOCK', 'BHEL', 'NHPC',
  'IDEA', 'YESBANK', 'IDFCFIRSTB', 'VEDL', 'DLF',
  'GODREJPROP', 'POLYCAB', 'TRENT', 'CHOLAFIN', 'PIDILITIND',
  'SIEMENS', 'ABB', 'HAVELLS', 'VBL', 'PERSISTENT',
  'COFORGE', 'MPHASIS', 'KPITTECH', 'LTIM', 'DIXON',
];

export const NFO_UNDERLYINGS = [
  'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTYNXT50',
  'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'SBIN',
  'ICICIBANK', 'AXISBANK', 'WIPRO', 'HCLTECH', 'KOTAKBANK',
];

export const MCX_COMMODITIES_LIST: CommodityDef[] = [
  // Energy
  { symbol: 'CRUDEOIL', name: 'Crude Oil', desc: '100 BBL • Standard Contract', category: 'energy' },
  { symbol: 'CRUDEOILM', name: 'Crude Oil Mini', desc: '10 BBL • Retail Mini', category: 'energy', isMini: true },
  { symbol: 'NATURALGAS', name: 'Natural Gas', desc: '1250 mmBtu • Standard', category: 'energy' },
  { symbol: 'NATURALGASM', name: 'Natural Gas Mini', desc: '250 mmBtu • Mini', category: 'energy', isMini: true },

  // Precious Metals
  { symbol: 'GOLD', name: 'Gold', desc: '1 KG • High Liquidity', category: 'precious' },
  { symbol: 'GOLDM', name: 'Gold Mini', desc: '100 Grams • Retail Mini', category: 'precious', isMini: true },
  { symbol: 'SILVER', name: 'Silver', desc: '30 KG • Standard', category: 'precious' },
  { symbol: 'SILVERM', name: 'Silver Mini', desc: '5 KG • Retail Mini', category: 'precious', isMini: true },
  { symbol: 'SILVERMIC', name: 'Silver Micro', desc: '1 KG • Micro Lot', category: 'precious', isMini: true },

  // Base Metals
  { symbol: 'COPPER', name: 'Copper', desc: '2500 KG • Base Metal', category: 'metals' },
  { symbol: 'ALUMINIUM', name: 'Aluminium', desc: '5 MT • Industrial', category: 'metals' },
  { symbol: 'ZINC', name: 'Zinc', desc: '5 MT • Industrial', category: 'metals' },
  { symbol: 'LEAD', name: 'Lead', desc: '5 MT • Industrial', category: 'metals' },
];

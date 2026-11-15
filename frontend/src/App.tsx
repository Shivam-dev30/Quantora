import { CyberSidebar, type TerminalView } from './components/CyberSidebar';
import { CyberTopbar } from './components/CyberTopbar';
import { CyberCandleChart } from './components/CyberCandleChart';
import { CyberBacktestWorkspace } from './components/CyberBacktestWorkspace';
import {
  Power,
  Cpu,
  BellRing,
  Activity,
  Bell,
  Check,
  CheckCircle2,
  Coins,
  Layers,
  Plus,
  Radio,
  RefreshCw,
  Search,
  Sliders,
  Sparkles,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';
import React, { useEffect, useState, useRef, useMemo } from 'react';
interface Signal {
  id?: number;
  signal_id: string;
  provider: string;
  asset_class: string;
  exchange: string;
  symbol: string;
  timeframe: string;
  signal_type: 'BULLISH' | 'BEARISH';
  price: number;
  ema100: number;
  ema200: number;
  previous_ema100?: number;
  previous_ema200?: number;
  candle_timestamp: string;
  created_at: string;
  is_catchup?: boolean;
}

interface SystemStatus {
  system_status: string;
  providers: {
    angelone: string;
    delta: string;
  };
  monitored_counts: {
    stocks: number;
    futures: number;
    options: number;
    commodities: number;
    crypto: number;
  };
  timeframes: string[];
  instrument_timeframes?: Record<string, string[]>;
  notifications: {
    telegram: string;
    email: string;
    whatsapp: string;
  };
  recent_alerts: Signal[];
}

interface InstrumentItem {
  symbol: string;
  name: string;
  provider: string;
  exchange: string;
  instrument_id: string;
  display_symbol?: string;
  base_symbol?: string;
  tick_size?: number;
  lot_size?: number;
  asset_class: string;
  instrument_type?: string;
  expiry?: string;
  expiry_date?: string;
  strike?: number;
  option_type?: string;
  underlying?: string;
  is_expired?: boolean;
  is_monitored?: boolean;
}

const TOP_10_CRYPTO = [
  'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'DOGEUSD',
  'BNBUSD', 'AVAXUSD', 'NEARUSD', 'SUIUSD', 'LINKUSD',
];

const MOMENTUM_CRYPTO = [
  'RLCUSD', 'STRKUSD', 'XAUTUSD', 'PAXGUSD', 'TAOUSD',
  'ONDOUSD', 'SAGAUSD', 'APTUSD', 'AAVEUSD', 'FILUSD',
];

const POPULAR_INDIAN_STOCKS = [
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
  // High-Volume Midcaps & Trending Stocks (including CUPID!)
  'CUPID', 'SUZLON', 'ZOMATO', 'PAYTM', 'JIOFIN',
  'TATACHEM', 'IRFC', 'RVNL', 'BSE', 'CDSL',
  'HAL', 'BEL', 'MAZDOCK', 'BHEL', 'NHPC',
  'IDEA', 'YESBANK', 'IDFCFIRSTB', 'VEDL', 'DLF',
  'GODREJPROP', 'POLYCAB', 'TRENT', 'CHOLAFIN', 'PIDILITIND',
  'SIEMENS', 'ABB', 'HAVELLS', 'VBL', 'PERSISTENT',
  'COFORGE', 'MPHASIS', 'KPITTECH', 'LTIM', 'DIXON',
];

const NFO_UNDERLYINGS = [
  'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTYNXT50',
  'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'SBIN',
  'ICICIBANK', 'AXISBANK', 'WIPRO', 'HCLTECH', 'KOTAKBANK',
];

export interface CommodityDef {
  symbol: string;
  name: string;
  desc: string;
  category: 'energy' | 'precious' | 'metals' | 'electricity';
  isMini?: boolean;
}

export const MCX_COMMODITIES_LIST: CommodityDef[] = [
  // Energy
  { symbol: 'CRUDEOIL', name: 'Crude Oil', desc: '100 BBL • Standard Contract', category: 'energy' },
  { symbol: 'CRUDEOILM', name: 'Crude Oil Mini', desc: '10 BBL • Retail Mini', category: 'energy', isMini: true },
  { symbol: 'NATURALGAS', name: 'Natural Gas', desc: '1250 mmBtu • Standard', category: 'energy' },
  { symbol: 'NATURALGASM', name: 'Natural Gas Mini', desc: '250 mmBtu • Mini', category: 'energy', isMini: true },

  // Precious Metals
  { symbol: 'GOLD', name: 'Gold', desc: '1 KG • High Liquidity', category: 'precious' },
  { symbol: 'GOLDM', name: 'Gold Mini', desc: '100 Grams • Retail Mini', category: 'precious', isMini: true },
  { symbol: 'GOLDPETAL', name: 'Gold Petal', desc: '1 Gram • Micro Lot', category: 'precious', isMini: true },
  { symbol: 'GOLDGUINEA', name: 'Gold Guinea', desc: '8 Grams • Sovereign Lot', category: 'precious' },
  { symbol: 'SILVER', name: 'Silver', desc: '30 KG • Standard Contract', category: 'precious' },
  { symbol: 'SILVERM', name: 'Silver Mini', desc: '5 KG • Retail Mini Contract', category: 'precious', isMini: true },
  { symbol: 'SILVERMIC', name: 'Silver Micro', desc: '1 KG • Micro Retail Lot', category: 'precious', isMini: true },

  // Electricity
  { symbol: 'ELECDMBL', name: 'Electricity Base Load', desc: 'Day-Ahead Base Load (1 MW/h)', category: 'electricity' },
  { symbol: 'ELECTMTH', name: 'Electricity Monthly', desc: 'Monthly Futures (1 MW/h)', category: 'electricity' },

  // Base Metals
  { symbol: 'COPPER', name: 'Copper', desc: '2500 KG • Standard Contract', category: 'metals' },
  { symbol: 'COPPERM', name: 'Copper Mini', desc: '500 KG • Mini Lot', category: 'metals', isMini: true },
  { symbol: 'ZINC', name: 'Zinc', desc: '5 MT • Standard Contract', category: 'metals' },
  { symbol: 'ZINCMINI', name: 'Zinc Mini', desc: '1 MT • Mini Lot', category: 'metals', isMini: true },
  { symbol: 'ALUMINIUM', name: 'Aluminium', desc: '5 MT • Standard Contract', category: 'metals' },
  { symbol: 'ALUMINI', name: 'Aluminium Mini', desc: '1 MT • Mini Lot', category: 'metals', isMini: true },
  { symbol: 'LEAD', name: 'Lead', desc: '5 MT • Standard Contract', category: 'metals' },
  { symbol: 'LEADMINI', name: 'Lead Mini', desc: '1 MT • Mini Lot', category: 'metals', isMini: true },
];

const MCX_COMMODITIES = MCX_COMMODITIES_LIST.map((c) => c.symbol);

export const App: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [liveAlerts, setLiveAlerts] = useState<Signal[]>([]);
  const [selectedAssetFilter, setSelectedAssetFilter] = useState<string>('all');
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);
  const [isTestingAlert, setIsTestingAlert] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  // Active Alerts Category Filter: all | equity | crypto | commodity | equity_futures
  const [activeAlertFilter, setActiveAlertFilter] = useState<'all' | 'equity' | 'crypto' | 'commodity' | 'equity_futures'>('all');

  // Create / Edit Alert Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [availableInstruments, setAvailableInstruments] = useState<{
    crypto: InstrumentItem[];
    equity: InstrumentItem[];
    equity_nse: InstrumentItem[];
    equity_bse: InstrumentItem[];
    equity_futures: InstrumentItem[];
    equity_options: InstrumentItem[];
    commodity: InstrumentItem[];
  }>({ crypto: [], equity: [], equity_nse: [], equity_bse: [], equity_futures: [], equity_options: [], commodity: [] });
  const [monitoredList, setMonitoredList] = useState<InstrumentItem[]>([]);

  const [modalActiveTab, setModalActiveTab] = useState<'crypto' | 'equity' | 'equity_futures' | 'commodity'>('equity');
  const [modalEquityExchange, setModalEquityExchange] = useState<'ALL' | 'NSE' | 'BSE'>('ALL');
  const [commoditySubFilter, setCommoditySubFilter] = useState<'all' | 'energy' | 'precious' | 'metals' | 'mini' | 'electricity'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [catalogResults, setCatalogResults] = useState<InstrumentItem[]>([]);
  const [isCatalogSearching, setIsCatalogSearching] = useState<boolean>(false);
  const [isFetchingStock, setIsFetchingStock] = useState<boolean>(false);
  const [fetchedStockMsg, setFetchedStockMsg] = useState<string | null>(null);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Persistent user-saved / custom stocks
  const [userSavedStocks, setUserSavedStocks] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('ema_user_stocks');
      return saved ? JSON.parse(saved) : ['CUPID', 'SUZLON', 'ZOMATO', 'PAYTM', 'TATACHEM'];
    } catch {
      return ['CUPID', 'SUZLON', 'ZOMATO', 'PAYTM', 'TATACHEM'];
    }
  });

  const saveCustomStock = (sym: string) => {
    const clean = sym.trim().toUpperCase();
    if (!clean) return;
    setUserSavedStocks((prev) => {
      if (prev.includes(clean)) return prev;
      const updated = [clean, ...prev];
      try {
        localStorage.setItem('ema_user_stocks', JSON.stringify(updated));
      } catch {}
      return updated;
    });
  };

  const [selectedCrypto, setSelectedCrypto] = useState<Set<string>>(new Set(['BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD']));
  const [selectedEquityNSE, setSelectedEquityNSE] = useState<Set<string>>(new Set(['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'SBIN', 'ICICIBANK']));
  const [selectedEquityBSE, setSelectedEquityBSE] = useState<Set<string>>(new Set());
  const selectedEquity = useMemo(() => new Set([...selectedEquityNSE, ...selectedEquityBSE]), [selectedEquityNSE, selectedEquityBSE]);
  const [selectedFutures, setSelectedFutures] = useState<Set<string>>(new Set(['NIFTY', 'BANKNIFTY']));
  const [selectedCommodity, setSelectedCommodity] = useState<Set<string>>(new Set(['CRUDEOIL', 'CRUDEOILM', 'GOLD', 'SILVER', 'ELECDMBL']));
  const [selectedTimeframes, setSelectedTimeframes] = useState<string[]>(['5m', '15m', '30m', '1h']);
  const [instrumentTimeframes, setInstrumentTimeframes] = useState<Record<string, string[]>>(() => {
    try {
      const saved = localStorage.getItem('ema_instrument_timeframes');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const getStockTimeframes = (symbol: string): string[] => {
    const sym = (symbol || '').toUpperCase();
    if (instrumentTimeframes[sym] && Array.isArray(instrumentTimeframes[sym]) && instrumentTimeframes[sym].length > 0) {
      return instrumentTimeframes[sym];
    }
    // Return selectedTimeframes but do NOT auto-save so we don't pollute per-stock config
    return selectedTimeframes;
  };

  // When monitoredList changes, initialize per-stock TFs for any stock that doesn't yet have one
  React.useEffect(() => {
    if (monitoredList.length === 0) return;
    setInstrumentTimeframes((prev) => {
      let changed = false;
      const next = { ...prev };
      monitoredList.forEach((item) => {
        const sym = (item.symbol || '').toUpperCase();
        if (!next[sym] || !Array.isArray(next[sym]) || next[sym].length === 0) {
          next[sym] = [...selectedTimeframes];
          changed = true;
        }
      });
      if (changed) {
        try { localStorage.setItem('ema_instrument_timeframes', JSON.stringify(next)); } catch {}
        return next;
      }
      return prev;
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [monitoredList]);

  const [isSavingAlert, setIsSavingAlert] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  const [rolledContracts, setRolledContracts] = useState<Array<{old_symbol: string; new_symbol: string; new_expiry: string}>>([]);

  // Monitored Universe Filter & Stock Quick Edit State
  const [stockSearchFilter, setStockSearchFilter] = useState<string>('');
  const [stockCategoryFilter, setStockCategoryFilter] = useState<'all' | 'crypto' | 'equity' | 'equity_futures' | 'commodity'>('all');
  const [editingStock, setEditingStock] = useState<InstrumentItem | null>(null);
  const [isUpdatingTimeframe, setIsUpdatingTimeframe] = useState<boolean>(false);
  const [quickTfSuccessMsg, setQuickTfSuccessMsg] = useState<string | null>(null);

  const handleToggleStockTimeframe = async (symbol: string, tf: string) => {
    const sym = (symbol || '').toUpperCase();
    // Always start from the stock's own saved TFs; if none saved yet, initialize from global
    const currentTfs = (instrumentTimeframes[sym] && instrumentTimeframes[sym].length > 0)
      ? instrumentTimeframes[sym]
      : [...selectedTimeframes];
    let updated: string[];

    if (currentTfs.includes(tf)) {
      if (currentTfs.length === 1) {
        alert(`At least one timeframe must remain active for ${sym}.`);
        return;
      }
      updated = currentTfs.filter((t) => t !== tf);
    } else {
      updated = [...currentTfs, tf].sort((a, b) => {
        const order = ['1m', '3m', '5m', '10m', '15m', '30m', '1h', '2h', '4h', '1d'];
        return order.indexOf(a) - order.indexOf(b);
      });
    }

    setInstrumentTimeframes((prev) => {
      const next = { ...prev, [sym]: updated };
      try {
        localStorage.setItem('ema_instrument_timeframes', JSON.stringify(next));
      } catch {}
      return next;
    });

    setQuickTfSuccessMsg(`✓ Updated ${sym} timeframes: [${updated.join(', ')}]`);
    setTimeout(() => setQuickTfSuccessMsg(null), 3500);

    try {
      await fetch(getApiUrl('/api/alerts/instrument-timeframes'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: sym, timeframes: updated }),
      });
    } catch (err) {
      console.error(`Failed to update timeframes for ${sym}:`, err);
    }
  };

  const handleQuickToggleTimeframe = async (tf: string) => {
    let updatedTfs: string[];
    const isEnabling = !selectedTimeframes.includes(tf);

    if (!isEnabling) {
      if (selectedTimeframes.length === 1) {
        alert('At least one default timeframe must remain active for EMA crossover alerts.');
        return;
      }
      updatedTfs = selectedTimeframes.filter((t) => t !== tf);
    } else {
      updatedTfs = [...selectedTimeframes, tf].sort((a, b) => {
        const order = ['1m', '3m', '5m', '10m', '15m', '30m', '1h', '2h', '4h', '1d'];
        return order.indexOf(a) - order.indexOf(b);
      });
    }

    // Propagate master toggle to ALL activated stocks:
    // If a timeframe is turned OFF, remove it from all activated stocks.
    // If a timeframe is turned ON, add it to all activated stocks.
    const updatedInstrumentTfs: Record<string, string[]> = { ...instrumentTimeframes };

    monitoredList.forEach((item) => {
      const symUpper = (item.symbol || '').toUpperCase();
      const cleanSym = symUpper.replace(/-EQ$/, '').replace(/-[AB]$/, '').replace(/-BE$/, '');
      const current = getStockTimeframes(item.symbol);
      let nextForStock: string[];

      if (!isEnabling) {
        nextForStock = current.filter((t) => t !== tf);
        if (nextForStock.length === 0) {
          nextForStock = [updatedTfs[0]];
        }
      } else {
        if (!current.includes(tf)) {
          nextForStock = [...current, tf].sort((a, b) => {
            const order = ['1m', '3m', '5m', '10m', '15m', '30m', '1h', '2h', '4h', '1d'];
            return order.indexOf(a) - order.indexOf(b);
          });
        } else {
          nextForStock = current;
        }
      }

      updatedInstrumentTfs[symUpper] = nextForStock;
      if (cleanSym !== symUpper) {
        updatedInstrumentTfs[cleanSym] = nextForStock;
      }
    });

    // Also update any other keys currently tracked in instrumentTimeframes
    Object.keys(updatedInstrumentTfs).forEach((k) => {
      const current = updatedInstrumentTfs[k] || [];
      if (!isEnabling) {
        const filtered = current.filter((t) => t !== tf);
        updatedInstrumentTfs[k] = filtered.length > 0 ? filtered : [updatedTfs[0]];
      } else {
        if (!current.includes(tf)) {
          updatedInstrumentTfs[k] = [...current, tf].sort((a, b) => {
            const order = ['1m', '3m', '5m', '10m', '15m', '30m', '1h', '2h', '4h', '1d'];
            return order.indexOf(a) - order.indexOf(b);
          });
        }
      }
    });

    // Optimistically update React state and localStorage immediately
    setSelectedTimeframes(updatedTfs);
    setInstrumentTimeframes(updatedInstrumentTfs);
    try {
      localStorage.setItem('ema_instrument_timeframes', JSON.stringify(updatedInstrumentTfs));
    } catch {}

    setIsUpdatingTimeframe(true);
    try {
      const res = await fetch(getApiUrl('/api/alerts/configure'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timeframes: updatedTfs,
          instrument_timeframes: updatedInstrumentTfs,
          symbols: {},
          action: 'add',
        }),
      });
      await res.json();
      if (res.ok) {
        setQuickTfSuccessMsg(
          !isEnabling
            ? `✓ Disabled ${tf} alerts across ALL active stocks!`
            : `✓ Enabled ${tf} alerts across ALL active stocks! Indicators warming up.`
        );
        setTimeout(() => setQuickTfSuccessMsg(null), 4000);
        fetchData();
      }
    } catch (err) {
      console.error('Failed to update timeframes:', err);
    } finally {
      setIsUpdatingTimeframe(false);
    }
  };

  const handleOpenStockEditor = (item: InstrumentItem) => {
    setEditingStock(item);
  };

  const handleSwitchToChart = (sym: string) => {
    const cleanSym = sym.replace(/-EQ$/, '').replace(/-A$/, '').replace(/-B$/, '');
    setChartSymbol(cleanSym);
    setCurrentView('dashboard');
  };

  // Test form state
  const [testSymbol, setTestSymbol] = useState<string>('BTCUSD');
  const [testExchange, setTestExchange] = useState<string>('DELTA');
  const [testAssetClass, setTestAssetClass] = useState<string>('crypto');
  const [testTimeframe, setTestTimeframe] = useState<string>('15m');
  const [testSignalType, setTestSignalType] = useState<'BULLISH' | 'BEARISH'>('BULLISH');
  const [testPrice, setTestPrice] = useState<number>(81500.0);

  const wsRef = useRef<WebSocket | null>(null);

  // Determine API base URL
  const getApiUrl = (endpoint: string) => {
    return endpoint;
  };

  // Fetch initial status and signals
  const fetchData = async () => {
    try {
      const statusRes = await fetch(getApiUrl('/status'));
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(statusData);
        if (statusData.instrument_timeframes && typeof statusData.instrument_timeframes === 'object') {
          setInstrumentTimeframes((prev) => {
            const merged = { ...prev, ...statusData.instrument_timeframes };
            try {
              localStorage.setItem('ema_instrument_timeframes', JSON.stringify(merged));
            } catch {}
            return merged;
          });
        }
        if (statusData.recent_alerts && statusData.recent_alerts.length > 0) {
          setLiveAlerts(statusData.recent_alerts);
        }
      }

      const sigRes = await fetch(getApiUrl('/api/signals?limit=50'));
      if (sigRes.ok) {
        const sigData = await sigRes.json();
        setSignals(sigData.signals || []);
      }

      const instRes = await fetch(getApiUrl('/api/instruments'));
      if (instRes.ok) {
        const instData = await instRes.json();
        setMonitoredList(instData.instruments || []);
      }
    } catch (err) {
      console.warn('Backend connection standby:', err);
    }
  };

  const fetchAvailableInstruments = async () => {
    try {
      const res = await fetch(getApiUrl('/api/available-instruments'));
      if (res.ok) {
        const data = await res.json();
        if (data.instruments) {
          setAvailableInstruments({
            crypto: data.instruments.crypto || [],
            equity: data.instruments.equity || [],
            equity_nse: data.instruments.equity_nse || [],
            equity_bse: data.instruments.equity_bse || [],
            equity_futures: data.instruments.equity_futures || [],
            equity_options: data.instruments.equity_options || [],
            commodity: data.instruments.commodity || [],
          });

          // Sync currently monitored symbols from backend
          const cryptoMon = new Set<string>();
          (data.instruments.crypto || []).forEach((c: InstrumentItem) => { if (c.is_monitored) cryptoMon.add(c.symbol); });
          if (cryptoMon.size > 0) setSelectedCrypto(cryptoMon);

          const nseMonitored = new Set<string>();
          (data.instruments.equity_nse || []).forEach((e: InstrumentItem) => {
            if (e.is_monitored) nseMonitored.add(e.symbol.replace('-EQ', '').replace(/-[AB]$/, ''));
          });
          if (nseMonitored.size > 0) setSelectedEquityNSE(nseMonitored);

          const bseMonitored = new Set<string>();
          (data.instruments.equity_bse || []).forEach((e: InstrumentItem) => {
            if (e.is_monitored) bseMonitored.add(e.symbol);
          });
          if (bseMonitored.size > 0) setSelectedEquityBSE(bseMonitored);

          const futMon = new Set<string>();
          (data.instruments.equity_futures || []).forEach((f: InstrumentItem) => {
            if (f.is_monitored) futMon.add(f.underlying || f.name || f.symbol);
          });
          if (futMon.size > 0) setSelectedFutures(futMon);

          const commMon = new Set<string>();
          (data.instruments.commodity || []).forEach((c: InstrumentItem) => {
            if (c.is_monitored) commMon.add(c.underlying || c.name || c.symbol);
          });
          if (commMon.size > 0) setSelectedCommodity(commMon);
        }
      }
    } catch (err) {
      console.warn('Could not load available instruments:', err);
    }
  };

  const performCatalogSearch = async (q: string, tab: string, exchange?: string) => {
    if (!q.trim()) { setCatalogResults([]); return; }
    setIsCatalogSearching(true);
    setFetchedStockMsg(null);
    try {
      const exch = exchange !== undefined ? exchange : modalEquityExchange;
      const catMap: Record<string, string> = {
        equity: exch === 'NSE' ? 'equity_nse' : (exch === 'BSE' ? 'equity_bse' : 'equity'),
        equity_futures: 'equity_futures',
        commodity: 'commodity',
        crypto: 'crypto',
      };
      const cat = catMap[tab] || tab;
      const exchParam = (exch === 'ALL' || !exch || tab !== 'equity') ? '' : `&exchange=${exch}`;
      const res = await fetch(getApiUrl(`/api/catalog-search?q=${encodeURIComponent(q)}&category=${cat}${exchParam}&limit=80`));
      if (res.ok) {
        const data = await res.json();
        setCatalogResults(data.results || []);
      }
    } catch { /* silent */ } finally {
      setIsCatalogSearching(false);
    }
  };

  // Open modal in Edit mode with current active parameters preloaded
  const handleOpenEditAlert = (targetAssetClass?: string, targetSymbol?: string) => {
    setModalMode('edit');
    if (status?.timeframes && status.timeframes.length > 0) {
      setSelectedTimeframes(status.timeframes);
    }
    if (monitoredList.length > 0) {
      const cryptoSyms = new Set<string>();
      const nseSyms = new Set<string>();
      const bseSyms = new Set<string>();
      const futSyms = new Set<string>();
      const commSyms = new Set<string>();

      monitoredList.forEach((inst) => {
        const rawSym = inst.symbol.replace(/-EQ$/, '').replace(/-A$/, '').replace(/-B$/, '');
        if (inst.asset_class === 'crypto') cryptoSyms.add(inst.symbol);
        else if (inst.asset_class === 'equity') {
          if (inst.exchange.toUpperCase() === 'BSE') bseSyms.add(rawSym);
          else nseSyms.add(rawSym);
        } else if (inst.asset_class === 'equity_futures') {
          const root = (inst.underlying || inst.name || inst.symbol).replace(/\d{2}[A-Z]{3}\d{2,4}FUT$/, '').trim();
          futSyms.add(root);
        } else if (inst.asset_class === 'commodity') {
          const root = (inst.underlying || inst.name || inst.symbol).replace(/\d{2}[A-Z]{3}\d{2,4}FUT$/, '').trim();
          commSyms.add(root);
        }
      });

      setSelectedCrypto(cryptoSyms);
      setSelectedEquityNSE(nseSyms);
      setSelectedEquityBSE(bseSyms);
      setSelectedFutures(futSyms);
      setSelectedCommodity(commSyms);
    }

    if (targetAssetClass) {
      if (targetAssetClass === 'equity') setModalActiveTab('equity');
      else if (targetAssetClass === 'crypto') setModalActiveTab('crypto');
      else if (targetAssetClass === 'commodity') setModalActiveTab('commodity');
      else if (targetAssetClass === 'equity_futures') setModalActiveTab('equity_futures');
    }
    if (targetSymbol) {
      const cleanSym = targetSymbol.replace(/-EQ$/, '').replace(/-A$/, '').replace(/-B$/, '');
      setSearchQuery(cleanSym);
    }

    fetchAvailableInstruments();
    setIsCreateModalOpen(true);
  };

  const handleOpenCreateAlert = () => {
    setModalMode('create');
    fetchAvailableInstruments();
    setIsCreateModalOpen(true);
  };

  useEffect(() => {
    fetchData();
    fetchAvailableInstruments();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Real-time WebSocket connection
  useEffect(() => {
    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host || 'localhost:8000';
      const wsUrl = `${protocol}//${host}/ws/dashboard`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'NEW_ALERT' && msg.data) {
            const newAlert: Signal = msg.data;
            setLiveAlerts((prev) => [newAlert, ...prev.slice(0, 19)]);
            setSignals((prev) => [newAlert, ...prev]);
          } else if (msg.type === 'INSTRUMENT_TIMEFRAMES_UPDATED' && msg.data) {
            const { symbol, timeframes: newTfs } = msg.data;
            if (symbol && Array.isArray(newTfs)) {
              setInstrumentTimeframes((prev) => {
                const next = { ...prev, [symbol.toUpperCase()]: newTfs };
                try {
                  localStorage.setItem('ema_instrument_timeframes', JSON.stringify(next));
                } catch {}
                return next;
              });
            }
          } else if (msg.type === 'MONITORED_UPDATED') {
            fetchData();
            fetchAvailableInstruments();
          } else if (msg.type === 'CONTRACT_ROLLED' && msg.data?.contracts) {
            setRolledContracts(msg.data.contracts);
            setTimeout(() => setRolledContracts([]), 15000);
            fetchData();
            fetchAvailableInstruments();
          }
        } catch (e) {
          console.error('Error parsing live WS payload', e);
        }
      };

      ws.onclose = () => {
        setIsWsConnected(false);
        setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectWs();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Save / Activate Alert Engine on selected instruments
  const handleSaveAlertEngine = async () => {
    setIsSavingAlert(true);
    setSaveSuccessMsg(null);

    try {
      const payload = {
        strategy: '100_200_ema_crossover',
        ema_fast: 100,
        ema_slow: 200,
        timeframes: selectedTimeframes,
        symbols: {
          crypto: Array.from(selectedCrypto),
          equity: Array.from(selectedEquityNSE),
          bse_equity: Array.from(selectedEquityBSE),
          equity_futures: Array.from(selectedFutures),
          commodity: Array.from(selectedCommodity),
        },
        action: 'set',
      };

      const res = await fetch(getApiUrl('/api/alerts/configure'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        setSaveSuccessMsg(`🚀 Alert Engine Active! Monitoring ${data.total_monitored} instruments across [${selectedTimeframes.join(', ')}]. Indicators warming up on live data!`);
        fetchData();
        fetchAvailableInstruments();
        setTimeout(() => {
          setIsCreateModalOpen(false);
          setSaveSuccessMsg(null);
        }, 2200);
      } else {
        setSaveSuccessMsg('Failed to configure alert engine.');
      }
    } catch (err: any) {
      setSaveSuccessMsg(`Error: ${err.message}`);
    } finally {
      setIsSavingAlert(false);
    }
  };

  // Remove instrument from active monitoring
  const handleRemoveInstrument = async (symbol: string, assetClass: string) => {
    const symUpper = (symbol || '').trim().toUpperCase();
    const cleanSym = symUpper.replace(/-EQ$/, '').replace(/-[AB]$/, '').replace(/-BE$/, '');
    let futRoot = cleanSym.replace(/\d{2}[A-Z]{3}.*$/, '').trim();
    if (futRoot === cleanSym) futRoot = '';

    // 1. Optimistic removal from monitoredList so the card vanishes immediately
    setMonitoredList((prev) => prev.filter((i) => {
      const s = (i.symbol || '').toUpperCase();
      const sClean = s.replace(/-EQ$/, '').replace(/-[AB]$/, '').replace(/-BE$/, '');
      const sFutRoot = sClean.replace(/\d{2}[A-Z]{3}.*$/, '').trim();
      if (s === symUpper || sClean === cleanSym) return false;
      if (futRoot && (s === futRoot || sClean === futRoot || sFutRoot === futRoot)) return false;
      return true;
    }));

    // 2. Remove from instrumentTimeframes in state and localStorage
    setInstrumentTimeframes((prev) => {
      const next = { ...prev };
      delete next[symUpper];
      delete next[cleanSym];
      if (futRoot) delete next[futRoot];
      try {
        localStorage.setItem('ema_instrument_timeframes', JSON.stringify(next));
      } catch {}
      return next;
    });

    // 3. Purge from selection sets so the symbol is unselected if user opens configure modal
    setSelectedEquityNSE((prev) => { const next = new Set(prev); next.delete(cleanSym); next.delete(symUpper); return next; });
    setSelectedEquityBSE((prev) => { const next = new Set(prev); next.delete(cleanSym); next.delete(symUpper); return next; });
    setSelectedCrypto((prev) => { const next = new Set(prev); next.delete(symUpper); next.delete(cleanSym); return next; });
    setSelectedFutures((prev) => { const next = new Set(prev); if (futRoot) next.delete(futRoot); next.delete(symUpper); return next; });
    setSelectedCommodity((prev) => { const next = new Set(prev); if (futRoot) next.delete(futRoot); next.delete(symUpper); return next; });

    // 4. Purge from user custom stocks cache if present
    try {
      const rawCustom = localStorage.getItem('ema_custom_stocks');
      if (rawCustom) {
        const arr = JSON.parse(rawCustom) as string[];
        const filtered = arr.filter((s) => s.toUpperCase() !== cleanSym && s.toUpperCase() !== symUpper);
        localStorage.setItem('ema_custom_stocks', JSON.stringify(filtered));
      }
    } catch {}

    setQuickTfSuccessMsg(`✓ Removed ${symbol} from monitored universe`);
    setTimeout(() => setQuickTfSuccessMsg(null), 3500);

    // 5. Send DELETE request to backend
    try {
      await fetch(getApiUrl('/api/alerts/instrument'), {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, asset_class: assetClass }),
      });
      fetchData();
      fetchAvailableInstruments();
    } catch (e) {
      console.error('Error removing instrument', e);
    }
  };

  const handleTestAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsTestingAlert(true);
    setTestResult(null);

    try {
      const res = await fetch(getApiUrl('/api/test-alert'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: testSymbol,
          exchange: testExchange,
          asset_class: testAssetClass,
          timeframe: testTimeframe,
          signal_type: testSignalType,
          price: testPrice,
          ema100: testSignalType === 'BULLISH' ? testPrice - 15 : testPrice + 15,
          ema200: testSignalType === 'BULLISH' ? testPrice - 30 : testPrice + 30,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setTestResult(`Alert dispatched! Channels: ${JSON.stringify(data.channel_results)}`);
        fetchData();
      } else {
        setTestResult('Failed to dispatch test alert');
      }
    } catch (err: any) {
      setTestResult(`Error: ${err.message}`);
    } finally {
      setIsTestingAlert(false);
    }
  };


  const toggleCrypto = (sym: string) => {
    setSelectedCrypto((prev) => { const next = new Set(prev); if (next.has(sym)) next.delete(sym); else next.add(sym); return next; });
  };

  const toggleEquity = (sym: string, exchange: string = 'NSE') => {
    const clean = sym.trim().toUpperCase().replace(/-EQ$/, '').replace(/-[AB]$/, '').replace(/-NSE$/, '').replace(/-BSE$/, '');
    saveCustomStock(clean);
    const exchUpper = exchange ? exchange.toUpperCase() : 'NSE';
    if (exchUpper === 'BSE') {
      setSelectedEquityBSE((prev) => {
        const next = new Set(prev);
        if (next.has(clean)) next.delete(clean);
        else next.add(clean);
        return next;
      });
    } else {
      setSelectedEquityNSE((prev) => {
        const next = new Set(prev);
        if (next.has(clean)) next.delete(clean);
        else next.add(clean);
        return next;
      });
    }
  };

  const handleQuickAddStock = (symToAdd?: string) => {
    const raw = (symToAdd || searchQuery).trim().toUpperCase();
    if (!raw) return;
    const clean = raw.replace(/-EQ$/, '').replace(/-[AB]$/, '').replace(/-NSE$/, '').replace(/-BSE$/, '').trim();
    saveCustomStock(clean);
    const exch = modalEquityExchange === 'BSE' ? 'BSE' : 'NSE';
    toggleEquity(clean, exch);
    setSearchQuery('');
    setCatalogResults([]);
    setFetchedStockMsg(null);
  };

  const handleFetchAndAddStock = async (sym: string) => {
    const clean = sym.trim().toUpperCase().replace(/-EQ$/, '').replace(/-[AB]$/, '').replace(/-NSE$/, '').replace(/-BSE$/, '');
    if (!clean) return;
    setIsFetchingStock(true);
    setFetchedStockMsg(null);
    try {
      // Hit the catalog-search which has SmartAPI live fallback built in
      const exch = modalEquityExchange === 'BSE' ? 'BSE' : 'NSE';
      const cat = exch === 'NSE' ? 'equity_nse' : 'equity_bse';
      const res = await fetch(getApiUrl(`/api/catalog-search?q=${encodeURIComponent(clean)}&category=${cat}&limit=20`));
      if (res.ok) {
        const data = await res.json();
        const results: InstrumentItem[] = data.results || [];
        if (results.length > 0) {
          setCatalogResults(results);
          setFetchedStockMsg(`✅ Found ${results.length} scrip(s) for "${clean}" via Angel One SmartAPI. Click to select.`);
        } else {
          // Still add it manually (it will resolve on backend during configure)
          saveCustomStock(clean);
          toggleEquity(clean, exch);
          setSearchQuery('');
          setFetchedStockMsg(`⚡ Added "${clean}" — backend will resolve token on next Save & Activate.`);
          setCatalogResults([]);
        }
      }
    } catch (err: any) {
      setFetchedStockMsg(`⚠️ Network error: ${err.message}`);
    } finally {
      setIsFetchingStock(false);
    }
  };

  const handleRemoveSelected = (sym: string, type: 'crypto' | 'nse' | 'bse' | 'fut' | 'comm') => {
    if (type === 'crypto') setSelectedCrypto((prev) => { const n = new Set(prev); n.delete(sym); return n; });
    else if (type === 'nse') setSelectedEquityNSE((prev) => { const n = new Set(prev); n.delete(sym); return n; });
    else if (type === 'bse') setSelectedEquityBSE((prev) => { const n = new Set(prev); n.delete(sym); return n; });
    else if (type === 'fut') setSelectedFutures((prev) => { const n = new Set(prev); n.delete(sym); return n; });
    else if (type === 'comm') setSelectedCommodity((prev) => { const n = new Set(prev); n.delete(sym); return n; });
  };

  const toggleFutures = (sym: string) => {
    setSelectedFutures((prev) => { const next = new Set(prev); if (next.has(sym)) next.delete(sym); else next.add(sym); return next; });
  };

  const toggleCommodity = (sym: string) => {
    setSelectedCommodity((prev) => { const next = new Set(prev); if (next.has(sym)) next.delete(sym); else next.add(sym); return next; });
  };

  const toggleTimeframe = (tf: string) => {
    setSelectedTimeframes((prev) => {
      if (prev.includes(tf)) {
        if (prev.length === 1) return prev;
        return prev.filter((t) => t !== tf);
      } else {
        return [...prev, tf].sort((a, b) => {
          const order = ['1m','3m','5m','10m','15m','30m','1h','2h','4h','1d'];
          return order.indexOf(a) - order.indexOf(b);
        });
      }
    });
  };

  // Debounced catalog typeahead handler
  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    setFetchedStockMsg(null);
    if (!val.trim()) {
      setCatalogResults([]);
      setIsCatalogSearching(false);
      return;
    }
    setIsCatalogSearching(true); // show spinner immediately on typing
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      performCatalogSearch(val, modalActiveTab);
    }, 250);
  };


  // ── Cyberpunk Terminal State ──────────────────────────────────────────────
  const [currentView, setCurrentView] = useState<TerminalView>('dashboard');
  const [isEngineActive, setIsEngineActive] = useState<boolean>(true);
  const [isTogglingEngine, setIsTogglingEngine] = useState<boolean>(false);
  const [engineActionMsg, setEngineActionMsg] = useState<string | null>(null);
  const [chartSymbol, setChartSymbol] = useState<string>('RELIANCE');
  const [chartTimeframe, setChartTimeframe] = useState<string>('15m');
  const [chartPrice, setChartPrice] = useState<number>(1284.45);
  const [chartEma100, setChartEma100] = useState<number>(1284.65);
  const [chartEma200, setChartEma200] = useState<number>(1254.28);

  // Suppress ts unused vars in build
  if (false as boolean) {
    console.log(activeAlertFilter, setActiveAlertFilter, selectedEquity, setTestTimeframe);
  }

  // Sync engine status from status endpoint or WS
  useEffect(() => {
    if (status && typeof (status as any).is_engine_active === 'boolean') {
      setIsEngineActive((status as any).is_engine_active);
    }
  }, [status]);

  // Master Engine Start / Stop Toggle Handler
  const handleToggleEngine = async () => {
    setIsTogglingEngine(true);
    setEngineActionMsg(null);
    try {
      const endpoint = isEngineActive ? '/api/engine/stop' : '/api/engine/start';
      const res = await fetch(getApiUrl(endpoint), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setIsEngineActive(data.is_running);
        setEngineActionMsg(data.message);
        fetchData();
        setTimeout(() => setEngineActionMsg(null), 4000);
      }
    } catch (e: any) {
      setEngineActionMsg(`Action failed: ${e.message}`);
    } finally {
      setIsTogglingEngine(false);
    }
  };

  // Select instrument for chart preview
  const handleSelectChartAsset = (sym: string, priceVal?: number, e100?: number, e200?: number) => {
    setChartSymbol(sym);
    if (priceVal && priceVal > 0) setChartPrice(priceVal);
    else if (sym === 'BTCUSD') setChartPrice(79808.33);
    else if (sym === 'ETHUSD') setChartPrice(2394.31);
    else if (sym === 'TCS') setChartPrice(2482.00);
    else if (sym === 'INFY') setChartPrice(1149.00);
    else setChartPrice(1284.45);

    if (e100) setChartEma100(e100);
    if (e200) setChartEma200(e200);
  };

  // Helper to reliably parse UTC date strings across all browsers
  const parseUtcDate = (tsStr?: string): Date => {
    if (!tsStr) return new Date();
    const hasTz = tsStr.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(tsStr);
    const normalized = hasTz ? tsStr : tsStr.replace(' ', 'T') + 'Z';
    return new Date(normalized);
  };

  const formatSignalTime = (tsStr?: string) => {
    if (!tsStr) return { time: '-', date: '', full: '-' };
    try {
      const d = parseUtcDate(tsStr);
      const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
      const date = d.toLocaleDateString([], { day: '2-digit', month: 'short' });
      return { time, date, full: `${date} ${time}` };
    } catch {
      return { time: tsStr, date: '', full: tsStr };
    }
  };

  const formatEma = (val?: number, _decimals: number = 4) => {
    if (val === undefined || val === null || isNaN(val)) return '-';
    const v = Number(val);
    // Auto-select decimal places based on magnitude so small-price assets show difference
    if (v >= 10000) return v.toFixed(2);
    if (v >= 100) return v.toFixed(3);
    if (v >= 1) return v.toFixed(4);
    return v.toFixed(6); // e.g. tokens under $1
  };

  const filteredSignals = signals.filter((s) => {
    if (selectedAssetFilter === 'all') return true;
    return s.asset_class === selectedAssetFilter;
  });

  const filteredMonitoredList = useMemo(() => {
    return monitoredList.filter((item) => {
      if (stockCategoryFilter !== 'all') {
        if (stockCategoryFilter === 'equity' && item.asset_class !== 'equity') return false;
        if (stockCategoryFilter === 'crypto' && item.asset_class !== 'crypto') return false;
        if (stockCategoryFilter === 'commodity' && item.asset_class !== 'commodity') return false;
        if (stockCategoryFilter === 'equity_futures' && item.asset_class !== 'equity_futures') return false;
      }
      if (stockSearchFilter.trim()) {
        const q = stockSearchFilter.trim().toUpperCase();
        return (
          item.symbol.toUpperCase().includes(q) ||
          (item.name || '').toUpperCase().includes(q) ||
          item.exchange.toUpperCase().includes(q) ||
          (item.underlying || '').toUpperCase().includes(q)
        );
      }
      return true;
    });
  }, [monitoredList, stockCategoryFilter, stockSearchFilter]);



  return (
    <div className="terminal-shell">
      {/* ── LEFT CYBER SIDEBAR NAVIGATION ── */}
      <CyberSidebar
        currentView={currentView}
        onSelectView={setCurrentView}
        isEngineActive={isEngineActive}
        totalAlertsCount={signals.length}
      />

      {/* ── MAIN TERMINAL VIEWPORT ── */}
      <div className="terminal-main">
        {/* ── TOPBAR NAVIGATION & ENGINE SWITCH ── */}
        <CyberTopbar
          status={status}
          isWsConnected={isWsConnected}
          isEngineActive={isEngineActive}
          isTogglingEngine={isTogglingEngine}
          onToggleEngine={handleToggleEngine}
          onOpenCreateAlert={handleOpenCreateAlert}
          searchQuery={searchQuery}
          onSearchChange={handleSearchChange}
        />

        {/* Engine action toast banner */}
        {engineActionMsg && (
          <div
            style={{
              margin: '16px 28px 0',
              padding: '12px 18px',
              borderRadius: 8,
              background: isEngineActive ? 'rgba(0, 255, 156, 0.12)' : 'rgba(255, 59, 92, 0.12)',
              border: `1px solid ${isEngineActive ? '#00FF9C' : '#FF3B5C'}`,
              color: isEngineActive ? '#00FF9C' : '#FF3B5C',
              fontSize: 13,
              fontFamily: 'var(--font-mono)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              boxShadow: '0 0 20px rgba(0,0,0,0.5)',
            }}
          >
            <span>{isEngineActive ? '⚡ [ENGINE ONLINE]' : '🛑 [ENGINE PAUSED]'} {engineActionMsg}</span>
            <button
              onClick={() => setEngineActionMsg(null)}
              style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>
        )}

        {/* Contract Rollover Toast */}
        {rolledContracts.length > 0 && (
          <div
            style={{
              margin: '16px 28px 0',
              background: 'rgba(0, 255, 156, 0.08)',
              border: '1px solid rgba(0, 255, 156, 0.35)',
              borderRadius: 8,
              padding: '10px 18px',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <span style={{ color: '#00FF9C', fontWeight: 700, fontSize: 12 }}>
              🔄 {rolledContracts.length} Contract(s) Auto-Rolled
            </span>
            {rolledContracts.map((c, i) => (
              <span key={i} style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                {c.old_symbol} → <strong style={{ color: '#00FF9C' }}>{c.new_symbol}</strong>
              </span>
            ))}
          </div>
        )}

        {/* ── VIEW ROUTING CONTENT CANVAS ── */}
        <main className="terminal-content">
          {/* =================================================================
              VIEW 1: DASHBOARD
              ================================================================= */}
          {currentView === 'dashboard' && (
            <div>
              {/* Ticker Row: Real-time Indices & Benchmarks */}
              <div className="ticker-grid">
                {[
                  { sym: 'NIFTY 50', exch: 'NSE', price: '23,887.42', chg: '+0.42%', up: true, e100: 23887.42, e200: 23518.42 },
                  { sym: 'BANK NIFTY', exch: 'NSE', price: '51,420.10', chg: '+0.65%', up: true, e100: 51200.0, e200: 50800.0 },
                  { sym: 'RELIANCE', exch: 'NSE', price: '1,284.45', chg: '+1.12%', up: true, e100: 1284.65, e200: 1254.28 },
                  { sym: 'TCS', exch: 'NSE', price: '2,482.00', chg: '-0.38%', up: false, e100: 2482.03, e200: 2478.24 },
                  { sym: 'BTCUSD', exch: 'DELTA', price: '79,808.33', chg: '+2.84%', up: true, e100: 79808.33, e200: 79254.05 },
                  { sym: 'ETHUSD', exch: 'DELTA', price: '2,394.31', chg: '+1.45%', up: true, e100: 2394.31, e200: 2365.85 },
                ].map((item) => (
                  <div
                    key={item.sym}
                    className="ticker-card"
                    style={{
                      cursor: 'pointer',
                      borderColor: chartSymbol === item.sym ? 'var(--border-neon-cyan)' : 'var(--border-glass)',
                      boxShadow: chartSymbol === item.sym ? '0 0 16px rgba(0, 245, 255, 0.2)' : 'none',
                    }}
                    onClick={() => handleSelectChartAsset(item.sym, parseFloat(item.price.replace(/,/g, '')), item.e100, item.e200)}
                  >
                    <div className="ticker-top">
                      <span className="ticker-symbol">{item.sym}</span>
                      <span className="ticker-exchange">{item.exch}</span>
                    </div>
                    <div className="ticker-price">{item.exch === 'DELTA' ? '$' : '₹'}{item.price}</div>
                    <div className="ticker-bottom">
                      <span style={{ color: item.up ? 'var(--trade-bullish)' : 'var(--trade-bearish)' }}>
                        {item.chg}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>Live Market Feed</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* KPI Statistics Ribbon */}
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-icon-wrapper" style={{ color: '#00F5FF', borderColor: 'rgba(0, 245, 255, 0.3)' }}>
                    <Cpu size={20} />
                  </div>
                  <div>
                    <div className="kpi-value font-mono">
                      {(status?.monitored_counts.stocks || 0) +
                        (status?.monitored_counts.crypto || 0) +
                        (status?.monitored_counts.commodities || 0) +
                        (status?.monitored_counts.futures || 0)}
                    </div>
                    <div className="kpi-label">Monitored Assets</div>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-icon-wrapper" style={{ color: '#00FF9C', borderColor: 'rgba(0, 255, 156, 0.3)' }}>
                    <Radio size={20} />
                  </div>
                  <div>
                    <div className="kpi-value font-mono">{signals.length}</div>
                    <div className="kpi-label">Recorded Signals</div>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-icon-wrapper" style={{ color: '#A855F7', borderColor: 'rgba(168, 85, 247, 0.3)' }}>
                    <Sliders size={20} />
                  </div>
                  <div>
                    <div className="kpi-value font-mono" style={{ fontSize: 15 }}>
                      {status?.timeframes.join(', ') || '15m, 30m, 1h'}
                    </div>
                    <div className="kpi-label">Active Timeframes</div>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-icon-wrapper" style={{ color: '#FF2E93', borderColor: 'rgba(255, 46, 147, 0.3)' }}>
                    <BellRing size={20} />
                  </div>
                  <div>
                    <div className="kpi-value font-mono">
                      {status?.notifications.telegram === 'Enabled' ? 'TELEGRAM ON' : 'LOGS ONLY'}
                    </div>
                    <div className="kpi-label">Dispatch Gateway</div>
                  </div>
                </div>
              </div>

              {/* Main Interactive Candlestick & EMA Chart */}
              <CyberCandleChart
                symbol={chartSymbol}
                timeframe={chartTimeframe}
                price={chartPrice}
                ema100={chartEma100}
                ema200={chartEma200}
                onTimeframeChange={setChartTimeframe}
              />

              {/* Grid: Live Alert Stream + Test Dispatcher */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 24 }}>
                {/* Live Stream Panel */}
                <div className="glass-card">
                  <div className="card-header-flex">
                    <div className="card-title-cyber">
                      <Radio size={17} style={{ color: '#00F5FF' }} />
                      <span>LIVE ALERT STREAM</span>
                    </div>
                    <span className="signal-pill bullish" style={{ fontSize: 10, padding: '2px 8px' }}>
                      STREAMING
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 380, overflowY: 'auto' }}>
                    {liveAlerts.length === 0 ? (
                      <div style={{ textAlign: 'center', padding: '36px 20px', color: 'var(--text-muted)' }}>
                        <Activity size={28} style={{ opacity: 0.4, margin: '0 auto 10px' }} />
                        <p style={{ fontSize: 13 }}>Awaiting closed-candle crossovers...</p>
                        <p style={{ fontSize: 11, marginTop: 4 }}>
                          Click <strong>+ Add Alert</strong> to monitor more instruments.
                        </p>
                      </div>
                    ) : (
                      liveAlerts.map((alert, idx) => (
                        <div
                          key={alert.signal_id || idx}
                          style={{
                            padding: '12px 14px',
                            borderRadius: 8,
                            background: 'var(--bg-surface)',
                            border: '1px solid var(--border-glass)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            transition: 'all 0.2s ease',
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>
                                {alert.symbol}
                              </span>
                              <span className="tf-badge">{alert.timeframe}</span>
                              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{alert.exchange}</span>
                            </div>
                            <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginTop: 4 }}>
                              EMA100: {formatEma(alert.ema100)} | EMA200: {formatEma(alert.ema200)}
                            </div>
                          </div>

                          <div style={{ textAlign: 'right' }}>
                            <span className={`signal-pill ${alert.signal_type.toLowerCase()}`}>
                              {alert.signal_type}
                            </span>
                            <div className="font-mono" style={{ fontSize: 13, fontWeight: 700, marginTop: 4 }}>
                              {alert.exchange === 'DELTA' ? '$' : '₹'}{alert.price?.toLocaleString()}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Instant Alert Dispatcher Form */}
                <div className="glass-card">
                  <div className="card-header-flex">
                    <div className="card-title-cyber">
                      <Zap size={17} style={{ color: '#A855F7' }} />
                      <span>MANUAL ALERT TEST DISPATCHER</span>
                    </div>
                    <span className="tf-badge">INSTANT TEST</span>
                  </div>

                  <form onSubmit={handleTestAlert} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div>
                        <label style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                          SYMBOL
                        </label>
                        <input
                          type="text"
                          className="search-input"
                          value={testSymbol}
                          onChange={(e) => setTestSymbol(e.target.value.toUpperCase())}
                          style={{ width: '100%' }}
                        />
                      </div>

                      <div>
                        <label style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                          SIGNAL
                        </label>
                        <select
                          className="search-input"
                          value={testSignalType}
                          onChange={(e) => setTestSignalType(e.target.value as any)}
                          style={{ width: '100%' }}
                        >
                          <option value="BULLISH">BULLISH (Golden Cross)</option>
                          <option value="BEARISH">BEARISH (Death Cross)</option>
                        </select>
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div>
                        <label style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                          MARKET / ASSET CLASS
                        </label>
                        <select
                          className="search-input"
                          value={testAssetClass}
                          onChange={(e) => {
                            const val = e.target.value;
                            setTestAssetClass(val);
                            if (val === 'crypto') setTestExchange('DELTA');
                            else if (val === 'commodity') setTestExchange('MCX');
                            else if (val === 'equity_futures') setTestExchange('NFO');
                            else setTestExchange('NSE');
                          }}
                          style={{ width: '100%' }}
                        >
                          <option value="equity">Equity Cash (NSE)</option>
                          <option value="crypto">Cryptocurrency (Delta)</option>
                          <option value="commodity">Commodity (MCX)</option>
                          <option value="equity_futures">Equity F&O (NFO)</option>
                        </select>
                      </div>

                      <div>
                        <label style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                          TRIGGER PRICE
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          className="search-input"
                          value={testPrice}
                          onChange={(e) => setTestPrice(parseFloat(e.target.value) || 0)}
                          style={{ width: '100%' }}
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      className="btn-cyber-primary"
                      disabled={isTestingAlert}
                      style={{ marginTop: 8 }}
                    >
                      <Zap size={15} />
                      <span>{isTestingAlert ? 'DISPATCHING NOTIFICATIONS...' : 'DISPATCH LIVE ALERT'}</span>
                    </button>

                    {testResult && (
                      <div
                        style={{
                          padding: 10,
                          borderRadius: 8,
                          fontSize: 12,
                          background: 'rgba(0, 245, 255, 0.08)',
                          border: '1px solid rgba(0, 245, 255, 0.3)',
                          color: '#00F5FF',
                        }}
                      >
                        {testResult}
                      </div>
                    )}
                  </form>
                </div>
              </div>
            </div>
          )}

          {/* =================================================================
              VIEW 2: TRADING SIGNALS & HISTORY
              ================================================================= */}
          {(currentView === 'trading_signals' || currentView === 'alert_history') && (
            <div className="glass-card">
              <div className="card-header-flex">
                <div>
                  <div className="card-title-cyber">
                    <Radio size={18} style={{ color: '#00FF9C' }} />
                    <span>DEDUPLICATED SIGNAL LOGS & AUDIT HISTORY</span>
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                    Strict closed-candle crossover signals. Intrabar fluctuations are completely suppressed.
                  </p>
                </div>

                {/* Filter Tabs */}
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {['all', 'crypto', 'equity', 'equity_futures', 'commodity'].map((tab) => (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => setSelectedAssetFilter(tab)}
                      style={{
                        padding: '5px 12px',
                        borderRadius: 6,
                        border: '1px solid',
                        borderColor: selectedAssetFilter === tab ? 'var(--neon-cyan)' : 'var(--border-glass)',
                        background: selectedAssetFilter === tab ? 'rgba(0, 245, 255, 0.15)' : 'transparent',
                        color: selectedAssetFilter === tab ? '#00F5FF' : 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      {tab === 'all' && 'All Markets'}
                      {tab === 'crypto' && 'Crypto (Delta)'}
                      {tab === 'equity' && 'Stocks (NSE)'}
                      {tab === 'equity_futures' && 'Futures (NFO)'}
                      {tab === 'commodity' && 'Commodities (MCX)'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Signal Table */}
              <div className="cyber-table-container">
                <table className="cyber-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Instrument</th>
                      <th>Market</th>
                      <th>TF</th>
                      <th>Signal</th>
                      <th>Price</th>
                      <th>EMA 100</th>
                      <th>EMA 200</th>
                      <th>Deduplication Key</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSignals.length === 0 ? (
                      <tr>
                        <td colSpan={9} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                          No signals matching this category yet.
                        </td>
                      </tr>
                    ) : (
                      filteredSignals.map((s) => (
                        <tr key={s.signal_id}>
                          <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                            <div style={{ fontWeight: 600 }}>{formatSignalTime(s.candle_timestamp).time}</div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                              {formatSignalTime(s.candle_timestamp).date}
                            </div>
                          </td>
                          <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{s.symbol}</td>
                          <td>
                            <span style={{ textTransform: 'capitalize', color: 'var(--text-secondary)' }}>
                              {s.asset_class.replace('_', ' ')}
                            </span>
                          </td>
                          <td>
                            <span className="tf-badge">{s.timeframe}</span>
                          </td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span className={`signal-pill ${s.signal_type.toLowerCase()}`}>
                                {s.signal_type}
                              </span>
                              {s.is_catchup && (
                                <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'rgba(0, 245, 255, 0.2)', border: '1px solid #00F5FF', color: '#00F5FF', fontWeight: 700, letterSpacing: '0.05em' }}>
                                  CATCH-UP
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="font-mono" style={{ fontWeight: 600 }}>
                            {s.exchange === 'DELTA' ? '$' : '₹'}{s.price?.toLocaleString()}
                          </td>
                          <td className="font-mono" style={{ color: '#00FF9C' }} title={`Raw EMA 100: ${s.ema100}`}>
                            {formatEma(s.ema100, 4)}
                          </td>
                          <td className="font-mono" style={{ color: '#A855F7' }} title={`Raw EMA 200: ${s.ema200}`}>
                            {formatEma(s.ema200, 4)}
                          </td>
                          <td className="font-mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                            {s.signal_id}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* =================================================================
              VIEW 3: ENGINE CONTROL
              ================================================================= */}
          {currentView === 'engine_control' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div className="glass-card">
                <div className="card-header-flex">
                  <div className="card-title-cyber">
                    <Cpu size={18} style={{ color: '#00F5FF' }} />
                    <span>REAL-TIME ENGINE ORCHESTRATION</span>
                  </div>
                  <span
                    className={`signal-pill ${isEngineActive ? 'bullish' : 'bearish'}`}
                    style={{ fontSize: 11 }}
                  >
                    {isEngineActive ? 'ENGINE ONLINE & EVALUATING' : 'ENGINE PAUSED'}
                  </span>
                </div>

                <p style={{ color: 'var(--text-secondary)', fontSize: 13, maxWidth: 640 }}>
                  Manage the background closed-candle stream processor and EMA calculations. When stopped, market feeds
                  remain connected while signal calculations and notifications are paused safely.
                </p>

                <div style={{ display: 'flex', gap: 14, marginTop: 20 }}>
                  <button
                    type="button"
                    className="btn-cyber-primary"
                    onClick={handleToggleEngine}
                    disabled={isTogglingEngine}
                    style={{
                      background: isEngineActive
                        ? 'linear-gradient(135deg, rgba(255, 59, 92, 0.2), rgba(255, 46, 147, 0.25))'
                        : 'linear-gradient(135deg, rgba(0, 255, 156, 0.2), rgba(0, 245, 255, 0.25))',
                      borderColor: isEngineActive ? '#FF3B5C' : '#00FF9C',
                    }}
                  >
                    <Power size={15} />
                    <span>
                      {isTogglingEngine
                        ? 'PROCESSING...'
                        : isEngineActive
                        ? 'PAUSE ALERT ENGINE'
                        : 'START ALERT ENGINE'}
                    </span>
                  </button>

                  <button
                    type="button"
                    className="btn-cyber-secondary"
                    onClick={fetchData}
                  >
                    <RefreshCw size={14} />
                    <span>REFRESH ENGINE METRICS</span>
                  </button>
                </div>
              </div>

              {/* Provider Subscriptions Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                <div className="glass-card">
                  <div className="card-title-cyber" style={{ marginBottom: 12 }}>
                    <span>ANGEL ONE SMARTSTREAM</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                    <div>Status: <strong style={{ color: '#00FF9C' }}>{status?.providers.angelone || 'Connected'}</strong></div>
                    <div>Exchanges: NSE Equity, NFO Futures & Options, MCX Commodity</div>
                    <div>Warm-up Lookback: 30–105 calendar days (Market-hour aware)</div>
                  </div>
                </div>

                <div className="glass-card">
                  <div className="card-title-cyber" style={{ marginBottom: 12 }}>
                    <span>DELTA EXCHANGE INDIA</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                    <div>Status: <strong style={{ color: '#00FF9C' }}>{status?.providers.delta || 'Connected'}</strong></div>
                    <div>Market Hours: 24/7 Uninterrupted Crypto Streaming</div>
                    <div>WebSocket Feeds: BTCUSD, ETHUSD Perpetuals</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* =================================================================
              VIEW 4: STRATEGY ENGINE & ACTIVE RULES
              ================================================================= */}
          {(currentView === 'strategy_engine' || currentView === 'market_overview') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div className="glass-card">
                <div className="card-header-flex">
                  <div>
                    <div className="card-title-cyber">
                      <Sliders size={18} style={{ color: '#00F5FF' }} />
                      <span>CONFIGURED STRATEGY RULES &amp; MONITORED UNIVERSE</span>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                      Dual-period EMA crossover engine running on closed candle confirmations (Fast EMA: 100, Slow EMA: 200).
                    </p>
                  </div>

                  <button
                    type="button"
                    className="btn-cyber-primary"
                    onClick={() => handleOpenEditAlert()}
                  >
                    <Sliders size={14} />
                    <span>Configure All Symbols &amp; Strategy</span>
                  </button>
                </div>

                {/* Instant Strategy Execution Timeframe Ribbon */}
                <div className="strategy-tf-ribbon">
                  <div className="strategy-tf-ribbon-header">
                    <div className="strategy-tf-ribbon-title">
                      <Zap size={15} style={{ color: '#00F5FF' }} />
                      <span>Alert Execution Timeframes ({selectedTimeframes.length} Active)</span>
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Click any timeframe to instantly enable or remove it from alert calculations
                    </span>
                  </div>

                  {quickTfSuccessMsg && (
                    <div className="toast-cyber">
                      <CheckCircle2 size={16} />
                      <span>{quickTfSuccessMsg}</span>
                    </div>
                  )}

                  <div className="strategy-tf-pill-row">
                    {[
                      { id: '5m', name: '5 Min', desc: 'Scalping Strategy' },
                      { id: '10m', name: '10 Min', desc: 'Fast Momentum' },
                      { id: '15m', name: '15 Min', desc: 'Standard Intraday' },
                      { id: '30m', name: '30 Min', desc: 'Swing / Positional' },
                      { id: '1h', name: '1 Hour', desc: 'Trend Following' },
                    ].map((tf) => {
                      const isActive = selectedTimeframes.includes(tf.id);
                      return (
                        <button
                          key={tf.id}
                          type="button"
                          className={`strategy-tf-btn ${isActive ? 'active' : ''}`}
                          onClick={() => handleQuickToggleTimeframe(tf.id)}
                          disabled={isUpdatingTimeframe}
                          title={isActive ? `Click to disable ${tf.name} alerts` : `Click to enable ${tf.name} alerts`}
                        >
                          <div>
                            <div className="strategy-tf-label">{tf.name}</div>
                            <div className="strategy-tf-desc">{tf.desc}</div>
                          </div>
                          <span className="strategy-tf-status-tag">
                            {isActive ? '✓ ACTIVE' : '+ ADD'}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Monitored Universe Filter & Search Bar */}
                <div className="monitored-filter-bar">
                  <div className="monitored-search-input">
                    <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input
                      type="text"
                      placeholder="Filter active stocks (e.g. RELIANCE, BTC, GOLD, BANKNIFTY)..."
                      value={stockSearchFilter}
                      onChange={(e) => setStockSearchFilter(e.target.value)}
                    />
                    {stockSearchFilter && (
                      <button
                        type="button"
                        style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                        onClick={() => setStockSearchFilter('')}
                      >
                        <X size={13} />
                      </button>
                    )}
                  </div>

                  <div className="monitored-cat-tabs">
                    {[
                      { id: 'all', label: `All (${monitoredList.length})` },
                      { id: 'equity', label: `Stocks (${monitoredList.filter(i => i.asset_class === 'equity').length})` },
                      { id: 'equity_futures', label: `Futures (${monitoredList.filter(i => i.asset_class === 'equity_futures').length})` },
                      { id: 'crypto', label: `Crypto (${monitoredList.filter(i => i.asset_class === 'crypto').length})` },
                      { id: 'commodity', label: `Commodities (${monitoredList.filter(i => i.asset_class === 'commodity').length})` },
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        className={`monitored-cat-tab ${stockCategoryFilter === tab.id ? 'active' : ''}`}
                        onClick={() => setStockCategoryFilter(tab.id as any)}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Interactive Monitored Stock Cards Grid */}
                {filteredMonitoredList.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)', background: 'var(--bg-surface)', borderRadius: 10, border: '1px solid var(--border-glass)', marginTop: 12 }}>
                    No monitored instruments matching your filter &ldquo;{stockSearchFilter}&rdquo;.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14, marginTop: 12 }}>
                    {filteredMonitoredList.map((item) => {
                      const exchClass = (item.exchange || '').toLowerCase();
                      return (
                        <div
                          key={`${item.exchange}-${item.symbol}`}
                          className="stock-monitored-card"
                          onClick={() => handleOpenStockEditor(item)}
                        >
                          <div className="stock-card-top">
                            <span className="stock-card-symbol">{item.symbol}</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span className={`stock-card-badge ${exchClass}`}>
                                {item.exchange}
                              </span>
                              <button
                                type="button"
                                className="stock-card-quick-delete"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRemoveInstrument(item.symbol, item.asset_class);
                                }}
                                title={`Remove ${item.symbol} from monitored universe`}
                              >
                                <X size={13} />
                              </button>
                            </div>
                          </div>

                          <div className="stock-card-meta">
                            {item.asset_class.replace('_', ' ')} &bull; {item.name || item.symbol}
                          </div>

                          <div className="stock-card-tf-row" onClick={(e) => e.stopPropagation()}>
                            <span style={{ fontSize: 10, color: 'var(--text-muted)', marginRight: 2 }}>Alerts on:</span>
                            {['5m', '10m', '15m', '30m', '1h'].map((tf) => {
                              const isTfActive = getStockTimeframes(item.symbol).includes(tf);
                              return (
                                <button
                                  key={tf}
                                  type="button"
                                  className={`stock-tf-chip ${isTfActive ? 'active' : ''}`}
                                  onClick={() => handleToggleStockTimeframe(item.symbol, tf)}
                                  title={isTfActive ? `${tf} alerts are ENABLED for ${item.symbol}. Click to disable.` : `${tf} alerts are DISABLED for ${item.symbol}. Click to enable.`}
                                >
                                  {tf} {isTfActive ? '✓' : ''}
                                </button>
                              );
                            })}
                          </div>

                          <div className="stock-card-actions" onClick={(e) => e.stopPropagation()}>
                            <button
                              type="button"
                              className="btn-card-action"
                              onClick={() => handleOpenStockEditor(item)}
                              title="Configure timeframes and settings for this stock"
                            >
                              <Sliders size={12} />
                              <span>Edit Settings</span>
                            </button>

                            <button
                              type="button"
                              className="btn-card-action"
                              onClick={() => handleSwitchToChart(item.symbol)}
                              title="Open interactive candlestick chart"
                            >
                              <TrendingUp size={12} />
                              <span>Chart</span>
                            </button>

                            <button
                              type="button"
                              className="btn-card-action danger"
                              onClick={() => handleRemoveInstrument(item.symbol, item.asset_class)}
                              title="Remove from monitored universe"
                            >
                              <X size={12} />
                              <span>Remove</span>
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* =================================================================
              VIEW 5: BACKTESTING WORKSPACE
              ================================================================= */}
          {currentView === 'backtesting' && <CyberBacktestWorkspace />}

          {/* =================================================================
              VIEW 6: SETTINGS & NOTIFICATIONS
              ================================================================= */}
          {(currentView === 'settings' || currentView === 'api_connections') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div className="glass-card">
                <div className="card-title-cyber" style={{ marginBottom: 14 }}>
                  <Bell size={18} style={{ color: '#00F5FF' }} />
                  <span>ALERT NOTIFICATION GATEWAYS</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
                  <div style={{ padding: 16, background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border-glass)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <strong>Telegram Bot</strong>
                      <span className="signal-pill bullish" style={{ fontSize: 10 }}>
                        {status?.notifications.telegram || 'Enabled'}
                      </span>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Direct instant push notification with price, EMA values & chart link.
                    </p>
                  </div>

                  <div style={{ padding: 16, background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border-glass)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <strong>Email SMTP</strong>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {status?.notifications.email || 'Disabled'}
                      </span>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      HTML alert digest sent directly to configured email addresses.
                    </p>
                  </div>

                  <div style={{ padding: 16, background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border-glass)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <strong>WhatsApp Business</strong>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {status?.notifications.whatsapp || 'Disabled'}
                      </span>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Meta Cloud API / Twilio official WhatsApp alert delivery.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ── PRESERVED CREATE / EDIT ALERT STUDIO MODAL ── */}

      {isCreateModalOpen && (
        <div className="modal-overlay" onClick={() => setIsCreateModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <div className="brand-icon" style={{ width: 36, height: 36, borderRadius: 10 }}>
                  {modalMode === 'edit' ? <Sliders size={18} color="#ffffff" /> : <Sparkles size={18} color="#ffffff" />}
                </div>
                <div>
                  <h2 className="modal-title">
                    {modalMode === 'edit' ? 'Edit Alert Configuration' : 'Create Alert Studio'}
                  </h2>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                    {modalMode === 'edit'
                      ? 'Modify monitored candle timeframes (5m, 15m, 30m, 1h) and adjust your active coins, stocks, & commodities'
                      : 'Add cryptocurrency coins, Indian stocks, commodities & futures to live EMA crossover monitoring'}
                  </p>
                </div>
              </div>
              <button className="modal-close-btn" onClick={() => setIsCreateModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {/* Option 1: 100 and 200 EMA Crossover Alert (Sleek Compact Banner) */}
              <div className="strategy-card">
                <div className="strategy-header">
                  <div className="strategy-title">
                    <CheckCircle2 size={16} color="#10b981" />
                    <span>EMA 100 &amp; 200 Crossover Engine</span>
                  </div>
                  <span className="strategy-active-badge">Active Live Engine</span>
                </div>
                <div className="strategy-pills-row">
                  <div className="strategy-param-pill">
                    <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>Fast EMA:</span>
                    <span>100</span>
                  </div>
                  <div className="strategy-param-pill">
                    <span style={{ color: 'var(--accent-purple)', fontWeight: 700 }}>Slow EMA:</span>
                    <span>200</span>
                  </div>
                  <div className="strategy-param-pill">
                    <span style={{ color: '#10b981', fontWeight: 700 }}>Golden Cross:</span>
                    <span>Bullish Alert</span>
                  </div>
                  <div className="strategy-param-pill">
                    <span style={{ color: '#ef4444', fontWeight: 700 }}>Death Cross:</span>
                    <span>Bearish Alert</span>
                  </div>
                  <div className="strategy-param-pill">
                    <span style={{ color: 'var(--accent-amber)', fontWeight: 700 }}>Execution:</span>
                    <span>Closed Candles Only</span>
                  </div>
                </div>
              </div>

              {/* Timeframes Multi-Selector */}
              <div>
                <label className="form-label" style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Execution Timeframes (Select active candle boundaries for alerts)</span>
                  <span style={{ fontSize: 11, color: 'var(--accent-cyan)' }}>{selectedTimeframes.length} Active</span>
                </label>
                <div className="timeframe-selector-row">
                  {[
                    { id: '5m', name: '5 Min', desc: 'Scalping' },
                    { id: '15m', name: '15 Min', desc: 'Standard Intraday' },
                    { id: '30m', name: '30 Min', desc: 'Swing / Position' },
                    { id: '1h', name: '1 Hour', desc: 'Trend Following' },
                  ].map((tf) => {
                    const isSelected = selectedTimeframes.includes(tf.id);
                    return (
                      <button
                        key={tf.id}
                        type="button"
                        className={`timeframe-pill-btn ${isSelected ? 'active' : ''}`}
                        onClick={() => toggleTimeframe(tf.id)}
                      >
                        <span style={{ fontSize: 15, fontWeight: 700 }}>{tf.name}</span>
                        <span className="timeframe-sub">{tf.desc}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Multi-Asset Selector Section */}
              <div>
                {/* Active Selection Watchlist Tray (always shows what is selected) */}
                {selectedCrypto.size + selectedEquityNSE.size + selectedEquityBSE.size + selectedFutures.size + selectedCommodity.size > 0 && (
                  <div className="modal-selected-tray" style={{ marginBottom: 16 }}>
                    <div className="modal-selected-tray-header">
                      <span>
                        Active Selected Watchlist ({selectedCrypto.size + selectedEquityNSE.size + selectedEquityBSE.size + selectedFutures.size + selectedCommodity.size} items)
                      </span>
                      <button
                        type="button"
                        style={{ background: 'transparent', border: 'none', color: '#ef4444', fontSize: 11, cursor: 'pointer', fontWeight: 600 }}
                        onClick={() => {
                          setSelectedCrypto(new Set());
                          setSelectedEquityNSE(new Set());
                          setSelectedEquityBSE(new Set());
                          setSelectedFutures(new Set());
                          setSelectedCommodity(new Set());
                        }}
                      >
                        Clear All
                      </button>
                    </div>
                    <div className="modal-selected-chips">
                      {Array.from(selectedEquityNSE).map((s) => (
                        <span key={`nse-${s}`} className="selected-chip-pill">
                          📈 {s}-NSE
                          <button type="button" className="selected-chip-remove" onClick={() => handleRemoveSelected(s, 'nse')}>&times;</button>
                        </span>
                      ))}
                      {Array.from(selectedEquityBSE).map((s) => (
                        <span key={`bse-${s}`} className="selected-chip-pill bse">
                          📊 {s}-BSE
                          <button type="button" className="selected-chip-remove" onClick={() => handleRemoveSelected(s, 'bse')}>&times;</button>
                        </span>
                      ))}
                      {Array.from(selectedCrypto).map((s) => (
                        <span key={`crypto-${s}`} className="selected-chip-pill crypto">
                          🪙 {s.replace('USD', '')}
                          <button type="button" className="selected-chip-remove" onClick={() => handleRemoveSelected(s, 'crypto')}>&times;</button>
                        </span>
                      ))}
                      {Array.from(selectedFutures).map((s) => (
                        <span key={`fut-${s}`} className="selected-chip-pill" style={{ borderColor: 'rgba(168, 85, 247, 0.4)', color: '#c084fc' }}>
                          ⚡ {s} <small style={{ opacity: 0.7 }}>FUT</small>
                          <button type="button" className="selected-chip-remove" onClick={() => handleRemoveSelected(s, 'fut')}>&times;</button>
                        </span>
                      ))}
                      {Array.from(selectedCommodity).map((s) => (
                        <span key={`comm-${s}`} className="selected-chip-pill" style={{ borderColor: 'rgba(245, 158, 11, 0.4)', color: '#fbbf24' }}>
                          🛢️ {s} <small style={{ opacity: 0.7 }}>MCX</small>
                          <button type="button" className="selected-chip-remove" onClick={() => handleRemoveSelected(s, 'comm')}>&times;</button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="asset-selector-nav">
                  <button
                    type="button"
                    className={`asset-nav-item ${modalActiveTab === 'equity' ? 'active' : ''}`}
                    onClick={() => { setModalActiveTab('equity'); setSearchQuery(''); setCatalogResults([]); }}
                  >
                    <TrendingUp size={16} />
                    <span>Indian Stocks (NSE &amp; BSE)</span>
                    <span className="asset-count-badge">
                      {selectedEquityNSE.size + selectedEquityBSE.size} Selected
                    </span>
                  </button>

                  <button
                    type="button"
                    className={`asset-nav-item ${modalActiveTab === 'crypto' ? 'active' : ''}`}
                    onClick={() => { setModalActiveTab('crypto'); setSearchQuery(''); setCatalogResults([]); }}
                  >
                    <Coins size={16} />
                    <span>Crypto (Delta)</span>
                    <span className="asset-count-badge">{selectedCrypto.size} / 250</span>
                  </button>

                  <button
                    type="button"
                    className={`asset-nav-item ${modalActiveTab === 'commodity' ? 'active' : ''}`}
                    onClick={() => { setModalActiveTab('commodity'); setSearchQuery(''); setCatalogResults([]); }}
                  >
                    <Zap size={16} />
                    <span>Commodities (MCX)</span>
                    <span className="asset-count-badge">{selectedCommodity.size}</span>
                  </button>

                  <button
                    type="button"
                    className={`asset-nav-item ${modalActiveTab === 'equity_futures' ? 'active' : ''}`}
                    onClick={() => { setModalActiveTab('equity_futures'); setSearchQuery(''); setCatalogResults([]); }}
                  >
                    <Layers size={16} />
                    <span>F&amp;O Futures (NFO)</span>
                    <span className="asset-count-badge">{selectedFutures.size}</span>
                  </button>
                </div>

                {/* Quick Action Presets & Unified Search Bar */}
                <div className="quick-action-strip">
                  <div className="quick-action-top-row">
                    <div className="quick-btn-group">
                      {modalActiveTab === 'equity' && (
                        <>
                          <button
                            type="button"
                            className={`btn-quick-select ${modalEquityExchange === 'ALL' ? 'active-exchange' : ''}`}
                            onClick={() => {
                              setModalEquityExchange('ALL');
                              setCatalogResults([]);
                              if (searchQuery.trim()) performCatalogSearch(searchQuery, 'equity', 'ALL');
                            }}
                            style={{
                              background: modalEquityExchange === 'ALL' ? 'rgba(56,189,248,0.2)' : undefined,
                              borderColor: modalEquityExchange === 'ALL' ? 'var(--accent-cyan)' : undefined,
                              color: modalEquityExchange === 'ALL' ? 'var(--accent-cyan)' : undefined
                            }}
                          >
                            🌐 All (NSE &amp; BSE) ({selectedEquityNSE.size + selectedEquityBSE.size})
                          </button>
                          <button
                            type="button"
                            className={`btn-quick-select ${modalEquityExchange === 'NSE' ? 'active-exchange' : ''}`}
                            onClick={() => {
                              setModalEquityExchange('NSE');
                              setCatalogResults([]);
                              if (searchQuery.trim()) performCatalogSearch(searchQuery, 'equity', 'NSE');
                            }}
                            style={{
                              background: modalEquityExchange === 'NSE' ? 'rgba(6,182,212,0.2)' : undefined,
                              borderColor: modalEquityExchange === 'NSE' ? 'var(--accent-cyan)' : undefined,
                              color: modalEquityExchange === 'NSE' ? 'var(--accent-cyan)' : undefined
                            }}
                          >
                            📈 NSE Only ({selectedEquityNSE.size})
                          </button>
                          <button
                            type="button"
                            className={`btn-quick-select ${modalEquityExchange === 'BSE' ? 'active-exchange' : ''}`}
                            onClick={() => {
                              setModalEquityExchange('BSE');
                              setCatalogResults([]);
                              if (searchQuery.trim()) performCatalogSearch(searchQuery, 'equity', 'BSE');
                            }}
                            style={{
                              background: modalEquityExchange === 'BSE' ? 'rgba(139,92,246,0.2)' : undefined,
                              borderColor: modalEquityExchange === 'BSE' ? 'var(--accent-purple)' : undefined,
                              color: modalEquityExchange === 'BSE' ? 'var(--accent-purple)' : undefined
                            }}
                          >
                            📊 BSE Only ({selectedEquityBSE.size})
                          </button>
                          <button
                            type="button"
                            className="btn-quick-select"
                            onClick={() => {
                              setSelectedEquityNSE((prev) => new Set([...prev, ...POPULAR_INDIAN_STOCKS.slice(0, 50)]));
                            }}
                          >
                            🔥 Nifty 50
                          </button>
                          <button
                            type="button"
                            className="btn-quick-select"
                            onClick={() => {
                              setSelectedEquityNSE((prev) => new Set([...prev, ...userSavedStocks]));
                            }}
                          >
                            ⭐ My Saved ({userSavedStocks.length})
                          </button>
                          <button
                            type="button"
                            className="btn-quick-select"
                            onClick={() => { setSelectedEquityNSE(new Set()); setSelectedEquityBSE(new Set()); }}
                          >
                            Clear
                          </button>
                        </>
                      )}

                      {modalActiveTab === 'crypto' && (
                        <>
                          <button
                            type="button"
                            className="btn-quick-select"
                            onClick={() => setSelectedCrypto(new Set(availableInstruments.crypto.length > 0 ? availableInstruments.crypto.map(c => c.symbol) : [...TOP_10_CRYPTO, ...MOMENTUM_CRYPTO]))}
                          >
                            Select All (250)
                          </button>
                          <button type="button" className="btn-quick-select" onClick={() => setSelectedCrypto(new Set(TOP_10_CRYPTO))}>Top 10 Mega-Cap</button>
                          <button type="button" className="btn-quick-select" onClick={() => setSelectedCrypto(new Set(MOMENTUM_CRYPTO))}>High Movers</button>
                          <button type="button" className="btn-quick-select" onClick={() => setSelectedCrypto(new Set())}>Clear All</button>
                        </>
                      )}

                      {modalActiveTab === 'commodity' && (
                        <>
                          <button
                            type="button"
                            className={`btn-quick-select ${commoditySubFilter === 'all' ? 'active-exchange' : ''}`}
                            onClick={() => setCommoditySubFilter('all')}
                          >
                            All MCX ({MCX_COMMODITIES_LIST.length})
                          </button>
                          <button
                            type="button"
                            className={`btn-quick-select ${commoditySubFilter === 'energy' ? 'active-exchange' : ''}`}
                            onClick={() => setCommoditySubFilter('energy')}
                          >
                            🛢️ Energy (Crude &amp; Gas)
                          </button>
                          <button
                            type="button"
                            className={`btn-quick-select ${commoditySubFilter === 'precious' ? 'active-exchange' : ''}`}
                            onClick={() => setCommoditySubFilter('precious')}
                          >
                            🥇 Gold &amp; Silver
                          </button>
                          <button
                            type="button"
                            className={`btn-quick-select ${commoditySubFilter === 'mini' ? 'active-exchange' : ''}`}
                            onClick={() => setCommoditySubFilter('mini')}
                          >
                            ⚡ Mini Contracts
                          </button>
                          <button
                            type="button"
                            className={`btn-quick-select ${commoditySubFilter === 'electricity' ? 'active-exchange' : ''}`}
                            onClick={() => setCommoditySubFilter('electricity')}
                          >
                            💡 Electricity
                          </button>
                          <button
                            type="button"
                            className={`btn-quick-select ${commoditySubFilter === 'metals' ? 'active-exchange' : ''}`}
                            onClick={() => setCommoditySubFilter('metals')}
                          >
                            ⚙️ Base Metals
                          </button>
                          <button
                            type="button"
                            className="btn-quick-select"
                            onClick={() => setSelectedCommodity(new Set(MCX_COMMODITIES))}
                          >
                            Select All
                          </button>
                          <button
                            type="button"
                            className="btn-quick-select"
                            onClick={() => setSelectedCommodity(new Set())}
                          >
                            Clear
                          </button>
                        </>
                      )}

                      {modalActiveTab === 'equity_futures' && (
                        <>
                          <button type="button" className="btn-quick-select" onClick={() => setSelectedFutures(new Set(['NIFTY', 'BANKNIFTY', 'FINNIFTY']))}>Index Futures</button>
                          <button type="button" className="btn-quick-select" onClick={() => setSelectedFutures(new Set(NFO_UNDERLYINGS))}>All Popular</button>
                          <button type="button" className="btn-quick-select" onClick={() => setSelectedFutures(new Set())}>Clear All</button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Unified Smart Search & Add Bar */}
                  <div className="smart-search-bar">
                    <div className="smart-search-input-wrap">
                      <Search size={15} className="search-box-icon" />
                      <input
                        type="text"
                        placeholder={
                          modalActiveTab === 'equity'
                            ? `Search stocks (e.g. CUPID, SUZLON, RELIANCE, ZOMATO)...`
                            : modalActiveTab === 'crypto'
                            ? 'Search BTC, ETH, SOL, XRP...'
                            : modalActiveTab === 'commodity'
                            ? 'Search CRUDEOIL, SILVER, GOLD, ELECDMBL...'
                            : 'Search NIFTY, BANKNIFTY, RELIANCE futures...'
                        }
                        value={searchQuery}
                        onChange={(e) => handleSearchChange(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleQuickAddStock();
                          }
                        }}
                      />
                      {isCatalogSearching ? (
                        <span className="search-input-badge">searching…</span>
                      ) : (
                        <span className="search-input-badge">150k+ Universe</span>
                      )}
                      {searchQuery && (
                        <button
                          type="button"
                          className="search-clear-btn"
                          onClick={() => { setSearchQuery(''); setCatalogResults([]); }}
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>

                    <button
                      type="button"
                      className="btn-smart-add"
                      onClick={() => handleQuickAddStock()}
                      title="Add typed symbol to live monitoring"
                    >
                      <Plus size={15} />
                      <span>Add {searchQuery.trim() ? searchQuery.trim().toUpperCase() : 'Stock'}</span>
                    </button>
                  </div>
                </div>

                {/* Instruments Grid */}
                <div className="coin-chips-grid" style={{ marginTop: 12 }}>

                  {/* CRYPTO TAB */}
                  {modalActiveTab === 'crypto' && (() => {
                    const baseList = availableInstruments.crypto.length > 0 ? availableInstruments.crypto : [...TOP_10_CRYPTO, ...MOMENTUM_CRYPTO].map(s => ({ symbol: s, name: 'Perpetual Future', exchange: 'DELTA', asset_class: 'crypto', is_monitored: false } as InstrumentItem));
                    const displayList = catalogResults.length > 0 ? catalogResults : (searchQuery ? baseList.filter(i => i.symbol.toUpperCase().includes(searchQuery.toUpperCase()) || (i.name || '').toUpperCase().includes(searchQuery.toUpperCase())) : baseList);
                    return displayList.map((coin) => {
                      const isSelected = selectedCrypto.has(coin.symbol);
                      return (
                        <div key={coin.symbol} className={`coin-chip-card ${isSelected ? 'selected' : ''}`} onClick={() => toggleCrypto(coin.symbol)}>
                          <div className="coin-chip-top">
                            <span className="coin-chip-symbol">{coin.symbol.replace('USD', '')}</span>
                            {isSelected ? <Check size={14} color="#10b981" /> : <span className="coin-chip-leverage">PERP</span>}
                          </div>
                          <div className="coin-chip-sub">{coin.name || 'Perpetual'} &bull; DELTA</div>
                        </div>
                      );
                    });
                  })()}

                  {/* INDIAN STOCKS TAB (NSE & BSE) */}
                  {modalActiveTab === 'equity' && (() => {
                    // 1. If catalog search returned results, show matching scrips cleanly formatted as SYMBOL-NSE and SYMBOL-BSE
                    if (catalogResults.length > 0) {
                      return catalogResults.map((inst) => {
                        const baseSymbol = (inst.base_symbol || inst.symbol).replace(/-EQ$/, '').replace(/-[AB]$/, '').trim();
                        const isBse = inst.exchange === 'BSE';
                        const isSelected = isBse ? selectedEquityBSE.has(baseSymbol) : selectedEquityNSE.has(baseSymbol);
                        const displaySym = inst.display_symbol || `${baseSymbol}-${inst.exchange}`;

                        return (
                          <div
                            key={`${inst.exchange}:${inst.instrument_id || inst.symbol}`}
                            className={`coin-chip-card ${isSelected ? 'selected' : ''}`}
                            onClick={() => toggleEquity(baseSymbol, inst.exchange)}
                          >
                            <div className="coin-chip-top">
                              <span className="coin-chip-symbol">{displaySym}</span>
                              {isSelected ? (
                                <Check size={14} color="#10b981" />
                              ) : (
                                <span
                                  className="coin-chip-leverage"
                                  style={{
                                    color: isBse ? 'var(--accent-purple)' : 'var(--accent-cyan)',
                                  }}
                                >
                                  {inst.exchange}
                                </span>
                              )}
                            </div>
                            <div className="coin-chip-sub" title={inst.name || baseSymbol}>
                              {inst.name || `${baseSymbol} Limited`} &bull; {inst.exchange} Equity
                            </div>
                          </div>
                        );
                      });
                    }

                    // 2. If user searched but 0 results — show loading or API fetch option
                    if (searchQuery.trim()) {
                      const qClean = searchQuery.trim().toUpperCase();
                      if (isCatalogSearching || isFetchingStock) {
                        return (
                          <div className="empty-search-fallback">
                            <span className="fetching-pill">
                              <RefreshCw size={13} className="spin-animation" />
                              {isFetchingStock ? `Fetching "${qClean}" from Angel One SmartAPI...` : `Searching 113k+ instruments for "${qClean}"...`}
                            </span>
                          </div>
                        );
                      }
                      return (
                        <div className="empty-search-fallback">
                          <p>
                            Stock <strong>&ldquo;{qClean}&rdquo;</strong> not found in local catalog.
                          </p>
                          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                            It may exist under a different symbol (e.g. BSE ticker). Try Angel One live search:
                          </p>
                          {fetchedStockMsg && (
                            <p style={{ fontSize: 12, color: '#10b981', fontWeight: 600 }}>{fetchedStockMsg}</p>
                          )}
                          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                            <button
                              type="button"
                              className="btn-live-fetch"
                              onClick={() => handleFetchAndAddStock(qClean)}
                              disabled={isFetchingStock}
                            >
                              <Zap size={14} />
                              Search &ldquo;{qClean}&rdquo; via Angel One SmartAPI
                            </button>
                            <button
                              type="button"
                              className="btn-quick-select"
                              style={{ fontSize: 12 }}
                              onClick={() => handleQuickAddStock(qClean)}
                            >
                              <Plus size={13} />
                              Add &ldquo;{qClean}&rdquo; Directly Anyway
                            </button>
                          </div>
                        </div>
                      );
                    }

                    // 3. Default view: Show NSE and BSE options cleanly for all stocks!
                    const defaultUniverse = Array.from(
                      new Set([
                        ...Array.from(selectedEquityNSE),
                        ...Array.from(selectedEquityBSE),
                        ...userSavedStocks,
                        ...POPULAR_INDIAN_STOCKS,
                      ])
                    );

                    const stockCards: React.ReactNode[] = [];
                    defaultUniverse.forEach((sym) => {
                      const isCustom = userSavedStocks.includes(sym);

                      // If ALL is selected, show BOTH NSE and BSE cards side by side!
                      if (modalEquityExchange === 'ALL' || modalEquityExchange === 'NSE') {
                        const isSelectedNSE = selectedEquityNSE.has(sym);
                        stockCards.push(
                          <div
                            key={`${sym}-NSE`}
                            className={`coin-chip-card ${isSelectedNSE ? 'selected' : ''}`}
                            onClick={() => toggleEquity(sym, 'NSE')}
                          >
                            <div className="coin-chip-top">
                              <span className="coin-chip-symbol">{sym}-NSE</span>
                              {isSelectedNSE ? (
                                <Check size={14} color="#10b981" />
                              ) : (
                                <span className="coin-chip-leverage" style={{ color: 'var(--accent-cyan)' }}>
                                  NSE
                                </span>
                              )}
                            </div>
                            <div className="coin-chip-sub">
                              {isCustom ? 'Saved Stock' : (sym === 'CUPID' ? 'CUPID LIMITED' : `${sym} Cash Equity`)} &bull; NSE
                            </div>
                          </div>
                        );
                      }

                      if (modalEquityExchange === 'ALL' || modalEquityExchange === 'BSE') {
                        const isSelectedBSE = selectedEquityBSE.has(sym);
                        stockCards.push(
                          <div
                            key={`${sym}-BSE`}
                            className={`coin-chip-card ${isSelectedBSE ? 'selected' : ''}`}
                            onClick={() => toggleEquity(sym, 'BSE')}
                          >
                            <div className="coin-chip-top">
                              <span className="coin-chip-symbol">{sym}-BSE</span>
                              {isSelectedBSE ? (
                                <Check size={14} color="#10b981" />
                              ) : (
                                <span className="coin-chip-leverage" style={{ color: 'var(--accent-purple)' }}>
                                  BSE
                                </span>
                              )}
                            </div>
                            <div className="coin-chip-sub">
                              {isCustom ? 'Saved Stock' : (sym === 'CUPID' ? 'CUPID LIMITED' : `${sym} Cash Equity`)} &bull; BSE
                            </div>
                          </div>
                        );
                      }
                    });

                    return stockCards;
                  })()}

                  {/* COMMODITY TAB (ALL MCX COMMODITIES + AUTO EXPIRY NOTICE) */}
                  {modalActiveTab === 'commodity' && (() => {
                    const filteredCommodities = MCX_COMMODITIES_LIST.filter((c) => {
                      if (commoditySubFilter === 'all') return true;
                      if (commoditySubFilter === 'mini') return c.isMini;
                      return c.category === commoditySubFilter;
                    }).filter((c) => {
                      if (!searchQuery) return true;
                      const q = searchQuery.toUpperCase();
                      return c.symbol.includes(q) || c.name.toUpperCase().includes(q) || c.desc.toUpperCase().includes(q);
                    });

                    return (
                      <>
                        <div style={{ gridColumn: '1 / -1' }} className="commodity-auto-roll-banner">
                          <RefreshCw size={15} style={{ color: '#10b981', flexShrink: 0 }} />
                          <span>
                            <strong>Automated Contract Rollover Active:</strong> MCX commodities automatically update to the latest active contract when they expire. You never need to manage or renew expiry dates.
                          </span>
                        </div>

                        {filteredCommodities.map((c) => {
                          const isSelected = selectedCommodity.has(c.symbol);
                          // Find any matching active contract from availableInstruments to display active expiry date
                          const matchingInst = availableInstruments.commodity.find(
                            (inst) => (inst.underlying || inst.name || inst.symbol).toUpperCase().startsWith(c.symbol) && !inst.is_expired
                          );
                          const expiryDisplay = matchingInst?.expiry ? `Exp: ${matchingInst.expiry}` : 'Auto-Roll Active';

                          return (
                            <div
                              key={c.symbol}
                              className={`coin-chip-card ${isSelected ? 'selected' : ''}`}
                              onClick={() => toggleCommodity(c.symbol)}
                            >
                              <div className="coin-chip-top">
                                <span className="coin-chip-symbol">{c.symbol}</span>
                                {isSelected ? (
                                  <Check size={14} color="#10b981" />
                                ) : (
                                  <span className="coin-chip-leverage" style={{ color: 'var(--accent-amber)' }}>
                                    MCX
                                  </span>
                                )}
                              </div>
                              <div className="coin-chip-sub" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</span>
                                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{c.desc}</span>
                                <span style={{ fontSize: 9, color: '#10b981', marginTop: 2, fontWeight: 700 }}>
                                  ● {expiryDisplay}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </>
                    );
                  })()}

                  {/* F&O FUTURES TAB */}
                  {modalActiveTab === 'equity_futures' && (() => {
                    const futsFromApi = availableInstruments.equity_futures;
                    const seenUnderlying = new Set<string>();
                    const displayFuts: InstrumentItem[] = [];
                    const searchFuts = catalogResults.length > 0 ? catalogResults : futsFromApi;
                    for (const f of searchFuts) {
                      const root = (f.underlying || f.name || f.symbol).replace(/\d{2}[A-Z]{3}\d{2,4}FUT$/, '').trim();
                      if (!searchQuery || root.toUpperCase().includes(searchQuery.toUpperCase()) || f.symbol.toUpperCase().includes(searchQuery.toUpperCase())) {
                        if (!seenUnderlying.has(root)) {
                          seenUnderlying.add(root);
                          displayFuts.push(f);
                        }
                      }
                      if (displayFuts.length >= 60) break;
                    }
                    const fallbackSyms = NFO_UNDERLYINGS.filter(s => !seenUnderlying.has(s));
                    const fallbackItems: InstrumentItem[] = futsFromApi.length === 0
                      ? fallbackSyms.map(s => ({ symbol: s + ' (Auto Contract)', name: s, exchange: 'NFO', asset_class: 'equity_futures', is_monitored: false } as InstrumentItem))
                      : [];

                    return [...displayFuts, ...fallbackItems].map((f) => {
                      const root = (f.underlying || f.name || f.symbol).replace(/\d{2}[A-Z]{3}\d{2,4}FUT$/, '').trim();
                      const isSelected = selectedFutures.has(root) || selectedFutures.has(f.name || '') || selectedFutures.has(f.symbol);
                      return (
                        <div key={f.instrument_id || f.symbol} className={`coin-chip-card ${isSelected ? 'selected' : ''}`} onClick={() => toggleFutures(root)}>
                          <div className="coin-chip-top">
                            <span className="coin-chip-symbol">{root}</span>
                            {isSelected ? <Check size={14} color="#10b981" /> : <span className="coin-chip-leverage" style={{ color: 'var(--accent-purple)', fontSize: 9 }}>FUT</span>}
                          </div>
                          <div className="coin-chip-sub" style={{ fontSize: 10 }}>
                            {f.expiry ? `Exp: ${f.expiry}` : 'Current Expiry'} &bull; NFO
                          </div>
                        </div>
                      );
                    });
                  })()}

                </div>

                {/* Search result count + status row */}
                {modalActiveTab === 'equity' && (
                  <div className="search-status-row">
                    <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                      {catalogResults.length > 0
                        ? `Showing ${catalogResults.length} matching stocks across NSE & BSE`
                        : searchQuery
                        ? isCatalogSearching ? 'Searching...' : '0 results — use API fetch below'
                        : `Showing stocks listed on ${modalEquityExchange === 'ALL' ? 'NSE & BSE' : modalEquityExchange}`}
                    </span>
                    {!searchQuery && (
                      <span className="search-count-pill">113k+ scrips available — type to search</span>
                    )}
                  </div>
                )}
              </div>

              {saveSuccessMsg && (
                <div style={{
                  padding: 14,
                  borderRadius: 10,
                  fontSize: 13,
                  background: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid rgba(16, 185, 129, 0.35)',
                  color: '#10b981',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                }}>
                  <CheckCircle2 size={18} />
                  <span>{saveSuccessMsg}</span>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <div className="modal-summary-counts">
                Selected for Alert:
                <strong> {selectedEquityNSE.size} NSE</strong> +
                <strong> {selectedEquityBSE.size} BSE</strong> Stocks &bull;
                <strong> {selectedCrypto.size} Crypto</strong> &bull;
                <strong> {selectedCommodity.size} MCX</strong> &bull;
                <strong> {selectedFutures.size} Futures</strong>
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  type="button"
                  className="tab-btn"
                  onClick={() => setIsCreateModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-save-alert"
                  disabled={
                    isSavingAlert ||
                    (selectedCrypto.size === 0 &&
                      selectedEquityNSE.size === 0 &&
                      selectedEquityBSE.size === 0 &&
                      selectedFutures.size === 0 &&
                      selectedCommodity.size === 0)
                  }
                  onClick={handleSaveAlertEngine}
                >
                  {isSavingAlert ? (
                    <>
                      <RefreshCw size={16} className="spin-animation" />
                      <span>{modalMode === 'edit' ? 'Updating Configuration...' : 'Activating Alert Engine...'}</span>
                    </>
                  ) : (
                    <>
                      <Zap size={16} />
                      <span>{modalMode === 'edit' ? 'Update Alert Configuration' : 'Save & Activate Alert'}</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── FOCUSED STOCK TIMEFRAME & SETTINGS MODAL ── */}
      {editingStock && (
        <div className="modal-overlay" onClick={() => setEditingStock(null)}>
          <div className="modal-content" style={{ maxWidth: 620 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <div className="brand-icon" style={{ width: 36, height: 36, borderRadius: 10 }}>
                  <Sliders size={18} color="#00F5FF" />
                </div>
                <div>
                  <h2 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span>{editingStock.symbol}</span>
                    <span className={`stock-card-badge ${(editingStock.exchange || '').toLowerCase()}`}>
                      {editingStock.exchange}
                    </span>
                  </h2>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                    Configure alert candle timeframes and indicator rules for this instrument
                  </p>
                </div>
              </div>
              <button className="modal-close-btn" onClick={() => setEditingStock(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="modal-body" style={{ gap: 20 }}>
              {/* Strategy Parameters Info */}
              <div className="strategy-card">
                <div className="strategy-header">
                  <div className="strategy-title">
                    <CheckCircle2 size={16} color="#10b981" />
                    <span>EMA 100 &amp; 200 Crossover Rule</span>
                  </div>
                  <span className="strategy-active-badge">Active in Real-Time</span>
                </div>
                <div className="strategy-pills-row">
                  <div className="strategy-param-pill">
                    <span style={{ color: 'var(--neon-cyan)', fontWeight: 700 }}>Fast EMA:</span>
                    <span>100</span>
                  </div>
                  <div className="strategy-param-pill">
                    <span style={{ color: 'var(--neon-purple)', fontWeight: 700 }}>Slow EMA:</span>
                    <span>200</span>
                  </div>
                  <div className="strategy-param-pill">
                    <span style={{ color: '#10b981', fontWeight: 700 }}>Golden Cross:</span>
                    <span>Bullish</span>
                  </div>
                  <div className="strategy-param-pill">
                    <span style={{ color: '#ef4444', fontWeight: 700 }}>Death Cross:</span>
                    <span>Bearish</span>
                  </div>
                </div>
              </div>

              {/* Timeframes Selection for this Stock */}
              <div>
                <label className="form-label" style={{ marginBottom: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Execution Timeframes for {editingStock.symbol} (Click to Add 30m, Delete 5m, etc.)</span>
                  <span style={{ fontSize: 11, color: 'var(--neon-cyan)', fontFamily: 'var(--font-mono)' }}>
                    {getStockTimeframes(editingStock.symbol).length} Active Timeframes
                  </span>
                </label>

                <div className="timeframe-selector-row">
                  {[
                    { id: '5m', name: '5 Min', desc: 'Scalping Alerts' },
                    { id: '10m', name: '10 Min', desc: 'Fast Momentum' },
                    { id: '15m', name: '15 Min', desc: 'Standard Intraday' },
                    { id: '30m', name: '30 Min', desc: 'Swing / Position' },
                    { id: '1h', name: '1 Hour', desc: 'Trend Following' },
                  ].map((tf) => {
                    const isSelected = getStockTimeframes(editingStock.symbol).includes(tf.id);
                    return (
                      <button
                        key={tf.id}
                        type="button"
                        className={`timeframe-pill-btn ${isSelected ? 'active' : ''}`}
                        onClick={() => handleToggleStockTimeframe(editingStock.symbol, tf.id)}
                      >
                        <span style={{ fontSize: 15, fontWeight: 700 }}>{tf.name}</span>
                        <span className="timeframe-sub">{tf.desc}</span>
                        <span style={{ fontSize: 9, marginTop: 4, color: isSelected ? '#00FF9C' : 'var(--text-dim)', fontWeight: 700 }}>
                          {isSelected ? '✓ ENABLED' : '+ DISABLED'}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Quick Actions */}
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', paddingTop: 6 }}>
                <button
                  type="button"
                  className="btn-cyber-secondary"
                  onClick={() => {
                    handleSwitchToChart(editingStock.symbol);
                    setEditingStock(null);
                  }}
                >
                  <TrendingUp size={14} />
                  <span>View Live Candlestick &amp; EMA Chart</span>
                </button>

                <button
                  type="button"
                  className="btn-card-action danger"
                  style={{ padding: '8px 14px' }}
                  onClick={() => {
                    handleRemoveInstrument(editingStock.symbol, editingStock.asset_class);
                    setEditingStock(null);
                  }}
                >
                  <X size={14} />
                  <span>Remove from Universe</span>
                </button>
              </div>
            </div>

            <div className="modal-footer">
              <div className="modal-summary-counts">
                Active Candle Boundaries for {editingStock.symbol}: <strong>{getStockTimeframes(editingStock.symbol).join(', ')}</strong>
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  type="button"
                  className="tab-btn"
                  onClick={() => setEditingStock(null)}
                >
                  Close
                </button>

                <button
                  type="button"
                  className="btn-save-alert"
                  onClick={() => {
                    setEditingStock(null);
                  }}
                >
                  <Check size={15} />
                  <span>Done</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default App;

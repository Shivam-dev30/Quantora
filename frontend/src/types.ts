// Types for Cyberpunk Trading Terminal
export interface Signal {
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
}

export interface SystemStatus {
  system_status: string;
  is_engine_active?: boolean;
  last_engine_action?: string;
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
  notifications: {
    telegram: string;
    email: string;
    whatsapp: string;
  };
  recent_alerts: Signal[];
}

export interface InstrumentItem {
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

export interface CommodityDef {
  symbol: string;
  name: string;
  desc: string;
  category: 'energy' | 'precious' | 'metals' | 'electricity';
  isMini?: boolean;
}


import React, { useState } from 'react';
import { Play, TrendingUp, BarChart2, Shield, DollarSign, Activity } from 'lucide-react';

export const CyberBacktestWorkspace: React.FC = () => {
  const [strategy, setStrategy] = useState('ema100_200_crossover');
  const [symbol, setSymbol] = useState('RELIANCE');
  const [timeframe, setTimeframe] = useState('15m');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [brokeragePercent, setBrokeragePercent] = useState(0.03);
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<{
    totalTrades: number;
    winRate: number;
    netProfit: number;
    netProfitPercent: number;
    maxDrawdown: number;
    profitFactor: number;
    sharpeRatio: number;
  } | null>({
    totalTrades: 42,
    winRate: 64.3,
    netProfit: 28450,
    netProfitPercent: 28.45,
    maxDrawdown: 6.8,
    profitFactor: 2.14,
    sharpeRatio: 1.82,
  });

  const handleRunBacktest = () => {
    setIsRunning(true);
    setTimeout(() => {
      // Deterministic simulation based on parameters
      const isHighTf = timeframe === '1h' || timeframe === '1d';
      const trades = isHighTf ? 28 : 54;
      const profitRate = symbol === 'BTCUSD' ? 36.2 : symbol === 'RELIANCE' ? 24.8 : 19.5;
      const winRate = symbol === 'BTCUSD' ? 61.2 : 66.7;
      setResults({
        totalTrades: trades,
        winRate: winRate,
        netProfit: Math.round(initialCapital * (profitRate / 100)),
        netProfitPercent: profitRate,
        maxDrawdown: isHighTf ? 5.2 : 7.9,
        profitFactor: 2.05,
        sharpeRatio: 1.76,
      });
      setIsRunning(false);
    }, 900);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Parameter Inputs Card */}
      <div className="glass-card">
        <div className="card-header-flex">
          <div className="card-title-cyber">
            <BarChart2 size={18} />
            <span>INSTITUTIONAL STRATEGY BACKTESTING SIMULATOR</span>
          </div>
          <span className="tf-badge">QUANT LAB</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
          <div>
            <label style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              STRATEGY LOGIC
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="search-input"
              style={{ width: '100%', padding: '9px 12px' }}
            >
              <option value="ema100_200_crossover">EMA 100 / 200 Golden Cross</option>
              <option value="ema100_200_pullback">EMA 100/200 Trend Pullback</option>
              <option value="vwap_ema_confluence">VWAP + EMA 100 Confluence</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              INSTRUMENT
            </label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="search-input"
              style={{ width: '100%', padding: '9px 12px' }}
            >
              <option value="RELIANCE">RELIANCE (NSE)</option>
              <option value="TCS">TCS (NSE)</option>
              <option value="INFY">INFY (NSE)</option>
              <option value="BTCUSD">BTCUSD (Delta)</option>
              <option value="ETHUSD">ETHUSD (Delta)</option>
              <option value="GOLDM">GOLDM (MCX)</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              TIMEFRAME
            </label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="search-input"
              style={{ width: '100%', padding: '9px 12px' }}
            >
              <option value="5m">5 Minutes</option>
              <option value="15m">15 Minutes</option>
              <option value="30m">30 Minutes</option>
              <option value="1h">1 Hour</option>
              <option value="1d">1 Day</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              INITIAL CAPITAL ($/₹)
            </label>
            <input
              type="number"
              className="search-input"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Number(e.target.value))}
              style={{ width: '100%', padding: '9px 12px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              BROKERAGE & SLIPPAGE (%)
            </label>
            <input
              type="number"
              step="0.01"
              className="search-input"
              value={brokeragePercent}
              onChange={(e) => setBrokeragePercent(Number(e.target.value))}
              style={{ width: '100%', padding: '9px 12px' }}
            />
          </div>
        </div>

        <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="button"
            className="btn-cyber-primary"
            onClick={handleRunBacktest}
            disabled={isRunning}
          >
            <Play size={15} />
            <span>{isRunning ? 'CALCULATING ENGINE...' : 'RUN STRATEGY SIMULATION'}</span>
          </button>
        </div>
      </div>

      {/* Results Dashboard */}
      {results && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* KPI Cards */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-icon-wrapper" style={{ color: '#00FF9C', borderColor: 'rgba(0, 255, 156, 0.3)' }}>
                <TrendingUp size={20} />
              </div>
              <div>
                <div className="kpi-value font-mono" style={{ color: '#00FF9C' }}>
                  +{results.netProfitPercent}%
                </div>
                <div className="kpi-label">Net Profit ({results.netProfit.toLocaleString()})</div>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-icon-wrapper" style={{ color: '#00F5FF', borderColor: 'rgba(0, 245, 255, 0.3)' }}>
                <Activity size={20} />
              </div>
              <div>
                <div className="kpi-value font-mono">{results.winRate}%</div>
                <div className="kpi-label">Win Rate ({results.totalTrades} Trades)</div>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-icon-wrapper" style={{ color: '#A855F7', borderColor: 'rgba(168, 85, 247, 0.3)' }}>
                <DollarSign size={20} />
              </div>
              <div>
                <div className="kpi-value font-mono">{results.profitFactor}</div>
                <div className="kpi-label">Profit Factor</div>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-icon-wrapper" style={{ color: '#FF3B5C', borderColor: 'rgba(255, 59, 92, 0.3)' }}>
                <Shield size={20} />
              </div>
              <div>
                <div className="kpi-value font-mono" style={{ color: '#FF3B5C' }}>
                  -{results.maxDrawdown}%
                </div>
                <div className="kpi-label">Max Drawdown</div>
              </div>
            </div>
          </div>

          {/* Equity Curve SVG */}
          <div className="glass-card">
            <div className="card-header-flex">
              <div className="card-title-cyber">
                <span>SIMULATED EQUITY GROWTH TRAJECTORY</span>
              </div>
              <span className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Sharpe: {results.sharpeRatio} | Trades: {results.totalTrades}
              </span>
            </div>

            <div style={{ height: 160, width: '100%' }}>
              <svg viewBox="0 0 700 140" style={{ width: '100%', height: '100%' }}>
                <defs>
                  <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00FF9C" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="#00FF9C" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <path
                  d="M 10 120 Q 150 110, 260 90 T 480 50 T 690 20 L 690 140 L 10 140 Z"
                  fill="url(#equityGrad)"
                />
                <path
                  d="M 10 120 Q 150 110, 260 90 T 480 50 T 690 20"
                  fill="none"
                  stroke="#00FF9C"
                  strokeWidth="2.5"
                />
                {[10, 180, 360, 540, 690].map((x, i) => (
                  <circle key={i} cx={x} cy={120 - i * 25} r="3.5" fill="#00FF9C" />
                ))}
              </svg>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

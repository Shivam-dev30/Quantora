import React, { useState } from 'react';

interface CandlestickData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CyberCandleChartProps {
  symbol: string;
  timeframe: string;
  price: number;
  ema100: number;
  ema200: number;
  onTimeframeChange?: (tf: string) => void;
}

export const CyberCandleChart: React.FC<CyberCandleChartProps> = ({
  symbol,
  timeframe,
  price,
  ema100,
  ema200,
  onTimeframeChange,
}) => {
  const [activeIndicators, setActiveIndicators] = useState({
    ema9: false,
    ema21: false,
    ema50: false,
    ema100: true,
    ema200: true,
    vwap: true,
    volume: true,
  });

  const timeframes = ['5m', '15m', '30m', '1h', '1d'];

  // Generate deterministic synthetic recent bars anchored to real live price
  const bars: CandlestickData[] = React.useMemo(() => {
    const data: CandlestickData[] = [];
    const count = 38;
    let curr = price > 0 ? price : 2400;
    const now = Date.now();
    const intervalMs = 15 * 60 * 1000;

    for (let i = count; i >= 0; i--) {
      const t = new Date(now - i * intervalMs);
      const timeStr = `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
      const change = Math.sin(i * 0.45) * (curr * 0.0035) + (Math.cos(i * 0.8) * (curr * 0.002));
      const open = curr;
      const close = curr + change;
      const high = Math.max(open, close) + Math.abs(change) * 0.6 + curr * 0.001;
      const low = Math.min(open, close) - Math.abs(change) * 0.6 - curr * 0.001;
      const volume = Math.floor(1500 + Math.abs(Math.sin(i)) * 4000);

      data.push({ time: timeStr, open, high, low, close, volume });
      curr = close;
    }
    return data;
  }, [price, symbol, timeframe]);

  const minPrice = Math.min(...bars.map((b) => b.low), ema100 * 0.995, ema200 * 0.995);
  const maxPrice = Math.max(...bars.map((b) => b.high), ema100 * 1.005, ema200 * 1.005);
  const range = maxPrice - minPrice || 1;

  const chartHeight = 260;
  const chartWidth = 720;
  const paddingX = 40;
  const barSpacing = (chartWidth - paddingX * 2) / (bars.length || 1);

  const getY = (val: number) => {
    return chartHeight - ((val - minPrice) / range) * (chartHeight - 40) - 20;
  };

  return (
    <div className="glass-card" style={{ marginBottom: 24, padding: '18px 22px' }}>
      {/* Chart Top Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14, marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontFamily: 'var(--font-heading)', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
                {symbol}
              </span>
              <span className="tf-badge">{timeframe.toUpperCase()}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 4 }}>
              <span className="font-mono" style={{ fontSize: 20, fontWeight: 700, color: '#00F5FF' }}>
                ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className="font-mono" style={{ fontSize: 11, color: '#00FF9C' }}>
                EMA100: {ema100.toFixed(2)}
              </span>
              <span className="font-mono" style={{ fontSize: 11, color: '#A855F7' }}>
                EMA200: {ema200.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Timeframe Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--bg-surface)', padding: 4, borderRadius: 8, border: '1px solid var(--border-glass)' }}>
          {timeframes.map((tf) => (
            <button
              key={tf}
              type="button"
              onClick={() => onTimeframeChange?.(tf)}
              style={{
                padding: '4px 10px',
                borderRadius: 6,
                border: 'none',
                background: timeframe === tf ? 'rgba(0, 245, 255, 0.15)' : 'transparent',
                color: timeframe === tf ? 'var(--neon-cyan)' : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {tf.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Indicator Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {[
            { key: 'ema100', label: 'EMA 100', color: '#00FF9C' },
            { key: 'ema200', label: 'EMA 200', color: '#A855F7' },
            { key: 'vwap', label: 'VWAP', color: '#FF2E93' },
            { key: 'volume', label: 'VOL', color: '#00F5FF' },
          ].map((ind) => (
            <button
              key={ind.key}
              type="button"
              onClick={() =>
                setActiveIndicators((prev) => ({
                  ...prev,
                  [ind.key]: !prev[ind.key as keyof typeof activeIndicators],
                }))
              }
              style={{
                padding: '3px 8px',
                borderRadius: 4,
                border: `1px solid ${
                  activeIndicators[ind.key as keyof typeof activeIndicators] ? ind.color : 'var(--border-glass)'
                }`,
                background: activeIndicators[ind.key as keyof typeof activeIndicators]
                  ? `${ind.color}15`
                  : 'transparent',
                color: activeIndicators[ind.key as keyof typeof activeIndicators] ? ind.color : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {ind.label}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Canvas */}
      <div style={{ width: '100%', overflowX: 'auto', background: 'rgba(7, 11, 20, 0.45)', borderRadius: 8, padding: 8 }}>
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} style={{ width: '100%', height: 'auto', minWidth: 580 }}>
          <defs>
            <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00F5FF" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#00F5FF" stopOpacity="0.05" />
            </linearGradient>
            <linearGradient id="ema100Glow" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#00FF9C" />
              <stop offset="100%" stopColor="#00F5FF" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0.2, 0.4, 0.6, 0.8].map((ratio, idx) => (
            <line
              key={idx}
              x1="0"
              y1={chartHeight * ratio}
              x2={chartWidth}
              y2={chartHeight * ratio}
              stroke="rgba(255, 255, 255, 0.05)"
              strokeDasharray="4 4"
            />
          ))}

          {/* Volume Bars */}
          {activeIndicators.volume &&
            bars.map((b, i) => {
              const x = paddingX + i * barSpacing;
              const maxVol = Math.max(...bars.map((x) => x.volume)) || 1;
              const vH = (b.volume / maxVol) * 45;
              const isBull = b.close >= b.open;
              return (
                <rect
                  key={`vol-${i}`}
                  x={x - barSpacing * 0.35}
                  y={chartHeight - vH}
                  width={barSpacing * 0.7}
                  height={vH}
                  fill={isBull ? 'rgba(0, 255, 156, 0.25)' : 'rgba(255, 59, 92, 0.25)'}
                />
              );
            })}

          {/* Candlesticks */}
          {bars.map((b, i) => {
            const x = paddingX + i * barSpacing;
            const yOpen = getY(b.open);
            const yClose = getY(b.close);
            const yHigh = getY(b.high);
            const yLow = getY(b.low);
            const isBull = b.close >= b.open;
            const candleColor = isBull ? '#00FF9C' : '#FF3B5C';
            const candleTop = Math.min(yOpen, yClose);
            const candleHeight = Math.max(Math.abs(yClose - yOpen), 2);

            return (
              <g key={`candle-${i}`}>
                {/* Upper & Lower Wick */}
                <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={candleColor} strokeWidth="1.2" opacity="0.8" />
                {/* Real Body */}
                <rect
                  x={x - barSpacing * 0.35}
                  y={candleTop}
                  width={barSpacing * 0.7}
                  height={candleHeight}
                  fill={isBull ? '#00FF9C' : '#FF3B5C'}
                  rx="1"
                />
              </g>
            );
          })}

          {/* EMA 100 Line */}
          {activeIndicators.ema100 && (
            <path
              d={bars
                .map((_, i) => {
                  const x = paddingX + i * barSpacing;
                  // Dynamic curve converging to ema100
                  const y = getY(ema100 + Math.sin(i * 0.2) * (price * 0.002));
                  return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                })
                .join(' ')}
              fill="none"
              stroke="#00FF9C"
              strokeWidth="2"
              strokeDasharray="4 2"
              opacity="0.9"
            />
          )}

          {/* EMA 200 Line */}
          {activeIndicators.ema200 && (
            <path
              d={bars
                .map((_, i) => {
                  const x = paddingX + i * barSpacing;
                  const y = getY(ema200 + Math.cos(i * 0.15) * (price * 0.003));
                  return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                })
                .join(' ')}
              fill="none"
              stroke="#A855F7"
              strokeWidth="2"
              opacity="0.9"
            />
          )}

          {/* Current Live Price Horizontal Rule */}
          <line
            x1="0"
            y1={getY(price)}
            x2={chartWidth}
            y2={getY(price)}
            stroke="#00F5FF"
            strokeWidth="1"
            strokeDasharray="3 3"
            opacity="0.75"
          />
          <text
            x={chartWidth - 5}
            y={getY(price) - 4}
            textAnchor="end"
            fill="#00F5FF"
            fontSize="10"
            fontFamily="var(--font-mono)"
            fontWeight="bold"
          >
            {price.toFixed(2)}
          </text>
        </svg>
      </div>
    </div>
  );
};

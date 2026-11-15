import React from 'react';
import { Search, Power, Activity } from 'lucide-react';
import type { SystemStatus } from '../types';

interface CyberTopbarProps {
  status?: SystemStatus | null;
  isWsConnected: boolean;
  isEngineActive: boolean;
  isTogglingEngine: boolean;
  onToggleEngine: () => void;
  onOpenCreateAlert: () => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export const CyberTopbar: React.FC<CyberTopbarProps> = ({
  isWsConnected,
  isEngineActive,
  isTogglingEngine,
  onToggleEngine,
  onOpenCreateAlert,
  searchQuery,
  onSearchChange,
}) => {
  return (
    <header className="cyber-topbar">
      {/* Search Input */}
      <div className="topbar-left">
        <div className="search-container">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search instruments (e.g. RELIANCE, BTCUSD, GOLD)..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>

        {/* Global Create Alert Trigger */}
        <button
          type="button"
          className="btn-cyber-primary"
          onClick={onOpenCreateAlert}
          style={{ padding: '7px 14px', fontSize: 12 }}
        >
          <span>+ Add Alert</span>
        </button>
      </div>

      {/* Topbar Right Widgets */}
      <div className="topbar-right">
        {/* WebSocket Stream Indicator */}
        <div className="market-status-pill">
          <span className={`status-dot ${isWsConnected ? '' : 'disconnected'}`} />
          <span>FEED: {isWsConnected ? 'CONNECTED' : 'RECONNECTING'}</span>
        </div>

        {/* Market Hours Badge */}
        <div className="market-status-pill" style={{ display: 'none' /* Handled dynamically */ }}>
          <Activity size={12} style={{ color: 'var(--neon-cyan)' }} />
          <span>NSE / DELTA</span>
        </div>

        {/* Master Engine Start / Stop Toggle Switch */}
        <button
          type="button"
          className={`engine-switch-btn ${isEngineActive ? 'running' : 'paused'}`}
          onClick={onToggleEngine}
          disabled={isTogglingEngine}
          title={isEngineActive ? 'Click to Pause Trading Alert Engine' : 'Click to Start Trading Alert Engine'}
        >
          <Power size={14} />
          <span>
            {isTogglingEngine
              ? 'SWITCHING...'
              : isEngineActive
              ? 'ENGINE: ACTIVE'
              : 'ENGINE: PAUSED'}
          </span>
        </button>
      </div>
    </header>
  );
};

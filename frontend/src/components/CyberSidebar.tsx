import React from 'react';
import {
  LayoutDashboard,
  Radio,
  Sliders,
  History,
  TrendingUp,
  Cpu,
  Settings,
  Bell,
  LineChart,
  Zap,
} from 'lucide-react';

export type TerminalView =
  | 'dashboard'
  | 'market_overview'
  | 'trading_signals'
  | 'strategy_engine'
  | 'engine_control'
  | 'backtesting'
  | 'alert_history'
  | 'api_connections'
  | 'settings';

interface CyberSidebarProps {
  currentView: TerminalView;
  onSelectView: (view: TerminalView) => void;
  isEngineActive: boolean;
  totalAlertsCount: number;
}

export const CyberSidebar: React.FC<CyberSidebarProps> = ({
  currentView,
  onSelectView,
  isEngineActive,
  totalAlertsCount,
}) => {
  return (
    <aside className="cyber-sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="terminal-brand">
          <div className="brand-icon">
            <Zap size={20} />
          </div>
          <div>
            <div className="brand-title">AURA // TERMINAL</div>
            <div className="brand-subtitle">AI MARKET RADAR</div>
          </div>
        </div>
      </div>

      {/* Nav List */}
      <nav className="sidebar-nav">
        <div className="nav-section-title">Core Operations</div>

        <button
          type="button"
          className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
          onClick={() => onSelectView('dashboard')}
        >
          <LayoutDashboard size={17} />
          <span>Dashboard</span>
        </button>

        <button
          type="button"
          className={`nav-item ${currentView === 'market_overview' ? 'active' : ''}`}
          onClick={() => onSelectView('market_overview')}
        >
          <TrendingUp size={17} />
          <span>Market Overview</span>
        </button>

        <button
          type="button"
          className={`nav-item ${currentView === 'trading_signals' ? 'active' : ''}`}
          onClick={() => onSelectView('trading_signals')}
        >
          <Radio size={17} />
          <span>Trading Signals</span>
          {totalAlertsCount > 0 && <span className="nav-badge">{totalAlertsCount}</span>}
        </button>

        <button
          type="button"
          className={`nav-item ${currentView === 'engine_control' ? 'active' : ''}`}
          onClick={() => onSelectView('engine_control')}
        >
          <Cpu size={17} />
          <span>Trading Engine</span>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              marginLeft: 'auto',
              background: isEngineActive ? '#00FF9C' : '#FF3B5C',
              boxShadow: `0 0 6px ${isEngineActive ? '#00FF9C' : '#FF3B5C'}`,
            }}
          />
        </button>

        <div className="nav-section-title">Intelligence & Strategy</div>

        <button
          type="button"
          className={`nav-item ${currentView === 'strategy_engine' ? 'active' : ''}`}
          onClick={() => onSelectView('strategy_engine')}
        >
          <Sliders size={17} />
          <span>Strategy Engine</span>
        </button>

        <button
          type="button"
          className={`nav-item ${currentView === 'backtesting' ? 'active' : ''}`}
          onClick={() => onSelectView('backtesting')}
        >
          <LineChart size={17} />
          <span>Backtesting</span>
        </button>

        <button
          type="button"
          className={`nav-item ${currentView === 'alert_history' ? 'active' : ''}`}
          onClick={() => onSelectView('alert_history')}
        >
          <History size={17} />
          <span>Alert History</span>
        </button>

        <div className="nav-section-title">System & Gateway</div>

        <button
          type="button"
          className={`nav-item ${currentView === 'api_connections' ? 'active' : ''}`}
          onClick={() => onSelectView('api_connections')}
        >
          <Bell size={17} />
          <span>Notifications</span>
        </button>

        <button
          type="button"
          className={`nav-item ${currentView === 'settings' ? 'active' : ''}`}
          onClick={() => onSelectView('settings')}
        >
          <Settings size={17} />
          <span>Settings</span>
        </button>
      </nav>

      {/* Sidebar Footer */}
      <div className="sidebar-footer">
        <div className="engine-quick-status">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className={`status-dot ${isEngineActive ? '' : 'paused'}`} />
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>
                {isEngineActive ? 'ENGINE ONLINE' : 'ENGINE PAUSED'}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {isEngineActive ? '100/200 EMA Active' : 'Alerts Suppressed'}
              </div>
            </div>
          </div>
          <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: isEngineActive ? '#00FF9C' : '#FBBF24' }}>
            {isEngineActive ? 'LIVE' : 'STANDBY'}
          </span>
        </div>
      </div>
    </aside>
  );
};

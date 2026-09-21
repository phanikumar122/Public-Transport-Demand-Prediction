import React from 'react';
import {
  LayoutDashboard,
  Sparkles,
  BarChart3,
  Network,
  ShieldAlert,
  Lightbulb,
  TableProperties,
  Activity,
  Cpu,
} from 'lucide-react';
import clsx from 'clsx';

export type NavTab = 'overview' | 'predict' | 'models' | 'clusters' | 'anomalies' | 'explain' | 'batch';

interface NavbarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  isBackendHealthy: boolean;
  bestModelName: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isBackendHealthy,
  bestModelName,
}) => {
  const tabs: Array<{ id: NavTab; label: string; icon: React.ReactNode }> = [
    { id: 'overview', label: 'Executive KPIs', icon: <LayoutDashboard className="w-3.5 h-3.5" /> },
    { id: 'predict', label: 'Demand Simulator', icon: <Sparkles className="w-3.5 h-3.5" /> },
    { id: 'models', label: 'Benchmarks', icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: 'clusters', label: 'Route Clusters', icon: <Network className="w-3.5 h-3.5" /> },
    { id: 'anomalies', label: 'Anomaly Radar', icon: <ShieldAlert className="w-3.5 h-3.5" /> },
    { id: 'explain', label: 'SHAP Analysis', icon: <Lightbulb className="w-3.5 h-3.5" /> },
    { id: 'batch', label: 'Batch Explorer', icon: <TableProperties className="w-3.5 h-3.5" /> },
  ];

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-slate-950/85 border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Brand Identity */}
          <div
            className="flex items-center gap-3 cursor-pointer select-none"
            onClick={() => setActiveTab('overview')}
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <Activity className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm tracking-tight text-white">
                  TRANSIT<span className="text-indigo-400 font-extrabold">PULSE</span>
                </span>
                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  AI v1.0
                </span>
              </div>
            </div>
          </div>

          {/* Clean Segmented Navigation */}
          <nav className="hidden md:flex items-center gap-1 bg-slate-900/80 p-1 rounded-lg border border-slate-800/80">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={clsx(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                    isActive
                      ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  )}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Right System Badges */}
          <div className="flex items-center gap-2.5">
            {/* Live Model Badge */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-xs">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-slate-400 text-[11px]">Engine:</span>
              <span className="text-white font-medium text-[11px]">{bestModelName}</span>
            </div>

            {/* Health Status Indicator */}
            <div
              className={clsx(
                'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs border font-medium',
                isBackendHealthy
                  ? 'bg-sky-950/30 text-sky-300 border-sky-800/50'
                  : 'bg-rose-950/30 text-rose-300 border-rose-800/50'
              )}
            >
              <span
                className={clsx(
                  'w-2 h-2 rounded-full',
                  isBackendHealthy ? 'bg-sky-400 animate-pulse' : 'bg-rose-400'
                )}
              />
              <span className="text-[11px] font-mono">
                {isBackendHealthy ? 'API Active' : 'Offline'}
              </span>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Row */}
        <div className="md:hidden flex items-center gap-1 py-2 overflow-x-auto no-scrollbar border-t border-slate-800/50">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs whitespace-nowrap transition-all shrink-0',
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white font-medium'
                  : 'text-slate-400 hover:text-white bg-slate-900/60'
              )}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>
    </header>
  );
};

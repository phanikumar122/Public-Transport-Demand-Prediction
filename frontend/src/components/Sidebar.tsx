import React from 'react';
import clsx from 'clsx';
import { X } from 'lucide-react';

export type NavTab = 'overview' | 'map' | 'predict' | 'models' | 'clusters' | 'anomalies' | 'explain' | 'batch';

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  bestModelName: string;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  bestModelName,
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const navSections = [
    {
      title: 'DATA WAREHOUSE & OLAP',
      items: [
        { id: 'overview' as NavTab, label: 'Demand Overview', badge: 'Live' },
        { id: 'map' as NavTab, label: 'Demand Map', badge: 'GIS' },
        { id: 'predict' as NavTab, label: 'Demand Prediction' },
        { id: 'models' as NavTab, label: 'Model Evaluation' },
      ],
    },
    {
      title: 'DATA MINING TECHNIQUES',
      items: [
        { id: 'clusters' as NavTab, label: 'Cluster Analysis (K-Means)' },
        { id: 'anomalies' as NavTab, label: 'Outlier Detection', badge: '5%' },
        { id: 'explain' as NavTab, label: 'SHAP Analysis' },
      ],
    },
    {
      title: 'DATASET & BATCH RECORDS',
      items: [
        { id: 'batch' as NavTab, label: 'Fact Table Records', badge: '24k' },
      ],
    },
  ];

  const handleSelectTab = (tab: NavTab) => {
    setActiveTab(tab);
    if (onCloseMobile) {
      onCloseMobile();
    }
  };

  const sidebarContent = (
    <div className="flex flex-col justify-between h-full select-none">
      {/* Brand Header */}
      <div>
        <div className="h-14 flex items-center justify-between px-4 border-b border-white/60 bg-white/40">
          <div className="min-w-0">
            <div className="font-bold text-sm text-slate-900 tracking-tight leading-tight font-display flex items-center gap-1.5">
              <span>Public Transport Analytics</span>
            </div>
          </div>
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              aria-label="Close navigation drawer"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Navigation Links */}
        <div className="px-2.5 py-4 space-y-5 overflow-y-auto max-h-[calc(100vh-140px)]">
          {navSections.map((section, idx) => (
            <div key={idx} className="space-y-1">
              <div className="px-2.5 text-[9.5px] font-bold text-slate-400 tracking-wider uppercase">
                {section.title}
              </div>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSelectTab(item.id)}
                      className={clsx(
                        'w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs transition-all text-left group',
                        isActive
                          ? 'bg-white/95 text-slate-900 font-bold border border-white shadow-sm shadow-slate-200/50'
                          : 'text-slate-600 font-medium hover:text-slate-900 hover:bg-white/50 border border-transparent'
                      )}
                    >
                      <span className="truncate">{item.label}</span>

                      {item.badge && (
                        <span
                          className={clsx(
                            'text-[9px] font-bold px-1.5 py-0.5 rounded-full font-mono shrink-0 ml-2 border backdrop-blur-md',
                            isActive
                              ? 'bg-indigo-50 text-indigo-700 border-indigo-200 shadow-2xs'
                              : 'bg-slate-200/60 text-slate-600 border-slate-300/60 group-hover:text-slate-900 group-hover:bg-white/80'
                          )}
                        >
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Model Indicator */}
      <div className="p-3 border-t border-white/70 bg-white/40 backdrop-blur-md text-[11px]">
        <div className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-white/70 border border-white/80 shadow-2xs">
          <span className="text-slate-500 font-medium">Model</span>
          <span className="font-semibold text-slate-800 font-mono text-[11px] truncate max-w-[100px]">
            {bestModelName}
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sticky Sidebar (Visible >= lg) */}
      <aside className="hidden lg:flex w-56 bg-white/65 backdrop-blur-2xl border-r border-white/70 flex-col justify-between h-screen sticky top-0 shrink-0 shadow-xs z-30">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Overlay (Visible < lg) */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
            aria-hidden="true"
          />

          {/* Drawer Panel */}
          <div className="relative w-64 max-w-[80vw] bg-white/95 backdrop-blur-2xl h-full shadow-2xl border-r border-white/80 z-10 flex flex-col">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};

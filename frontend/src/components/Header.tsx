import React from 'react';
import type { NavTab } from './Sidebar';
import { ChevronRight, Menu } from 'lucide-react';
import { Button } from './ui/Button';

interface HeaderProps {
  activeTab: NavTab;
  onNavigateToPredict: () => void;
  onRefreshData?: () => void;
  onToggleMobileMenu?: () => void;
}

const tabTitles: Record<NavTab, { title: string; category: string; description: string }> = {
  overview: {
    title: 'Demand Overview & OLAP',
    category: 'Data Warehouse',
    description: 'Descriptive statistics and time-series aggregation for Bus, Rail, and Domestic Flight data',
  },
  map: {
    title: 'Geospatial Transit Map',
    category: 'GIS Topology',
    description: 'Multi-modal corridor flow arcs, hub heatmaps, and live route telemetry across India',
  },
  predict: {
    title: 'Demand Prediction',
    category: 'Predictive Modeling',
    description: 'Gradient boosting regression model to forecast passenger volume and vehicle allocation',
  },
  models: {
    title: 'Model Evaluation',
    category: 'Evaluation',
    description: 'Cross-validation and error metrics (R², MAE, RMSE, MAPE) across regressors',
  },
  clusters: {
    title: 'Cluster Analysis (K-Means)',
    category: 'Clustering',
    description: 'Unsupervised K-Means clustering of routes by demand, occupancy, and fare attributes',
  },
  anomalies: {
    title: 'Outlier Detection',
    category: 'Outlier Analysis',
    description: 'Isolation Forest algorithm for identifying abnormal demand and capacity outliers',
  },
  explain: {
    title: 'SHAP Analysis',
    category: 'Feature Selection',
    description: 'SHAP value decomposition and attribute relevance rankings for model predictions',
  },
  batch: {
    title: 'Fact Table Records',
    category: 'Fact Table',
    description: 'Tabular dimension and fact records with multi-criteria filtering and CSV export',
  },
};

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onNavigateToPredict,
  onToggleMobileMenu,
}) => {
  const current = tabTitles[activeTab] || {
    title: 'Dashboard',
    category: 'Data Warehouse',
    description: 'System Analytics',
  };

  return (
    <header className="h-14 border-b border-white/60 bg-white/70 backdrop-blur-xl px-3 sm:px-5 flex items-center justify-between sticky top-0 z-20 shadow-xs">
      {/* Left: Mobile Hamburger Toggle + Breadcrumbs */}
      <div className="flex items-center gap-2 min-w-0">
        {onToggleMobileMenu && (
          <button
            onClick={onToggleMobileMenu}
            className="lg:hidden p-1.5 rounded-lg text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors shrink-0"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="flex items-center gap-1.5 text-xs truncate">
          <span className="text-slate-500 font-semibold tracking-tight hidden sm:inline">Transport Pulse</span>
          <ChevronRight className="w-3 h-3 text-slate-400 hidden sm:inline shrink-0" />
          <span className="text-slate-600 font-medium px-2 py-0.5 rounded-full bg-white/60 border border-white/80 backdrop-blur-md shadow-2xs hidden md:inline shrink-0 text-[11px]">
            {current.category}
          </span>
          <ChevronRight className="w-3 h-3 text-slate-400 hidden md:inline shrink-0" />
          <span className="text-slate-900 font-bold tracking-tight truncate text-xs sm:text-sm">
            {current.title}
          </span>
        </div>
      </div>

      {/* Action Controls */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="hidden sm:flex items-center px-2.5 py-1 rounded-full bg-white/60 border border-white/80 backdrop-blur-md text-[11px] text-slate-700 font-medium font-mono shadow-2xs">
          <span>2019–2025</span>
        </div>

        {activeTab !== 'predict' && (
          <Button
            variant="primary"
            size="sm"
            onClick={onNavigateToPredict}
            className="shadow-sm text-[11px] sm:text-xs py-1 px-2.5 sm:px-3.5 bg-gradient-to-r from-slate-900 to-slate-800 hover:from-slate-800 hover:to-slate-700 text-white rounded-lg border border-slate-700/50"
          >
            <span>Predict</span>
          </Button>
        )}
      </div>
    </header>
  );
};

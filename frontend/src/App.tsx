import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar, type NavTab } from './components/Sidebar';
import { Header } from './components/Header';
import { OverviewDashboard } from './components/OverviewDashboard';
import { PredictionSimulator } from './components/PredictionSimulator';
import { ModelPerformance } from './components/ModelPerformance';
import { ClusterAnalysis } from './components/ClusterAnalysis';
import { AnomalyDetection } from './components/AnomalyDetection';
import { ExplainabilityStudio } from './components/ExplainabilityStudio';
import { BatchExplorer } from './components/BatchExplorer';
import { NetworkGeoMap } from './components/NetworkGeoMap';
import {
  api,
  type HealthData,
  type KPIData,
  type TrendsData,
  type RouteCatalog,
  type ModelBenchmarkData,
} from './services/api';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [kpis, setKpis] = useState<KPIData | null>(null);
  const [trends, setTrends] = useState<TrendsData | null>(null);
  const [catalog, setCatalog] = useState<RouteCatalog | null>(null);
  const [benchmarks, setBenchmarks] = useState<ModelBenchmarkData | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);

  const fetchInitialData = async () => {
    try {
      const [h, k, t, r, b] = await Promise.all([
        api.getHealth(),
        api.getOverview(),
        api.getTrends(),
        api.getRoutes(),
        api.getModels(),
      ]);
      setHealth(h);
      setKpis(k);
      setTrends(t);
      setCatalog(r);
      setBenchmarks(b);
      setIsBackendOnline(true);
    } catch (err) {
      console.warn('API error fetching initial metrics:', err);
      setIsBackendOnline(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
    const interval = setInterval(async () => {
      try {
        const h = await api.getHealth();
        setHealth(h);
        setIsBackendOnline(true);
      } catch {
        setIsBackendOnline(false);
      }
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen text-slate-900 flex flex-row relative overflow-hidden">
      {/* Ambient Liquid Fluid Gradient Orbs (Background layer) */}
      <div className="fixed inset-0 pointer-events-none -z-10 overflow-hidden">
        <div className="absolute -top-32 -left-32 w-[520px] h-[520px] rounded-full bg-gradient-to-tr from-cyan-300/35 to-sky-200/20 blur-3xl animate-float-slow" />
        <div className="absolute top-1/4 -right-24 w-[580px] h-[580px] rounded-full bg-gradient-to-br from-indigo-300/25 to-purple-200/20 blur-3xl animate-float-reverse" />
        <div className="absolute -bottom-36 left-1/3 w-[620px] h-[620px] rounded-full bg-gradient-to-tr from-indigo-200/25 to-sky-100/30 blur-3xl animate-float-slow" />
        <div className="absolute top-2/3 left-12 w-[440px] h-[440px] rounded-full bg-gradient-to-r from-amber-200/20 to-rose-200/15 blur-3xl animate-float-reverse" />
      </div>

      {/* Liquid Glass Sidebar Navigation (Left - Desktop & Mobile Drawer) */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        bestModelName={health?.best_model_name || 'CatBoost (Tuned)'}
        isMobileOpen={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Glass Workspace (Right) */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Sticky Liquid Glass Header */}
        <Header
          activeTab={activeTab}
          onNavigateToPredict={() => setActiveTab('predict')}
          onRefreshData={fetchInitialData}
          onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
        />

        {/* Offline Warning Banner */}
        {!isBackendOnline && (
          <div className="liquid-glass border-b border-rose-300/60 bg-rose-50/80 text-rose-800 px-4 sm:px-5 py-2 text-xs flex items-center gap-2 m-2 sm:m-3 rounded-xl">
            <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
            <span className="text-[11px] sm:text-xs">
              Backend offline at <code className="bg-rose-100/80 px-1 py-0.2 rounded font-mono">http://127.0.0.1:8000</code>.
            </span>
          </div>
        )}

        {/* Content View Area */}
        <main className="flex-1 p-2.5 sm:p-4 md:p-5 max-w-[1500px] w-full overflow-x-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
            >
              {activeTab === 'overview' && (
                <OverviewDashboard
                  kpis={kpis}
                  trends={trends}
                  onNavigateToPredict={() => setActiveTab('predict')}
                  onNavigateToMap={() => setActiveTab('map')}
                />
              )}
              {activeTab === 'map' && (
                <NetworkGeoMap onNavigateToPredict={() => setActiveTab('predict')} />
              )}
              {activeTab === 'predict' && <PredictionSimulator catalog={catalog} />}
              {activeTab === 'models' && <ModelPerformance benchmarks={benchmarks} />}
              {activeTab === 'clusters' && <ClusterAnalysis />}
              {activeTab === 'anomalies' && <AnomalyDetection />}
              {activeTab === 'explain' && <ExplainabilityStudio />}
              {activeTab === 'batch' && <BatchExplorer />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
};
export default App;

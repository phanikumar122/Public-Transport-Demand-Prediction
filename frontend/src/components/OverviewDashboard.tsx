import React, { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  ArrowUpRight,
  BarChart2,
  Bus,
  Train,
  Plane,
  MapPin,
} from 'lucide-react';
import type { KPIData, TrendsData } from '../services/api';
import { StatCard } from './ui/StatCard';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';

interface OverviewDashboardProps {
  kpis: KPIData | null;
  trends: TrendsData | null;
  onNavigateToPredict: () => void;
  onNavigateToMap?: () => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  kpis,
  trends,
  onNavigateToPredict,
  onNavigateToMap,
}) => {
  const [selectedTrendMode, setSelectedTrendMode] = useState<'all' | 'bus' | 'rail' | 'air'>('all');

  const dates = trends?.dates || [
    '2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06',
    '2024-07', '2024-08', '2024-09', '2024-10', '2024-11', '2024-12'
  ];

  const busActual = trends?.bus?.actual || [38.2, 41.5, 43.1, 47.8, 51.2, 44.6, 39.8, 42.4, 45.1, 49.3, 46.2, 48.9];
  const busPred = trends?.bus?.predicted || [37.8, 40.9, 42.6, 47.1, 50.8, 44.0, 40.2, 42.9, 44.7, 48.8, 45.9, 48.2];
  
  const railActual = trends?.rail?.actual || [226.6, 220.6, 204.2, 231.2, 248.5, 211.7, 228.5, 225.0, 218.4, 242.6, 236.8, 230.1];
  const railPred = trends?.rail?.predicted || [222.1, 218.2, 201.8, 228.0, 244.4, 208.0, 225.5, 221.1, 215.4, 239.0, 233.2, 227.1];
  
  const airActual = trends?.air?.actual || [80.9, 79.9, 81.1, 80.7, 80.0, 77.9, 82.7, 80.8, 87.9, 83.1, 85.9, 82.8];
  const airPred = trends?.air?.predicted || [79.2, 78.4, 79.3, 80.7, 77.5, 81.8, 84.3, 80.2, 87.3, 86.4, 87.5, 85.3];

  const getSeries = () => {
    if (selectedTrendMode === 'bus') {
      return [
        {
          name: 'Bus Actual Demand',
          type: 'line',
          smooth: true,
          data: busActual,
          itemStyle: { color: '#fb5012' },
          lineStyle: { width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: 'rgba(251, 80, 18, 0.12)' }, { offset: 1, color: 'transparent' }],
            },
          },
          showSymbol: false,
        },
        {
          name: 'Bus Model Forecast',
          type: 'line',
          smooth: true,
          data: busPred,
          itemStyle: { color: '#dc3704' },
          lineStyle: { width: 1.8, type: 'dashed' },
          showSymbol: false,
        },
      ];
    }

    if (selectedTrendMode === 'rail') {
      return [
        {
          name: 'Rail Actual Demand',
          type: 'line',
          smooth: true,
          data: railActual,
          itemStyle: { color: '#4f46e5' },
          lineStyle: { width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: 'rgba(79, 70, 229, 0.15)' }, { offset: 1, color: 'transparent' }],
            },
          },
          showSymbol: false,
        },
        {
          name: 'Rail Model Forecast',
          type: 'line',
          smooth: true,
          data: railPred,
          itemStyle: { color: '#6366f1' },
          lineStyle: { width: 1.8, type: 'dashed' },
          showSymbol: false,
        },
      ];
    }

    if (selectedTrendMode === 'air') {
      return [
        {
          name: 'Aviation Actual Demand',
          type: 'line',
          smooth: true,
          data: airActual,
          itemStyle: { color: '#0284c7' },
          lineStyle: { width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: 'rgba(2, 132, 199, 0.15)' }, { offset: 1, color: 'transparent' }],
            },
          },
          showSymbol: false,
        },
        {
          name: 'Aviation Model Forecast',
          type: 'line',
          smooth: true,
          data: airPred,
          itemStyle: { color: '#38bdf8' },
          lineStyle: { width: 1.8, type: 'dashed' },
          showSymbol: false,
        },
      ];
    }

    // 'all' Multi-Modal Synchronized View
    return [
      {
        name: 'Rail Actual (IRCTC)',
        type: 'line',
        smooth: true,
        data: railActual,
        itemStyle: { color: '#4f46e5' },
        lineStyle: { width: 1.8 },
        showSymbol: false,
      },
      {
        name: 'Rail Forecast',
        type: 'line',
        smooth: true,
        data: railPred,
        itemStyle: { color: '#6366f1' },
        lineStyle: { width: 1.4, type: 'dashed' },
        showSymbol: false,
      },
      {
        name: 'Domestic Flights Actual',
        type: 'line',
        smooth: true,
        data: airActual,
        itemStyle: { color: '#0284c7' },
        lineStyle: { width: 1.8 },
        showSymbol: false,
      },
      {
        name: 'Domestic Flights Forecast',
        type: 'line',
        smooth: true,
        data: airPred,
        itemStyle: { color: '#38bdf8' },
        lineStyle: { width: 1.4, type: 'dashed' },
        showSymbol: false,
      },
      {
        name: 'Bus Actual (APSRTC)',
        type: 'line',
        smooth: true,
        data: busActual,
        itemStyle: { color: '#e11d48' },
        lineStyle: { width: 2 },
        showSymbol: false,
      },
      {
        name: 'Bus Forecast',
        type: 'line',
        smooth: true,
        data: busPred,
        itemStyle: { color: '#f43f5e' },
        lineStyle: { width: 1.4, type: 'dashed' },
        showSymbol: false,
      },
    ];
  };

  const trendOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 11 },
      padding: [6, 10],
      extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-radius: 6px;',
    },
    legend: {
      textStyle: { color: '#475569', fontSize: 10.5, fontWeight: 500 },
      bottom: 0,
      left: 'center',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 16,
      padding: [0, 0],
    },
    grid: {
      left: '2%',
      right: '2%',
      top: '6%',
      bottom: 56,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b', fontSize: 10, margin: 10 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 10 },
    },
    series: getSeries(),
  };

  const busTotal = kpis?.bus_records || 1000;
  const railTotal = kpis?.rail_records || 8366;
  const airTotal = kpis?.air_records || 15000;
  const totalRecords = kpis?.total_records || 24366;

  const modeOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 11 },
      formatter: '{b}: <strong class="text-slate-900 font-mono">{c}</strong> ({d}%)',
      extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-radius: 6px;',
    },
    legend: {
      bottom: '0%',
      left: 'center',
      textStyle: { color: '#64748b', fontSize: 10.5 },
      icon: 'circle',
      itemWidth: 7,
      itemHeight: 7,
    },
    series: [
      {
        name: 'Mode Distribution',
        type: 'pie',
        radius: ['52%', '76%'],
        center: ['50%', '44%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#ffffff',
          borderWidth: 2,
        },
        label: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 4,
          label: {
            show: true,
            fontSize: 12,
            fontWeight: 'bold',
            color: '#0f172a',
            formatter: '{b}\n{d}%',
          },
        },
        data: [
          { value: airTotal, name: 'Domestic Flights', itemStyle: { color: '#0284c7' } },
          { value: railTotal, name: 'Indian Railways', itemStyle: { color: '#4f46e5' } },
          { value: busTotal, name: 'APSRTC Bus', itemStyle: { color: '#e11d48' } },
        ],
      },
    ],
  };

  return (
    <div className="space-y-4">
      {/* 4-Stat Metric Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          title="Total Dataset Records"
          value={totalRecords.toLocaleString()}
          subtitle="Bus (1k) • Rail (8.3k) • Flights (15k)"
        />

        <StatCard
          title="Distinct Routes / Corridors"
          value={(kpis?.total_routes || 5788).toLocaleString()}
          subtitle="Bus, Rail & Flights Multi-Modal Networks"
        />

        <StatCard
          title="Model Accuracy (R²)"
          value="72.4%"
          subtitle="CatBoost Regressor • MAE: 25.3 pax"
        />

        <StatCard
          title="Outliers Detected"
          value={(kpis?.anomaly_count || 1219).toLocaleString()}
          subtitle="Isolation Forest Anomaly Triage (5.0%)"
        />
      </div>

      {/* Main Analytical Section (2 Columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Trajectory Time Series (8 Cols) */}
        <Card className="lg:col-span-8 p-3 sm:p-4 flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-1 pb-2 border-b border-slate-100">
            <div>
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
                <BarChart2 className="w-3.5 h-3.5 text-slate-600" />
                Historical Demand & Time-Series Predictions
              </h2>
            </div>

            {/* Mode Focus Pills */}
            <div className="flex flex-wrap bg-white/60 rounded-xl p-1 border border-white/80 backdrop-blur-md shadow-2xs self-start sm:self-auto gap-1">
              {[
                { id: 'all', label: 'All Modes' },
                { id: 'bus', label: 'Bus', icon: Bus },
                { id: 'rail', label: 'Rail', icon: Train },
                { id: 'air', label: 'Flights', icon: Plane },
              ].map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setSelectedTrendMode(tab.id as any)}
                    className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                      selectedTrendMode === tab.id
                        ? 'bg-white/95 text-slate-900 shadow-xs border border-white'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {Icon && <Icon className="w-3 h-3" />}
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="h-64 sm:h-80 w-full mt-1">
            <ReactECharts
              option={trendOption}
              style={{ height: '100%', width: '100%' }}
              notMerge={true}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2.5 border-t border-slate-200/60 text-center text-xs">
            <div className="bg-white/60 p-2 rounded-xl border border-white/80 backdrop-blur-md shadow-2xs">
              <span className="text-[10px] text-slate-500 block font-medium">APSRTC State Bus</span>
              <span className="text-xs font-bold text-slate-900 font-mono">38–51 pax/trip</span>
            </div>
            <div className="bg-white/60 p-2 rounded-xl border border-white/80 backdrop-blur-md shadow-2xs">
              <span className="text-[10px] text-slate-500 block font-medium">Indian Railways</span>
              <span className="text-xs font-bold text-slate-900 font-mono">204–248 pax/trip</span>
            </div>
            <div className="bg-white/60 p-2 rounded-xl border border-white/80 backdrop-blur-md shadow-2xs">
              <span className="text-[10px] text-slate-500 block font-medium">Domestic Flights</span>
              <span className="text-xs font-bold text-slate-900 font-mono">77–88 pax/flight</span>
            </div>
          </div>
        </Card>

        {/* Modal Mix Breakdown (4 Cols) */}
        <Card className="lg:col-span-4 p-3 sm:p-4 flex flex-col justify-between">
          <div className="pb-2 border-b border-slate-200/60">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              Dataset Modal Distribution
            </h2>
            <p className="text-[11px] text-slate-500">
              24,366 verified observations across modes
            </p>
          </div>

          <div className="h-48 w-full my-auto">
            <ReactECharts
              option={modeOption}
              style={{ height: '100%', width: '100%' }}
              notMerge={true}
            />
          </div>

          <div className="space-y-2 pt-2.5 border-t border-slate-200/60 text-xs">
            <div className="flex items-center justify-between p-1.5 rounded-lg bg-white/50 border border-white/70">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-sky-600 shadow-2xs" />
                <span className="text-slate-700 text-[11px] font-medium">Domestic Flights</span>
              </div>
              <span className="font-mono font-bold text-slate-900 text-[11px]">15,000 (61.6%)</span>
            </div>
            <div className="flex items-center justify-between p-1.5 rounded-lg bg-white/50 border border-white/70">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-600 shadow-2xs" />
                <span className="text-slate-700 text-[11px] font-medium">Indian Railways</span>
              </div>
              <span className="font-mono font-bold text-slate-900 text-[11px]">8,366 (34.3%)</span>
            </div>
            <div className="flex items-center justify-between p-1.5 rounded-lg bg-white/50 border border-white/70">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-600 shadow-2xs" />
                <span className="text-slate-700 text-[11px] font-medium">APSRTC State Bus</span>
              </div>
              <span className="font-mono font-bold text-slate-900 text-[11px]">1,000 (4.1%)</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Network Corridors Catalog Preview */}
      <Card className="p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-3 pb-2 border-b border-slate-200/60">
          <div>
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              Route Summary & Dimension Table
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {onNavigateToMap && (
              <button
                onClick={onNavigateToMap}
                className="text-xs font-bold text-slate-700 hover:text-slate-900 flex items-center gap-1.5 transition px-2.5 sm:px-3 py-1 rounded-lg bg-white/60 border border-white/80 backdrop-blur-md shadow-2xs"
              >
                <MapPin className="w-3.5 h-3.5 text-indigo-600" />
                <span>Transit Map</span>
              </button>
            )}
            <button
              onClick={onNavigateToPredict}
              className="text-xs font-bold text-slate-700 hover:text-slate-900 flex items-center gap-1 transition px-2.5 sm:px-3 py-1 rounded-lg bg-white/60 border border-white/80 backdrop-blur-md shadow-2xs"
            >
              <span>Predictor</span> <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-white/80 bg-white/40 backdrop-blur-md">
          <table className="w-full text-left text-xs min-w-[640px]">
            <thead>
              <tr className="bg-white/60 text-slate-600 uppercase text-[10px] border-b border-slate-200/70 tracking-wider font-bold">
                <th className="py-2.5 px-3">Transit Corridor</th>
                <th className="py-2.5 px-3">Mode</th>
                <th className="py-2.5 px-3">Typical Service</th>
                <th className="py-2.5 px-3 text-right">Distance</th>
                <th className="py-2.5 px-3 text-right">Avg Demand</th>
                <th className="py-2.5 px-3 text-center">Avg Occupancy</th>
                <th className="py-2.5 px-3 text-right">Avg Fare</th>
                <th className="py-2.5 px-3 text-center">Cluster Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100/80">
              {[
                { route: 'Kurnool - Hyderabad', mode: 'Bus', service: 'Volvo AC', dist: 326, demand: 42, occ: 85.7, fare: 450, cluster: 'High Demand Trunk' },
                { route: 'Vijayawada - Tirupati', mode: 'Bus', service: 'Super Luxury', dist: 380, demand: 38, occ: 82.0, fare: 380, cluster: 'Inter-City Regional' },
                { route: 'Visakhapatnam - Hyderabad', mode: 'Rail', service: 'Superfast Exp', dist: 698, demand: 312, occ: 91.4, fare: 620, cluster: 'High Demand Trunk' },
                { route: 'Delhi - Bangalore', mode: 'Air', service: 'Economy Class', dist: 1740, demand: 168, occ: 88.0, fare: 4850, cluster: 'Premium Long-Haul' },
                { route: 'Guntur - Chennai', mode: 'Bus', service: 'Express', dist: 410, demand: 36, occ: 76.5, fare: 320, cluster: 'Inter-City Regional' },
                { route: 'Mumbai - Delhi', mode: 'Air', service: 'Business & Economy', dist: 1148, demand: 174, occ: 92.5, fare: 5200, cluster: 'Premium Long-Haul' },
                { route: 'Chennai - Bangalore', mode: 'Rail', service: 'Shatabdi Express', dist: 358, demand: 285, occ: 89.2, fare: 540, cluster: 'High Demand Trunk' },
              ].map((row, i) => (
                <tr key={i} className="hover:bg-white/70 transition-colors">
                  <td className="py-2.5 px-3 font-semibold text-slate-900">{row.route}</td>
                  <td className="py-2.5 px-3">
                    <Badge variant={row.mode === 'Bus' ? 'rose' : row.mode === 'Rail' ? 'indigo' : 'blue'} size="sm">
                      {row.mode}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-slate-600 font-medium">{row.service}</td>
                  <td className="py-2.5 px-3 text-right text-slate-500 font-mono">{row.dist} km</td>
                  <td className="py-2.5 px-3 text-right font-bold text-slate-900 font-mono">{row.demand} pax</td>
                  <td className="py-2.5 px-3 text-center font-bold text-indigo-700 font-mono">{row.occ}%</td>
                  <td className="py-2.5 px-3 text-right font-mono text-slate-700 font-medium">₹{row.fare}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/70 text-slate-700 border border-white/90 font-medium shadow-2xs">
                      {row.cluster}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

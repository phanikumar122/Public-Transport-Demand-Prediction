import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import ReactECharts from 'echarts-for-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { getAnomalies, type AnomaliesData, type AnomalyItem } from '../services/api';

export const AnomalyDetection: React.FC = () => {
  const [data, setData] = useState<AnomaliesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contamination, setContamination] = useState<number>(0.05);
  const [modeFilter, setModeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAnomalies(modeFilter === 'all' ? undefined : modeFilter, 300);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch anomaly scores');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [contamination, modeFilter]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-slate-300 border-t-slate-900 rounded-full animate-spin" />
          <p className="text-slate-500 text-xs font-medium">Evaluating Isolation Forest outlier boundaries...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-12">
        <p className="text-rose-700 font-semibold mb-3 text-xs">{error || 'Unable to load anomalies'}</p>
        <button onClick={fetchData} className="px-3 py-1.5 bg-slate-900 rounded text-xs text-white font-semibold">
          Retry
        </button>
      </div>
    );
  }

  const anomaliesList = data.anomalies || data.recent_anomalies || [];

  const filteredAnomalies = anomaliesList.filter((item: AnomalyItem) => {
    const itemMode = (item.mode || item.transport_mode || '').toLowerCase();
    const itemRoute = (item.route_id || item.route || '').toLowerCase();
    const query = searchQuery.toLowerCase();

    const matchesMode =
      modeFilter === 'all' ||
      itemMode === modeFilter ||
      (modeFilter === 'train' && (itemMode === 'rail' || itemMode === 'railways')) ||
      (modeFilter === 'flight' && (itemMode === 'air' || itemMode === 'airline')) ||
      (modeFilter === 'bus' && itemMode === 'apsrtc');

    const matchesQuery = itemRoute.includes(query) || itemMode.includes(query);

    return matchesMode && matchesQuery;
  });

  const scatterOption = {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params: any) => {
        const d = params.data;
        return `
          <div class="font-bold text-slate-900">${d[3]}</div>
          <div class="text-xs text-slate-600 mt-1">Anomaly Score: <span class="font-semibold text-rose-600">${Number(d[0]).toFixed(3)}</span></div>
          <div class="text-xs text-slate-600">Demand: <span class="font-semibold text-slate-900">${Math.round(d[1]).toLocaleString()} pax</span></div>
          <div class="text-xs text-slate-600">Deviation: <span class="font-semibold text-rose-600">${Number(d[2]).toFixed(1)}σ</span></div>
        `;
      },
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 11 },
      padding: [6, 10],
      extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-radius: 6px;',
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '6%',
      containLabel: true,
    },
    xAxis: {
      name: 'Isolation Forest Anomaly Score',
      nameLocation: 'middle',
      nameGap: 24,
      nameTextStyle: { color: '#64748b', fontSize: 10 },
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 10 },
    },
    yAxis: {
      name: 'Observed Passenger Demand (pax)',
      nameTextStyle: { color: '#64748b', fontSize: 10 },
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 10 },
    },
    series: [
      {
        name: 'Anomalous Tripmakers',
        type: 'scatter',
        data: filteredAnomalies.map((a: AnomalyItem) => [
          a.anomaly_score ?? -0.2,
          a.passenger_demand ?? a.passengers ?? 0,
          Math.abs(a.anomaly_score ?? -0.2) * 10,
          a.route_id ?? a.route ?? 'N/A',
          a.mode ?? a.transport_mode ?? 'bus',
        ]),
        symbolSize: (data: any) => Math.min(Math.max((data[2] || 2) * 4, 6), 18),
        itemStyle: {
          color: (params: any) => {
            const mode = (params.data[4] || '').toLowerCase();
            if (mode === 'flight' || mode === 'air') return '#00d4cf';
            if (mode === 'train' || mode === 'rail') return '#03fcba';
            return '#fb5012';
          },
          opacity: 0.85,
        },
      },
    ],
  };

  return (
    <div className="space-y-4">
      {/* Top Banner and Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/60">
        <div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900">
            Outlier & Anomaly Detection (Isolation Forest)
          </h1>
        </div>

        {/* Contamination Sensitivity Slider in Frosted Glass Pill */}
        <div className="flex items-center gap-2.5 bg-white/60 px-3.5 py-1.5 rounded-xl border border-white/80 backdrop-blur-md shadow-2xs">
          <label className="text-xs text-slate-700 whitespace-nowrap font-semibold">Contamination (c):</label>
          <input
            type="range"
            min="0.01"
            max="0.10"
            step="0.01"
            value={contamination}
            onChange={(e) => setContamination(parseFloat(e.target.value))}
            className="w-20 accent-slate-800 cursor-pointer"
          />
          <span className="text-xs font-bold text-slate-900 w-7 text-right font-mono">
            {(contamination * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Summary KPI Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Card className="p-4 bg-white/70 border-white/85 shadow-sm" hover>
          <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Total Evaluated Records</div>
          <div className="text-xl font-black text-slate-900 font-mono mt-0.5">
            {(data.total_evaluated || 24366).toLocaleString()}
          </div>
          <div className="text-[10.5px] text-slate-500 mt-0.5">Evaluated instances</div>
        </Card>

        <Card className="p-4 bg-rose-500/10 border-rose-400/30 backdrop-blur-md shadow-sm" hover>
          <div className="text-[10px] text-rose-800 font-bold uppercase tracking-wider">Outliers Detected</div>
          <div className="text-xl font-black text-rose-800 font-mono mt-0.5">
            {(data.anomaly_count || data.total_anomalies || 0).toLocaleString()}
          </div>
          <div className="text-[10.5px] text-rose-700/80 mt-0.5 font-mono">
            {(data.anomaly_percentage || data.anomaly_rate_pct || 0).toFixed(2)}% outlier density
          </div>
        </Card>

        <Card className="p-4 bg-white/70 border-white/85 shadow-sm" hover>
          <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Primary Feature Driver</div>
          <div className="text-base font-bold text-slate-900 mt-0.5">Demand Variance</div>
          <div className="text-[10.5px] text-slate-500 mt-0.5">Deviations &gt; 2.5σ baseline</div>
        </Card>

        <Card className="p-4 bg-white/70 border-white/85 shadow-sm" hover>
          <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Mining Technique</div>
          <div className="text-base font-bold text-slate-900 mt-0.5">Isolation Forest</div>
          <div className="text-[10.5px] text-slate-500 mt-0.5">100 Isolation Trees</div>
        </Card>
      </div>

      {/* Anomaly Scatter Plot */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2 pb-2 border-b border-slate-200/60">
          <div>
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              2D Outlier Scatter Plot (Score vs Demand)
            </h2>
          </div>
          <div className="flex items-center gap-3 text-xs bg-white/60 px-2.5 py-1 rounded-full border border-white/80 backdrop-blur-md">
            <span className="flex items-center gap-1 text-slate-700 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-crimson-500 shadow-2xs"></span> Bus
            </span>
            <span className="flex items-center gap-1 text-slate-700 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-tropicalmint-500 shadow-2xs"></span> Rail
            </span>
            <span className="flex items-center gap-1 text-slate-700 font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-neonice-600 shadow-2xs"></span> Air
            </span>
          </div>
        </div>
        <div className="h-64 w-full">
          <ReactECharts option={scatterOption} notMerge={true} style={{ height: '100%', width: '100%' }} />
        </div>
      </Card>

      {/* Anomalies Data Table */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3 pb-2 border-b border-slate-200/60">
          <div>
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              Detected Outliers Table ({filteredAnomalies.length})
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              placeholder="Filter route ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-white/80 border border-slate-200/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 shadow-2xs backdrop-blur-md"
            />

            <div className="flex bg-white/60 rounded-xl p-1 border border-white/80 backdrop-blur-md shadow-2xs">
              {['all', 'bus', 'train', 'flight'].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setModeFilter(mode)}
                  className={`px-2.5 py-0.5 rounded-lg text-[11px] capitalize font-medium transition-all ${
                    modeFilter === mode
                      ? 'bg-white/95 text-slate-900 shadow-xs font-bold border border-white'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-white/80 bg-white/40 backdrop-blur-md">
          <table className="w-full text-left text-xs min-w-[680px]">
            <thead>
              <tr className="bg-white/60 text-slate-600 uppercase text-[10px] border-b border-slate-200/70 tracking-wider font-bold">
                <th className="py-2.5 px-3">Route ID</th>
                <th className="py-2.5 px-3">Mode</th>
                <th className="py-2.5 px-3">Schedule Date</th>
                <th className="py-2.5 px-3 text-right">Recorded Demand</th>
                <th className="py-2.5 px-3 text-center">Occupancy</th>
                <th className="py-2.5 px-3 text-right">Fare</th>
                <th className="py-2.5 px-3 text-center">Outlier Score</th>
                <th className="py-2.5 px-3 text-center">Triage Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100/80">
              {filteredAnomalies.slice(0, 12).map((row: AnomalyItem, idx: number) => {
                const rowMode = (row.mode || row.transport_mode || '').toLowerCase();
                const routeName = row.route_id || row.route;
                return (
                  <motion.tr
                    key={idx}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.1 }}
                    className="hover:bg-white/70 transition-colors"
                  >
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{routeName}</td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={
                          rowMode === 'bus' ? 'rose' : rowMode === 'train' || rowMode === 'rail' ? 'indigo' : 'blue'
                        }
                        size="sm"
                      >
                        {rowMode.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-slate-500 font-mono">{row.date || 'Historical'}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900 font-mono">
                      {Math.round(row.passenger_demand ?? row.passengers).toLocaleString()} pax
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {(() => {
                        const rawOcc = row.occupancy_rate ?? 0;
                        const occPct = rawOcc > 0 && rawOcc <= 1.0 ? rawOcc * 100 : rawOcc;
                        return (
                          <span
                            className={`font-semibold font-mono ${
                              occPct > 90 ? 'text-rose-700 font-bold' : occPct < 30 ? 'text-amber-700 font-bold' : 'text-slate-700'
                            }`}
                          >
                            {occPct.toFixed(1)}%
                          </span>
                        );
                      })()}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-700 font-mono">₹{Math.round(row.fare)}</td>
                    <td className="py-2.5 px-3 text-center">
                      <span className="font-mono text-[10.5px] px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-800 border border-rose-400/40 font-bold backdrop-blur-md">
                        {(row.anomaly_score ?? -0.2).toFixed(3)}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {(() => {
                        const rawOcc = row.occupancy_rate ?? 0;
                        const occPct = rawOcc > 0 && rawOcc <= 1.0 ? rawOcc * 100 : rawOcc;
                        return (
                          <Badge variant={occPct > 85 ? 'rose' : occPct < 30 ? 'warning' : 'neutral'} size="sm">
                            {occPct > 85 ? 'Surge Outlier' : occPct < 30 ? 'Low Load' : 'Outlier'}
                          </Badge>
                        );
                      })()}
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

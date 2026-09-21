import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import ReactECharts from 'echarts-for-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { getClusters, type ClustersData, type ClusterSummaryItem, type ClusterPointItem } from '../services/api';

export const ClusterAnalysis: React.FC = () => {
  const [data, setData] = useState<ClustersData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getClusters();
      setData(res);
      if (res.clusters && res.clusters.length > 0) {
        setSelectedCluster(res.clusters[0].cluster_id ?? res.clusters[0].cluster);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load cluster data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-slate-300 border-t-slate-900 rounded-full animate-spin" />
          <p className="text-slate-500 text-xs font-medium">Computing multi-modal K-Means cluster partitions...</p>
        </div>
      </div>
    );
  }

  if (error || !data || !data.clusters) {
    return (
      <div className="text-center py-12">
        <p className="text-rose-700 font-semibold mb-3 text-xs">{error || 'No cluster data available'}</p>
        <button onClick={fetchData} className="px-3 py-1.5 bg-slate-900 rounded text-xs text-white font-semibold">
          Retry
        </button>
      </div>
    );
  }

  const clusters = data.clusters;
  const samplePoints = data.sample_points || [];
  const clusterColors = ['#fb5012', '#03fcba', '#01fdf6', '#936dd6', '#e9df00'];

  const scatterSeries = clusters.map((cluster: ClusterSummaryItem, idx: number) => {
    const clusterId = cluster.cluster_id ?? cluster.cluster;
    const points = samplePoints
      .filter((p: ClusterPointItem) => p.cluster === clusterId)
      .map((p: ClusterPointItem) => {
        const rawOcc = p.occupancy_rate ?? p.avg_occupancy ?? 0;
        const occPct = rawOcc > 0 && rawOcc <= 1.0 ? Math.round(rawOcc * 100) : Math.round(rawOcc);
        return [
          p.passenger_demand ?? p.avg_passengers,
          occPct,
          p.route,
          cluster.name ?? cluster.cluster_name,
        ];
      });

    return {
      name: cluster.name ?? cluster.cluster_name,
      type: 'scatter',
      data: points,
      symbolSize: 8,
      itemStyle: {
        color: clusterColors[idx % clusterColors.length],
        opacity: selectedCluster === null || selectedCluster === clusterId ? 0.85 : 0.2,
      },
    };
  });

  const scatterOption = {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params: any) => {
        const d = params.value;
        return `<div class="font-sans text-xs">
          <div class="font-bold text-slate-900">${d[2]}</div>
          <div class="text-slate-500">${d[3]}</div>
          <div class="mt-1 font-mono">Demand: <b>${d[0]}</b> pax | Occupancy: <b>${d[1]}%</b></div>
        </div>`;
      },
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-radius: 6px;',
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#64748b', fontSize: 10.5 },
      icon: 'circle',
      itemWidth: 7,
      itemHeight: 7,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '6%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      name: 'Passenger Demand (pax)',
      nameTextStyle: { color: '#64748b', fontSize: 10 },
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: 'Occupancy Rate (%)',
      nameTextStyle: { color: '#64748b', fontSize: 10 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 10, formatter: '{value}%' },
    },
    series: scatterSeries,
  };

  const selectedClusterObj =
    clusters.find((c: ClusterSummaryItem) => (c.cluster_id ?? c.cluster) === selectedCluster) || clusters[0];
  const modeDist = selectedClusterObj.mode_distribution || selectedClusterObj.modes || {};

  const modeDistributionOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 11 },
      padding: [6, 10],
      extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-radius: 6px;',
    },
    series: [
      {
        name: 'Transport Modes',
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#ffffff',
          borderWidth: 2,
        },
        label: {
          show: true,
          color: '#475569',
          fontSize: 10,
          formatter: '{b}: {d}%',
        },
        data: Object.entries(modeDist).map(([mode, count], idx) => {
          const colors: Record<string, string> = {
            bus: '#fb5012',
            train: '#03fcba',
            flight: '#01fdf6',
          };
          return {
            value: count as number,
            name: mode.toUpperCase(),
            itemStyle: { color: colors[mode.toLowerCase()] || clusterColors[idx] },
          };
        }),
      },
    ],
  };

  return (
    <div className="space-y-4">
      {/* Top Banner and Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/60">
        <div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900">
            Corridor Cluster Analysis (K-Means Clustering)
          </h1>
        </div>

        <button
          onClick={() => setSelectedCluster(null)}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border shadow-2xs backdrop-blur-md ${
            selectedCluster === null
              ? 'bg-white/95 text-slate-900 border-white shadow-xs font-bold'
              : 'bg-white/60 text-slate-600 border-white/80 hover:text-slate-900'
          }`}
        >
          View All Clusters
        </button>
      </div>

      {/* 4 Cluster Archetype Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {clusters.map((cluster: ClusterSummaryItem, idx: number) => {
          const clusterId = cluster.cluster_id ?? cluster.cluster;
          const isSelected = selectedCluster === clusterId;
          const color = clusterColors[idx % clusterColors.length];

          return (
            <motion.div
              key={clusterId}
              whileHover={{ y: -2 }}
              transition={{ duration: 0.15 }}
              onClick={() => setSelectedCluster(clusterId)}
              className={`p-4 rounded-xl cursor-pointer transition-all ${
                isSelected
                  ? 'bg-white/95 border-2 border-slate-700/80 shadow-md ring-1 ring-slate-900/10'
                  : 'liquid-glass-interactive'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full shadow-2xs" style={{ backgroundColor: color }} />
                  <span className={`text-[10px] font-bold uppercase tracking-wider ${isSelected ? 'text-slate-900' : 'text-slate-500'}`}>
                    Cluster {clusterId}
                  </span>
                </div>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border backdrop-blur-md ${isSelected ? 'bg-white text-slate-900 border-slate-300 font-bold' : 'bg-white/70 text-slate-700 border-white/90'}`}>
                  {cluster.size ?? cluster.total_routes} routes
                </span>
              </div>

              <h4 className="text-sm font-bold mb-1.5 truncate text-slate-900">{cluster.name ?? cluster.cluster_name}</h4>

              <div className={`space-y-1 text-xs pt-2 border-t ${isSelected ? 'border-slate-200 text-slate-800' : 'border-slate-200/60 text-slate-600'}`}>
                <div className="flex justify-between text-[11px]">
                  <span>Avg Demand:</span>
                  <span className="font-bold font-mono text-slate-900">
                    {Math.round(cluster.avg_demand ?? cluster.avg_passengers).toLocaleString()} pax
                  </span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span>Avg Occupancy:</span>
                  <span className="font-bold font-mono text-indigo-700">
                    {(cluster.avg_occupancy * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span>Avg Fare:</span>
                  <span className="font-mono text-slate-800 font-medium">₹{Math.round(cluster.avg_fare)}</span>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Scatter Visualization */}
        <Card className="lg:col-span-8 p-4">
          <div className="mb-1 pb-2 border-b border-slate-200/60">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              2D Cluster Scatter Plot (Demand vs Occupancy Rate)
            </h2>
            <p className="text-[11px] text-slate-500">
              Route data points colored by assigned K-Means cluster
            </p>
          </div>
          <div className="h-72 w-full mt-1">
            <ReactECharts option={scatterOption} notMerge={true} style={{ height: '100%', width: '100%' }} />
          </div>
        </Card>

        {/* Selected Cluster Deep Dive */}
        <Card className="lg:col-span-4 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-200/60">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                Cluster {selectedClusterObj.cluster_id ?? selectedClusterObj.cluster} Profile
              </h2>
              <Badge variant="neutral" size="sm">{selectedClusterObj.name ?? selectedClusterObj.cluster_name}</Badge>
            </div>

            <div className="p-3 rounded-xl bg-white/60 border border-white/80 backdrop-blur-md mb-3 text-xs text-slate-600 leading-relaxed font-normal shadow-2xs">
              <span className="font-bold text-slate-900">Cluster Characteristics:</span>{' '}
              {(selectedClusterObj.cluster_id ?? selectedClusterObj.cluster) === 0 &&
                'High-capacity, high-frequency trunk routes characterized by high average passenger volume.'}
              {(selectedClusterObj.cluster_id ?? selectedClusterObj.cluster) === 1 &&
                'Medium-volume regional routes connecting secondary hubs and suburban corridors.'}
              {(selectedClusterObj.cluster_id ?? selectedClusterObj.cluster) === 2 &&
                'Long-distance express routes with higher average fares and premium seating classes.'}
              {(selectedClusterObj.cluster_id ?? selectedClusterObj.cluster) >= 3 &&
                'Short-haul feeder and commuter routes with low average passenger volumes and lower fares.'}
            </div>

            <div className="h-44 w-full">
              <ReactECharts option={modeDistributionOption} notMerge={true} style={{ height: '100%', width: '100%' }} />
            </div>
          </div>

          <div className="pt-2 border-t border-slate-200/60 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Sample instances: {samplePoints.length}</span>
            <span className="text-slate-800 font-bold">K-Means Model</span>
          </div>
        </Card>
      </div>
    </div>
  );
};

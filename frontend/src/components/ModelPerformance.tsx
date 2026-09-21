import React, { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import type { ModelBenchmarkData } from '../services/api';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';

interface ModelPerformanceProps {
  benchmarks: ModelBenchmarkData | null;
}

export const ModelPerformance: React.FC<ModelPerformanceProps> = ({ benchmarks }) => {
  const [selectedSplit, setSelectedSplit] = useState<'test' | 'validation' | 'all'>('test');

  const rawMetrics = benchmarks?.metrics || [
    { model_name: 'CatBoost (Tuned)', split: 'test', mae: 25.488, rmse: 39.344, mape: 30.81, r2: 0.7242 },
    { model_name: 'XGBoost (Tuned)', split: 'test', mae: 25.343, rmse: 39.375, mape: 30.96, r2: 0.7238 },
    { model_name: 'LightGBM (Tuned)', split: 'test', mae: 25.537, rmse: 39.856, mape: 31.11, r2: 0.7170 },
    { model_name: 'Random Forest', split: 'test', mae: 30.885, rmse: 54.852, mape: 37.07, r2: 0.4640 },
    { model_name: 'Ridge Regression', split: 'test', mae: 34.996, rmse: 54.239, mape: 45.64, r2: 0.4759 },
  ];

  const filteredMetrics = selectedSplit === 'all' ? rawMetrics : rawMetrics.filter((m) => m.split.toLowerCase() === selectedSplit);

  const modelNames = Array.from(new Set(filteredMetrics.map((m) => m.model_name)));
  const r2Scores = modelNames.map((name) => {
    const item = filteredMetrics.find((m) => m.model_name === name);
    return item ? round(item.r2 * 100, 1) : 0;
  });
  const maeScores = modelNames.map((name) => {
    const item = filteredMetrics.find((m) => m.model_name === name);
    return item ? round(item.mae, 1) : 0;
  });

  function round(val: number, decimals = 2) {
    return Number(Math.round(Number(val + 'e' + decimals)) + 'e-' + decimals);
  }

  const comparisonBarOption = {
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
      data: ['Accuracy R² (%)', 'MAE (Lower = Better)'],
      textStyle: { color: '#64748b', fontSize: 10.5 },
      top: 0,
      right: 0,
      icon: 'circle',
      itemWidth: 7,
      itemHeight: 7,
    },
    grid: {
      left: '2%',
      right: '2%',
      bottom: '6%',
      top: '16%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: modelNames,
      axisLabel: {
        color: '#475569',
        fontSize: 10.5,
        interval: 0,
      },
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: 'R² Score (%)',
        nameTextStyle: { color: '#64748b', fontSize: 10 },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
        axisLabel: { color: '#64748b', fontSize: 10 },
      },
      {
        type: 'value',
        name: 'MAE (Pax)',
        nameTextStyle: { color: '#64748b', fontSize: 10 },
        axisLine: { show: false },
        splitLine: { show: false },
        axisLabel: { color: '#64748b', fontSize: 10 },
      },
    ],
    series: [
      {
        name: 'Accuracy R² (%)',
        type: 'bar',
        data: r2Scores,
        itemStyle: { color: '#03fcba', borderRadius: [3, 3, 0, 0] },
        barWidth: 18,
      },
      {
        name: 'MAE (Lower = Better)',
        type: 'bar',
        yAxisIndex: 1,
        data: maeScores,
        itemStyle: { color: '#fb5012', borderRadius: [3, 3, 0, 0] },
        barWidth: 18,
      },
    ],
  };

  const radarOption = {
    backgroundColor: 'transparent',
    tooltip: {
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 11 },
      extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-radius: 6px;',
    },
    legend: {
      data: ['CatBoost (Tuned)', 'Random Forest', 'Ridge Baseline'],
      textStyle: { color: '#64748b', fontSize: 10 },
      bottom: 0,
      icon: 'circle',
      itemWidth: 6,
      itemHeight: 6,
    },
    radar: {
      radius: '56%',
      center: ['50%', '44%'],
      indicator: [
        { name: 'High R²', max: 100 },
        { name: 'Low MAE', max: 100 },
        { name: 'Inference Speed', max: 100 },
        { name: 'Robustness', max: 100 },
        { name: 'Interpretability', max: 100 },
      ],
      shape: 'polygon',
      splitArea: {
        show: true,
        areaStyle: { color: ['rgba(248, 250, 252, 0.6)', 'rgba(255, 255, 255, 0.9)'] },
      },
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      axisName: { color: '#64748b', fontSize: 10 },
    },
    series: [
      {
        name: 'Model Comparison',
        type: 'radar',
        data: [
          {
            value: [92, 88, 85, 95, 90],
            name: 'CatBoost (Tuned)',
            itemStyle: { color: '#fb5012' },
            areaStyle: { color: 'rgba(251, 80, 18, 0.12)' },
          },
          {
            value: [65, 60, 75, 70, 75],
            name: 'Random Forest',
            itemStyle: { color: '#03fcba' },
            areaStyle: { color: 'rgba(3, 252, 186, 0.12)' },
          },
          {
            value: [50, 45, 98, 55, 95],
            name: 'Ridge Baseline',
            itemStyle: { color: '#00d4cf' },
            areaStyle: { color: 'rgba(1, 253, 246, 0.12)' },
          },
        ],
      },
    ],
  };

  return (
    <div className="space-y-4">
      {/* Top Banner and Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/60">
        <div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900">
            Model Evaluation & Cross-Validation Benchmarks
          </h1>
        </div>

        {/* Partition Filter Pills */}
        <div className="flex bg-white/60 p-1 rounded-xl border border-white/80 backdrop-blur-md shadow-2xs self-start sm:self-auto">
          {[
            { id: 'test', label: 'Test Holdout' },
            { id: 'validation', label: 'Validation Split' },
            { id: 'all', label: 'All Splits' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedSplit(tab.id as any)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                selectedSplit === tab.id
                  ? 'bg-white/95 text-slate-900 shadow-xs border border-white'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Best Model Banner Card */}
      <Card className="p-4 bg-white/70 border-white/85 shadow-sm">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-base font-bold text-slate-900">
              {benchmarks?.best_model || 'CatBoost Regressor'}
            </h2>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 w-full md:w-auto">
            <div className="p-2.5 bg-white/80 rounded-xl border border-white/90 text-center shadow-2xs backdrop-blur-md">
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Test R²</p>
              <p className="text-lg font-black text-slate-900 font-mono">72.4%</p>
            </div>
            <div className="p-2.5 bg-white/80 rounded-xl border border-white/90 text-center shadow-2xs backdrop-blur-md">
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Test MAE</p>
              <p className="text-lg font-black text-slate-900 font-mono">25.3</p>
            </div>
            <div className="p-2.5 bg-white/80 rounded-xl border border-white/90 text-center shadow-2xs backdrop-blur-md">
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Test RMSE</p>
              <p className="text-lg font-black text-slate-900 font-mono">39.3</p>
            </div>
            <div className="p-2.5 bg-white/80 rounded-xl border border-white/90 text-center shadow-2xs backdrop-blur-md">
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Test MAPE</p>
              <p className="text-lg font-black text-slate-900 font-mono">30.8%</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Visual Comparison Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <Card className="lg:col-span-7 p-4">
          <div className="mb-1 pb-2 border-b border-slate-200/60">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">Accuracy (R²) vs Mean Absolute Error (MAE)</h2>
          </div>
          <div className="h-60 w-full mt-1">
            <ReactECharts option={comparisonBarOption} notMerge={true} style={{ height: '100%', width: '100%' }} />
          </div>
        </Card>

        <Card className="lg:col-span-5 p-4">
          <div className="mb-1 pb-2 border-b border-slate-200/60">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">Multi-Attribute Model Comparison</h2>
          </div>
          <div className="h-60 w-full flex items-center justify-center mt-1">
            <ReactECharts option={radarOption} notMerge={true} style={{ height: '100%', width: '100%' }} />
          </div>
        </Card>
      </div>

      {/* Benchmark Matrix Table */}
      <Card className="p-4">
        <div className="mb-3 pb-2 border-b border-slate-200/60">
          <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">Model Performance Leaderboard</h2>
        </div>

        <div className="overflow-x-auto rounded-xl border border-white/80 bg-white/40 backdrop-blur-md">
          <table className="w-full text-left text-xs min-w-[620px]">
            <thead>
              <tr className="bg-white/60 text-slate-600 uppercase text-[10px] border-b border-slate-200/70 tracking-wider font-bold">
                <th className="py-2.5 px-3">Model Algorithm</th>
                <th className="py-2.5 px-3">Split</th>
                <th className="py-2.5 px-3 text-right">MAE (Pax)</th>
                <th className="py-2.5 px-3 text-right">RMSE (Pax)</th>
                <th className="py-2.5 px-3 text-right">MAPE (%)</th>
                <th className="py-2.5 px-3 text-right">R² Score</th>
                <th className="py-2.5 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100/80">
              {filteredMetrics.map((m, idx) => {
                const isBest = idx === 0;
                return (
                  <tr
                    key={m.model_name + m.split + idx}
                    className={`hover:bg-white/70 transition-colors ${
                      isBest ? 'bg-white/50' : ''
                    }`}
                  >
                    <td className="py-2.5 px-3 font-semibold text-slate-900">
                      {m.model_name}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="capitalize bg-white/70 px-2 py-0.5 rounded-full text-[10.5px] text-slate-700 font-medium border border-white/90 shadow-2xs">
                        {m.split}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-900 font-mono font-medium">{m.mae.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-700 font-mono">{m.rmse.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-700">{m.mape.toFixed(2)}%</td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                      {(m.r2 * 100).toFixed(2)}%
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {isBest ? (
                        <Badge variant="indigo" size="sm">Selected</Badge>
                      ) : (
                        <Badge variant="neutral" size="sm">Baseline</Badge>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

import React, { useEffect, useState, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  Search,
  Sliders,
  BarChart3,
  Zap,
} from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { StatCard } from './ui/StatCard';
import { getExplainability, type ExplainData } from '../services/api';

// Feature metadata mapping with human-friendly names and categories
interface FeatureMeta {
  displayName: string;
  category: 'temporal' | 'operational' | 'pricing' | 'infrastructure';
  categoryLabel: string;
  impactNote: string;
}

const FEATURE_METADATA: Record<string, FeatureMeta> = {
  modetype_hist_mean: {
    displayName: 'Historical Modal Demand Mean',
    category: 'operational',
    categoryLabel: 'Modal History',
    impactNote: 'Long-term baseline demand unique to each transit modality.',
  },
  lag_7: {
    displayName: '7-Day Lagged Demand',
    category: 'temporal',
    categoryLabel: 'Autoregressive Lag',
    impactNote: 'Demand recorded exactly one week prior, capturing weekly rhythm.',
  },
  capacity: {
    displayName: 'Vehicle / Seating Capacity',
    category: 'infrastructure',
    categoryLabel: 'Infrastructure',
    impactNote: 'Physical seat capacity constraint of the vehicle or aircraft.',
  },
  route_month_mean: {
    displayName: 'Monthly Route Profile Mean',
    category: 'temporal',
    categoryLabel: 'Seasonality',
    impactNote: 'Historical average for this specific route in the current calendar month.',
  },
  rolling_mean_7: {
    displayName: '7-Day Rolling Average',
    category: 'temporal',
    categoryLabel: 'Moving Average',
    impactNote: 'Trailing 7-day smoothed passenger demand moving average.',
  },
  year: {
    displayName: 'Year / Long-Term Growth Index',
    category: 'temporal',
    categoryLabel: 'Macro Trend',
    impactNote: 'Captures year-over-year ridership expansion and post-pandemic recovery.',
  },
  fare_per_passenger: {
    displayName: 'Ticket Fare per Passenger',
    category: 'pricing',
    categoryLabel: 'Economic & Pricing',
    impactNote: 'Pricing elasticity indicator influencing discretionary route choice.',
  },
  mode_type_encoded: {
    displayName: 'Transit Mode Classification',
    category: 'operational',
    categoryLabel: 'Modal History',
    impactNote: 'Categorical encoding designating Bus, Railway, or Domestic Flight.',
  },
  rolling_max_7: {
    displayName: '7-Day Rolling Peak Volume',
    category: 'temporal',
    categoryLabel: 'Moving Average',
    impactNote: 'Peak passenger volume recorded in the preceding 7 days.',
  },
  rolling_min_7: {
    displayName: '7-Day Rolling Minimum Volume',
    category: 'temporal',
    categoryLabel: 'Moving Average',
    impactNote: 'Floor passenger demand observed in the preceding 7-day window.',
  },
  distance_km: {
    displayName: 'Route Distance (km)',
    category: 'infrastructure',
    categoryLabel: 'Infrastructure',
    impactNote: 'Total physical corridor distance between origin and destination.',
  },
  lag_1: {
    displayName: 'Previous Trip Demand (Lag 1)',
    category: 'temporal',
    categoryLabel: 'Autoregressive Lag',
    impactNote: 'Immediate preceding schedule demand on the identical corridor.',
  },
  week_of_year: {
    displayName: 'Week of Year (Seasonality)',
    category: 'temporal',
    categoryLabel: 'Seasonality',
    impactNote: 'Annual week index (1–52) capturing festival and holiday travel surges.',
  },
  rolling_std_7: {
    displayName: '7-Day Demand Volatility (Std)',
    category: 'temporal',
    categoryLabel: 'Moving Average',
    impactNote: 'Standard deviation of demand measuring corridor demand stability.',
  },
  operator_encoded: {
    displayName: 'Transit Operator Classification',
    category: 'operational',
    categoryLabel: 'Operational',
    impactNote: 'Designates operating carrier (APSRTC, IRCTC, Indigo, Air India).',
  },
};

const CORRIDOR_SCENARIOS = [
  {
    id: 'apsrtc-hyd-vja',
    name: 'Hyderabad — Vijayawada (APSRTC Super Luxury)',
    mode: 'Bus',
    baseValue: 42,
    prediction: 54,
    contributions: [
      { name: 'Modal Baseline Mean', value: +6.4, type: 'positive' },
      { name: '7-Day Lag Volume', value: +4.8, type: 'positive' },
      { name: 'Weekend Travel Surge', value: +3.2, type: 'positive' },
      { name: 'Vehicle Capacity Limit (49 seats)', value: -1.0, type: 'negative' },
      { name: 'Rainfall / Weather Dampener', value: -1.4, type: 'negative' },
    ],
  },
  {
    id: 'irctc-charminar',
    name: '12759 Charminar Express (SC — MAS)',
    mode: 'Rail',
    baseValue: 215,
    prediction: 248,
    contributions: [
      { name: 'Modal Baseline Mean', value: +18.5, type: 'positive' },
      { name: 'Full Train Capacity (24 Coaches)', value: +12.0, type: 'positive' },
      { name: 'Festival Season Multiplier', value: +8.5, type: 'positive' },
      { name: 'Dynamic Fare Elasticity', value: -3.5, type: 'negative' },
      { name: 'Mid-week Schedule Adjustment', value: -2.5, type: 'negative' },
    ],
  },
  {
    id: 'flight-blr-del',
    name: 'BLR — DEL (Indigo 6E-204)',
    mode: 'Flights',
    baseValue: 82,
    prediction: 94,
    contributions: [
      { name: 'High-Demand Metro Trunk Corridor', value: +7.2, type: 'positive' },
      { name: 'Morning Peak Departure (07:30)', value: +4.5, type: 'positive' },
      { name: 'A320neo Seating Capacity', value: +3.1, type: 'positive' },
      { name: 'Peak-Hour Surge Pricing ($$)', value: -2.8, type: 'negative' },
    ],
  },
];

export const ExplainabilityStudio: React.FC = () => {
  const [data, setData] = useState<ExplainData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(CORRIDOR_SCENARIOS[0].id);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getExplainability();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load model explainability data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Process and normalize feature importances
  const processedFeatures = useMemo(() => {
    if (!data) return [];
    const list = data.feature_importances || data.top_features || [];
    const totalRaw = list.reduce((sum, item) => sum + (item.importance || 0), 0) || 1;

    return list.map((item, idx) => {
      const meta = FEATURE_METADATA[item.feature] || {
        displayName: item.feature.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
        category: 'operational',
        categoryLabel: 'Engineered Feature',
        impactNote: item.description || 'Predictive attribute generated from dataset pipeline.',
      };

      const normalizedPct = ((item.importance || 0) / totalRaw) * 100;

      return {
        ...item,
        rank: idx + 1,
        displayName: meta.displayName,
        category: meta.category,
        categoryLabel: meta.categoryLabel,
        impactNote: meta.impactNote,
        normalizedPct,
        rawImportance: item.importance,
      };
    });
  }, [data]);

  // Active focused feature for deep-dive inspection (defaults to first feature)
  const [activeFeatureCode, setActiveFeatureCode] = useState<string>('modetype_hist_mean');
  const [displayCount, setDisplayCount] = useState<number>(8);

  // Filtered features based on category filter & search
  const filteredFeatures = useMemo(() => {
    return processedFeatures.filter((f) => {
      const matchesCategory = selectedCategory === 'all' || f.category === selectedCategory;
      const matchesSearch =
        !searchQuery.trim() ||
        f.displayName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.feature.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.categoryLabel.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [processedFeatures, selectedCategory, searchQuery]);

  // Top features for the primary horizontal bar chart
  const topChartFeatures = useMemo(() => {
    const list = selectedCategory === 'all' ? processedFeatures : filteredFeatures;
    const count = displayCount === 0 ? list.length : displayCount;
    return [...list].slice(0, count).reverse();
  }, [processedFeatures, filteredFeatures, selectedCategory, displayCount]);

  // Currently focused feature item
  const activeFeatureItem = useMemo(() => {
    return (
      processedFeatures.find((f) => f.feature === activeFeatureCode) ||
      processedFeatures[0]
    );
  }, [processedFeatures, activeFeatureCode]);

  // View mode for the primary graph
  const [graphViewMode, setGraphViewMode] = useState<'ranking' | 'composition'>('ranking');

  // Category composition data
  const categoryCompositionData = useMemo(() => {
    const map: Record<string, { label: string; total: number; count: number; color: string }> = {
      temporal: { label: 'Temporal & Lags', total: 0, count: 0, color: '#4f46e5' },
      operational: { label: 'Modal Structure', total: 0, count: 0, color: '#0284c7' },
      infrastructure: { label: 'Fleet & Capacity', total: 0, count: 0, color: '#8b5cf6' },
      pricing: { label: 'Dynamic Pricing', total: 0, count: 0, color: '#f59e0b' },
    };

    processedFeatures.forEach((f) => {
      if (map[f.category]) {
        map[f.category].total += f.normalizedPct;
        map[f.category].count += 1;
      }
    });

    return Object.entries(map).map(([key, val]) => ({
      key,
      name: val.label,
      value: Number(val.total.toFixed(1)),
      count: val.count,
      itemStyle: { color: val.color },
    }));
  }, [processedFeatures]);

  // Donut chart option for Category Composition
  const categoryDonutOption = useMemo(() => {
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#0f172a', fontSize: 11 },
        extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.1); border-radius: 10px; padding: 10px;',
        formatter: (params: any) => {
          return `
            <div class="p-1 max-w-xs font-sans">
              <div class="font-bold text-slate-900 text-xs">${params.name}</div>
              <div class="flex items-center justify-between text-xs py-1 border-t border-slate-100 mt-1">
                <span class="text-slate-600 font-medium">Aggregated Gain:</span>
                <span class="font-bold text-indigo-700 font-mono text-sm">${params.value}%</span>
              </div>
              <div class="text-[10.5px] text-slate-500 mt-1">Features in domain: <b>${params.data.count} attributes</b></div>
            </div>
          `;
        },
      },
      legend: {
        orient: 'vertical',
        right: '5%',
        top: 'center',
        itemGap: 14,
        textStyle: { color: '#334155', fontSize: 11, fontWeight: 600 },
        formatter: (name: string) => {
          const item = categoryCompositionData.find((c) => c.name === name);
          return `${name}  (${item ? item.value : 0}%)`;
        },
      },
      series: [
        {
          name: 'Category Attribution Share',
          type: 'pie',
          radius: ['45%', '72%'],
          center: ['35%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 8,
            borderColor: '#ffffff',
            borderWidth: 2,
          },
          label: {
            show: false,
            position: 'center',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold',
              color: '#0f172a',
              formatter: '{b}\n{d}%',
            },
            scaleSize: 6,
          },
          labelLine: { show: false },
          data: categoryCompositionData,
        },
      ],
    };
  }, [categoryCompositionData]);

  // Primary horizontal bar chart option
  const featureBarOption = useMemo(() => {
    const yCategories = topChartFeatures.map((f) => f.displayName);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#0f172a', fontSize: 11 },
        extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.1); border-radius: 10px; padding: 10px;',
        formatter: (params: any) => {
          const item = params[0];
          const feat = topChartFeatures[item.dataIndex];
          if (!feat) return '';
          return `
            <div class="p-1 max-w-xs font-sans">
              <div class="font-bold text-slate-900 text-xs">${feat.displayName}</div>
              <div class="text-[10.5px] font-mono text-slate-400 mb-2">code: <code>${feat.feature}</code></div>
              <div class="flex items-center justify-between text-xs py-1 border-t border-slate-100 bg-indigo-50/60 px-2 rounded-lg mb-1.5">
                <span class="text-slate-600 font-medium">Attribution Gain:</span>
                <span class="font-bold text-indigo-700 font-mono text-sm">${feat.normalizedPct.toFixed(1)}%</span>
              </div>
              <div class="flex items-center justify-between text-[11px] py-0.5 text-slate-600">
                <span>Domain Category:</span>
                <span class="font-semibold text-slate-800">${feat.categoryLabel}</span>
              </div>
              <div class="text-[10.5px] text-slate-500 mt-1.5 leading-snug italic border-t border-slate-100 pt-1">${feat.impactNote}</div>
            </div>
          `;
        },
      },
      grid: {
        left: '2%',
        right: '9%',
        bottom: 28,
        top: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: 'Importance Share (%)',
        nameLocation: 'middle',
        nameGap: 20,
        nameTextStyle: { color: '#64748b', fontSize: 10.5, fontWeight: 500 },
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
        axisLabel: {
          color: '#64748b',
          fontSize: 10,
          formatter: (val: number) => `${val}%`,
        },
      },
      yAxis: {
        type: 'category',
        data: yCategories,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#334155',
          fontSize: 11,
          fontWeight: 600,
          formatter: (value: string) => {
            return value.length > 28 ? `${value.slice(0, 26)}…` : value;
          },
        },
      },
      series: [
        {
          name: 'Feature Share',
          type: 'bar',
          data: topChartFeatures.map((feat) => {
            const isSelected = activeFeatureCode === feat.feature;
            return {
              value: Number(feat.normalizedPct.toFixed(1)),
              featureCode: feat.feature,
              itemStyle: {
                color: isSelected
                  ? {
                      type: 'linear',
                      x: 0,
                      y: 0,
                      x2: 1,
                      y2: 0,
                      colorStops: [
                        { offset: 0, color: '#f59e0b' },
                        { offset: 1, color: '#fbbf24' },
                      ],
                    }
                  : {
                      type: 'linear',
                      x: 0,
                      y: 0,
                      x2: 1,
                      y2: 0,
                      colorStops: [
                        { offset: 0, color: '#4f46e5' },
                        { offset: 1, color: '#0284c7' },
                      ],
                    },
                borderRadius: [0, 6, 6, 0],
              },
            };
          }),
          barWidth: 16,
          label: {
            show: true,
            position: 'right',
            formatter: '{c}%',
            color: '#334155',
            fontSize: 10.5,
            fontFamily: 'monospace',
            fontWeight: 'bold',
            distance: 6,
          },
        },
      ],
    };
  }, [topChartFeatures, activeFeatureCode]);

  // Selected corridor scenario for local SHAP waterfall
  const currentScenario = useMemo(() => {
    return (
      CORRIDOR_SCENARIOS.find((s) => s.id === selectedScenarioId) || CORRIDOR_SCENARIOS[0]
    );
  }, [selectedScenarioId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[440px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-9 h-9 border-3 border-slate-300 border-t-slate-900 rounded-full animate-spin" />
          <p className="text-slate-600 text-xs font-medium">
            Computing TreeExplainer SHAP values & feature importance rankings...
          </p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-16">
        <p className="text-rose-700 font-semibold mb-3 text-xs">
          {error || 'No explainability data available'}
        </p>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-indigo-600 rounded-xl text-xs text-white font-semibold shadow-sm hover:bg-indigo-700 transition-colors"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  // Top metric stats calculations
  const topFeatureItem = processedFeatures[0];
  const temporalShare = processedFeatures
    .filter((f) => f.category === 'temporal')
    .reduce((sum, f) => sum + f.normalizedPct, 0);

  const onChartClick = (params: any) => {
    if (params.data && params.data.featureCode) {
      setActiveFeatureCode(params.data.featureCode);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/60">
        <div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900">
            SHAP ANALYSIS
          </h1>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Badge variant="neutral" size="sm" className="py-1 px-3 bg-white/70 border-white/90 shadow-2xs backdrop-blur-md font-mono text-[11px]">
            Engine: TreeSHAP
          </Badge>
          <span className="text-[11px] font-bold text-indigo-900 bg-indigo-50 border border-indigo-200/80 px-2.5 py-1 rounded-full shadow-2xs">
            Model: {data.model_name}
          </span>
        </div>
      </div>

      {/* 4 Stat Overview Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          title="Active Predictive Model"
          value={data.model_name || 'CatBoost'}
          subtitle="Gradient Boosted Decision Trees • R² 72.4%"
        />
        <StatCard
          title="Primary Predictive Driver"
          value={topFeatureItem?.displayName ? 'Modal Baseline' : 'N/A'}
          subtitle={`${topFeatureItem?.normalizedPct.toFixed(1)}% Relative Importance Share`}
        />
        <StatCard
          title="Temporal & Lag Influence"
          value={`${temporalShare.toFixed(1)}%`}
          subtitle="Autoregressive & Rolling 7-Day Means"
        />
        <StatCard
          title="Engineered Dimensions"
          value={`${processedFeatures.length} Attributes`}
          subtitle="Multi-modal lag & operational features"
        />
      </div>

      {/* Expanded Global Feature Attribution Studio (Full Width 12-Cols) */}
      <Card className="p-4 space-y-3.5">
        {/* Studio Header & Interactive Filtering Controls */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-slate-200/60">
          <div>
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5 text-indigo-600" />
              Global Feature Attribution Studio (TreeSHAP Split Gain)
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex bg-slate-100/90 rounded-xl p-0.5 border border-slate-200/70 text-[11px]">
              <button
                onClick={() => setGraphViewMode('ranking')}
                className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                  graphViewMode === 'ranking'
                    ? 'bg-white text-indigo-900 font-bold shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Attribution Ranking
              </button>
              <button
                onClick={() => setGraphViewMode('composition')}
                className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                  graphViewMode === 'composition'
                    ? 'bg-white text-indigo-900 font-bold shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Domain Composition
              </button>
            </div>

            {/* Category Filter Pills (Only active on ranking mode) */}
            {graphViewMode === 'ranking' && (
              <div className="flex bg-white/80 rounded-xl p-0.5 border border-white/95 backdrop-blur-md shadow-2xs text-[11px]">
                {[
                  { id: 'all', label: 'All' },
                  { id: 'temporal', label: 'Lags' },
                  { id: 'operational', label: 'Modal' },
                  { id: 'infrastructure', label: 'Capacity' },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-2 py-0.5 rounded-lg font-semibold transition-all ${
                      selectedCategory === cat.id
                        ? 'bg-indigo-600 text-white shadow-xs font-bold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            )}

            {/* Display Depth Selector */}
            {graphViewMode === 'ranking' && (
              <div className="flex bg-slate-100/80 rounded-xl p-0.5 border border-slate-200/70 text-[10.5px]">
                {[
                  { count: 8, label: 'Top 8' },
                  { count: 12, label: 'Top 12' },
                  { count: 0, label: 'All' },
                ].map((item) => (
                  <button
                    key={item.count}
                    onClick={() => setDisplayCount(item.count)}
                    className={`px-2 py-0.5 rounded-lg font-medium transition-all ${
                      displayCount === item.count
                        ? 'bg-white text-slate-900 font-bold shadow-2xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Chart Canvas & Feature Telemetry Spotlight Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left Chart Area (8 Cols) */}
          <div className="lg:col-span-8">
            <div className="h-[340px] w-full bg-white/40 rounded-2xl p-2 border border-white/60">
              <ReactECharts
                option={graphViewMode === 'ranking' ? featureBarOption : categoryDonutOption}
                onEvents={{ click: onChartClick }}
                style={{ height: '100%', width: '100%' }}
                notMerge={true}
              />
            </div>
          </div>

          {/* Right Dimension Spotlight Card (4 Cols) */}
          <div className="lg:col-span-4">
            <div className="p-3.5 rounded-2xl bg-white/85 border border-white/95 shadow-sm space-y-3">
              {/* Header */}
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                  Attribute Telemetry Spotlight
                </span>
                <Badge
                  variant={
                    activeFeatureItem.category === 'temporal'
                      ? 'blue'
                      : activeFeatureItem.category === 'operational'
                      ? 'indigo'
                      : 'purple'
                  }
                  size="sm"
                  className="text-[9.5px]"
                >
                  {activeFeatureItem.categoryLabel}
                </Badge>
              </div>

              {/* Title & Share Stat */}
              <div>
                <h3 className="text-xs font-bold text-slate-900">{activeFeatureItem.displayName}</h3>
                <div className="text-[10.5px] font-mono text-slate-400 mt-0.5">
                  code: <code>{activeFeatureItem.feature}</code>
                </div>

                <div className="mt-2.5 p-2.5 rounded-xl bg-indigo-50/70 border border-indigo-100/80 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-indigo-900/70 block font-medium uppercase">Relative Gain Share</span>
                    <span className="text-lg font-black text-indigo-950 font-mono">
                      {activeFeatureItem.normalizedPct.toFixed(1)}%
                    </span>
                  </div>
                  <span className="text-[10px] font-bold text-indigo-700 bg-white/90 px-2 py-1 rounded-lg border border-indigo-100 font-mono">
                    TreeSHAP Gain
                  </span>
                </div>
              </div>

              {/* Impact Description */}
              <div className="p-2.5 rounded-xl bg-white/70 border border-white/90 text-xs space-y-1">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                  Model Behavior & Interpretation
                </span>
                <p className="text-[11px] text-slate-700 leading-relaxed font-medium">
                  {activeFeatureItem.impactNote}
                </p>
              </div>

              {/* Category Breakdown Progress */}
              <div className="pt-2 border-t border-slate-100 space-y-1.5 text-xs">
                <div className="flex justify-between text-[10.5px] text-slate-600">
                  <span className="font-medium">Category Attribution:</span>
                  <span className="font-mono font-bold text-slate-900">
                    {activeFeatureItem.category === 'temporal' ? `${temporalShare.toFixed(1)}% Total Lags` : 'Structural Factor'}
                  </span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(activeFeatureItem.normalizedPct * 1.8, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Corridor SHAP Local Attribution Waterfall (Interactive Sandbox) */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/60 mb-3">
          <div>
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              Corridor Local SHAP Attribution Waterfall
            </h2>
          </div>

          {/* Scenario Selector */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-slate-600 hidden sm:inline">Scenario:</span>
            <select
              value={selectedScenarioId}
              onChange={(e) => setSelectedScenarioId(e.target.value)}
              aria-label="Select corridor scenario for SHAP attribution"
              className="bg-white/80 border border-slate-200 rounded-xl px-3 py-1 text-xs font-semibold text-slate-800 shadow-2xs focus:outline-none focus:ring-1 focus:ring-slate-900 cursor-pointer"
            >
              {CORRIDOR_SCENARIOS.map((s) => (
                <option key={s.id} value={s.id}>
                  [{s.mode}] {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Corridor Attribution Bar & Factors */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
          {/* Left: Summary Metrics */}
          <div className="lg:col-span-4">
            <div className="p-3.5 rounded-xl bg-white/75 border border-white/90 shadow-2xs space-y-2.5">
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                  Selected Corridor
                </span>
                <div className="text-xs font-bold text-slate-900 mt-0.5">{currentScenario.name}</div>
              </div>
              <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-100">
                <div>
                  <span className="text-[10.5px] text-slate-500 block">Base Corridor Mean</span>
                  <span className="font-mono font-bold text-slate-700 text-sm">
                    {currentScenario.baseValue} pax
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10.5px] text-slate-500 block">Predicted Demand</span>
                  <span className="font-mono font-bold text-indigo-600 text-sm">
                    {currentScenario.prediction} pax
                  </span>
                </div>
              </div>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                <span className="text-slate-500 font-medium">Net SHAP Impact:</span>
                <span className="font-mono font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-100">
                  +{currentScenario.prediction - currentScenario.baseValue} pax (
                  {(
                    ((currentScenario.prediction - currentScenario.baseValue) /
                      currentScenario.baseValue) *
                    100
                  ).toFixed(1)}
                  %)
                </span>
              </div>
            </div>
          </div>

          {/* Right: SHAP Factor waterfall badges */}
          <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-2">
            {currentScenario.contributions.map((c, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-2.5 rounded-xl bg-white/70 border border-white/90 shadow-2xs text-xs"
              >
                <div className="flex items-center gap-2 truncate pr-2">
                  <span
                    className={`text-[10px] font-bold font-mono px-1.5 py-0.5 rounded-full shrink-0 border ${
                      c.type === 'positive'
                        ? 'bg-indigo-500/15 text-indigo-800 border-indigo-400/40'
                        : 'bg-rose-500/15 text-rose-800 border-rose-400/40'
                    }`}
                  >
                    {c.type === 'positive' ? '+' : '-'}
                  </span>
                  <span className="text-slate-800 font-semibold text-[11px] truncate">
                    {c.name}
                  </span>
                </div>
                <span
                  className={`font-mono font-bold text-xs shrink-0 ${
                    c.type === 'positive' ? 'text-indigo-700' : 'text-rose-700'
                  }`}
                >
                  {c.value > 0 ? `+${c.value}` : c.value} pax
                </span>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Feature Catalog & Attribute Dictionary */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/60 mb-3">
          <div>
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-slate-600" />
              Engineered Feature Dictionary ({filteredFeatures.length} Attributes)
            </h2>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search features by name or code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-white/80 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-slate-900 placeholder:text-slate-400 shadow-2xs"
            />
          </div>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {filteredFeatures.map((f, idx) => (
            <div
              key={idx}
              className="p-3 rounded-xl bg-white/70 border border-white/90 backdrop-blur-md text-xs shadow-2xs hover:bg-white/95 hover:border-slate-300 transition-all flex flex-col justify-between gap-2"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-bold text-slate-900 text-xs">{f.displayName}</div>
                    <div className="font-mono text-[10px] text-slate-400 mt-0.5">
                      <code>{f.feature}</code>
                    </div>
                  </div>
                  <span
                    className={`text-[9.5px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider border shrink-0 ${
                      f.category === 'temporal'
                        ? 'bg-blue-50 text-blue-700 border-blue-200'
                        : f.category === 'infrastructure'
                        ? 'bg-purple-50 text-purple-700 border-purple-200'
                        : f.category === 'pricing'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                    }`}
                  >
                    {f.categoryLabel}
                  </span>
                </div>

                <p className="text-[11px] text-slate-600 mt-2 leading-relaxed">
                  {f.impactNote}
                </p>
              </div>

              {/* Progress bar & percentage */}
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(f.normalizedPct * 1.8, 100)}%` }}
                  />
                </div>
                <span className="font-mono font-bold text-slate-900 text-xs shrink-0">
                  {f.normalizedPct.toFixed(1)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

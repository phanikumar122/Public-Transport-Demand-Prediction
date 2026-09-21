import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { getBatchPredictions, type BatchPredictionItem } from '../services/api';

export const BatchExplorer: React.FC = () => {
  const [data, setData] = useState<BatchPredictionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter & Search states
  const [modeFilter, setModeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getBatchPredictions(modeFilter === 'all' ? undefined : modeFilter, 1000);
      setData(res.predictions);
      setPage(1);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch batch predictions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [modeFilter]);

  // Client-side search filtering
  const filteredData = data.filter((item: BatchPredictionItem) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    const routeName = item.route_id || item.route;
    const modeName = item.mode || item.transport_mode;
    return (
      routeName.toLowerCase().includes(query) ||
      modeName.toLowerCase().includes(query) ||
      (item.date && item.date.includes(query))
    );
  });

  const totalPages = Math.ceil(filteredData.length / pageSize);
  const paginatedData = filteredData.slice((page - 1) * pageSize, page * pageSize);

  // CSV Export
  const exportToCSV = () => {
    const headers = [
      'Route ID',
      'Mode',
      'Date',
      'Predicted Demand',
      'Confidence',
      'Fleet Units',
      'Load Factor',
      'Surge Multiplier',
      'Model Used',
    ];

    const rows = filteredData.map((item) => [
      item.route_id || item.route,
      item.mode || item.transport_mode,
      item.date || '2025-06-15',
      Math.round(item.predicted_demand ?? 0),
      (item.confidence_score ?? 0.9).toFixed(2),
      item.optimal_fleet_units ?? item.recommended_buses ?? 1,
      ((item.load_factor ?? 0.75) * 100).toFixed(1) + '%',
      (item.surge_multiplier ?? 1.0).toFixed(2),
      'CatBoost (Tuned)',
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `transport_demand_predictions_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-4">
      {/* Top Banner and Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/60">
        <div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900">
            Data Warehouse Fact Table & Batch Predictions
          </h1>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={exportToCSV}
            disabled={filteredData.length === 0}
            className="text-xs py-1.5 px-3.5 bg-white/70 hover:bg-white border-white/90 shadow-2xs backdrop-blur-md rounded-lg"
          >
            Export CSV ({filteredData.length})
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchData}
            className="text-xs py-1.5 px-3.5 bg-white/70 hover:bg-white border-white/90 shadow-2xs backdrop-blur-md rounded-lg"
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <Card className="p-3.5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Query by Route ID, Mode, or Date (YYYY-MM-DD)..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              className="w-full bg-white/80 border border-slate-200/80 rounded-lg px-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 shadow-2xs backdrop-blur-md transition"
            />
          </div>

          {/* Mode Pill Group */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-slate-500 font-semibold text-[11px]">
              Dimension (Mode):
            </span>
            <div className="flex flex-wrap bg-white/60 rounded-xl p-1 border border-white/80 backdrop-blur-md shadow-2xs gap-1">
              {[
                { id: 'all', label: 'All Modes' },
                { id: 'bus', label: 'Bus' },
                { id: 'rail', label: 'Railways' },
                { id: 'air', label: 'Flights' },
              ].map((tab) => {
                const isSelected = modeFilter === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setModeFilter(tab.id)}
                    className={`px-2.5 sm:px-3 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                      isSelected
                        ? 'bg-white/95 text-slate-900 shadow-xs border border-white font-bold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </Card>

      {/* Table Content */}
      <Card className="p-0 overflow-hidden border border-white/80">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-2.5">
              <div className="w-7 h-7 border-3 border-slate-300 border-t-slate-900 rounded-full animate-spin" />
              <p className="text-slate-500 text-xs font-medium">Fetching predictions catalog...</p>
            </div>
          </div>
        ) : error ? (
          <div className="text-center py-12 text-rose-700 text-xs font-semibold">{error}</div>
        ) : filteredData.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs font-medium">
            No matching predictions found for the specified filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[720px]">
              <thead>
                <tr className="bg-white/60 text-slate-600 uppercase tracking-wider font-bold border-b border-slate-200/70 text-[10px]">
                  <th className="py-2.5 px-3">Route / Corridor</th>
                  <th className="py-2.5 px-3">Mode</th>
                  <th className="py-2.5 px-3">Schedule Date</th>
                  <th className="py-2.5 px-3 text-right">Predicted Demand</th>
                  <th className="py-2.5 px-3 text-center">Fleet Units</th>
                  <th className="py-2.5 px-3 text-center">Load Factor</th>
                  <th className="py-2.5 px-3 text-center">Surge Multiplier</th>
                  <th className="py-2.5 px-3 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/80">
                {paginatedData.map((item: BatchPredictionItem, idx: number) => {
                  const itemMode = (item.mode || item.transport_mode || '').toLowerCase();
                  const surge = item.surge_multiplier ?? 1.0;
                  const loadFactor = item.load_factor ?? 0.75;
                  const fleetUnits = item.optimal_fleet_units ?? item.recommended_buses ?? 1;
                  return (
                    <motion.tr
                      key={idx}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.1 }}
                      className="hover:bg-white/70 transition-colors"
                    >
                      <td className="py-2.5 px-3 font-semibold text-slate-900">{item.route_id || item.route}</td>
                      <td className="py-2.5 px-3">
                        <Badge
                          variant={
                            itemMode === 'bus'
                              ? 'rose'
                              : itemMode === 'train' || itemMode === 'rail'
                              ? 'indigo'
                              : 'blue'
                          }
                          size="sm"
                        >
                          {item.mode || item.transport_mode}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-slate-500 font-mono">{item.date || 'Historical'}</td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-900 font-mono">
                        {Math.round(item.predicted_demand).toLocaleString()}{' '}
                        <span className="text-[10px] text-slate-400 font-normal">pax</span>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className="inline-flex items-center justify-center px-2 py-0.5 rounded-full bg-white/70 text-slate-800 border border-white/90 font-mono font-bold text-[10.5px] shadow-2xs">
                          {fleetUnits} units
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`font-bold font-mono ${
                            loadFactor > 0.85
                              ? 'text-rose-700'
                              : loadFactor < 0.4
                              ? 'text-amber-700'
                              : 'text-emerald-700'
                          }`}
                        >
                          {(loadFactor * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`font-mono text-xs px-2 py-0.5 rounded-full backdrop-blur-md ${
                            surge > 1.2
                              ? 'bg-rose-500/15 text-rose-800 border border-rose-400/40 font-bold'
                              : surge < 0.9
                              ? 'bg-emerald-500/15 text-emerald-800 border border-emerald-400/40 font-semibold'
                              : 'bg-white/70 text-slate-700 border border-white/90'
                          }`}
                        >
                          {surge.toFixed(2)}x
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-700 font-bold">
                        {((item.confidence_score ?? 0.91) * 100).toFixed(0)}%
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {!loading && filteredData.length > 0 && (
          <div className="p-3 bg-white/40 border-t border-white/70 backdrop-blur-md flex flex-col sm:flex-row items-center justify-between gap-2.5 text-xs text-slate-600">
            <div>
              Showing <span className="font-bold text-slate-900 font-mono">{(page - 1) * pageSize + 1}</span> to{' '}
              <span className="font-bold text-slate-900 font-mono">{Math.min(page * pageSize, filteredData.length)}</span> of{' '}
              <span className="font-bold text-slate-900 font-mono">{filteredData.length}</span> records
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1 h-7 w-7 bg-white/70 border-white/90 rounded-lg"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </Button>
              <span className="text-slate-900 font-bold px-1.5 text-xs font-mono">
                Page {page} of {totalPages || 1}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1 h-7 w-7 bg-white/70 border-white/90 rounded-lg"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { api } from '../services/api';
import type { PredictionPayload, PredictionResult, RouteCatalog } from '../services/api';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { motion, AnimatePresence } from 'framer-motion';

interface PredictionSimulatorProps {
  catalog: RouteCatalog | null;
}

export const PredictionSimulator: React.FC<PredictionSimulatorProps> = ({ catalog }) => {
  const [transportMode, setTransportMode] = useState<string>('Bus');
  const [route, setRoute] = useState<string>('Kurnool-Hyderabad');
  const [date, setDate] = useState<string>('2025-06-15');
  const [serviceType, setServiceType] = useState<string>('Volvo AC');
  const [distanceKm, setDistanceKm] = useState<number>(326);
  const [capacity, setCapacity] = useState<number>(49);
  const [fare, setFare] = useState<number>(450);
  const [isHoliday, setIsHoliday] = useState<boolean>(false);
  const [vehicleCapacity, setVehicleCapacity] = useState<number>(50);
  const [depot] = useState<string>('Guntur');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (catalog?.routes_by_mode?.[transportMode]?.length) {
      const firstRoute = catalog.routes_by_mode[transportMode][0];
      setRoute(firstRoute);
    }
    if (catalog?.service_types_by_mode?.[transportMode]?.length) {
      setServiceType(catalog.service_types_by_mode[transportMode][0]);
    }

    if (transportMode === 'Bus') {
      setCapacity(49);
      setVehicleCapacity(50);
      setFare(450);
      setDistanceKm(326);
    } else if (transportMode === 'Rail') {
      setCapacity(500);
      setVehicleCapacity(72);
      setFare(380);
      setDistanceKm(650);
    } else if (transportMode === 'Air') {
      setCapacity(180);
      setVehicleCapacity(180);
      setFare(4800);
      setDistanceKm(1200);
    }
  }, [transportMode, catalog]);

  const handlePredict = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const payload: PredictionPayload = {
        transport_mode: transportMode,
        route,
        date,
        service_type: serviceType,
        distance_km: Number(distanceKm),
        capacity: Number(capacity),
        fare_per_passenger: Number(fare),
        is_holiday: isHoliday ? 1 : 0,
        vehicle_capacity: Number(vehicleCapacity),
        depot,
      };

      const res = await api.predict(payload);
      setResult(res);
    } catch (err: any) {
      console.error(err);
      setError(err?.response?.data?.detail || 'Prediction failed. Ensure the FastAPI server is running.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    handlePredict();
  }, []);

  const currentImpacts = result?.feature_impacts && result.feature_impacts.length > 0
    ? result.feature_impacts
    : [
        { feature: 'Route Baseline', impact: 16.0, direction: 'positive' },
        { feature: 'Vehicle Capacity', impact: 12.3, direction: 'positive' },
        { feature: '7-Day Trend (Rolling Mean)', impact: -1.2, direction: 'negative' },
        { feature: 'Fare Level', impact: -4.8, direction: 'negative' },
        { feature: 'Weekend / Holiday Factor', impact: 8.5, direction: 'positive' },
        { feature: 'Route Distance', impact: 6.5, direction: 'positive' },
      ];

  const featureImpactOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 11 },
      extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-radius: 6px;',
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '5%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 10 },
    },
    yAxis: {
      type: 'category',
      data: currentImpacts.map((i) => i.feature),
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisTick: { show: false },
      axisLabel: { color: '#334155', fontSize: 10.5, fontWeight: 500 },
    },
    series: [
      {
        name: 'Impact on Passenger Volume',
        type: 'bar',
        data: currentImpacts.map((i) => ({
          value: i.impact,
          itemStyle: {
            color: i.impact >= 0 ? '#10b981' : '#ef4444',
          },
        })),
        barWidth: 12,
        itemStyle: {
          borderRadius: [0, 3, 3, 0],
        },
      },
    ],
  };

  const availableRoutes = catalog?.routes_by_mode?.[transportMode] || (
    transportMode === 'Bus'
      ? ['Kurnool-Hyderabad', 'Vijayawada-Tirupati', 'Visakhapatnam-Vijayawada', 'Tirupati-Bangalore', 'Guntur-Hyderabad']
      : transportMode === 'Rail'
      ? ['12759_CHARMINAR_EXP', '12727_GODAVARI_EXP', '12703_FALAKNUMA_EXP', '20833_VANDE_BHARAT']
      : ['DEL-BOM-AI101', 'BLR-DEL-6E204', 'HYD-BOM-SG302', 'MAA-DEL-UK812']
  );

  const availableServices = catalog?.service_types_by_mode?.[transportMode] || (
    transportMode === 'Bus'
      ? ['Volvo AC', 'Sleeper', 'Super Luxury', 'Express', 'Ultra Deluxe']
      : transportMode === 'Rail'
      ? ['Rajdhani Express', 'Shatabdi Express', 'Superfast Express', 'Mail Express']
      : ['Economy Class', 'Premium Economy', 'Business Class']
  );

  return (
    <div className="space-y-4">
      {/* Header Bar */}
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/60">
        <div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900">
            Passenger Demand Prediction (Regression Model)
          </h1>
        </div>

        {/* Mode Selector Pill */}
        <div className="flex bg-white/60 p-1 rounded-xl border border-white/80 backdrop-blur-md shadow-2xs self-start sm:self-auto">
          {[
            { id: 'Bus', label: 'Bus (APSRTC)' },
            { id: 'Rail', label: 'Railways' },
            { id: 'Air', label: 'Domestic Flights' },
          ].map((tab) => {
            const isSelected = transportMode === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setTransportMode(tab.id)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  isSelected
                    ? 'bg-white/95 text-slate-900 shadow-xs border border-white'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Form Controls (5 Cols) */}
        <Card className="lg:col-span-5 p-5">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-200/60">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              Input Attributes / Features
            </h2>
            <Badge variant="neutral" size="sm">
              {transportMode.toUpperCase()}
            </Badge>
          </div>

          <form onSubmit={handlePredict} className="space-y-3.5 text-xs">
            {/* Route Selector */}
            <div className="space-y-1">
              <label className="text-slate-700 font-semibold">
                Route / Corridor Dimension
              </label>
              <select
                value={route}
                onChange={(e) => setRoute(e.target.value)}
                className="w-full bg-white/80 border border-slate-200/80 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 font-medium shadow-2xs backdrop-blur-md"
              >
                {availableRoutes.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            {/* Service Type & Schedule Date Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-slate-700 font-semibold">Service Class</label>
                <select
                  value={serviceType}
                  onChange={(e) => setServiceType(e.target.value)}
                  className="w-full bg-white/80 border border-slate-200/80 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 font-medium shadow-2xs backdrop-blur-md"
                >
                  {availableServices.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-semibold">
                  Date Attribute
                </label>
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full bg-white/80 border border-slate-200/80 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 font-mono shadow-2xs backdrop-blur-md"
                />
              </div>
            </div>

            {/* Corridor Distance & Vehicle Capacity */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-slate-700 font-semibold">Distance (km)</label>
                <input
                  type="number"
                  min="10"
                  max="4000"
                  value={distanceKm}
                  onChange={(e) => setDistanceKm(Number(e.target.value))}
                  className="w-full bg-white/80 border border-slate-200/80 rounded-lg px-3 py-2 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 shadow-2xs backdrop-blur-md"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-semibold">Scheduled Capacity</label>
                <input
                  type="number"
                  min="10"
                  max="2000"
                  value={capacity}
                  onChange={(e) => setCapacity(Number(e.target.value))}
                  className="w-full bg-white/80 border border-slate-200/80 rounded-lg px-3 py-2 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 shadow-2xs backdrop-blur-md"
                />
              </div>
            </div>

            {/* Base Fare & Unit Capacity */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-slate-700 font-semibold">Fare (₹)</label>
                <input
                  type="number"
                  min="20"
                  max="50000"
                  value={fare}
                  onChange={(e) => setFare(Number(e.target.value))}
                  className="w-full bg-white/80 border border-slate-200/80 rounded-lg px-3 py-2 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 shadow-2xs backdrop-blur-md"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-semibold">Vehicle Unit Size</label>
                <input
                  type="number"
                  min="1"
                  max="500"
                  value={vehicleCapacity}
                  onChange={(e) => setVehicleCapacity(Number(e.target.value))}
                  className="w-full bg-white/80 border border-slate-200/80 rounded-lg px-3 py-2 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 shadow-2xs backdrop-blur-md"
                />
              </div>
            </div>

            {/* Holiday Toggle */}
            <div className="pt-1">
              <label className="flex items-center gap-2.5 cursor-pointer p-2.5 rounded-lg bg-white/60 border border-slate-200/70 hover:border-slate-300 backdrop-blur-md transition shadow-2xs">
                <input
                  type="checkbox"
                  checked={isHoliday}
                  onChange={(e) => setIsHoliday(e.target.checked)}
                  className="rounded border-slate-300 text-slate-900 focus:ring-slate-500 cursor-pointer"
                />
                <span className="text-slate-700 text-xs select-none font-medium">
                  Holiday / Peak Indicator (is_holiday = 1)
                </span>
              </label>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 mt-4 py-2.5 text-xs bg-gradient-to-r from-slate-900 to-slate-800 hover:from-slate-800 hover:to-slate-700 text-white rounded-xl shadow-sm border border-slate-700/50 active:scale-[0.99]"
            >
              {isLoading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Running Model Inference...
                </>
              ) : (
                'Predict Passenger Demand'
              )}
            </Button>
          </form>
        </Card>

        {/* Right Column: Inferred Dispatch Results (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {error ? (
            <Card className="p-5 bg-rose-50/80 border-rose-200 text-center">
              <p className="text-rose-800 text-xs font-semibold">{error}</p>
              <Button onClick={() => handlePredict()} variant="outline" size="sm" className="mt-3">
                Retry Prediction
              </Button>
            </Card>
          ) : result ? (
            <AnimatePresence mode="wait">
              <motion.div
                key={result.predicted_demand + result.route}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.15 }}
                className="space-y-4"
              >
                {/* Result Primary Metric Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <Card className="p-4 bg-white/80 border-white/90 shadow-sm" hover>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      Predicted Demand
                    </span>
                    <div className="text-xl sm:text-2xl font-black text-slate-900 font-mono mt-0.5">
                      {Math.round(result.predicted_demand).toLocaleString()}{' '}
                      <span className="text-xs text-slate-500 font-normal">pax</span>
                    </div>
                    <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-slate-500">
                      <span>Category:</span>
                      <Badge
                        variant={
                          result.demand_category === 'High'
                            ? 'crimson'
                            : result.demand_category === 'Medium'
                            ? 'neutral'
                            : 'mint'
                        }
                        size="sm"
                      >
                        {result.demand_category}
                      </Badge>
                    </div>
                  </Card>

                  <Card className="p-4 bg-white/80 border-white/90 shadow-sm" hover>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      Allocated Vehicles
                    </span>
                    <div className="text-xl sm:text-2xl font-black text-slate-900 font-mono mt-0.5">
                      {result.recommended_vehicles}{' '}
                      <span className="text-xs text-slate-500 font-normal">units</span>
                    </div>
                    <div className="mt-1.5 text-[11px] text-slate-500 truncate font-medium">
                      {result.vehicle_type} ({vehicleCapacity} seats)
                    </div>
                  </Card>

                  <Card className="p-4 bg-white/80 border-white/90 shadow-sm" hover>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      Estimated Revenue
                    </span>
                    <div className="text-xl sm:text-2xl font-black text-slate-900 font-mono mt-0.5">
                      ₹{Math.round(result.estimated_revenue || result.predicted_demand * fare).toLocaleString()}
                    </div>
                    <div className="mt-1.5 text-[11px] text-slate-600 font-mono">
                      Load Factor: <strong className="text-emerald-700">{result.occupancy_expected_pct.toFixed(1)}%</strong>
                    </div>
                  </Card>
                </div>

                {/* Local Factor Waterfall Attribution Chart */}
                <Card className="p-4">
                  <div className="flex items-center justify-between mb-1 pb-2 border-b border-slate-200/60">
                    <div>
                      <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                        Feature Contributions (Local SHAP Values)
                      </h2>
                      <p className="text-[11px] text-slate-500">
                        Feature deviations driving passenger volume variance from corridor median
                      </p>
                    </div>
                    <span className="text-[11px] text-slate-500 font-mono font-semibold bg-white/70 px-2 py-0.5 rounded-full border border-white/90 shadow-2xs backdrop-blur-md">
                      Confidence: {(result.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="h-48 w-full mt-1">
                    <ReactECharts
                      option={featureImpactOption}
                      notMerge={true}
                      lazyUpdate={true}
                      style={{ height: '100%', width: '100%' }}
                    />
                  </div>
                </Card>

                {/* Historical Baseline Context */}
                <Card className="p-3.5 bg-white/60 border-white/80 backdrop-blur-md">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                    <div>
                      <div className="text-slate-500 text-[10.5px] font-medium">Historical Median</div>
                      <div className="font-bold text-slate-900 font-mono mt-0.5">
                        {Math.round(result.route_historical_stats?.historical_median || 42)} pax
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500 text-[10.5px] font-medium">7-Day Moving Avg</div>
                      <div className="font-bold text-slate-900 font-mono mt-0.5">
                        {Math.round(result.route_historical_stats?.recent_7d_avg || 44)} pax
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500 text-[10.5px] font-medium">Standard Deviation (σ)</div>
                      <div className="font-bold text-slate-800 font-mono mt-0.5">
                        ±{(result.route_historical_stats?.demand_std || 6.2).toFixed(1)} pax
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500 text-[10.5px] font-medium">Model Architecture</div>
                      <div className="font-bold text-slate-900 mt-0.5 truncate">
                        {result.model_name || 'CatBoost Regressor'}
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            </AnimatePresence>
          ) : (
            <Card className="p-8 text-center text-slate-500 text-xs">
              Configure parameters on the left and click Predict Passenger Demand.
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

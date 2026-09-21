import React, { useState, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bus,
  Train,
  Plane,
  ArrowRight,
  Zap,
  Activity,
  X,
  Gauge,
  Compass,
  Clock,
  Sparkles,
  TrendingUp,
  Map,
  Users,
  IndianRupee,
  Flame,
  Layers,
} from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { StatCard } from './ui/StatCard';
import { Button } from './ui/Button';

// Geo coordinates of major transit hubs
export interface TransitHub {
  name: string;
  shortName: string;
  code: string;
  coords: [number, number]; // [lng, lat]
  type: 'metro' | 'hub' | 'regional';
  throughput: number; // pax / day
  labelPosition: 'top' | 'bottom' | 'left' | 'right' | 'topRight' | 'bottomRight' | 'bottomLeft';
}

export interface TransitCorridor {
  id: string;
  name: string;
  mode: 'Bus' | 'Rail' | 'Air';
  from: string;
  to: string;
  fromCoords: [number, number];
  toCoords: [number, number];
  predictedDemand: number;
  historicalMedian: number;
  capacity: number;
  occupancy: number; // percentage (e.g. 84.5)
  fare: number;
  distanceKm: number;
  recommendedFleet: number;
  fleetType: string;
  peakHours: string;
  surgeMultiplier: number;
  triage: 'Surge' | 'Optimal' | 'Low';
  operator: string;
}

const TRANSIT_HUBS: Record<string, TransitHub> = {
  Hyderabad: { name: 'Hyderabad (HYD)', shortName: 'Hyderabad', code: 'HYD', coords: [78.4867, 17.385], type: 'metro', throughput: 48500, labelPosition: 'top' },
  Vijayawada: { name: 'Vijayawada (BZA)', shortName: 'Vijayawada', code: 'BZA', coords: [80.648, 16.5062], type: 'hub', throughput: 32400, labelPosition: 'top' },
  Visakhapatnam: { name: 'Visakhapatnam (VSKP)', shortName: 'Visakhapatnam', code: 'VSKP', coords: [83.2185, 17.6868], type: 'hub', throughput: 28900, labelPosition: 'right' },
  Tirupati: { name: 'Tirupati (TPTY)', shortName: 'Tirupati', code: 'TPTY', coords: [79.4192, 13.6288], type: 'hub', throughput: 24600, labelPosition: 'bottom' },
  Kurnool: { name: 'Kurnool (KNL)', shortName: 'Kurnool', code: 'KNL', coords: [78.0373, 15.8281], type: 'regional', throughput: 14200, labelPosition: 'left' },
  Guntur: { name: 'Guntur (GNT)', shortName: 'Guntur', code: 'GNT', coords: [80.4365, 16.3067], type: 'regional', throughput: 16800, labelPosition: 'bottom' },
  Anantapur: { name: 'Anantapur (ATP)', shortName: 'Anantapur', code: 'ATP', coords: [77.6006, 14.6819], type: 'regional', throughput: 11500, labelPosition: 'left' },
  Nellore: { name: 'Nellore (NLR)', shortName: 'Nellore', code: 'NLR', coords: [79.9864, 14.4426], type: 'regional', throughput: 13800, labelPosition: 'right' },
  Kadapa: { name: 'Kadapa (CDP)', shortName: 'Kadapa', code: 'CDP', coords: [78.8242, 14.4673], type: 'regional', throughput: 10400, labelPosition: 'bottomLeft' },
  Bengaluru: { name: 'Bengaluru (BLR)', shortName: 'Bengaluru', code: 'BLR', coords: [77.5946, 12.9716], type: 'metro', throughput: 64000, labelPosition: 'bottom' },
  Chennai: { name: 'Chennai (MAA)', shortName: 'Chennai', code: 'MAA', coords: [80.2707, 13.0827], type: 'metro', throughput: 58000, labelPosition: 'right' },
  Mumbai: { name: 'Mumbai (BOM)', shortName: 'Mumbai', code: 'BOM', coords: [72.8777, 19.076], type: 'metro', throughput: 82000, labelPosition: 'left' },
  Delhi: { name: 'New Delhi (DEL)', shortName: 'New Delhi', code: 'DEL', coords: [77.1025, 28.7041], type: 'metro', throughput: 95000, labelPosition: 'top' },
  Kolkata: { name: 'Kolkata (CCU)', shortName: 'Kolkata', code: 'CCU', coords: [88.3639, 22.5726], type: 'metro', throughput: 51000, labelPosition: 'right' },
};

const CORRIDORS: TransitCorridor[] = [
  // 🚌 APSRTC Bus Corridors
  {
    id: 'bus-hyd-vja',
    name: 'Hyderabad — Vijayawada Express Corridor',
    mode: 'Bus',
    from: 'Hyderabad',
    to: 'Vijayawada',
    fromCoords: TRANSIT_HUBS.Hyderabad.coords,
    toCoords: TRANSIT_HUBS.Vijayawada.coords,
    predictedDemand: 54,
    historicalMedian: 42,
    capacity: 49,
    occupancy: 94.2,
    fare: 450,
    distanceKm: 275,
    recommendedFleet: 2,
    fleetType: 'Super Luxury / Volvo AC',
    peakHours: '06:00 - 09:30 & 18:00 - 21:30',
    surgeMultiplier: 1.25,
    triage: 'Surge',
    operator: 'APSRTC',
  },
  {
    id: 'bus-vja-tpty',
    name: 'Vijayawada — Tirupati Trunk Route',
    mode: 'Bus',
    from: 'Vijayawada',
    to: 'Tirupati',
    fromCoords: TRANSIT_HUBS.Vijayawada.coords,
    toCoords: TRANSIT_HUBS.Tirupati.coords,
    predictedDemand: 46,
    historicalMedian: 38,
    capacity: 49,
    occupancy: 88.5,
    fare: 520,
    distanceKm: 380,
    recommendedFleet: 1,
    fleetType: 'Garuda Plus Sleeper',
    peakHours: '20:00 - 23:00 (Overnight)',
    surgeMultiplier: 1.15,
    triage: 'Optimal',
    operator: 'APSRTC',
  },
  {
    id: 'bus-vskp-vja',
    name: 'Visakhapatnam — Vijayawada Coastal Route',
    mode: 'Bus',
    from: 'Visakhapatnam',
    to: 'Vijayawada',
    fromCoords: TRANSIT_HUBS.Visakhapatnam.coords,
    toCoords: TRANSIT_HUBS.Vijayawada.coords,
    predictedDemand: 48,
    historicalMedian: 39,
    capacity: 49,
    occupancy: 92.0,
    fare: 480,
    distanceKm: 350,
    recommendedFleet: 1,
    fleetType: 'Ultra Deluxe Express',
    peakHours: '07:00 - 10:00 & 17:00 - 20:00',
    surgeMultiplier: 1.2,
    triage: 'Surge',
    operator: 'APSRTC',
  },
  {
    id: 'bus-knl-hyd',
    name: 'Kurnool — Hyderabad Highway Line',
    mode: 'Bus',
    from: 'Kurnool',
    to: 'Hyderabad',
    fromCoords: TRANSIT_HUBS.Kurnool.coords,
    toCoords: TRANSIT_HUBS.Hyderabad.coords,
    predictedDemand: 42,
    historicalMedian: 35,
    capacity: 49,
    occupancy: 85.7,
    fare: 350,
    distanceKm: 215,
    recommendedFleet: 1,
    fleetType: 'Express Bus',
    peakHours: '06:30 - 09:00',
    surgeMultiplier: 1.1,
    triage: 'Optimal',
    operator: 'APSRTC',
  },
  {
    id: 'bus-tpty-blr',
    name: 'Tirupati — Bengaluru Inter-State Shuttle',
    mode: 'Bus',
    from: 'Tirupati',
    to: 'Bengaluru',
    fromCoords: TRANSIT_HUBS.Tirupati.coords,
    toCoords: TRANSIT_HUBS.Bengaluru.coords,
    predictedDemand: 45,
    historicalMedian: 36,
    capacity: 49,
    occupancy: 91.8,
    fare: 410,
    distanceKm: 250,
    recommendedFleet: 1,
    fleetType: 'Amaravati Multi-Axle',
    peakHours: '05:00 - 08:30 & 16:00 - 19:30',
    surgeMultiplier: 1.2,
    triage: 'Surge',
    operator: 'APSRTC',
  },
  {
    id: 'bus-gnt-hyd',
    name: 'Guntur — Hyderabad Commuter Corridor',
    mode: 'Bus',
    from: 'Guntur',
    to: 'Hyderabad',
    fromCoords: TRANSIT_HUBS.Guntur.coords,
    toCoords: TRANSIT_HUBS.Hyderabad.coords,
    predictedDemand: 39,
    historicalMedian: 32,
    capacity: 49,
    occupancy: 79.5,
    fare: 420,
    distanceKm: 290,
    recommendedFleet: 1,
    fleetType: 'Super Luxury',
    peakHours: '07:00 - 09:30',
    surgeMultiplier: 1.05,
    triage: 'Optimal',
    operator: 'APSRTC',
  },

  // 🚆 Indian Railways Lines
  {
    id: 'rail-charminar',
    name: '12759 Charminar Express (SC — MAS)',
    mode: 'Rail',
    from: 'Hyderabad',
    to: 'Chennai',
    fromCoords: TRANSIT_HUBS.Hyderabad.coords,
    toCoords: TRANSIT_HUBS.Chennai.coords,
    predictedDemand: 248,
    historicalMedian: 215,
    capacity: 280,
    occupancy: 88.6,
    fare: 380,
    distanceKm: 708,
    recommendedFleet: 24,
    fleetType: 'LHB Superfast Rake',
    peakHours: '18:30 (Daily Departure)',
    surgeMultiplier: 1.15,
    triage: 'Optimal',
    operator: 'Indian Railways (SCR)',
  },
  {
    id: 'rail-godavari',
    name: '12727 Godavari Express (VSKP — HYD)',
    mode: 'Rail',
    from: 'Visakhapatnam',
    to: 'Hyderabad',
    fromCoords: TRANSIT_HUBS.Visakhapatnam.coords,
    toCoords: TRANSIT_HUBS.Hyderabad.coords,
    predictedDemand: 265,
    historicalMedian: 220,
    capacity: 280,
    occupancy: 94.6,
    fare: 410,
    distanceKm: 700,
    recommendedFleet: 24,
    fleetType: 'LHB Express Coaches',
    peakHours: '17:20 (Daily Departure)',
    surgeMultiplier: 1.25,
    triage: 'Surge',
    operator: 'Indian Railways (SCR)',
  },
  {
    id: 'rail-vandebharat',
    name: '20833 Vande Bharat (VSKP — SC)',
    mode: 'Rail',
    from: 'Visakhapatnam',
    to: 'Hyderabad',
    fromCoords: TRANSIT_HUBS.Visakhapatnam.coords,
    toCoords: TRANSIT_HUBS.Hyderabad.coords,
    predictedDemand: 220,
    historicalMedian: 195,
    capacity: 230,
    occupancy: 95.6,
    fare: 1450,
    distanceKm: 700,
    recommendedFleet: 16,
    fleetType: 'Vande Bharat Semi-High Speed',
    peakHours: '05:45 (Morning Express)',
    surgeMultiplier: 1.3,
    triage: 'Surge',
    operator: 'Indian Railways (ECoR)',
  },
  {
    id: 'rail-rayalaseema',
    name: '12793 Rayalaseema Express (TPTY — HYD)',
    mode: 'Rail',
    from: 'Tirupati',
    to: 'Hyderabad',
    fromCoords: TRANSIT_HUBS.Tirupati.coords,
    toCoords: TRANSIT_HUBS.Hyderabad.coords,
    predictedDemand: 235,
    historicalMedian: 205,
    capacity: 280,
    occupancy: 83.9,
    fare: 395,
    distanceKm: 715,
    recommendedFleet: 22,
    fleetType: 'Express Sleeper & 3AC',
    peakHours: '17:30 (Daily Departure)',
    surgeMultiplier: 1.1,
    triage: 'Optimal',
    operator: 'Indian Railways (SCR)',
  },
  {
    id: 'rail-janmabhoomi',
    name: '12805 Janmabhoomi Express (VSKP — GNT)',
    mode: 'Rail',
    from: 'Visakhapatnam',
    to: 'Guntur',
    fromCoords: TRANSIT_HUBS.Visakhapatnam.coords,
    toCoords: TRANSIT_HUBS.Guntur.coords,
    predictedDemand: 210,
    historicalMedian: 185,
    capacity: 240,
    occupancy: 87.5,
    fare: 280,
    distanceKm: 382,
    recommendedFleet: 18,
    fleetType: 'Intercity Chair Car Rake',
    peakHours: '06:20 (Morning Intercity)',
    surgeMultiplier: 1.12,
    triage: 'Optimal',
    operator: 'Indian Railways (ECoR)',
  },
  {
    id: 'rail-falaknuma',
    name: '12703 Falaknuma Express (HWH — SC)',
    mode: 'Rail',
    from: 'Kolkata',
    to: 'Hyderabad',
    fromCoords: TRANSIT_HUBS.Kolkata.coords,
    toCoords: TRANSIT_HUBS.Hyderabad.coords,
    predictedDemand: 240,
    historicalMedian: 210,
    capacity: 280,
    occupancy: 85.7,
    fare: 620,
    distanceKm: 1545,
    recommendedFleet: 22,
    fleetType: 'Superfast Mail Express',
    peakHours: '08:35 (Daily Departure)',
    surgeMultiplier: 1.1,
    triage: 'Optimal',
    operator: 'Indian Railways (SER)',
  },

  // ✈️ Domestic & Regional Air Corridors
  {
    id: 'air-hyd-vskp',
    name: 'HYD — VSKP (IndiGo 6E-542)',
    mode: 'Air',
    from: 'Hyderabad',
    to: 'Visakhapatnam',
    fromCoords: TRANSIT_HUBS.Hyderabad.coords,
    toCoords: TRANSIT_HUBS.Visakhapatnam.coords,
    predictedDemand: 82,
    historicalMedian: 74,
    capacity: 180,
    occupancy: 84.4,
    fare: 3400,
    distanceKm: 520,
    recommendedFleet: 1,
    fleetType: 'Airbus A320neo',
    peakHours: '06:15 & 19:40',
    surgeMultiplier: 1.18,
    triage: 'Optimal',
    operator: 'IndiGo Airlines',
  },
  {
    id: 'air-hyd-tpty',
    name: 'HYD — TPTY (Alliance Air 9I-871)',
    mode: 'Air',
    from: 'Hyderabad',
    to: 'Tirupati',
    fromCoords: TRANSIT_HUBS.Hyderabad.coords,
    toCoords: TRANSIT_HUBS.Tirupati.coords,
    predictedDemand: 68,
    historicalMedian: 58,
    capacity: 72,
    occupancy: 94.4,
    fare: 3100,
    distanceKm: 460,
    recommendedFleet: 1,
    fleetType: 'ATR 72-600',
    peakHours: '08:30 (Morning Pilgrimage)',
    surgeMultiplier: 1.3,
    triage: 'Surge',
    operator: 'Alliance Air',
  },
  {
    id: 'air-hyd-blr',
    name: 'HYD — BLR (Air India AI-512)',
    mode: 'Air',
    from: 'Hyderabad',
    to: 'Bengaluru',
    fromCoords: TRANSIT_HUBS.Hyderabad.coords,
    toCoords: TRANSIT_HUBS.Bengaluru.coords,
    predictedDemand: 92,
    historicalMedian: 80,
    capacity: 180,
    occupancy: 88.2,
    fare: 3600,
    distanceKm: 500,
    recommendedFleet: 1,
    fleetType: 'Airbus A320neo',
    peakHours: '07:15 & 20:30',
    surgeMultiplier: 1.2,
    triage: 'Optimal',
    operator: 'Air India',
  },
  {
    id: 'air-blr-del',
    name: 'BLR — DEL (IndiGo 6E-204)',
    mode: 'Air',
    from: 'Bengaluru',
    to: 'Delhi',
    fromCoords: TRANSIT_HUBS.Bengaluru.coords,
    toCoords: TRANSIT_HUBS.Delhi.coords,
    predictedDemand: 94,
    historicalMedian: 82,
    capacity: 180,
    occupancy: 91.2,
    fare: 5400,
    distanceKm: 1740,
    recommendedFleet: 1,
    fleetType: 'Airbus A320neo',
    peakHours: '07:00 & 19:30 (Trunk Slots)',
    surgeMultiplier: 1.35,
    triage: 'Surge',
    operator: 'IndiGo Airlines',
  },
  {
    id: 'air-del-bom',
    name: 'DEL — BOM (Air India AI-101)',
    mode: 'Air',
    from: 'Delhi',
    to: 'Mumbai',
    fromCoords: TRANSIT_HUBS.Delhi.coords,
    toCoords: TRANSIT_HUBS.Mumbai.coords,
    predictedDemand: 98,
    historicalMedian: 86,
    capacity: 180,
    occupancy: 94.4,
    fare: 5800,
    distanceKm: 1140,
    recommendedFleet: 1,
    fleetType: 'Boeing 737 MAX',
    peakHours: '08:00 & 20:00 (Prime Metros)',
    surgeMultiplier: 1.4,
    triage: 'Surge',
    operator: 'Air India',
  },
  {
    id: 'air-hyd-bom',
    name: 'HYD — BOM (SpiceJet SG-302)',
    mode: 'Air',
    from: 'Hyderabad',
    to: 'Mumbai',
    fromCoords: TRANSIT_HUBS.Hyderabad.coords,
    toCoords: TRANSIT_HUBS.Mumbai.coords,
    predictedDemand: 86,
    historicalMedian: 78,
    capacity: 180,
    occupancy: 82.5,
    fare: 4200,
    distanceKm: 620,
    recommendedFleet: 1,
    fleetType: 'Boeing 737-800',
    peakHours: '10:15 & 18:45',
    surgeMultiplier: 1.15,
    triage: 'Optimal',
    operator: 'SpiceJet',
  },
  {
    id: 'air-maa-del',
    name: 'MAA — DEL (Vistara UK-812)',
    mode: 'Air',
    from: 'Chennai',
    to: 'Delhi',
    fromCoords: TRANSIT_HUBS.Chennai.coords,
    toCoords: TRANSIT_HUBS.Delhi.coords,
    predictedDemand: 90,
    historicalMedian: 80,
    capacity: 180,
    occupancy: 86.8,
    fare: 5600,
    distanceKm: 1760,
    recommendedFleet: 1,
    fleetType: 'Airbus A321LR',
    peakHours: '06:45 & 17:30',
    surgeMultiplier: 1.25,
    triage: 'Optimal',
    operator: 'Vistara',
  },
];

// Regional AP & TG hub names set for fast spatial bounding
const REGIONAL_HUB_NAMES = new Set([
  'Hyderabad', 'Vijayawada', 'Visakhapatnam', 'Tirupati', 'Kurnool',
  'Guntur', 'Anantapur', 'Nellore', 'Kadapa', 'Bengaluru', 'Chennai'
]);

// India subcontinent boundary outline coordinates
const INDIA_LANDMASS_OUTLINE: [number, number][] = [
  [74.5, 34.5], [77.5, 34.5], [79.0, 31.0], [80.5, 29.5], [88.5, 27.5],
  [89.5, 26.0], [92.0, 26.0], [92.5, 24.0], [91.0, 22.5], [88.5, 22.0],
  [86.8, 20.5], [83.5, 18.0], [81.5, 16.5], [80.3, 13.5], [79.8, 10.5],
  [77.6, 8.2], [76.5, 9.8], [74.8, 14.5], [73.0, 19.0], [70.0, 21.0],
  [69.0, 23.5], [71.0, 25.5], [71.5, 28.5], [74.0, 32.0], [74.5, 34.5]
];

// Regional Andhra Pradesh & Telangana polygon bounds
const REGIONAL_AP_TG_ZONE: [number, number][] = [
  [77.2, 19.8], [79.5, 19.9], [81.3, 18.8], [83.5, 18.4], [84.3, 19.0],
  [83.5, 17.6], [81.8, 16.2], [80.2, 13.8], [79.5, 13.2], [78.2, 13.5],
  [76.8, 14.8], [77.4, 16.5], [77.8, 18.2], [77.2, 19.8]
];

interface NetworkGeoMapProps {
  onNavigateToPredict?: (routeId?: string) => void;
}

export const NetworkGeoMap: React.FC<NetworkGeoMapProps> = ({ onNavigateToPredict }) => {
  const [selectedMode, setSelectedMode] = useState<'all' | 'Bus' | 'Rail' | 'Air'>('all');
  const [viewScope, setViewScope] = useState<'national' | 'regional'>('national');
  const [selectedMetric, setSelectedMetric] = useState<'demand' | 'occupancy' | 'fare'>('demand');
  const [activeCorridorId, setActiveCorridorId] = useState<string>(CORRIDORS[0].id);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true);

  // Automatically adjust view scope when Bus mode is chosen
  const handleModeChange = (mode: 'all' | 'Bus' | 'Rail' | 'Air') => {
    setSelectedMode(mode);
  };

  // Filtered corridors based on mode & scope
  const filteredCorridors = useMemo(() => {
    let list = CORRIDORS;
    if (viewScope === 'regional') {
      list = list.filter((c) => REGIONAL_HUB_NAMES.has(c.from) && REGIONAL_HUB_NAMES.has(c.to));
    }
    if (selectedMode !== 'all') {
      const modeMatches = list.filter((c) => c.mode === selectedMode);
      list = modeMatches.length > 0 ? modeMatches : list;
    }
    return list;
  }, [selectedMode, viewScope]);

  // Sorted corridors for the Quick Focus / Leaderboard bar based on the active highlighted metric
  const sortedCorridors = useMemo(() => {
    return [...filteredCorridors].sort((a, b) => {
      if (selectedMetric === 'demand') {
        return b.predictedDemand - a.predictedDemand;
      } else if (selectedMetric === 'occupancy') {
        return b.occupancy - a.occupancy;
      } else {
        return b.fare - a.fare;
      }
    });
  }, [filteredCorridors, selectedMetric]);

  const activeCorridor = useMemo(() => {
    return filteredCorridors.find((c) => c.id === activeCorridorId) || filteredCorridors[0] || CORRIDORS[0];
  }, [filteredCorridors, activeCorridorId]);

  // Metric Legend statistics counts
  const metricStats = useMemo(() => {
    if (selectedMetric === 'demand') {
      const high = filteredCorridors.filter((c) => c.predictedDemand >= 200).length;
      const med = filteredCorridors.filter((c) => c.predictedDemand >= 70 && c.predictedDemand < 200).length;
      const low = filteredCorridors.filter((c) => c.predictedDemand < 70).length;
      return { high, med, low };
    } else if (selectedMetric === 'occupancy') {
      const high = filteredCorridors.filter((c) => c.occupancy >= 92).length;
      const med = filteredCorridors.filter((c) => c.occupancy >= 85 && c.occupancy < 92).length;
      const low = filteredCorridors.filter((c) => c.occupancy < 85).length;
      return { high, med, low };
    } else {
      const high = filteredCorridors.filter((c) => c.fare >= 3000).length;
      const med = filteredCorridors.filter((c) => c.fare >= 500 && c.fare < 3000).length;
      const low = filteredCorridors.filter((c) => c.fare < 500).length;
      return { high, med, low };
    }
  }, [filteredCorridors, selectedMetric]);

  // ECharts Geographic Map Option
  const mapOption = useMemo(() => {
    const isRegional = viewScope === 'regional';

    // Filter hubs based on view scope
    const activeHubs = Object.values(TRANSIT_HUBS).filter((h) => {
      if (!isRegional) return true;
      return [
        'Hyderabad', 'Vijayawada', 'Visakhapatnam', 'Tirupati', 'Kurnool',
        'Guntur', 'Anantapur', 'Nellore', 'Kadapa', 'Bengaluru', 'Chennai'
      ].includes(h.shortName);
    });

    const metroHubs = activeHubs
      .filter((h) => h.type === 'metro')
      .map((h) => ({
        name: h.name,
        shortName: h.shortName,
        value: [...h.coords, h.throughput],
        labelPos: h.labelPosition,
        itemStyle: { color: selectedMetric === 'occupancy' ? '#e11d48' : '#4f46e5' },
      }));

    const regionalHubs = activeHubs
      .filter((h) => h.type !== 'metro')
      .map((h) => ({
        name: h.name,
        shortName: h.shortName,
        value: [...h.coords, h.throughput],
        labelPos: h.labelPosition,
        itemStyle: { color: h.type === 'hub' ? '#0284c7' : '#64748b' },
      }));

    const lineData = filteredCorridors.map((c) => {
      let lineColor = '#0284c7';
      let lineWidth = isRegional ? 3.2 : 2.4;
      let lineOpacity = 0.88;

      if (selectedMetric === 'demand') {
        if (c.predictedDemand >= 200) {
          lineColor = '#4f46e5'; // Trunk heavy demand (Indigo)
          lineWidth = isRegional ? 4.8 : 3.8;
        } else if (c.predictedDemand >= 70) {
          lineColor = '#0284c7'; // Medium flow (Sky)
          lineWidth = isRegional ? 3.6 : 2.8;
        } else {
          lineColor = '#64748b'; // Regional line (Slate)
          lineWidth = isRegional ? 2.8 : 2.2;
        }
      } else if (selectedMetric === 'occupancy') {
        if (c.occupancy >= 92) {
          lineColor = '#e11d48'; // Critical Surge Stress (Rose-Red)
          lineWidth = isRegional ? 5.2 : 4.0;
          lineOpacity = 1.0;
        } else if (c.occupancy >= 85) {
          lineColor = '#d97706'; // High Load (Amber)
          lineWidth = isRegional ? 3.8 : 3.0;
        } else {
          lineColor = '#0284c7'; // Balanced / Under capacity (Sky)
          lineWidth = isRegional ? 2.6 : 2.0;
        }
      } else if (selectedMetric === 'fare') {
        if (c.fare >= 3000) {
          lineColor = '#9333ea'; // Premium Air Tier (Purple)
          lineWidth = isRegional ? 5.0 : 3.8;
        } else if (c.fare >= 500) {
          lineColor = '#0891b2'; // Express Rail Tier (Cyan)
          lineWidth = isRegional ? 3.6 : 2.8;
        } else {
          lineColor = '#475569'; // State Bus Tier (Slate)
          lineWidth = isRegional ? 2.6 : 2.0;
        }
      }

      const isSelected = activeCorridorId === c.id;

      return {
        fromName: c.from,
        toName: c.to,
        coords: [c.fromCoords, c.toCoords],
        corridorId: c.id,
        lineStyle: {
          color: isSelected ? '#f59e0b' : lineColor,
          width: isSelected ? lineWidth + 2 : lineWidth,
          opacity: isSelected ? 1.0 : lineOpacity,
          curveness: c.mode === 'Air' ? 0.28 : c.mode === 'Rail' ? 0.15 : 0.08,
        },
      };
    });

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#0f172a', fontSize: 11 },
        extraCssText: 'box-shadow: 0 4px 20px rgba(0,0,0,0.12); border-radius: 10px; padding: 10px;',
        formatter: (params: any) => {
          if (params.seriesType === 'lines') {
            const corr = CORRIDORS.find((c) => c.from === params.data.fromName && c.to === params.data.toName) ||
              CORRIDORS.find((c) => c.id === params.data.corridorId);
            if (!corr) return '';
            return `
              <div class="p-1 max-w-xs font-sans">
                <div class="flex items-center justify-between gap-2 mb-1">
                  <div class="font-bold text-slate-900 text-xs">${corr.name}</div>
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    corr.mode === 'Bus' ? 'bg-rose-100 text-rose-800' : corr.mode === 'Rail' ? 'bg-indigo-100 text-indigo-800' : 'bg-sky-100 text-sky-800'
                  }">${corr.mode}</span>
                </div>
                <div class="text-[10.5px] text-slate-500 font-mono mb-2">${corr.operator} • ${corr.distanceKm} km</div>
                
                <div class="p-1.5 rounded-lg mb-1.5 ${
                  selectedMetric === 'demand'
                    ? 'bg-indigo-50 border border-indigo-100 text-indigo-900'
                    : selectedMetric === 'occupancy'
                    ? 'bg-rose-50 border border-rose-100 text-rose-900'
                    : 'bg-purple-50 border border-purple-100 text-purple-900'
                }">
                  <div class="text-[10px] uppercase tracking-wider font-bold opacity-75">
                    Highlighted Metric (${selectedMetric.toUpperCase()})
                  </div>
                  <div class="text-sm font-black font-mono mt-0.5">
                    ${selectedMetric === 'demand' ? `${corr.predictedDemand} pax` : selectedMetric === 'occupancy' ? `${corr.occupancy}% Occupancy` : `₹${corr.fare} / Seat`}
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-1 text-[11px] pt-1 border-t border-slate-100">
                  <span class="text-slate-500">Peak Hours:</span>
                  <span class="text-slate-800 font-medium text-right">${corr.peakHours}</span>
                  <span class="text-slate-500">Fleet Dispatch:</span>
                  <span class="text-slate-800 font-bold font-mono text-right">${corr.recommendedFleet} units</span>
                </div>
              </div>
            `;
          }
          if (params.seriesType === 'scatter' || params.seriesType === 'effectScatter') {
            return `
              <div class="p-1 font-sans">
                <div class="font-bold text-slate-900 text-xs">${params.name}</div>
                <div class="text-[11px] text-slate-600 mt-1">Daily Transit Volume: <b class="text-indigo-600">${params.value[2]?.toLocaleString()} pax/day</b></div>
              </div>
            `;
          }
          return params.name;
        },
      },
      grid: {
        left: isRegional ? 30 : 20,
        right: isRegional ? 30 : 20,
        top: 25,
        bottom: 25,
        containLabel: false,
      },
      xAxis: {
        type: 'value',
        min: isRegional ? 76.5 : 68,
        max: isRegional ? 84.5 : 93,
        show: false,
      },
      yAxis: {
        type: 'value',
        min: isRegional ? 12.2 : 7,
        max: isRegional ? 18.8 : 35,
        show: false,
      },
      series: [
        // 1. Subcontinent & Regional Contour Outlines (Subtle Indigo/Slate dashed outlines)
        ...(!isRegional
          ? [
              {
                name: 'Subcontinent Outline',
                type: 'line',
                smooth: true,
                symbol: 'none',
                data: INDIA_LANDMASS_OUTLINE,
                lineStyle: {
                  color: 'rgba(99, 102, 241, 0.22)',
                  width: 1.5,
                  type: 'dashed',
                },
                areaStyle: {
                  color: {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 1,
                    y2: 1,
                    colorStops: [
                      { offset: 0, color: 'rgba(248, 250, 252, 0.7)' },
                      { offset: 1, color: 'rgba(238, 242, 255, 0.5)' },
                    ],
                  },
                },
                zlevel: 0,
                silent: true,
              },
            ]
          : [
              // Regional Andhra / Telangana Zone Outline (Clean subtle slate/indigo)
              {
                name: 'Regional Zone',
                type: 'line',
                smooth: true,
                symbol: 'none',
                data: REGIONAL_AP_TG_ZONE,
                lineStyle: {
                  color: 'rgba(99, 102, 241, 0.25)',
                  width: 1.5,
                  type: 'dashed',
                },
                areaStyle: {
                  color: {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 1,
                    y2: 1,
                    colorStops: [
                      { offset: 0, color: 'rgba(248, 250, 252, 0.7)' },
                      { offset: 1, color: 'rgba(238, 242, 255, 0.45)' },
                    ],
                  },
                },
                zlevel: 0,
                silent: true,
              },
            ]),
        // 2. Animated Flow Lines
        {
          type: 'lines',
          coordinateSystem: 'cartesian2d',
          zlevel: 2,
          effect: {
            show: true,
            period: 3.6,
            trailLength: 0.25,
            symbol: 'arrow',
            symbolSize: isRegional ? 7.5 : 5.8,
            color: '#ffffff',
          },
          lineStyle: {
            curveness: 0.15,
          },
          data: lineData,
        },
        // 3. Static Base Interactive Lines
        {
          type: 'lines',
          coordinateSystem: 'cartesian2d',
          zlevel: 3,
          data: lineData,
        },
        // 4. Pulsing Metro Hubs
        {
          type: 'effectScatter',
          coordinateSystem: 'cartesian2d',
          zlevel: 4,
          rippleEffect: {
            brushType: 'stroke',
            scale: 2.6,
            period: 3,
          },
          symbolSize: isRegional ? 16 : 13,
          data: metroHubs,
          label: {
            show: true,
            position: 'top',
            formatter: (params: any) => params.data.shortName,
            color: '#0f172a',
            fontSize: isRegional ? 11.5 : 10.5,
            fontWeight: 'bold',
            distance: 6,
          },
        },
        // 5. Regional Hub Nodes with Staggered Labels
        {
          type: 'scatter',
          coordinateSystem: 'cartesian2d',
          zlevel: 4,
          symbolSize: isRegional ? 11 : 8.5,
          data: regionalHubs,
          label: {
            show: true,
            position: (params: any) => params.data.labelPos || 'right',
            formatter: (params: any) => params.data.shortName,
            color: '#334155',
            fontSize: isRegional ? 10.5 : 9.5,
            fontWeight: 600,
            distance: 6,
          },
          emphasis: {
            scale: true,
            scaleSize: 1.4,
          },
        },
      ],
    };
  }, [filteredCorridors, activeCorridorId, viewScope, selectedMetric]);

  const onChartClick = (params: any) => {
    if (params.data && params.data.corridorId) {
      setActiveCorridorId(params.data.corridorId);
      setIsDrawerOpen(true);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/60">
        <div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Compass className="w-5 h-5 text-indigo-600" />
            Interactive Geospatial Transit Demand Map
          </h1>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Badge variant="neutral" size="sm" className="py-1 px-3 bg-white/70 border-white/90 shadow-2xs backdrop-blur-md font-mono text-[11px]">
            GIS Live Topology
          </Badge>
          <span className="text-[11px] font-bold text-indigo-900 bg-indigo-50 border border-indigo-200/80 px-2.5 py-1 rounded-full shadow-2xs flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-pulse" />
            {CORRIDORS.length} Corridors Active
          </span>
        </div>
      </div>

      {/* 4 KPI Metric Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          title="Monitored Transit Hubs"
          value="14 Major Hubs"
          subtitle="Bus Terminals • Rail Junctions • Airports"
        />
        <StatCard
          title="Active Corridors"
          value={`${filteredCorridors.length} Routes`}
          subtitle={viewScope === 'regional' ? 'AP & TG Regional Network' : 'Pan-India National Grid'}
        />
        <StatCard
          title={
            selectedMetric === 'demand'
              ? 'Avg Predicted Demand'
              : selectedMetric === 'occupancy'
              ? 'Avg Network Occupancy'
              : 'Avg Ticket Yield'
          }
          value={
            selectedMetric === 'demand'
              ? `${Math.round(filteredCorridors.reduce((acc, c) => acc + c.predictedDemand, 0) / (filteredCorridors.length || 1))} pax`
              : selectedMetric === 'occupancy'
              ? `${(filteredCorridors.reduce((acc, c) => acc + c.occupancy, 0) / (filteredCorridors.length || 1)).toFixed(1)}%`
              : `₹${Math.round(filteredCorridors.reduce((acc, c) => acc + c.fare, 0) / (filteredCorridors.length || 1))}`
          }
          subtitle={`Across ${filteredCorridors.length} active multi-modal routes`}
        />
        <StatCard
          title="Optimal Vehicle Fleet"
          value={`${filteredCorridors.reduce((acc, c) => acc + c.recommendedFleet, 0)} Units`}
          subtitle="Recommended synchronized vehicle dispatch"
        />
      </div>

      {/* Main Map & Inspection Drawer Container */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: GIS Map View */}
        <Card className={`${isDrawerOpen ? 'lg:col-span-8' : 'lg:col-span-12'} p-3 sm:p-4 flex flex-col justify-between transition-all duration-300 relative overflow-hidden min-h-[420px] sm:min-h-[580px]`}>
          <div>
            {/* Map Header Controls */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-200/60 mb-2">
              {/* Left group: Mode Pills & View Scope Toggle */}
              <div className="flex flex-wrap items-center gap-2">
                {/* Mode Selection Pills */}
                <div className="flex bg-white/80 p-0.5 rounded-xl border border-white/95 shadow-2xs backdrop-blur-md">
                  {[
                    { id: 'all', label: 'All Modes' },
                    { id: 'Bus', label: 'APSRTC Bus', icon: Bus },
                    { id: 'Rail', label: 'Railways', icon: Train },
                    { id: 'Air', label: 'Air Trunk', icon: Plane },
                  ].map((tab) => {
                    const Icon = tab.icon;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => handleModeChange(tab.id as any)}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                          selectedMode === tab.id
                            ? 'bg-white text-slate-900 shadow-xs border border-white font-bold'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        {Icon && <Icon className="w-3 h-3" />}
                        {tab.label}
                      </button>
                    );
                  })}
                </div>

                {/* View Scope Toggle */}
                <div className="flex bg-slate-100/80 p-0.5 rounded-xl border border-slate-200/80 text-[10.5px]">
                  <button
                    onClick={() => setViewScope('national')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-lg font-medium transition-all ${
                      viewScope === 'national'
                        ? 'bg-white text-slate-900 font-bold shadow-2xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <Map className="w-3 h-3" />
                    <span>National Grid</span>
                  </button>
                  <button
                    onClick={() => setViewScope('regional')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-lg font-medium transition-all ${
                      viewScope === 'regional'
                        ? 'bg-white text-indigo-900 font-bold shadow-2xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                    <span>AP & TG Mesh</span>
                  </button>
                </div>
              </div>

              {/* Metric View Selector: Demand | Occupancy | Fare */}
              <div className="flex items-center gap-1.5 text-xs bg-slate-50/90 p-1 rounded-xl border border-slate-200/70">
                <span className="text-[10.5px] font-bold text-slate-600 ml-1 hidden sm:inline flex items-center gap-1">
                  <Layers className="w-3 h-3 text-slate-500" />
                  Highlight:
                </span>
                {[
                  { id: 'demand', label: 'Demand', icon: Users, activeClass: 'bg-indigo-600 text-white shadow-xs font-bold' },
                  { id: 'occupancy', label: 'Occupancy', icon: Activity, activeClass: 'bg-rose-600 text-white shadow-xs font-bold' },
                  { id: 'fare', label: 'Fare', icon: IndianRupee, activeClass: 'bg-purple-600 text-white shadow-xs font-bold' },
                ].map((m) => {
                  const Icon = m.icon;
                  const isActive = selectedMetric === m.id;
                  return (
                    <button
                      key={m.id}
                      onClick={() => setSelectedMetric(m.id as any)}
                      className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] transition-all ${
                        isActive
                          ? m.activeClass
                          : 'bg-white/80 text-slate-600 hover:bg-white hover:text-slate-900'
                      }`}
                    >
                      <Icon className="w-3 h-3" />
                      <span>{m.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Map Canvas */}
            <div className="h-[470px] w-full relative">
              <ReactECharts
                option={mapOption}
                onEvents={{ click: onChartClick }}
                style={{ height: '100%', width: '100%' }}
                notMerge={true}
              />

              {/* Dynamic Map Legend Overlay */}
              <div className="absolute bottom-3 left-3 bg-white/95 p-3 rounded-xl border border-white/95 shadow-sm backdrop-blur-md text-[10.5px] space-y-1.5 z-10 min-w-[200px]">
                {selectedMetric === 'demand' && (
                  <>
                    <div className="flex items-center justify-between font-bold text-indigo-950 uppercase tracking-wider text-[10px] pb-1 border-b border-indigo-50">
                      <span className="flex items-center gap-1">
                        <Users className="w-3 h-3 text-indigo-600" />
                        Demand Volume Scale
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-slate-700">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1.5 rounded-full bg-indigo-600" />
                        <span>Trunk Line (&gt;200 pax)</span>
                      </div>
                      <span className="font-mono font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.2 rounded text-[9.5px]">{metricStats.high} routes</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-700">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1.5 rounded-full bg-sky-500" />
                        <span>Medium Flow (70–200 pax)</span>
                      </div>
                      <span className="font-mono font-bold text-sky-700 bg-sky-50 px-1.5 py-0.2 rounded text-[9.5px]">{metricStats.med} routes</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-700">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1.5 rounded-full bg-slate-400" />
                        <span>Regional Line (&lt;70 pax)</span>
                      </div>
                      <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.2 rounded text-[9.5px]">{metricStats.low} routes</span>
                    </div>
                  </>
                )}

                {selectedMetric === 'occupancy' && (
                  <>
                    <div className="flex items-center justify-between font-bold text-rose-950 uppercase tracking-wider text-[10px] pb-1 border-b border-rose-50">
                      <span className="flex items-center gap-1">
                        <Flame className="w-3 h-3 text-rose-600" />
                        Occupancy Stress Scale
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-rose-800 font-semibold">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1.5 rounded-full bg-rose-600" />
                        <span>Critical Surge (&gt;92%)</span>
                      </div>
                      <span className="font-mono font-bold text-rose-700 bg-rose-50 px-1.5 py-0.2 rounded text-[9.5px]">{metricStats.high} routes</span>
                    </div>
                    <div className="flex items-center justify-between text-amber-800 font-medium">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1.5 rounded-full bg-amber-500" />
                        <span>High Load (85–92%)</span>
                      </div>
                      <span className="font-mono font-bold text-amber-700 bg-amber-50 px-1.5 py-0.2 rounded text-[9.5px]">{metricStats.med} routes</span>
                    </div>
                    <div className="flex items-center justify-between text-sky-800">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1.5 rounded-full bg-sky-500" />
                        <span>Balanced (&lt;85%)</span>
                      </div>
                      <span className="font-mono font-bold text-sky-700 bg-sky-50 px-1.5 py-0.2 rounded text-[9.5px]">{metricStats.low} routes</span>
                    </div>
                  </>
                )}

                {selectedMetric === 'fare' && (
                  <>
                    <div className="flex items-center justify-between font-bold text-purple-950 uppercase tracking-wider text-[10px] pb-1 border-b border-purple-50">
                      <span className="flex items-center gap-1">
                        <IndianRupee className="w-3 h-3 text-purple-600" />
                        Fare Tier Spectrum
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-purple-900 font-medium">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1.5 rounded-full bg-purple-600" />
                        <span>Premium Trunk (&gt;₹3,000)</span>
                      </div>
                      <span className="font-mono font-bold text-purple-700 bg-purple-50 px-1.5 py-0.2 rounded text-[9.5px]">{metricStats.high} routes</span>
                    </div>
                    <div className="flex items-center justify-between text-cyan-900 font-medium">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1.5 rounded-full bg-cyan-600" />
                        <span>Rail Express (₹500–₹3k)</span>
                      </div>
                      <span className="font-mono font-bold text-cyan-700 bg-cyan-50 px-1.5 py-0.2 rounded text-[9.5px]">{metricStats.med} routes</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-700">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1.5 rounded-full bg-slate-500" />
                        <span>State Bus (&lt;₹500)</span>
                      </div>
                      <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.2 rounded text-[9.5px]">{metricStats.low} routes</span>
                    </div>
                  </>
                )}

                <div className="flex items-center gap-2 text-slate-600 pt-1 border-t border-slate-100">
                  <span className="w-2 h-2 rounded-full bg-indigo-600 animate-ping" />
                  <span>Interactive Node Hubs</span>
                </div>
              </div>

              {!isDrawerOpen && (
                <button
                  onClick={() => setIsDrawerOpen(true)}
                  className="absolute top-2 right-2 bg-white/95 hover:bg-white text-slate-800 p-2 rounded-xl border border-white shadow-sm text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <Activity className="w-3.5 h-3.5 text-indigo-600" />
                  Open Corridor Telemetry
                </button>
              )}
            </div>
          </div>

          {/* Quick Corridor Selection Strip & Leaderboard sorted by active metric */}
          <div className="pt-3 border-t border-slate-200/60">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider flex items-center gap-1">
                <TrendingUp className="w-3 h-3 text-indigo-600" />
                Corridors Ranked by {selectedMetric === 'demand' ? 'Passenger Demand' : selectedMetric === 'occupancy' ? 'Occupancy Stress' : 'Ticket Yield'}:
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Click to Inspect Telemetry</span>
            </div>
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
              {sortedCorridors.map((c) => {
                const isSelected = activeCorridorId === c.id;
                let badgeText = `${c.predictedDemand} pax`;
                if (selectedMetric === 'occupancy') {
                  badgeText = `${c.occupancy}%`;
                } else if (selectedMetric === 'fare') {
                  badgeText = `₹${c.fare}`;
                }

                return (
                  <button
                    key={c.id}
                    onClick={() => {
                      setActiveCorridorId(c.id);
                      setIsDrawerOpen(true);
                    }}
                    className={`px-2.5 py-1.5 rounded-xl text-[11px] font-medium shrink-0 border transition-all flex items-center gap-1.5 ${
                      isSelected
                        ? 'bg-slate-900 text-white border-slate-900 shadow-sm font-bold ring-2 ring-slate-400/50'
                        : 'bg-white/80 text-slate-700 border-white/95 hover:bg-white hover:text-slate-900 hover:shadow-2xs'
                    }`}
                  >
                    <span className="font-semibold">{c.from} ➔ {c.to}</span>
                    <span
                      className={`px-1.5 py-0.2 rounded-md font-mono text-[10px] font-bold ${
                        isSelected
                          ? 'bg-white/20 text-white'
                          : selectedMetric === 'demand'
                          ? 'bg-indigo-50 text-indigo-700'
                          : selectedMetric === 'occupancy'
                          ? c.occupancy >= 92 ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700'
                          : 'bg-purple-50 text-purple-700'
                      }`}
                    >
                      {badgeText}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </Card>

        {/* Right: Live Corridor Inspection Drawer */}
        <AnimatePresence>
          {isDrawerOpen && (
            <motion.div
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 16 }}
              transition={{ duration: 0.2 }}
              className="lg:col-span-4"
            >
              <Card className="p-4 flex flex-col justify-between h-full bg-white/90 border-white/95 shadow-sm space-y-3">
                <div>
                  {/* Drawer Header */}
                  <div className="flex items-center justify-between pb-2.5 border-b border-slate-200/60">
                    <div>
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                        Corridor Telemetry & ML Forecast
                      </span>
                      <h2 className="text-xs font-bold text-slate-900 mt-0.5 flex items-center gap-1.5">
                        <Activity className="w-3.5 h-3.5 text-indigo-600" />
                        {activeCorridor.name}
                      </h2>
                    </div>
                    <button
                      onClick={() => setIsDrawerOpen(false)}
                      className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                      title="Close drawer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Mode & Operator Info */}
                  <div className="mt-2.5 flex items-center justify-between p-2 rounded-xl bg-white/70 border border-white/90 shadow-2xs text-xs">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          activeCorridor.mode === 'Bus'
                            ? 'crimson'
                            : activeCorridor.mode === 'Rail'
                            ? 'indigo'
                            : 'ice'
                        }
                        size="sm"
                      >
                        {activeCorridor.mode.toUpperCase()}
                      </Badge>
                      <span className="font-semibold text-slate-800 text-[11px]">{activeCorridor.operator}</span>
                    </div>
                    <span className="font-mono text-slate-500 text-[11px] font-bold">
                      {activeCorridor.distanceKm} km
                    </span>
                  </div>

                  {/* Highlighted Metric Dynamic Spotlight Banner */}
                  <div className="mt-2.5">
                    {selectedMetric === 'demand' && (
                      <div className="p-2.5 rounded-xl bg-gradient-to-r from-indigo-50 to-blue-50/70 border border-indigo-100/90 shadow-2xs">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-[10px] uppercase font-bold text-indigo-900 flex items-center gap-1">
                            <Users className="w-3 h-3 text-indigo-600" />
                            Highlighted: Predicted Demand
                          </span>
                          <span className="text-[9.5px] font-bold text-indigo-700 bg-white/80 px-2 py-0.5 rounded-md border border-indigo-100">
                            +{(activeCorridor.predictedDemand - activeCorridor.historicalMedian)} vs Normal
                          </span>
                        </div>
                        <div className="flex items-baseline gap-2 mt-1">
                          <span className="text-xl font-black text-indigo-950 font-mono">{activeCorridor.predictedDemand}</span>
                          <span className="text-xs text-indigo-700 font-medium">passengers / run</span>
                        </div>
                        <p className="text-[10px] text-indigo-800/80 mt-0.5">
                          Historical median baseline: <strong className="font-mono">{activeCorridor.historicalMedian} pax</strong>. Model confidence score is <strong className="font-mono">93.4%</strong>.
                        </p>
                      </div>
                    )}

                    {selectedMetric === 'occupancy' && (
                      <div className={`p-2.5 rounded-xl border shadow-2xs ${
                        activeCorridor.occupancy >= 92
                          ? 'bg-gradient-to-r from-rose-50 to-orange-50/70 border-rose-200/90'
                          : 'bg-gradient-to-r from-sky-50 to-blue-50/70 border-sky-100/90'
                      }`}>
                        <div className="flex items-center justify-between text-xs">
                          <span className={`text-[10px] uppercase font-bold flex items-center gap-1 ${
                            activeCorridor.occupancy >= 92 ? 'text-rose-900' : 'text-sky-900'
                          }`}>
                            <Flame className={`w-3 h-3 ${activeCorridor.occupancy >= 92 ? 'text-rose-600' : 'text-sky-600'}`} />
                            Highlighted: Occupancy Stress
                          </span>
                          <span className={`text-[9.5px] font-bold px-2 py-0.5 rounded-md border ${
                            activeCorridor.occupancy >= 92
                              ? 'bg-rose-100/80 text-rose-800 border-rose-200'
                              : 'bg-sky-100/80 text-sky-800 border-sky-200'
                          }`}>
                            {activeCorridor.occupancy >= 92 ? 'Critical Overcrowding' : 'Capacity Headroom'}
                          </span>
                        </div>
                        <div className="flex items-baseline gap-2 mt-1">
                          <span className={`text-xl font-black font-mono ${
                            activeCorridor.occupancy >= 92 ? 'text-rose-950' : 'text-sky-950'
                          }`}>{activeCorridor.occupancy}%</span>
                          <span className={`text-xs font-medium ${
                            activeCorridor.occupancy >= 92 ? 'text-rose-700' : 'text-sky-700'
                          }`}>of {activeCorridor.capacity} seat rating</span>
                        </div>
                        <p className={`text-[10px] mt-0.5 ${
                          activeCorridor.occupancy >= 92 ? 'text-rose-800/80' : 'text-sky-800/80'
                        }`}>
                          {activeCorridor.occupancy >= 92
                            ? 'Vehicle requires auxiliary relief coaches/buses to prevent platform crowding.'
                            : 'Normal passenger dispersion within target operating comfort range.'}
                        </p>
                      </div>
                    )}

                    {selectedMetric === 'fare' && (
                      <div className="p-2.5 rounded-xl bg-gradient-to-r from-purple-50 to-fuchsia-50/70 border border-purple-100/90 shadow-2xs">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-[10px] uppercase font-bold text-purple-900 flex items-center gap-1">
                            <IndianRupee className="w-3 h-3 text-purple-600" />
                            Highlighted: Fare Yield & Tier
                          </span>
                          <span className="text-[9.5px] font-bold text-purple-700 bg-white/80 px-2 py-0.5 rounded-md border border-purple-100">
                            {activeCorridor.surgeMultiplier}x Surge Multiplier
                          </span>
                        </div>
                        <div className="flex items-baseline gap-2 mt-1">
                          <span className="text-xl font-black text-purple-950 font-mono">₹{activeCorridor.fare}</span>
                          <span className="text-xs text-purple-700 font-medium">per passenger ticket</span>
                        </div>
                        <p className="text-[10px] text-purple-800/80 mt-0.5">
                          Estimated gross trip revenue: <strong className="font-mono">₹{(activeCorridor.fare * activeCorridor.predictedDemand).toLocaleString()}</strong>. Dynamic yield active.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Telemetry Numbers Grid */}
                  <div className="mt-2.5 grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 rounded-xl bg-white/70 border border-white/90 shadow-2xs">
                      <span className="text-[10px] text-slate-500 block font-medium">Demand Forecast</span>
                      <div className="text-base font-black text-slate-900 font-mono mt-0.5">
                        {activeCorridor.predictedDemand}{' '}
                        <span className="text-xs font-normal text-slate-500">pax</span>
                      </div>
                      <div className="flex items-center gap-1 text-[9.5px] text-indigo-700 font-semibold mt-0.5">
                        <Sparkles className="w-3 h-3 text-indigo-600" />
                        <span>Confidence: 93%</span>
                      </div>
                    </div>

                    <div className="p-2.5 rounded-xl bg-white/70 border border-white/90 shadow-2xs">
                      <span className="text-[10px] text-slate-500 block font-medium">Occupancy Stress</span>
                      <div className="text-base font-black font-mono mt-0.5 text-slate-900">
                        {activeCorridor.occupancy}%
                      </div>
                      <span className={`text-[9.5px] font-semibold block mt-0.5 ${activeCorridor.triage === 'Surge' ? 'text-rose-600' : 'text-sky-700'}`}>
                        {activeCorridor.triage === 'Surge' ? 'Surge Load' : 'Stable Load'}
                      </span>
                    </div>
                  </div>

                  {/* Occupancy Progress Gauge */}
                  <div className="mt-2.5 p-2.5 rounded-xl bg-white/70 border border-white/90 shadow-2xs space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-600 font-medium flex items-center gap-1">
                        <Gauge className="w-3.5 h-3.5 text-slate-500" />
                        Capacity Utilization:
                      </span>
                      <span className="font-mono font-bold text-slate-900">{activeCorridor.occupancy}%</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${
                          activeCorridor.occupancy > 90
                            ? 'bg-rose-500'
                            : activeCorridor.occupancy > 75
                            ? 'bg-indigo-600'
                            : 'bg-amber-500'
                        }`}
                        style={{ width: `${Math.min(activeCorridor.occupancy, 100)}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-400 font-mono pt-0.5">
                      <span>0%</span>
                      <span>Seating Floor</span>
                      <span>100% Max</span>
                    </div>
                  </div>

                  {/* Peak Hours & Surge Factor */}
                  <div className="mt-2.5 p-2.5 rounded-xl bg-white/60 border border-white/80 shadow-2xs text-[11px] space-y-1.5">
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1 font-medium">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        Peak Hours:
                      </span>
                      <span className="font-semibold text-slate-800 text-[10.5px]">{activeCorridor.peakHours}</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600 pt-1 border-t border-slate-100">
                      <span className="flex items-center gap-1 font-medium">
                        <TrendingUp className="w-3.5 h-3.5 text-indigo-600" />
                        Surge Dynamic:
                      </span>
                      <span className="font-mono font-bold text-indigo-700">{activeCorridor.surgeMultiplier}x Multiplier</span>
                    </div>
                  </div>

                  {/* Dispatch Recommendation */}
                  <div className="mt-2.5 p-2.5 rounded-xl bg-gradient-to-br from-indigo-50/70 to-purple-50/50 border border-indigo-100/90 shadow-2xs space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-indigo-900 font-bold text-[11px] flex items-center gap-1.5">
                        <Zap className="w-3.5 h-3.5 text-indigo-600" />
                        Optimal Fleet Allocation
                      </span>
                      <Badge variant="indigo" size="sm" className="text-[9.5px]">
                        AI Inferred
                      </Badge>
                    </div>
                    <p className="text-[11px] text-slate-700 mt-1 font-medium">
                      Dispatch <strong className="text-slate-900 font-mono">{activeCorridor.recommendedFleet} units</strong> of{' '}
                      <strong className="text-indigo-950">{activeCorridor.fleetType}</strong> to satisfy peak volume.
                    </p>
                  </div>
                </div>

                {/* Bottom CTA to Simulator */}
                <div className="pt-2 border-t border-slate-200/60 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-600">
                    <span className="text-[11px]">Average Ticket Fare:</span>
                    <span className="font-mono font-bold text-slate-900 text-sm">₹{activeCorridor.fare}</span>
                  </div>

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => onNavigateToPredict && onNavigateToPredict(activeCorridor.id)}
                    className="w-full flex items-center justify-center gap-2 py-2.5 text-xs bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white rounded-xl shadow-sm active:scale-[0.99]"
                  >
                    <span>Open in Demand Simulator</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

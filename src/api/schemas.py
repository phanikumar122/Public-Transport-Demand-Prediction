"""
api/schemas.py — Pydantic schemas for the Public Transport Demand Prediction API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ── Prediction Request / Response ──────────────────────────────────────────

class PredictionRequest(BaseModel):
    transport_mode: str = Field(default="Bus", description="Transport mode: Bus, Rail, Air")
    route: str = Field(default="Kurnool-Hyderabad", description="Route name")
    date: str = Field(default="2025-06-15", description="Trip date (YYYY-MM-DD)")
    service_type: str = Field(default="Volvo AC", description="Bus type / Train class / Airline tier")
    distance_km: float = Field(default=326.0, description="Route distance in km")
    capacity: int = Field(default=49, description="Vehicle seat capacity")
    fare_per_passenger: float = Field(default=450.0, description="Ticket fare / price per passenger")
    is_holiday: int = Field(default=0, description="1 if holiday, 0 otherwise")
    vehicle_capacity: Optional[int] = Field(default=50, description="Capacity per dispatch vehicle")
    depot: Optional[str] = Field(default="Guntur", description="Operating depot or origin station")


class PredictionResponse(BaseModel):
    predicted_demand: int
    demand_category: str  # Low, Medium, High
    recommended_vehicles: int
    vehicle_type: str
    occupancy_expected_pct: float
    estimated_revenue: float
    confidence_score: float
    model_name: str
    route: str
    date: str
    distance_km: float
    feature_impacts: List[Dict[str, Any]]
    route_historical_stats: Dict[str, Any]


# ── Overview & Health ────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    best_model_name: str
    available_models: List[str]
    records_indexed: int


class KPIStats(BaseModel):
    total_records: int
    total_routes: int
    bus_records: int
    rail_records: int
    air_records: int
    best_model_r2: float
    best_model_mae: float
    anomaly_count: int
    anomaly_rate_pct: float
    cluster_count: int


# ── Routes & Catalog ─────────────────────────────────────────────────────────

class RouteItem(BaseModel):
    route: str
    transport_mode: str
    avg_passengers: float
    avg_fare: float
    avg_distance_km: float
    avg_occupancy: float
    trip_count: int
    cluster_name: Optional[str] = None


class CatalogResponse(BaseModel):
    routes: List[str]
    routes_by_mode: Dict[str, List[str]]
    modes: List[str]
    service_types_by_mode: Dict[str, List[str]]
    depots: List[str]
    route_details: List[RouteItem]


# ── Model Performance ────────────────────────────────────────────────────────

class ModelMetric(BaseModel):
    model_name: str
    split: str
    mae: float
    rmse: float
    mape: float
    r2: float


class ModelComparisonResponse(BaseModel):
    best_model: str
    metrics: List[ModelMetric]
    feature_names: List[str]
    best_params: Optional[Dict[str, Any]] = None


# ── Clustering ───────────────────────────────────────────────────────────────

class ClusterPoint(BaseModel):
    route: str
    transport_mode: str
    cluster: int
    cluster_name: str
    avg_passengers: float
    avg_occupancy: float
    avg_fare: float
    avg_distance_km: float
    trip_count: int


class ClusterSummary(BaseModel):
    cluster: int
    cluster_name: str
    total_routes: int
    avg_passengers: float
    avg_occupancy: float
    avg_fare: float
    modes: Dict[str, int]


class ClustersResponse(BaseModel):
    clusters_summary: List[ClusterSummary]
    points: List[ClusterPoint]


# ── Anomalies ────────────────────────────────────────────────────────────────

class AnomalyRecord(BaseModel):
    id: int
    date: Optional[str]
    transport_mode: str
    route: str
    service_type: Optional[str]
    passengers: float
    occupancy_rate: float
    distance_km: float
    fare: float
    anomaly_score: Optional[float] = None
    reason: Optional[str] = None


class AnomaliesResponse(BaseModel):
    total_anomalies: int
    anomaly_rate_pct: float
    breakdown_by_mode: Dict[str, int]
    top_routes: List[Dict[str, Any]]
    recent_anomalies: List[AnomalyRecord]


# ── Explainability ───────────────────────────────────────────────────────────

class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float
    rank: int
    description: str


class ExplainResponse(BaseModel):
    model_name: str
    top_features: List[FeatureImportanceItem]
    insights: List[str]

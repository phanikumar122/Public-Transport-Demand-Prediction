-- ============================================================
-- schema.sql — Transport Data Warehouse Star Schema
-- Database: transport_dw
-- ============================================================
-- Run this file to create the warehouse schema:
--   mysql -u root -p < src/warehouse/schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS transport_dw
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE transport_dw;

-- ─── DIMENSION TABLES ──────────────────────────────────────

-- DIM_DATE: one row per calendar date
CREATE TABLE IF NOT EXISTS dim_date (
    date_key      INT          NOT NULL,           -- YYYYMMDD
    full_date     DATE         NOT NULL,
    year          SMALLINT     NOT NULL,
    quarter       TINYINT      NOT NULL,
    month         TINYINT      NOT NULL,
    month_name    VARCHAR(15)  NOT NULL,
    week_of_year  TINYINT      NOT NULL,
    day_of_month  TINYINT      NOT NULL,
    day_of_week   TINYINT      NOT NULL,           -- 0=Mon, 6=Sun
    day_name      VARCHAR(10)  NOT NULL,
    is_weekend    TINYINT(1)   NOT NULL DEFAULT 0,
    is_holiday    TINYINT(1)   NOT NULL DEFAULT 0,
    holiday_name  VARCHAR(100) NULL,
    PRIMARY KEY (date_key),
    INDEX idx_dim_date_full   (full_date),
    INDEX idx_dim_date_year   (year),
    INDEX idx_dim_date_month  (year, month)
) ENGINE=InnoDB;


-- DIM_ROUTE: one row per distinct route
CREATE TABLE IF NOT EXISTS dim_route (
    route_key        INT          NOT NULL AUTO_INCREMENT,
    route_name       VARCHAR(200) NOT NULL,
    source_city      VARCHAR(100) NULL,
    destination_city VARCHAR(100) NULL,
    PRIMARY KEY (route_key),
    UNIQUE KEY uk_route_name (route_name)
) ENGINE=InnoDB;


-- DIM_TRANSPORT_MODE: bus / railway / flight
CREATE TABLE IF NOT EXISTS dim_transport_mode (
    mode_key    INT         NOT NULL AUTO_INCREMENT,
    mode_name   VARCHAR(50) NOT NULL,               -- Bus, Railway, Flight
    sub_type    VARCHAR(100) NULL,                  -- Volvo AC, Sleeper, Economy...
    operator    VARCHAR(100) NULL,                  -- APSRTC, Indian Railways, IndiGo...
    PRIMARY KEY (mode_key),
    UNIQUE KEY uk_mode_subtype (mode_name, sub_type, operator)
) ENGINE=InnoDB;


-- DIM_LOCATION: depots / stations / airports
CREATE TABLE IF NOT EXISTS dim_location (
    location_key  INT          NOT NULL AUTO_INCREMENT,
    location_name VARCHAR(200) NOT NULL,
    location_type VARCHAR(50)  NULL,      -- Depot, Station, Airport
    city          VARCHAR(100) NULL,
    state         VARCHAR(100) NULL,
    PRIMARY KEY (location_key),
    UNIQUE KEY uk_location_name (location_name, location_type)
) ENGINE=InnoDB;


-- ─── FACT TABLE ─────────────────────────────────────────────

-- FACT_TRANSPORT: central fact table — one row per trip/journey record
CREATE TABLE IF NOT EXISTS fact_transport (
    fact_id          BIGINT       NOT NULL AUTO_INCREMENT,
    date_key         INT          NOT NULL,
    route_key        INT          NOT NULL,
    mode_key         INT          NOT NULL,
    location_key     INT          NOT NULL,

    -- APSRTC measures
    passenger_count  INT          NULL,
    capacity         INT          NULL,
    occupancy_rate   DECIMAL(6,2) NULL,
    distance_km      DECIMAL(10,2) NULL,
    revenue          DECIMAL(12,2) NULL,
    fare_per_passenger DECIMAL(10,2) NULL,
    fuel_liters      DECIMAL(10,2) NULL,

    -- Flight measures
    price            DECIMAL(10,2) NULL,
    duration_minutes INT          NULL,
    num_stops        TINYINT      NULL,

    -- Railways measures (schedule-based)
    train_distance_km DECIMAL(10,2) NULL,
    num_classes       TINYINT      NULL,

    -- Derived measures
    seats_remaining  INT          NULL,

    -- Source tracking
    source_dataset   VARCHAR(20)  NOT NULL,         -- apsrtc / flights / railways

    PRIMARY KEY (fact_id),
    CONSTRAINT fk_fact_date   FOREIGN KEY (date_key)     REFERENCES dim_date(date_key),
    CONSTRAINT fk_fact_route  FOREIGN KEY (route_key)    REFERENCES dim_route(route_key),
    CONSTRAINT fk_fact_mode   FOREIGN KEY (mode_key)     REFERENCES dim_transport_mode(mode_key),
    CONSTRAINT fk_fact_loc    FOREIGN KEY (location_key) REFERENCES dim_location(location_key),
    INDEX idx_fact_date      (date_key),
    INDEX idx_fact_route     (route_key),
    INDEX idx_fact_mode      (mode_key),
    INDEX idx_fact_source    (source_dataset),
    INDEX idx_fact_passengers (passenger_count)
) ENGINE=InnoDB;


-- ─── PREDICTION RESULTS TABLE ───────────────────────────────

CREATE TABLE IF NOT EXISTS fact_predictions (
    prediction_id     BIGINT       NOT NULL AUTO_INCREMENT,
    date_key          INT          NOT NULL,
    route_key         INT          NOT NULL,
    mode_key          INT          NOT NULL,

    actual_demand     INT          NULL,
    predicted_demand  DECIMAL(10,2) NOT NULL,
    demand_category   VARCHAR(30)  NOT NULL,        -- Low / Medium / High
    model_name        VARCHAR(100) NOT NULL,
    prediction_error  DECIMAL(10,4) NULL,
    recommended_buses TINYINT      NULL,
    bus_capacity_used INT          NOT NULL DEFAULT 50,

    created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (prediction_id),
    INDEX idx_pred_date   (date_key),
    INDEX idx_pred_route  (route_key),
    INDEX idx_pred_model  (model_name)
) ENGINE=InnoDB;


-- ─── ML MODEL METRICS TABLE ─────────────────────────────────

CREATE TABLE IF NOT EXISTS ml_model_metrics (
    metric_id     INT          NOT NULL AUTO_INCREMENT,
    model_name    VARCHAR(100) NOT NULL,
    split         VARCHAR(20)  NOT NULL,            -- validation / test
    mae           DECIMAL(12,4) NULL,
    rmse          DECIMAL(12,4) NULL,
    mape          DECIMAL(8,4)  NULL,
    r2_score      DECIMAL(8,6)  NULL,
    trained_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (metric_id),
    INDEX idx_metrics_model (model_name)
) ENGINE=InnoDB;


-- ─── CLUSTERING RESULTS TABLE ───────────────────────────────

CREATE TABLE IF NOT EXISTS mining_clusters (
    cluster_id     INT          NOT NULL AUTO_INCREMENT,
    route_name     VARCHAR(200) NOT NULL,
    cluster_label  TINYINT      NOT NULL,
    cluster_name   VARCHAR(100) NULL,
    avg_passengers DECIMAL(10,2) NULL,
    avg_revenue    DECIMAL(12,2) NULL,
    avg_distance   DECIMAL(10,2) NULL,
    trip_count     INT          NULL,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cluster_id),
    INDEX idx_cluster_route  (route_name),
    INDEX idx_cluster_label  (cluster_label)
) ENGINE=InnoDB;


-- ─── ANOMALY DETECTION TABLE ────────────────────────────────

CREATE TABLE IF NOT EXISTS mining_anomalies (
    anomaly_id     BIGINT       NOT NULL AUTO_INCREMENT,
    source_dataset VARCHAR(20)  NOT NULL,
    date_key       INT          NULL,
    route_name     VARCHAR(200) NULL,
    anomaly_score  DECIMAL(10,6) NULL,
    is_anomaly     TINYINT(1)   NOT NULL DEFAULT 1,
    passenger_count INT         NULL,
    revenue        DECIMAL(12,2) NULL,
    anomaly_reason VARCHAR(200) NULL,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (anomaly_id),
    INDEX idx_anom_date    (date_key),
    INDEX idx_anom_route   (route_name),
    INDEX idx_anom_dataset (source_dataset)
) ENGINE=InnoDB;

-- End of schema

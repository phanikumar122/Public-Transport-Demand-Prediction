-- ============================================================
-- queries.sql — OLAP Queries for Transport Data Warehouse
-- ============================================================
-- Each section demonstrates a classic OLAP operation.
-- Run against the transport_dw MySQL database.
-- ============================================================

USE transport_dw;

-- ─────────────────────────────────────────────────────────────
-- SECTION 1: ROLL-UP  (Hour → Day → Month → Year)
-- Summarise APSRTC passenger demand at progressively higher granularity
-- ─────────────────────────────────────────────────────────────

-- 1a. Daily passenger totals (finest granularity used here: daily)
SELECT
    d.full_date,
    d.year,
    d.month,
    d.month_name,
    d.day_name,
    SUM(f.passenger_count)  AS total_passengers,
    SUM(f.revenue)          AS total_revenue,
    COUNT(f.fact_id)        AS total_trips
FROM fact_transport f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.source_dataset = 'apsrtc'
GROUP BY d.full_date, d.year, d.month, d.month_name, d.day_name
ORDER BY d.full_date;


-- 1b. ROLL-UP to Monthly level
SELECT
    d.year,
    d.month,
    d.month_name,
    SUM(f.passenger_count)  AS total_passengers,
    AVG(f.passenger_count)  AS avg_passengers_per_trip,
    SUM(f.revenue)          AS total_revenue,
    COUNT(f.fact_id)        AS total_trips,
    AVG(f.occupancy_rate)   AS avg_occupancy_rate
FROM fact_transport f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.source_dataset = 'apsrtc'
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;


-- 1c. ROLL-UP to Quarterly level
SELECT
    d.year,
    d.quarter,
    SUM(f.passenger_count)  AS total_passengers,
    SUM(f.revenue)          AS total_revenue,
    COUNT(f.fact_id)        AS total_trips
FROM fact_transport f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.source_dataset = 'apsrtc'
GROUP BY d.year, d.quarter
ORDER BY d.year, d.quarter;


-- 1d. ROLL-UP to Yearly level
SELECT
    d.year,
    SUM(f.passenger_count)  AS total_passengers,
    SUM(f.revenue)          AS total_revenue,
    COUNT(f.fact_id)        AS total_trips,
    AVG(f.occupancy_rate)   AS avg_occupancy,
    SUM(f.distance_km)      AS total_km_operated
FROM fact_transport f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.source_dataset = 'apsrtc'
GROUP BY d.year
ORDER BY d.year;


-- ─────────────────────────────────────────────────────────────
-- SECTION 2: DRILL-DOWN  (Year → Month → Day → Route)
-- ─────────────────────────────────────────────────────────────

-- 2a. Start at year 2024
SELECT
    d.year,
    SUM(f.passenger_count) AS total_passengers,
    COUNT(f.fact_id)        AS trips
FROM fact_transport f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.source_dataset = 'apsrtc'
  AND d.year = 2024
GROUP BY d.year;


-- 2b. Drill to months of 2024
SELECT
    d.year,
    d.month,
    d.month_name,
    SUM(f.passenger_count) AS total_passengers,
    COUNT(f.fact_id)        AS trips
FROM fact_transport f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.source_dataset = 'apsrtc'
  AND d.year = 2024
GROUP BY d.year, d.month, d.month_name
ORDER BY d.month;


-- 2c. Drill to specific month (e.g. November 2024)
SELECT
    d.year,
    d.month_name,
    d.day_of_month,
    d.day_name,
    SUM(f.passenger_count) AS total_passengers
FROM fact_transport f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.source_dataset = 'apsrtc'
  AND d.year = 2024
  AND d.month = 11
GROUP BY d.year, d.month_name, d.day_of_month, d.day_name
ORDER BY d.day_of_month;


-- 2d. Drill to route within a specific day
SELECT
    d.full_date,
    r.route_name,
    f.passenger_count,
    f.capacity,
    f.occupancy_rate
FROM fact_transport f
JOIN dim_date  d ON f.date_key  = d.date_key
JOIN dim_route r ON f.route_key = r.route_key
WHERE f.source_dataset = 'apsrtc'
  AND d.full_date = '2024-11-01'
ORDER BY f.passenger_count DESC;


-- ─────────────────────────────────────────────────────────────
-- SECTION 3: SLICE — single dimension filter
-- Filter transport mode = Bus (APSRTC only)
-- ─────────────────────────────────────────────────────────────

-- 3a. Bus slice: all metrics for APSRTC
SELECT
    r.route_name,
    COUNT(f.fact_id)         AS trip_count,
    SUM(f.passenger_count)   AS total_passengers,
    AVG(f.occupancy_rate)    AS avg_occupancy_pct,
    SUM(f.revenue)           AS total_revenue,
    AVG(f.distance_km)       AS avg_distance_km
FROM fact_transport f
JOIN dim_route          r ON f.route_key = r.route_key
JOIN dim_transport_mode m ON f.mode_key  = m.mode_key
WHERE m.mode_name = 'Bus'
GROUP BY r.route_name
ORDER BY total_passengers DESC;


-- 3b. Flight slice: price analytics
SELECT
    m.operator                AS airline,
    COUNT(f.fact_id)          AS flight_count,
    AVG(f.price)              AS avg_price_inr,
    MIN(f.price)              AS min_price_inr,
    MAX(f.price)              AS max_price_inr,
    AVG(f.duration_minutes)   AS avg_duration_min,
    AVG(f.num_stops)          AS avg_stops
FROM fact_transport f
JOIN dim_transport_mode m ON f.mode_key = m.mode_key
WHERE m.mode_name = 'Flight'
GROUP BY m.operator
ORDER BY flight_count DESC;


-- ─────────────────────────────────────────────────────────────
-- SECTION 4: DICE — multiple dimension filters
-- Example: Bus, August, Weekdays, selected routes
-- ─────────────────────────────────────────────────────────────

-- 4a. DICE: Bus + August + Weekdays
SELECT
    r.route_name,
    d.day_name,
    AVG(f.passenger_count)  AS avg_passengers,
    SUM(f.passenger_count)  AS total_passengers,
    AVG(f.occupancy_rate)   AS avg_occupancy,
    COUNT(f.fact_id)        AS trip_count
FROM fact_transport f
JOIN dim_date           d ON f.date_key  = d.date_key
JOIN dim_route          r ON f.route_key = r.route_key
JOIN dim_transport_mode m ON f.mode_key  = m.mode_key
WHERE m.mode_name    = 'Bus'
  AND d.month        = 8                -- August
  AND d.is_weekend   = 0               -- Weekdays only
  AND f.source_dataset = 'apsrtc'
GROUP BY r.route_name, d.day_name
ORDER BY avg_passengers DESC;


-- 4b. DICE: High revenue routes on weekends
SELECT
    r.route_name,
    d.day_name,
    SUM(f.revenue)         AS total_revenue,
    SUM(f.passenger_count) AS total_passengers,
    AVG(f.occupancy_rate)  AS avg_occupancy
FROM fact_transport f
JOIN dim_date           d ON f.date_key  = d.date_key
JOIN dim_route          r ON f.route_key = r.route_key
JOIN dim_transport_mode m ON f.mode_key  = m.mode_key
WHERE m.mode_name  = 'Bus'
  AND d.is_weekend = 1
  AND f.source_dataset = 'apsrtc'
GROUP BY r.route_name, d.day_name
ORDER BY total_revenue DESC
LIMIT 20;


-- ─────────────────────────────────────────────────────────────
-- SECTION 5: KPIs — Executive Overview
-- ─────────────────────────────────────────────────────────────

-- 5a. Overall KPIs (APSRTC)
SELECT
    COUNT(DISTINCT r.route_name)  AS total_routes,
    COUNT(f.fact_id)              AS total_trips,
    SUM(f.passenger_count)        AS total_passengers,
    AVG(f.passenger_count)        AS avg_demand_per_trip,
    MAX(f.passenger_count)        AS peak_demand,
    MIN(f.passenger_count)        AS min_demand,
    SUM(f.revenue)                AS total_revenue,
    AVG(f.occupancy_rate)         AS avg_occupancy_pct
FROM fact_transport f
JOIN dim_route r ON f.route_key = r.route_key
WHERE f.source_dataset = 'apsrtc';


-- 5b. Multi-modal summary
SELECT
    m.mode_name,
    COUNT(f.fact_id)               AS record_count,
    SUM(f.passenger_count)         AS total_passengers,
    SUM(f.revenue)                 AS total_revenue,
    AVG(f.price)                   AS avg_price
FROM fact_transport f
JOIN dim_transport_mode m ON f.mode_key = m.mode_key
GROUP BY m.mode_name;


-- ─────────────────────────────────────────────────────────────
-- SECTION 6: Day-of-week demand pattern
-- ─────────────────────────────────────────────────────────────
SELECT
    d.day_of_week,
    d.day_name,
    AVG(f.passenger_count)  AS avg_passengers,
    SUM(f.passenger_count)  AS total_passengers,
    COUNT(f.fact_id)        AS trip_count
FROM fact_transport f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.source_dataset = 'apsrtc'
GROUP BY d.day_of_week, d.day_name
ORDER BY d.day_of_week;


-- ─────────────────────────────────────────────────────────────
-- SECTION 7: Holiday vs Non-holiday demand
-- ─────────────────────────────────────────────────────────────
SELECT
    d.is_holiday,
    CASE WHEN d.is_holiday = 1 THEN 'Holiday' ELSE 'Normal Day' END AS day_type,
    AVG(f.passenger_count)  AS avg_passengers,
    COUNT(f.fact_id)        AS trip_count
FROM fact_transport f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.source_dataset = 'apsrtc'
GROUP BY d.is_holiday;


-- ─────────────────────────────────────────────────────────────
-- SECTION 8: Flight price analytics by route
-- ─────────────────────────────────────────────────────────────
SELECT
    r.route_name,
    COUNT(f.fact_id)        AS flight_count,
    AVG(f.price)            AS avg_price,
    MIN(f.price)            AS cheapest_price,
    MAX(f.price)            AS most_expensive,
    AVG(f.num_stops)        AS avg_stops,
    AVG(f.duration_minutes) AS avg_duration_min
FROM fact_transport f
JOIN dim_route r ON f.route_key = r.route_key
WHERE f.source_dataset = 'flights'
GROUP BY r.route_name
ORDER BY avg_price DESC
LIMIT 20;

-- End of OLAP queries


-- Flow Framework Standardization Views
-- Implements the Mik Kersten's Flow Framework logic by normalizing Issue data.

-- 1. Standardization Layer: Normalize Issues into Flow Items
-- Logic: Maps raw labels/types to the 4 Flow Types: Feature, Defect, Debt, Risk.
CREATE OR REPLACE VIEW view_flow_items AS
SELECT
    i.id,
    i.project_id,
    p.name as project_name,
    i.title,
    i.state,
    i.created_at,
    i.closed_at,
    -- Determine Flow Type based on Labels (Priority Order: Risk > Defect > Debt > Feature)
    CASE 
        -- Risk: Security, Compliance, Vulnerability
        WHEN i.labels LIKE '%security%' OR i.labels LIKE '%compliance%' OR i.labels LIKE '%risk%' OR i.labels LIKE '%vulnerability%' THEN 'Risk'
        -- Defect: Bug, Fix, Incident, Hotfix
        WHEN i.labels LIKE '%bug%' OR i.labels LIKE '%fix%' OR i.labels LIKE '%defect%' OR i.labels LIKE '%incident%' THEN 'Defect'
        -- Debt: Refactor, Cleanup, Upgrade, Tech-Debt
        WHEN i.labels LIKE '%refactor%' OR i.labels LIKE '%cleanup%' OR i.labels LIKE '%debt%' OR i.labels LIKE '%upgrade%' THEN 'Debt'
        -- Feature: Default or explicit tags (Story, Feature, Enhancement)
        ELSE 'Feature' 
    END as flow_type,
    
    -- Flow Time Calculation (Days) - Null if not closed
    CASE 
        WHEN i.closed_at IS NOT NULL THEN (JULIANDAY(i.closed_at) - JULIANDAY(i.created_at))
        ELSE NULL 
    END as flow_time_days,

    -- Flow Load Indicator (Active Status)
    CASE 
        WHEN i.state = 'opened' THEN 1 ELSE 0 
    END as is_active_wip

FROM issues i
LEFT JOIN projects p ON i.project_id = p.id;


-- 2. Aggregation Layer: Weekly Flow Metrics
-- Aggregates Velocity, Load, and Time by Week and Type.
CREATE OR REPLACE VIEW view_flow_metrics_weekly AS
SELECT
    STRFTIME('%Y-%W', i.created_at) as week_identifier,
    MIN(DATE(i.created_at, 'weekday 0', '-6 days')) as week_start_date,
    i.project_id,
    
    -- Flow Distribution (Type Count)
    COUNT(CASE WHEN flow_type='Feature' AND state='closed' THEN 1 END) as closed_features,
    COUNT(CASE WHEN flow_type='Defect' AND state='closed' THEN 1 END) as closed_defects,
    COUNT(CASE WHEN flow_type='Debt' AND state='closed' THEN 1 END) as closed_debts,
    COUNT(CASE WHEN flow_type='Risk' AND state='closed' THEN 1 END) as closed_risks,
    
    -- Flow Velocity (Total Closed)
    COUNT(CASE WHEN state='closed' THEN 1 END) as flow_velocity,
    
    -- Flow Load (Total Still Open at specific time - approximated here as current view snapshot)
    -- True historical load requires discrete event logs; this is a simplified view using current state
    COUNT(CASE WHEN state='opened' THEN 1 END) as current_flow_load,
    
    -- Avg Flow Time (Efficiency)
    AVG(flow_time_days) as avg_flow_time_days

FROM view_flow_items i
WHERE i.created_at >= DATE('now', '-180 days')
GROUP BY 1, 2, 3
ORDER BY week_start_date DESC;

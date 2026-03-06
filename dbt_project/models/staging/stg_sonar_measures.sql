-- stg_sonar_measures.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'sonar_measures') }}
),

renamed AS (
    SELECT
        id AS measure_id,
        project_id,
        analysis_date,
        -- 核心存量指标
        ncloc AS lines_of_code,
        coverage,
        bugs,
        vulnerabilities,
        code_smells,
        complexity,
        cognitive_complexity,
        sqale_index AS technical_debt_minutes,
        -- 核心增量指标 (New Code)
        new_coverage,
        new_bugs,
        new_vulnerabilities,
        new_reliability_rating,
        new_security_rating,
        quality_gate_status,
        created_at
    FROM source
)

SELECT * FROM renamed

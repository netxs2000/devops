
with source as (
    select * from {{ source('raw', 'sonar_measures') }}
),

renamed as (
    select
        project_id as sonar_project_id,
        analysis_date,
        -- Core Metrics
        ncloc,
        complexity,
        cognitive_complexity,
        bugs,
        vulnerabilities,
        code_smells,
        coverage,
        sqale_index as technical_debt_minutes,
        quality_gate_status
    from source
)

select * from renamed

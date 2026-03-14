-- stg_zentao_builds.sql
with source as (
    select * from {{ source('raw', 'zentao_builds') }}
),

renamed as (
    select
        id as build_id,
        product_id,
        execution_id,
        name as build_name,
        builder as build_author,
        date as build_date,
        raw_data
    from source
)

select * from renamed

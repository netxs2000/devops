with source as (
    select * from "devops_db"."public"."stg_mdm_resource_costs"
),

renamed as (
    select
        id as cost_id,
        service_id,
        cost_code_id,
        purchase_contract_id,
        period,
        amount,
        currency,
        cost_type,
        cost_item,
        vendor_name,
        capex_opex_flag,
        source_system,
        created_at,
        updated_at
    from source
)

select * from renamed
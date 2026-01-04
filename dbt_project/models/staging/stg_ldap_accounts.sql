
with source as (
    select * from {{ source('raw', 'ldap_accounts') }}
),

renamed as (
    select
        employee_id,
        email as ldap_email,
        sam_account_name as ldap_username,
        last_logon_at
    from source
)

select * from renamed

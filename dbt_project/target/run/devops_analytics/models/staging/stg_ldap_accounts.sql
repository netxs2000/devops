
  create view "devops_db"."public_staging"."stg_ldap_accounts__dbt_tmp"
    
    
  as (
    with source as (
    select * from "devops_db"."public"."ldap_accounts"
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
  );
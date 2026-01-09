
  create view "devops_db"."public_intermediate"."int_golden_identity__dbt_tmp"
    
    
  as (
    /*
    Golden Identity Resolution Model (金本位身份融合模型)
    
    重构逻辑：
    1. 以 mdm_identities 为 ID 索引骨架 (Master Index)
    2. 融合 HR 信号：强制覆盖 姓名、部门、状态
    3. 融合 LDAP 信号：强制覆盖 邮箱、登录账号
    4. 产生最健壮的“黄金档案”供下游全量引用
*/

with 

master_index as (
    select 
        user_id as global_user_id,
        employee_id 
    from "devops_db"."public_staging"."stg_mdm_identities"
),

hr as (
    select * from "devops_db"."public_staging"."stg_hr_employees"
),

ldap as (
    select * from "devops_db"."public_staging"."stg_ldap_accounts"
),

joined as (
    select
        m.global_user_id,
        m.employee_id,
        
        -- 【金本位：人员/部门信息以 HR 为准】
        coalesce(h.hr_name, 'Unknown') as full_name,
        coalesce(h.hr_dept, 'Unassigned') as department_name,
        h.job_title,
        coalesce(h.hr_status, 'Inactive') as work_status,
        
        -- 【金本位：邮箱以 LDAP 为准】
        l.ldap_email as primary_email,
        l.ldap_username as login_name,
        
        -- 辅助审计元数据
        case when h.employee_id is not null then true else false end as has_hr_record,
        case when l.employee_id is not null then true else false end as has_ldap_record

    from master_index m
    left join hr h on m.employee_id = h.employee_id
    left join ldap l on m.employee_id = l.employee_id
)

select * from joined
  );
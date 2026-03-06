
/*
    Golden Identity Resolution Model (金本位身份融合模型) - v6 [SCD Self-Healing + Inferred Orgs]
    
    设计逻辑：
    1. 骨架层 (Skeleton)：以 global_user_id 为主键，不依赖单个系统的 is_current=true，实现跨版本数据自愈。
    2. 自愈层 (Healing)：
       - 若当前记录 department_id 为空，向下寻找该用户曾经拥有过的任何非空部门 ID。
       - 引入组织机构归一化 (int_org_normalization)，将 zentao_dept_* 映射为 HR 规范 ID (CTR-/DEP-)。
    3. 推断层 (Inference)：
       - 针对 1000+ 无部门资产 (Unassigned)，通过 int_identity_inferred_orgs 引入行为频次归因推断。
    4. 融合层 (Golden Record)：
       - 部门信息优先级：HR (hr_dept) > 归一化后的中心部门 ID > 行为推断部门 > 历史部门 ID > 默认 Unassigned。
*/

with 

identities_raw as (
    -- 取所有历史记录，以便进行字段自愈
    select * from {{ source('raw', 'mdm_identities') }}
),

identities_current as (
    -- 仅取当前记录作为骨架
    select * from identities_raw where is_current = true
),

org_normalization as (
    select * from {{ ref('int_org_normalization') }}
),

inferred_orgs as (
    select * from {{ ref('int_identity_inferred_orgs') }}
),

-- SCD 自愈逻辑：查找每个用户的历史非空字段 (使用 First_Value 或 Last_Value 处理)
identity_healing as (
    select distinct on (global_user_id)
        global_user_id,
        department_id as healed_dept_id,
        employee_id as healed_employee_id,
        full_name as healed_full_name
    from identities_raw
    where department_id is not null or employee_id is not null or full_name is not null
    order by global_user_id, is_current desc, updated_at desc
),

hr as (
    select * from {{ ref('stg_hr_employees') }}
),

ldap as (
    select * from {{ ref('stg_ldap_accounts') }}
),

joined as (
    select
        c.global_user_id,
        coalesce(c.employee_id, h_id.healed_employee_id) as employee_id,
        
        -- 【自愈及融合机制：姓名】
        coalesce(h.hr_name, c.full_name, h_id.healed_full_name, 'Unknown') as full_name,
        
        -- 【自愈机制 + ID 归一化 + 行为推断：部门汇总】
        -- 优先级：HR 部门名 > 归一化后的中心部门 ID > 行为推断部门 > 历史部门 ID > 默认 Unassigned
        coalesce(
            h.hr_dept, 
            n_cur.canonical_org_id, 
            n_inferred.canonical_org_id,
            n_healed.canonical_org_id,
            i.inferred_org_id,
            h_id.healed_dept_id, 
            'Unassigned'
        ) as department_name,

        h.job_title,
        coalesce(h.hr_status, 'Inactive') as work_status,
        
        -- 【邮箱对齐与辅助元数据】
        l.ldap_email as primary_email,
        l.ldap_username as login_name,
        
        case when h.employee_id is not null then true else false end as has_hr_record,
        case when l.employee_id is not null then true else false end as has_ldap_record

    from identities_current c
    left join identity_healing h_id on c.global_user_id = h_id.global_user_id
    left join inferred_orgs i on c.global_user_id = i.global_user_id
    left join hr h on coalesce(c.employee_id, h_id.healed_employee_id) = h.employee_id
    left join ldap l on coalesce(c.employee_id, h_id.healed_employee_id) = l.employee_id
    
    -- 1. 当前部门归一化
    left join org_normalization n_cur on c.department_id = n_cur.original_org_id
    -- 2. 推断部门归一化
    left join org_normalization n_inferred on i.inferred_org_id = n_inferred.original_org_id
    -- 3. 历史自愈部门归一化
    left join org_normalization n_healed on h_id.healed_dept_id = n_healed.original_org_id
)

select * from joined

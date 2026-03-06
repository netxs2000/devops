
/*
    Golden Identity Resolution Model (金本位身份融合模型) - v7 [SCD Self-Healing + Name Normalization]
    
    设计逻辑：
    1. 骨架层 (Skeleton)：以 global_user_id 为主键，实现跨记录的属性整合。
    2. 自愈层 (Healing)：
       - 针对 department_id/employee_id 等关键字段，若当前记录缺失，则从历史记录中自动回溯寻找最近的一个非空值。
    3. 融合层 (Consolidation)：
       - 字段优先级逻辑：从置信度最高的数据源开始回填。
       - 部门名称对齐：通过 int_org_normalization 将 zentao_dept_xxx 穿透为真实的业务部门名称（如“外包人员”）。
*/

with 

identities_raw as (
    -- 获取全量历史身份记录
    select * from {{ source('raw', 'mdm_identities') }}
),

identities_current as (
    -- 获取当前的骨架记录
    select * from identities_raw where is_current = true
),

org_normalization as (
    -- 引入组织机构映射表（含名称对齐）
    select * from {{ ref('int_org_normalization') }}
),

inferred_orgs as (
    -- 引入行为频次归因推断结果
    select * from {{ ref('int_identity_inferred_orgs') }}
),

-- [自愈逻辑]：通过窗口函数或 Distinct On 提取每个用户在历史长河中出现过的“最近一个非空值”
identity_healing as (
    select distinct on (global_user_id)
        global_user_id,
        department_id as healed_dept_id,
        employee_id as healed_employee_id,
        full_name as healed_full_name,
        primary_email as healed_email,
        updated_at
    from identities_raw
    where department_id is not null 
       or employee_id is not null 
       or full_name is not null
       or primary_email is not null
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
        
        -- 工号自愈
        coalesce(c.employee_id, h_id.healed_employee_id) as employee_id,
        
        -- 姓名自愈与对齐
        coalesce(h.hr_name, c.full_name, h_id.healed_full_name, 'Unknown') as full_name,
        
        -- 【核心修正：部门名称对齐】
        -- 逻辑：优先 HR 系统名 -> normalization 后的名称（穿透屏蔽 zentao_dept_xxx） -> 行为推断名称 -> 历史自愈名 -> 默认
        coalesce(
            h.hr_dept, 
            n_cur.org_name, 
            n_inferred.org_name,
            n_healed.org_name,
            'Unassigned'
        ) as department_name,

        -- 部门 ID 保持（用于二次关联）
        coalesce(
            n_cur.canonical_org_id,
            n_inferred.canonical_org_id,
            n_healed.canonical_org_id,
            c.department_id,
            h_id.healed_dept_id
        ) as department_id,

        h.job_title,
        coalesce(h.hr_status, 'Inactive') as work_status,
        
        -- 邮箱与登录名对齐
        coalesce(l.ldap_email, c.primary_email, h_id.healed_email) as primary_email,
        coalesce(l.ldap_username, c.username) as login_name,
        
        case when h.employee_id is not null then true else false end as has_hr_record,
        case when l.employee_id is not null then true else false end as has_ldap_record,
        
        -- 溯源标识
        case 
            when h.hr_dept is not null then 'HR'
            when n_cur.org_name is not null then 'OrgMapping'
            when n_inferred.org_name is not null then 'Inferred'
            when n_healed.org_name is not null then 'Healed (SCD2)'
            else 'Default'
        end as attribution_source

    from identities_current c
    left join identity_healing h_id on c.global_user_id = h_id.global_user_id
    left join inferred_orgs i on c.global_user_id = i.global_user_id
    left join hr h on coalesce(c.employee_id, h_id.healed_employee_id) = h.employee_id
    left join ldap l on coalesce(c.employee_id, h_id.healed_employee_id) = l.employee_id
    
    -- 1. 基于当前部门 ID 的归一化
    left join org_normalization n_cur on c.department_id = n_cur.original_org_id
    -- 2. 基于行为推断部门 ID 的归一化
    left join org_normalization n_inferred on i.inferred_org_id = n_inferred.original_org_id
    -- 3. 基于历史自愈部门 ID 的归一化
    left join org_normalization n_healed on h_id.healed_dept_id = n_healed.original_org_id
)

select * from joined

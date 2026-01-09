
  create view "devops_db"."public_intermediate"."int_org_hierarchy__dbt_tmp"
    
    
  as (
    /*
    组织架构递归平铺模型 (Organization Hierarchy Flattening)
    
    实现目标：
    1. 为每个部门计算其全路径名称 (e.g., 研发部 > 技术中台 > 架构组)
    2. 标识根部门 (Root Department)
    3. 支持 SCD Type 2 环境下的快照分析
*/

with recursive org_tree as (
    -- 锚点：顶层部门
    select 
        org_id,
        org_name,
        org_level,
        parent_org_id,
        cast(org_name as varchar(1000)) as full_path,
        org_id as root_org_id,
        org_name as root_org_name
    from "devops_db"."public_staging"."stg_mdm_organizations"
    where parent_org_id is null or parent_org_id = ''

    union all

    -- 递归：关联子部门
    select 
        child.org_id,
        child.org_name,
        child.org_level,
        child.parent_org_id,
        cast(parent.full_path || ' > ' || child.org_name as varchar(1000)) as full_path,
        parent.root_org_id,
        parent.root_org_name
    from "devops_db"."public_staging"."stg_mdm_organizations" child
    join org_tree parent on child.parent_org_id = parent.org_id
)

select * from org_tree
  );
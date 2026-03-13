
/*
    ZenTao Execution Hierarchy Flat Map
    
    Recursive CTE to find the mapping from any ZenTao Execution/Project ID 
    to the Master Project ID in MDM.
*/

with recursive zentao_tree as (
    -- Anchor: Nodes that have a direct mdm_project_id
    select 
        execution_id,
        parent_id,
        mdm_project_id as master_project_id
    from {{ ref('stg_zentao_executions') }}
    where mdm_project_id is not null

    union all

    -- Recursive: Children of the above nodes
    select
        child.execution_id,
        child.parent_id,
        parent.master_project_id
    from {{ ref('stg_zentao_executions') }} child
    join zentao_tree parent on child.parent_id = parent.execution_id
)

select 
    execution_id,
    master_project_id
from zentao_tree

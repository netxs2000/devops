/*
    GitLab 用户映射助手
    将 GitLab 的 internal_user_id 转换为 MDM global_user_id
*/

with 

alignment as (
    select * from "devops_db"."public_intermediate"."int_identity_alignment"
    where source_system = 'GITLAB' and identifier_type = 'EXTERNAL_ID'
)

select 
    identifier_value as gitlab_user_id,
    master_user_id
from alignment
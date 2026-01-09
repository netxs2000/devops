
  
    

  create  table "devops_db"."public_marts"."fct_developer_activity_profile__dbt_tmp"
  
  
    as
  
  (
    /*
    开发者 DNA 画像 (Developer Activity Profile) - Refactored v2
    
    基于 DWS 层模型汇总，刻画开发者的行为特征。
    相对于 v1，本模型不再从原子原子事件流重算，而是利用预聚合的 DWS 层提高查询效率。
*/

with 

dws_stats as (
    select
        user_id,
        sum(commit_count) as commit_count,
        sum(review_count) as review_comment_count,
        sum(mr_open_count) as mr_open_count,
        sum(issue_close_count) as issue_closed_count,
        sum(daily_impact_score) as total_impact_score,
        min(metric_date) as first_active_day,
        max(metric_date) as last_active_day
    from "devops_db"."public_marts"."dws_developer_metrics_daily"
    group by 1
),

users as (
    select * from "devops_db"."public_staging"."stg_mdm_identities"
)

select
    u.user_id,
    u.real_name,
    u.department,
    s.commit_count,
    s.review_comment_count,
    s.mr_open_count,
    s.issue_closed_count,
    s.total_impact_score,
    
    -- 角色判定逻辑 (封装在应用层事实表中)
    case 
        when s.review_comment_count > s.commit_count * 2 then 'Review Master'
        when s.commit_count > 50 and s.issue_closed_count < 5 then 'Code Machine'
        when s.issue_closed_count > 20 then 'Task Closer'
        else 'Generalist'
    end as developer_archetype,
    
    round(
        s.total_impact_score / 
        nullif(extract(day from (s.last_active_day::timestamp - s.first_active_day::timestamp)) + 1, 0)::numeric, 
        2
    ) as daily_velocity
    
from users u
join dws_stats s on u.user_id = s.user_id
where u.is_active = true
order by s.total_impact_score desc
  );
  
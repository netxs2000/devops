-- Nexus 组件与 GitLab 提交关联中间表
-- 小白版逻辑：把 Nexus 里的“防伪印章”和 GitLab 里的“代码指纹”对对碰

with nexus_components as (
    select * from {{ ref('stg_nexus_components') }}
    where commit_sha is not null
),

gitlab_commits as (
    select * from {{ ref('stg_gitlab_commits') }}
),

-- 1. 核心关联逻辑
joined as (
    select
        n.component_id,
        n.component_group,
        n.component_name,
        n.component_version,
        n.commit_sha,
        n.created_at as nexus_created_at, -- Nexus 发现制品的时间
        
        g.project_id as gitlab_project_id,
        g.committed_date as git_committed_at, -- 代码提交时间
        g.author_email,
        
        -- 2. 计算打包延迟 (Nexus 创建时间 - 代码提交时间)
        -- 用来衡量从代码写完到包飞进仓库要等多久
        extract(epoch from (n.created_at - g.committed_date)) / 60.0 as build_latency_minutes
    from nexus_components n
    inner join gitlab_commits g on n.commit_sha = g.commit_sha
)

select * from joined

-- fct_pm_requirement_traceability.sql
-- 整合需求(Story)及其对应的测试状态与发布计划
WITH stories AS (
    SELECT 
        issue_unique_id,
        story_id,
        issue_title,
        issue_status,
        priority,
        product_id,
        plan_id,
        opened_by,
        created_at
    FROM {{ ref('stg_zentao_issues') }}
    WHERE issue_type = 'feature'
),

test_coverage AS (
    SELECT * FROM {{ ref('int_zentao_story_test_coverage') }}
),

release_mapping AS (
    -- 关联到推导出的发布版本
    SELECT * FROM {{ ref('int_zentao_release_plans') }}
)

SELECT
    s.issue_unique_id,
    s.issue_title,
    s.issue_status,
    s.priority,
    s.opened_by,
    s.created_at,
    -- 关联产品
    p.product_name,
    -- 关联质量状态
    COALESCE(t.testing_status, 'UNCOVERED') AS testing_status,
    t.test_case_count,
    t.automation_coverage,
    -- 关联发布信息
    r.release_name AS target_release
FROM stories s
LEFT JOIN {{ ref('stg_zentao_products') }} p ON s.product_id = p.product_id
LEFT JOIN test_coverage t ON s.story_id = t.story_id
LEFT JOIN release_mapping r ON s.plan_id = r.inferred_plan_id

-- int_zentao_release_plans.sql
-- 逻辑：通过 Release -> Build -> Story -> Plan 链路进行自动推导
WITH releases AS (
    SELECT * FROM {{ ref('stg_zentao_releases') }}
),

stories AS (
    SELECT * FROM {{ ref('stg_zentao_issues') }}
    WHERE issue_type = 'feature'
      AND plan_id IS NOT NULL
),

-- 建立发布与计划的交叉关联
release_plan_cross AS (
    SELECT
        r.release_id,
        r.release_name,
        r.product_id,
        s.plan_id,
        COUNT(s.issue_unique_id) AS covered_stories_count,
        -- 找出包含需求最多的计划作为主关联计划
        ROW_NUMBER() OVER(PARTITION BY r.release_id ORDER BY COUNT(s.issue_unique_id) DESC) as rank
    FROM releases r
    JOIN stories s ON 
        -- 检查 Release 所属的 Build ID 是否在 Story 关联的 Build 列表中
        -- 适配 JSON 数组或逗号分隔字符串
        (s.raw_data->>'build')::text LIKE concat('%', r.build_id::text, '%')
    GROUP BY 1, 2, 3, 4
)

SELECT
    release_id,
    release_name,
    product_id,
    plan_id AS inferred_plan_id,
    covered_stories_count
FROM release_plan_cross
WHERE rank = 1

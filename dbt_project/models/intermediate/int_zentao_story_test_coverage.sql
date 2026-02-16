-- int_zentao_story_test_coverage.sql
WITH stories AS (
    SELECT 
        issue_unique_id,
        raw_id AS story_id,
        product_id,
        issue_title
    FROM {{ ref('stg_zentao_issues') }}
    WHERE issue_type = 'feature'
),

test_stats AS (
    -- 聚合需求关联的用例信息
    SELECT 
        requirement_id,
        COUNT(case_id) AS total_cases,
        COUNT(CASE WHEN is_automated THEN 1 END) AS automated_cases,
        -- 获取该需求下所有用例的集成状态 (只要有一个用例挂了，需求质量就不及格)
        MIN(CASE 
            WHEN last_run_result = 'pass' THEN 3
            WHEN last_run_result = 'blocked' THEN 2
            WHEN last_run_result = 'fail' THEN 1
            ELSE 0 
        END) AS quality_score
    FROM {{ ref('stg_zentao_test_cases') }}
    WHERE requirement_id IS NOT NULL
    GROUP BY 1
)

SELECT
    s.issue_unique_id,
    s.story_id,
    s.issue_title,
    COALESCE(t.total_cases, 0) AS test_case_count,
    COALESCE(t.automated_cases, 0) AS automated_case_count,
    CASE 
        WHEN t.total_cases IS NULL THEN 'UNCOVERED'
        WHEN t.quality_score = 3 THEN 'PASS'
        WHEN t.quality_score = 1 THEN 'FAIL'
        ELSE 'PENDING'
    END AS testing_status,
    -- 自动化率
    CASE 
        WHEN COALESCE(t.total_cases, 0) = 0 THEN 0
        ELSE ROUND(t.automated_cases::numeric / t.total_cases, 2)
    END AS automation_coverage
FROM stories s
LEFT JOIN test_stats t ON s.story_id = t.requirement_id

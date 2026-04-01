# DevOps Platform 系统资源清单 (PROJECT_MAP.md)

> **定位**：本文件为 AI 助手（及开发者）提供全局资源导航。在寻找 Client, Worker, Test, Model 时优先读取本图谱。

## devops_collector
```text
devops_collector/
  config.py
  mq.py
  scheduler.py
  worker.py [⚙️ WORKER: Business Orchestration]
  alembic/
    env.py
    versions/
      15670218bb0d_check_sync.py
      24a4cf7d18f5_surrogate_pk_shift.py
      2a026ee8eec0_add_cognitive_complexity_column.py
      2cc810bde1ac_add_lookup_index_to_nexus_components.py
      3414408a4c10_refactor_rbac_models.py [📄 MODELS: Schema]
      68009a76ff76_add_lineage_fields.py
      6fcea0da41c5_add_commit_sha_to_nexus_components.py
      9778479f5120_merge_heads.py
      a1b2c3d4e5f6_rename_mdm_product_to_mdm_products.py
      b1cf984c9cd9_extend_sync_log_with_external_fields.py
      c7cdb0fad960_remove_product_code_column.py
      f1e2d3c4b5a6_comprehensive_schema_refinement.py
  auth/
    auth_database.py
    auth_dependency.py
    auth_router.py
    auth_schema.py
    auth_service.py [🛠️ SERVICE: Data Logic]
  core/
    admin_service.py [🛠️ SERVICE: Data Logic]
    algorithms.py
    base_client.py [⚡ CLIENT: API Connection]
    base_worker.py [⚙️ WORKER: Business Orchestration]
    business_auth.py
    devex_pulse_service.py [🛠️ SERVICE: Data Logic]
    dora_service.py [🛠️ SERVICE: Data Logic]
    exceptions.py
    identity_manager.py
    notifiers.py
    okr_service.py [🛠️ SERVICE: Data Logic]
    organization_service.py [🛠️ SERVICE: Data Logic]
    plugin_loader.py
    promotion_service.py [🛠️ SERVICE: Data Logic]
    registry.py
    retention_manager.py
    reverse_etl.py
    schemas.py
    security.py
    services.py [🛠️ SERVICE: Data Logic]
    utils.py
    analytics/
      eloc.py
  models/
    base_models.py [📄 MODELS: Schema]
    dependency.py
    events.py
    service_desk.py [🛠️ SERVICE: Data Logic]
    test_management.py [🚀 TEST: Unit Protection]
  plugins/
    dependency_check/
      add_dependency_check_tables.sql
      config.py
      worker.py [⚙️ WORKER: Business Orchestration]
    gitlab/
      airbyte_client.py [⚡ CLIENT: API Connection]
      config.py
      events.py
      gitlab_client.py [⚡ CLIENT: API Connection]
      identity_service.py [🛠️ SERVICE: Data Logic]
      iteration_plan_service.py [🛠️ SERVICE: Data Logic]
      labels.py
      models.py [📄 MODELS: Schema]
      parser.py
      quality_service.py [🛠️ SERVICE: Data Logic]
      service_desk_service.py [🛠️ SERVICE: Data Logic]
      test_management_service.py [🛠️ SERVICE: Data Logic]
      worker.py [⚙️ WORKER: Business Orchestration]
      mixins/
        asset_mixin.py
        base_mixin.py
        commit_mixin.py
        issue_mixin.py
        mr_mixin.py
        pipeline_mixin.py
        traceability_mixin.py
      sql_views/
        activity_analysis.sql
        author_stats.sql
        branch_ops.sql
        burnout_radar.sql
        code_evolution.sql
        dept_performance.sql
        dora_metrics.sql
        extension_stats.sql
        innersource.sql
        process_deviation.sql
        project_value.sql
        review_quality.sql
        tag_analytics.sql
        user_code_review.sql
        user_heatmap.sql
        user_impact.sql
        user_lifecycle.sql
        user_tech_stack.sql
    jenkins/
      airbyte_client.py [⚡ CLIENT: API Connection]
      client.py [⚡ CLIENT: API Connection]
      config.py
      models.py [📄 MODELS: Schema]
      parser.py
      worker.py [⚙️ WORKER: Business Orchestration]
    jfrog/
      client.py [⚡ CLIENT: API Connection]
      config.py
      models.py [📄 MODELS: Schema]
      worker.py [⚙️ WORKER: Business Orchestration]
    jira/
      airbyte_client.py [⚡ CLIENT: API Connection]
      client.py [⚡ CLIENT: API Connection]
      config.py
      models.py [📄 MODELS: Schema]
      worker.py [⚙️ WORKER: Business Orchestration]
    nexus/
      client.py [⚡ CLIENT: API Connection]
      config.py
      models.py [📄 MODELS: Schema]
      worker.py [⚙️ WORKER: Business Orchestration]
    sonarqube/
      airbyte_client.py [⚡ CLIENT: API Connection]
      client.py [⚡ CLIENT: API Connection]
      config.py
      models.py [📄 MODELS: Schema]
      quality_metrics.sql
      transformer.py
      worker.py [⚙️ WORKER: Business Orchestration]
    wecom/
      client.py [⚡ CLIENT: API Connection]
      worker.py [⚙️ WORKER: Business Orchestration]
    zentao/
      client.py [⚡ CLIENT: API Connection]
      config.py
      models.py [📄 MODELS: Schema]
      worker.py [⚙️ WORKER: Business Orchestration]
  sql/
    ABI_Analysis.sql
    Capitalization_Audit.sql
    Compliance_Audit.sql
    Gitprime.sql
    Michael_Feathers_Code_Hotspots.sql
    Project_Health.sql
    SPACE_Framework.sql
    Talent_Radar.sql
    User_Profile.sql
    Value_Stream.sql
    Work_Items.sql
  utils/
    schema_sync.py
```

## tests/unit/devops_collector
```text
devops_collector/
  conftest.py
  test_jenkins_test_execution.py [🚀 TEST: Unit Protection]
  test_new_models.py [📄 MODELS: Schema]
  test_pyairbyte_adapter.py [🚀 TEST: Unit Protection]
  test_pyairbyte_sonarqube.py [🚀 TEST: Unit Protection]
  core/
    test_admin_service.py [🛠️ SERVICE: Data Logic]
    test_algorithms.py [🚀 TEST: Unit Protection]
    test_base_client.py [⚡ CLIENT: API Connection]
    test_business_auth.py [🚀 TEST: Unit Protection]
    test_rate_limiter.py [🚀 TEST: Unit Protection]
  plugins/
    gitlab/
      test_analyzer.py [🚀 TEST: Unit Protection]
      test_gitlab_client.py [⚡ CLIENT: API Connection]
      test_gitlab_mapping.py [🚀 TEST: Unit Protection]
      test_gitlab_matcher.py [🚀 TEST: Unit Protection]
      test_gitlab_worker.py [⚙️ WORKER: Business Orchestration]
      test_quality_service.py [🛠️ SERVICE: Data Logic]
      test_test_management_service.py [🛠️ SERVICE: Data Logic]
      test_traceability_logic.py [🚀 TEST: Unit Protection]
    jira/
      test_jira_client.py [⚡ CLIENT: API Connection]
      test_jira_worker.py [⚙️ WORKER: Business Orchestration]
    nexus/
      test_nexus_worker.py [⚙️ WORKER: Business Orchestration]
    zentao/
      test_zentao_client.py [⚡ CLIENT: API Connection]
      test_zentao_sync.py [🚀 TEST: Unit Protection]
      test_zentao_worker.py [⚙️ WORKER: Business Orchestration]
```

## devops_portal
```text
devops_portal/
  dependencies.py
  events.py
  main.py
  schemas.py
  schemas_pulse.py
  state.py
  routers/
    admin_router.py
    devex_pulse_router.py
    iteration_plan_router.py
    plugin_router.py
    quality_router.py
    security_router.py
    service_desk_router.py [🛠️ SERVICE: Data Logic]
    test_management_router.py [🚀 TEST: Unit Protection]
    webhook_router.py
  static/
    css/
    js/
      components/
      modules/
    tests/
```


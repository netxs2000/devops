# 高级研发效能指标体系设计方案 (GitPrime-Style Metrics)

## 1. 概述

本设计旨在引入 GitPrime (现 Pluralsight Flow) 风格的“行为模式”分析指标，从代码搅动、结构影响、心流状态和协作贡献四个维度，对现有的 ELOC 体系进行补充，更全面地评估研发效能。

## 2. 新增核心指标定义

### 2.1 代码搅动率 (Code Churn) - "返工率"

* **定义**: 衡量近期代码的修改频率，识别需求不确定性或返工风险。
* **计算逻辑**:
  * 如果一行代码在创建后的 **21天内** 被修改或删除，则视为 "Churn"。
  * **Churn Rate** = `(近期自身代码修改行数)` / `(总代码变动行数)`
* **洞察**:
  * < 10%: 健康，一次做对。
  * \> 30%: 风险，可能在反复试错或需求变动剧烈。

### 2.2 影响力指数 (Impact Score) - "技术暴击"

* **定义**: 衡量代码变更对系统的结构性影响，而非简单的行数堆砌。
* **计算逻辑**:
  * 基于 ELOC，但增加权重：
  * **老代码修改 (Legacy Refactor)**: 权重 1.5x (修改 >6个月前的代码)
  * **广度 (Breadth)**: 权重 `log(涉及文件数 + 1)` (跨模块修改更复杂)
  * **复杂度 (Complexity)**: 权重 `f(圈复杂度变化)` (如果可用)
  * **公式**: `Impact = ELOC * LegacyFactor * BreadthFactor`
* **洞察**: 识别代码量少但解决核心难题的架构师。

### 2.3 心流效率 (Flow Efficiency / TTF) - "工作状态"

* **定义**: 衡量开发者的工作连贯性和抗打断能力。
* **计算逻辑**:
  * **活跃时段 (Active Hours)**: 当天第一次 Commit 到最后一次 Commit 的时间跨度。
  * **提交密度 (Commit Density)**: `活跃时段 / 提交次数`。
  * **TTF (Time to First Commit)**: 每日打卡时间。
* **洞察**: 分析是否存在过度会议导致的碎片化工作。

### 2.4 摆渡人指数 (Sherpa Score) - "协作贡献"

* **定义**: 衡量非代码产出的工程贡献，特别是 Code Review。
* **计算逻辑**:
  * **Review 参与度**: `参与 Review 的 MR 数量`
  * **深度评论**: `发表的 Comment 数量` (权重 1.0)
  * **把关 (Approvals)**: `通过的 MR 数量` (权重 0.5)
  * **公式**: `Sherpa Score = (Comments * 1.0) + (Approvals * 0.5) + (Rejected MRs * 2.0)`
* **洞察**: 识别保障团队质量的幕后英雄 (Tech Lead/Mentor)。

## 3. 数据库设计 (Schema Changes)

需在 `devops_collector/models` 中进行如下扩展：

### 3.1 扩展 `CommitMetrics` 表

增加单次提交的高级属性：

```python
class CommitMetrics(Base):
    # ... 现有字段 ...
    impact_score = Column(Float, default=0.0)  # 影响力分数
    churn_lines = Column(Integer, default=0)   # 属于返工的行数
    is_legacy_refactor = Column(Boolean, default=False) # 是否包含老代码修改
    file_count = Column(Integer, default=0)    # 涉及文件数
```

### 3.2 新增 `DailyDevStats` 表 (每日快照)

按天聚合开发者的状态，用于计算 TTF 和 Flow：

```python
class DailyDevStats(Base):
    __tablename__ = 'daily_dev_stats'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('mdm_identities.id'))
    date = Column(Date, index=True)
    
    first_commit_time = Column(DateTime)
    last_commit_time = Column(DateTime)
    commit_count = Column(Integer, default=0)
    
    total_impact = Column(Float, default=0.0)
    total_churn = Column(Integer, default=0)
    
    review_count = Column(Integer, default=0)   # 参与评审数
    review_comments = Column(Integer, default=0) # 评论数
```

## 4. 实现计划

1. **Schema 迁移**: 更新 `base_models.py`。
2. **算法实现**:
    * 升级 `ELOCAnalyzer` 增加 `Impact` 计算。
    * 新建 `ChurnAnalyzer` (需回溯历史)。
    * 新建 `DailyAggregator` (每日定时任务)。
3. **视图更新**: 更新 SQL View 以包含新指标。
4. **可视化**: 升级 Streamlit `Value Leaderboard` 页面，增加 "Quality" 和 "Collaboration" 选项卡。

## 5. 预期效果

看板将从单一的 "排位赛" 变为多维度的 "能力雷达图"：

* **输出型 (Output)**: ELOC, Impact
* **质量型 (Quality)**: Churn Rate, Test Coverage
* **协作型 (Collaboration)**: Sherpa Score

---
status: Proposed
date: 2026-03-14
author: AI Architect
topic: CI/CD Pipeline Artifact Traceability Strategy (Jenkins & GitLab CI)
---

# Jenkins & GitLab CI 制品防伪印章埋点方案设计 (RFC)

## 1. 业务痛点与目标
目前 DevOps 平台的血缘追溯存在一处断层：我们可以计算 `代码 Merge`，也能抓取 `Nexus 制品生成`，但**无法建立它们之间的 1:1 精确绑定关系**。这使得 DORA 的核心指标 `Lead Time for Changes` 难以统计真实的端到端耗时。

**目标 / DoD**：
在不动业务线任何一行 Application 源码的前提下，通过修改公共 CI 脚本，使得产出的每一块 Java/Docker 制品，在发布至 Nexus 时都强制携带唯一印章（主要是 `GIT_COMMIT_SHA`）。

## 2. 埋点策略库 (The Tracking Strategy)

由于贵司存在双重构建链条 (80% Jenkins + 20% GitLab Runner)，且底层技术栈聚焦于 Java (Maven)，以下按执行成本由低到高提供三种技术实现候选方案：

### Option A: Maven 打包附带文件法 (最普适，修改小)
**推荐度**：⭐⭐⭐⭐⭐
**原理**：在 `mvn package` / `mvn deploy` 执行前，向 Target 最终发布目录生成一个包含环境变量元数据的 Properties 文件。它将与 JAR/WAR 包一起发布在同一个 Nexus Path 下。

* **Jenkins 脚本 (Pipeline 版)**:
  ```groovy
  stage('Build & Tag') {
      steps {
          // 当前 Git Checkout 的 SHA 通常以环境变量 GIT_COMMIT 存在
          sh """
          echo "commit_sha=${env.GIT_COMMIT}" > target/devops-trace.properties
          echo "pipeline_job=${env.JOB_NAME}" >> target/devops-trace.properties
          echo "pipeline_id=${env.BUILD_NUMBER}" >> target/devops-trace.properties
          
          mvn clean deploy
          """
      }
  }
  ```
* **GitLab CI (`.gitlab-ci.yml`)**:
  ```yaml
  build-and-deploy:
    stage: deploy
    script:
      # 借助 GitLab 官方内置的环境变量，生成防伪溯源文件
      - echo "commit_sha=${CI_COMMIT_SHA}" > target/devops-trace.properties
      - echo "pipeline_job=${CI_JOB_NAME}" >> target/devops-trace.properties
      - echo "pipeline_id=${CI_PIPELINE_ID}" >> target/devops-trace.properties
      
      # 执行 Maven 构建并推送到 Nexus
      - mvn clean deploy
  ```

  > 💡 **小白专区：GitLab CI 是如何工作的？**
  > 如果您觉得上方的脚本有些陌生，别担心。在 GitLab 体系中，上述的 `CI_COMMIT_SHA`（当前代码提交的唯一防伪码）、`CI_PIPELINE_ID` 等变量**不需要您手动去配置*。它们是 **GitLab Runner 自动注入** 到执行环境中的系统内置参数。
  > 
  > 只要将上方的 `script` 补充到您现有的 `.gitlab-ci.yml`（GitLab 专属流水线配制文件）的 `deploy` 环节中，平台以后在 Nexus 里拉下来的包，就如同烙上了一个“GitLab 出品”的出厂二维码！

**优势**：不需要修改业务方的 `pom.xml` 源码，不需要去研究复杂的构建插件升级。DevOps 侧的 Nexus Collector 爬虫以后只需抓取这个附属的 `.properties` 文件，就能像“滴血认亲”一样，百分百将生成的 JAR 与您写在 GitLab 里的某一行代码挂靠在一起。


### Option B: Maven Manifest 注入法 (最优雅，需改业务)
**推荐度**：⭐⭐⭐
**原理**：通过在公共父级 `pom.xml` 中配置 `maven-jar-plugin` 或者 `spring-boot-maven-plugin`，直接将环境变量嵌入生成物 (`META-INF/MANIFEST.MF`) 中。

```xml
<!-- 在公司的父 pom.xml 中加入统一配置 -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-jar-plugin</artifactId>
    <configuration>
        <archive>
            <manifestEntries>
                <Git-Commit>${env.GIT_COMMIT}</Git-Commit>
                <Jenkins-Build>${env.BUILD_NUMBER}</Jenkins-Build>
            </manifestEntries>
        </archive>
    </configuration>
</plugin>
```
**缺点**：如果存在很多脱离父 Pom 规范的历史孤岛项目，推行难度极高。我们的 Nexus 平台解析 JAR 内部数据成本高于解析旁路文件。

### Option C: Docker Image Label 注入法 (适用于云原生服务)
**推荐度**：⭐⭐⭐⭐ (如果是容器镜像，必选)
**原理**：对于 Docker 化交付的项目，在生成镜像时通过 `--label` 打入业务元数据。

```bash
docker build \
  --label "com.company.devops.commit_sha=${GIT_COMMIT}" \
  --label "com.company.devops.pipeline_url=${BUILD_URL}" \
  -t my-nexus.com:8082/repo/app:v1 .

docker push my-nexus.com:8082/repo/app:v1
```

## 3. DevOps 侧平台协同
一旦**开发部/运维组**开始采纳如上的 Option A，平台开发会做以下配合作业：

1. 修改 `devops_collector/plugins/nexus/worker.py`，增加对以 `devops-trace.properties` 结尾的 NexusAsset 的解析。
2. 将解析出来的 `commit_sha` 关联键更新入 `nexus_components` 模型中新扩充的字段。
3. 利用 dbt 生成终极事实表 `fct_lead_time_from_commit_to_nexus()`。

## 4. 落地建议 (研讨议题)
在开会拉齐运维时，您可以聚焦一个抓手：**“我们只修改 Jenkins 模板（全局 Library）”**，不用让业务开发改动他们的 `pom.xml` 源码。

如果觉得 Option A 写入文件再发布会弄脏 Nexus（虽然是主流做法），可以讨论是否有条件让 CI 直接在这边触发一个 DevOps Collector 自定义的“发包成功 Webhook 登记”接口作为替代方案。

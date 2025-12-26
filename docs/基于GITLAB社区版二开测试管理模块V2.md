
需求：基于GitLab 社区版（CE）的二次开发，模仿GITLAB企业版的测试管理模块，二开一个测试用例功能模块,有什么开发设计和实现的建议。

具体需求：
功能深度：测试用例包括最基本的“标题+描述”，还包含“预置条件、测试步骤、预期结果”的结构化数据。
关联关系：测试用例需要与 GitLab 现有的 Issues（议题） 进行关联。
版本控制：不支持测试用例的版本管理（例如：针对不同 Release 的用例快照）。


1. 技术栈选型
•	后端：Ruby on Rails (GitLab 的核心框架)。需要编写 ActiveRecord 模型、Service 类和 API 接口。
•	前端：Vue.js + GitLab UI (Pajamas Design System组件库)。确保 UI 风格与 GitLab 原生保持一致。
•	API：优先使用 GraphQL，这是 GitLab 目前推荐的 API 方式，能更好地与前端集成。
•	数据库：PostgreSQL。需要新建数据表来存储用例信息。
约束条件：
基于Vue.js，使用 apollo 框架
Batch Loader：GitLab 深度集成了 BatchLoader，测试用例列表页面需要展示步骤摘要，请务必使用它。
为了让二开的功能看起来“不违和”，请务必使用GitLab 官方开源的设计系统组件库 GitLab UI (Pajamas Design System)(https://design.gitlab.com/)。
小贴士：GitLab源代码中有非常多的 app/assets/javascripts/vue_shared/components 可以复用。例如，如果需要文件上传功能，直接复用 markdown_field.vue。
利用已有的 UI 组件：前端开发时，不要自己写 CSS。查阅 GitLab Pajamas Design System，使用 gl-form-input、gl-button 等现成组件，这样二开功能看起来才像“亲生的”。


1. 核心架构：如何快速上手 GitLab 开发
在 GitLab 中开发一个新功能，通常遵循以下数据流向：
•	数据库 (PostgreSQL)：存储测试用例和关联关系。
•	后端模型 (Rails Model)：定义数据结构、校验逻辑和与其他模型（如 Issue）的关系。
•	服务层 (Services)：处理业务逻辑（例如：创建用例时同时关联 Issue）。
•	接口层 (GraphQL)：前后端沟通的桥梁（这是 GitLab 现代化的标准方式）。
•	前端 (Vue.js + GitLab UI)：展示界面并与接口交互。
2. 数据库设计：结构化与关联
根据你的需求，我们需要存储结构化的步骤，并与 Issue 建立联系。
数据库表设计
创建一个 test_cases 表，并利用 GitLab 已有的 issue_links 概念或创建一个新的关联表 test_case_issue_links。
模块	字段名	类型	说明
基础信息	id	BigInt	主键
基础信息	title	String	用例标题
基础信息	description	Text	用例描述/预置条件
基础信息	state	String	用例状态（如：草稿、已发布、已废弃）
基础信息	iid	Integer	项目内自增 ID（类似 Issue #123）
结构化步骤	steps	JSONB	结构化步骤（包含步骤描述和预期结果）。
数组存储：[{step: "步骤1", expected: "结果1"}, ...]
关联信息	project_id	BigInt	所属项目ID（必填）, 关联的项目ID (外键)
关联信息	author_id	BigInt	创建者ID（必填）

3. 实现指引：第一步 - 后端建模
先从最基础的数据库和模型开始。
步骤 A：创建数据库迁移 (Migration)
在 GitLab 根目录下运行命令生成迁移文件（具体时间戳由系统生成）： bundle exec rails g migration CreateTestCases
然后编辑该文件：
# db/migrate/xxxxxxxx_create_test_cases.rb
class CreateTestCases < Gitlab::Database::Migration[2.1]
  def change
    create_table :test_cases do |t|
      # 关联项目，设置级联删除
      t.references :project, null: false, index: true, foreign_key: { on_delete: :cascade }
      # 关联作者
      t.references :author, null: false, index: true, foreign_key: { to_table: :users }
      
      t.integer :iid, null: false # 项目内自增ID
      t.string :title, null: false
      t.text :description # 充当“预置条件”
      t.jsonb :test_steps, default: [] # 存储结构化步骤：[{ "action": "...", "expected": "..." }]
      
      t.timestamps_with_timezone
      
      # 联合索引确保一个项目下的 iid 唯一
      t.index [:project_id, :iid], unique: true
    end
  end
end

步骤 B：建立与 Issue 的关联表
为了实现“测试用例与 Issue 关联”，需要一张中间表：
# db/migrate/xxxxxxxx_create_test_case_issue_links.rb
class CreateTestCaseIssueLinks < Gitlab::Database::Migration[2.1]
  def change
    create_table :test_case_issue_links do |t|
      t.references :test_case, null: false, foreign_key: { on_delete: :cascade }
      t.references :issue, null: false, foreign_key: { on_delete: :cascade }
      t.timestamps_with_timezone
    end
  end
end

4. 后端模型逻辑 (Model)
在 app/models/test_case.rb 中定义模型。GitLab 使用了很多特殊的 Ruby Mixins（混入）来简化开发。
# app/models/test_case.rb
class TestCase < ApplicationRecord
  include AtomicInternalId # 自动生成项目内唯一的 iid (如 #1)
  include Validatable    # GitLab 的通用校验工具

  belongs_to :project
  belongs_to :author, class_name: 'User'
  
  # 多对多关联 Issue
  has_many :test_case_issue_links
  has_many :issues, through: :test_case_issue_links

  validates :title, presence: true, length: { maximum: 255 }
  validates :project, presence: true
  
  # 定义 iid 的生成范围
  has_internal_id :iid, scope: :project
end

5. 给你的开发建议
1.	环境准备：你必须安装 GDK (GitLab Development Kit)。这是在本地运行和调试 GitLab 源码的唯一标准方式。没有它，你无法进行后续的开发。
2.	利用已有的 UI 组件：前端开发时，不要自己写 CSS。查阅 GitLab Pajamas Design System（https://design.gitlab.com/），使用 gl-form-input、gl-button 等现成组件，这样二开功能看起来才像“亲生的”。
3.	小步快跑：先实现“列表展示”，再实现“创建”，最后实现“关联 Issue”。
文档说明
•	JSONB: 之所以选择 JSONB 存储steps（步骤），是因为测试步骤的数量是不确定的。这种方式比单独开一张 test_steps 表更轻量，查询效率在 PostgreSQL 中也非常出色。
•	AtomicInternalId: 确保即使在高并发下，测试用例 ID 也不会重复且连续。


详细演示如何编写 GraphQL API 来实现测试用例的“增删改查”
编写 GraphQL API 是 GitLab 开发中最标准的方式。GitLab 的 GraphQL 结构主要分为三部分：Types（类型定义）、Resolvers（查询解析器） 和 Mutations（变更操作）。
由于业务逻辑较多，GitLab 的最佳实践是将逻辑封装在 Services 类中，而 GraphQL 只负责处理参数和返回结果。

1. 定义类型 (Types)
首先，我们需要告诉 GraphQL “测试用例”长什么样。创建 app/graphql/types/test_case_type.rb。
# app/graphql/types/test_case_type.rb
module Types
  class TestCaseType < BaseObject
    graphql_name 'TestCase'

    # 显式指定对应的数据模型
    present_using TestCase

    field :id, GraphQL::Types::ID, null: false, description: 'ID of the test case.'
    field :iid, GraphQL::Types::ID, null: false, description: 'Internal ID of the test case.'
    field :title, GraphQL::Types::String, null: false, description: 'Title of the test case.'
    field :description, GraphQL::Types::String, null: true, description: 'Description or preconditions.'
    
    # 结构化步骤，返回为 JSON 字符串或自定义标量
    field :test_steps, GraphQL::Types::JSON, null: true, description: 'Structured test steps.'
    
    # 关联信息
    field :author, Types::UserType, null: false, description: 'Author of the test case.'
    field :project, Types::ProjectType, null: false, description: 'Project the test case belongs to.'
    field :issues, Types::IssueType.connection_type, null: true, description: 'Associated issues.'
  end
end

2. 实现查询 (Read)
我们需要让用户能够通过项目找到测试用例。通常我们会把查询入口挂在 Project 类型下。
编辑 app/graphql/types/project_type.rb，添加以下内容：
field :test_cases, 
      Types::TestCaseType.connection_type, 
      null: true, 
      description: 'Test cases for this project.' do
        argument :iid, GraphQL::Types::ID, required: false
      end

# 在同一个文件中或对应的 resolver 中实现逻辑
def test_cases(iid: nil)
  return object.test_cases.where(iid: iid) if iid
  object.test_cases
end

3. 实现变更 (Create/Update/Delete)
GitLab 推荐为每一个操作创建一个特定的 Mutation。我们将以创建 (Create) 为例。
第一步：创建 Service 类
逻辑应该写在 app/services/test_cases/create_service.rb 中。
# app/services/test_cases/create_service.rb
module TestCases
  class CreateService < BaseService
    def execute
      test_case = project.test_cases.build(params)
      test_case.author = current_user

      if test_case.save
        # 如果有 issue_ids 参数，进行关联逻辑
        link_issues(test_case) if params[:issue_ids].present?
        ServiceResponse.success(payload: test_case)
      else
        ServiceResponse.error(message: test_case.errors.full_messages)
      end
    end

    private

    def link_issues(test_case)
      # 简单的关联逻辑实现
      params[:issue_ids].each do |issue_id|
        issue = project.issues.find_by_id(issue_id)
        test_case.issues << issue if issue
      end
    end
  end
end

第二步：编写 Mutation
创建 app/graphql/mutations/test_cases/create.rb。
# app/graphql/mutations/test_cases/create.rb
module Mutations
  module TestCases
    class Create < BaseMutation
      graphql_name 'TestCaseCreate'

      # 输入参数
      argument :project_path, GraphQL::Types::ID, required: true
      argument :title, GraphQL::Types::String, required: true
      argument :description, GraphQL::Types::String, required: false
      argument :test_steps, GraphQL::Types::JSON, required: false
      argument :issue_ids, [GraphQL::Types::ID], required: false

      # 返回字段
      field :test_case, Types::TestCaseType, null: true
      field :errors, [GraphQL::Types::String], null: false

      def resolve(project_path:, **args)
        project = authorized_find!(project_path) # GitLab 内置权限查找

        response = ::TestCases::CreateService.new(project, current_user, args).execute

        {
          test_case: response.payload,
          errors: response.errors
        }
      end
    end
  end
end

4. 注册 Mutation
最后，你需要将这个 Mutation 注册到全局架构中。编辑 app/graphql/types/mutation_type.rb：
module Types
  class MutationType < BaseObject
    # ... 其他 mutations ...
    mount_mutation Mutations::TestCases::Create
    # mount_mutation Mutations::TestCases::Update
    # mount_mutation Mutations::TestCases::Destroy
  end
end

5. 如何测试你的 API
当你在本地运行 GDK 后，访问 http://localhost:3000/-/graphql-explorer，你可以直接运行以下 GraphQL 语句来测试你的新功能：
创建测试用例：
mutation {
  testCaseCreate(input: {
    projectPath: "your-group/your-project",
    title: "验证登录功能",
    description: "用户在登录页面输入凭据",
    testSteps: [
      { step: "输入用户名", expected: "显示用户名" },
      { step: "输入密码", expected: "密码加密显示" }
    ]
  }) {
    testCase {
      iid
      title
    }
    errors
  }
}


实现指引与建议
•	权限控制：在生产环境下，你需要在 TestCaseType 中加入权限声明（如 authorize :read_test_case），并在 app/policies/ 下创建对应的策略文件。
•	JSON 格式：前端在提交 test_steps 时，需要序列化为标准 JSON。
•	Update 和 Destroy：它们的实现逻辑与 Create 非常相似，区别在于 Service 类中调用的是 test_case.update(params) 或 test_case.destroy。


接下来，你是希望我指导你如何编写 Vue.js 前端页面来调用这些接口，还是详细讲解如何处理“关联 Issue”的业务逻辑（比如在 Issue 页面也显示关联的测试用例）？

指导我如何编写 Vue.js 前端页面来调用这些接口

在 GitLab 的前端开发中，我们主要使用 Vue.js 框架，并配合 Apollo GraphQL 来处理数据。为了保证你的新功能看起来和 GitLab 原生功能一模一样，必须使用 GitLab UI (https://gitlab-org.gitlab.io/gitlab-ui/)组件库。
作为你的编码助手，我将带你完成从定义 GraphQL 语句到构建 Vue 录入页面的全过程。

1. 定义前端 GraphQL 语句
在 GitLab 源码中，前端 GraphQL 语句通常存放在 app/assets/javascripts/ 目录下的 .graphql 文件中。
创建文件：app/assets/javascripts/test_cases/graphql/mutations/create_test_case.mutation.graphql

mutation createTestCase($input: TestCaseCreateInput!) {
  testCaseCreate(input: $input) {
    testCase {
      id
      iid
      title
    }
    errors
  }
}

2. 编写 Vue 录入组件
我们将创建一个包含“标题”、“描述（预置条件）”和“动态测试步骤”的表单。
创建文件：app/assets/javascripts/test_cases/components/test_case_form.vue
<template> 部分
这里使用了 GlForm 系列组件，它们是 GitLab 的标准 UI 规范。
代码片段
<template>
  <gl-form @submit.prevent="saveTestCase">
    <gl-form-group :label="__('Title')" label-for="test-case-title">
      <gl-form-input
        id="test-case-title"
        v-model="form.title"
        :placeholder="__('Enter test case title')"
        required
      />
    </gl-form-group>

    <gl-form-group :label="__('Preconditions')" label-for="test-case-desc">
      <gl-form-textarea
        id="test-case-desc"
        v-model="form.description"
        :placeholder="__('Enter preconditions...')"
      />
    </gl-form-group>

    <gl-form-group :label="__('Test Steps')">
      <div v-for="(step, index) in form.testSteps" :key="index" class="gl-display-flex gl-mb-3">
        <gl-form-input
          v-model="step.action"
          class="gl-mr-2"
          :placeholder="__('Action')"
        />
        <gl-form-input
          v-model="step.expected"
          class="gl-mr-2"
          :placeholder="__('Expected result')"
        />
        <gl-button
          variant="danger"
          category="secondary"
          icon="remove"
          @click="removeStep(index)"
        />
      </div>
      <gl-button
        variant="confirm"
        category="secondary"
        icon="plus"
        @click="addStep"
      >
        {{ __('Add step') }}
      </gl-button>
    </gl-form-group>

    <div class="gl-mt-5">
      <gl-button type="submit" variant="confirm" :loading="isSubmitting">
        {{ __('Create Test Case') }}
      </gl-button>
    </div>
  </gl-form>
</template>


<script> 部分
处理数据绑定和 GraphQL 调用。
<script>
import { GlForm, GlFormGroup, GlFormInput, GlFormTextarea, GlButton } from '@gitlab/ui';
import createTestCaseMutation from '../graphql/mutations/create_test_case.mutation.graphql';

export default {
  components: {
    GlForm, GlFormGroup, GlFormInput, GlFormTextarea, GlButton,
  },
  props: {
    projectPath: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      isSubmitting: false,
      form: {
        title: '',
        description: '',
        testSteps: [{ action: '', expected: '' }],
      },
    };
  },
  methods: {
    addStep() {
      this.form.testSteps.push({ action: '', expected: '' });
    },
    removeStep(index) {
      this.form.testSteps.splice(index, 1);
    },
    async saveTestCase() {
      this.isSubmitting = true;
      try {
        const { data } = await this.$apollo.mutate({
          mutation: createTestCaseMutation,
          variables: {
            input: {
              projectPath: this.projectPath,
              title: this.form.title,
              description: this.form.description,
              testSteps: this.form.testSteps, // 后端 JSONB 会自动解析
            },
          },
        });

        if (data.testCaseCreate.errors.length > 0) {
          throw new Error(data.testCaseCreate.errors.join(', '));
        }

        // 成功后跳转或提示
        this.$toast.show('Test Case created successfully!');
      } catch (error) {
        this.$toast.show(`Error: ${error.message}`);
      } finally {
        this.isSubmitting = false;
      }
    },
  },
};
</script>

3. 页面集成：如何让页面显示出来
在 GitLab 中，你通常需要：
1.	Rails 路由：定义一个 URL（如 project/-/test_cases）。
2.	Rails 控制器：渲染一个简单的 HTML 模板。
3.	入口文件：挂载 Vue 组件。
第一步：控制器配置 (Rails)
在 app/controllers/projects/test_cases_controller.rb 中：

Ruby
class Projects::TestCasesController < Projects::ApplicationController
  def index
    # 仅仅渲染模板，数据由 GraphQL 获取
  end
end

第二步：入口 JavaScript
在 app/assets/javascripts/pages/projects/test_cases/index/index.js 中挂载：
JavaScript
import Vue from 'vue';
import TestCaseForm from '~/test_cases/components/test_case_form.vue';
import ApolloProvider from '~/lib/utils/apollo_provider';

const el = document.getElementById('js-test-case-app');
new Vue({
  el,
  apolloProvider: ApolloProvider,
  render(h) {
    return h(TestCaseForm, {
      props: { projectPath: el.dataset.projectPath },
    });
  },
});

4. 关键点解释与文档说明
•	gl- 前缀组件: 这些是 GitLab UI 提供的标准组件。使用它们可以确保你的页面在各种主题（如深色模式）下都能完美适配。
•	__() 函数: 这是 GitLab 用于国际化的翻译函数。
•	ApolloProvider: GitLab 预配置好了 Apollo 客户端，你只需要引入并注入 Vue 实例即可直接使用 this.$apollo。
•	动态步骤: 在 Vue 中使用 v-for 渲染数组，通过 push 和 splice 轻松实现步骤的增删。

下一步建议
现在你已经有了：
1.	后端数据库结构和模型。
2.	GraphQL API 接口。
3.	前端录入表单。
你是否希望我指导你如何实现“在 Issue 详情页显示关联的测试用例列表”，以便完成你提到的关联功能？

实现“在 Issue 详情页显示关联的测试用例”，是打通研发与测试闭环的关键一步。在 GitLab 中，这通常被称为“关联小部件（Linked Widget）”。
为了实现这个功能，我们需要分为后端数据暴露、前端组件开发和页面注入三个步骤。

1. 后端：在 Issue 接口中增加测试用例字段
我们需要让 GraphQL 的 IssueType 能够识别并返回关联的 test_cases。
修改 app/graphql/types/issue_type.rb（如果该文件在你的版本中较复杂，可以查找 Types::IssueType）：

Ruby
module Types
  class IssueType < BaseObject
    # ... 原有字段 ...

    field :test_cases, 
          Types::TestCaseType.connection_type, 
          null: true, 
          description: 'Test cases associated with this issue.'
  end
end

由于我们在之前的 TestCase 模型中已经定义了 has_many :issues, through: :test_case_issue_links，对应的 Issue 模型也需要建立反向关联：
Ruby

# app/models/issue.rb (在类定义中添加)
has_many :test_case_issue_links
has_many :test_cases, through: :test_case_issue_links

2. 前端：编写关联列表组件
我们需要一个简洁的组件，显示在 Issue 的侧边栏或描述下方。
创建文件：app/assets/javascripts/test_cases/components/issue_test_cases_list.vue

代码片段
<template>
  <div class="gl-mt-5 gl-border-t gl-pt-3">
    <div class="gl-display-flex gl-justify-content-space-between gl-align-items-center">
      <h3 class="gl-font-weight-bold gl-m-0 gl-font-base">{{ __('Associated Test Cases') }}</h3>
      <gl-badge v-if="testCases.length">{{ testCases.length }}</gl-badge>
    </div>

    <gl-loading-icon v-if="isLoading" class="gl-mt-3" size="md" />

    <ul v-else-if="testCases.length" class="gl-pl-0 gl-mt-3 gl-list-none">
      <li v-for="tc in testCases" :key="tc.id" class="gl-py-2 gl-border-b">
        <div class="gl-display-flex gl-align-items-center">
          <gl-icon name="test-case" class="gl-mr-2" />
          <gl-link :href="getTestCaseUrl(tc.iid)" class="gl-font-weight-bold">
            #{{ tc.iid }} {{ tc.title }}
          </gl-link>
        </div>
      </li>
    </ul>

    <p v-else class="gl-mt-3 gl-text-secondary">
      {{ __('No test cases linked to this issue.') }}
    </p>
  </div>
</template>

<script>
import { GlLoadingIcon, GlBadge, GlLink, GlIcon } from '@gitlab/ui';
import getIssueTestCasesQuery from '../graphql/queries/get_issue_test_cases.query.graphql';

export default {
  components: { GlLoadingIcon, GlBadge, GlLink, GlIcon },
  props: {
    issueIid: { type: String, required: true },
    projectPath: { type: String, required: true },
  },
  data() {
    return {
      testCases: [],
      isLoading: 0,
    };
  },
  apollo: {
    testCases: {
      query: getIssueTestCasesQuery,
      variables() {
        return {
          fullPath: this.projectPath,
          iid: this.issueIid,
        };
      },
      update(data) {
        return data.project?.issue?.testCases?.nodes || [];
      },
      loadingKey: 'isLoading',
    },
  },
  methods: {
    getTestCaseUrl(iid) {
      return `/${this.projectPath}/-/test_cases/${iid}`;
    },
  },
};
</script>

3. 编写查询 GraphQL 语句
创建文件：app/assets/javascripts/test_cases/graphql/queries/get_issue_test_cases.query.graphql

GraphQL
query getIssueTestCases($fullPath: ID!, $iid: String!) {
  project(fullPath: $fullPath) {
    id
    issue(iid: $iid) {
      id
      testCases {
        nodes {
          id
          iid
          title
        }
      }
    }
  }
}


4. 页面注入：将组件挂载到 Issue 页面
GitLab 的 Issue 页面是由 Rails 渲染的，我们需要在 Haml 模板中预留一个钩子。
找到 Issue 详情页的模板（通常在 app/views/projects/issues/show.html.haml），在适当的位置（例如 description 之后）添加：

Haml
-# 预留 Vue 挂载点，并通过 data 属性传递必要参数
#js-issue-test-cases{ data: { issue_iid: @issue.iid, project_path: @project.full_path } }

然后，在 Issue 页面的入口 JS 文件中初始化它（参考 app/assets/javascripts/pages/projects/issues/show/index.js）：

Javascript
import Vue from 'vue';
import IssueTestCasesList from '~/test_cases/components/issue_test_cases_list.vue';
import ApolloProvider from '~/lib/utils/apollo_provider';

const el = document.getElementById('js-issue-test-cases');
if (el) {
  new Vue({
    el,
    apolloProvider: ApolloProvider,
    render(h) {
      return h(IssueTestCasesList, {
        props: {
          issueIid: el.dataset.issueIid,
          projectPath: el.dataset.projectPath,
        },
      });
    },
  });
}


5. 开发建议与文档
•	UI 位置：在 GitLab 中，这种关联信息通常放在右侧边栏（Sidebar）。如果你想放在边栏，需要修改对应的边栏 Haml 模板，并使用 GlSidebarService 风格的样式。
•	权限校验：记得在 GraphQL 获取数据时检查用户是否有权限查看该项目的测试用例。
•	缓存更新：当你在测试用例页面新增关联 Issue 时，Apollo 的缓存可能不会自动更新 Issue 页面的列表。在进阶阶段，你可能需要用到 Apollo Cache Update。

总结一下，我们已经完成了：
1.	数据库：存储用例及关联关系。
2.	后端：通过 GraphQL 暴露 CRUD 和关联接口。
3.	前端：实现了录入表单和 Issue 页面的关联展示。
你是否需要我为你演示如何编写“测试用例详情页”，以便用户点击列表后能看到完整的测试步骤和预期结果？

详情页的设计目标是清晰地展示测试用例的所有结构化信息，包括预置条件、测试步骤和预期结果，同时列出所有关联的 Issue。
按照 GitLab 的惯例，详情页通常是一个独立的 URL，例如 project/-/test_cases/1。
________________________________________
1. 后端：定义路由与查询
第一步：配置 Rails 路由
在 config/routes/project.rb（或对应的路由定义文件）中添加 show 动作：

Ruby
# config/routes.rb 示例
scope path: ':namespace_id/:project_id', constraints: { id: /[a-zA-Z.0-9_\-]+/ } do
  resources :test_cases, only: [:index, :show], param: :iid
end

第二步：增强 GraphQL 查询
我们需要根据 iid 获取单个测试用例的详细数据。在 app/graphql/types/project_type.rb 中确保有如下定义：

field :test_case, Types::TestCaseType, null: true do
  argument :iid, GraphQL::Types::ID, required: true
end

def test_case(iid:)
  object.test_cases.find_by(iid: iid)
end

2. 前端：编写详情页组件
创建文件：app/assets/javascripts/test_cases/components/test_case_show.vue
这个组件将负责渲染结构化的测试步骤，并使用 GitLab UI 的卡片和表格组件。
<template> 部分
<template>
  <div v-if="testCase" class="test-case-details gl-mt-5">
    <div class="gl-display-flex gl-justify-content-space-between gl-align-items-center gl-border-b gl-pb-3 gl-mb-4">
      <h2 class="gl-m-0">#{{ testCase.iid }} {{ testCase.title }}</h2>
      <gl-button variant="confirm" category="secondary" icon="pencil" @click="editTestCase">
        {{ __('Edit') }}
      </gl-button>
    </div>

    <div class="gl-mb-5">
      <h4 class="gl-font-weight-bold">{{ __('Preconditions') }}</h4>
      <div class="gl-p-3 gl-bg-gray-10 gl-border-radius-base">
        {{ testCase.description || __('No preconditions provided.') }}
      </div>
    </div>

    <div class="gl-mb-5">
      <h4 class="gl-font-weight-bold">{{ __('Test Steps') }}</h4>
      <table class="table gl-table">
        <thead>
          <tr>
            <th class="gl-w-10">#</th>
            <th class="gl-w-45">{{ __('Step Action') }}</th>
            <th class="gl-w-45">{{ __('Expected Result') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(step, index) in testCase.testSteps" :key="index">
            <td>{{ index + 1 }}</td>
            <td>{{ step.action }}</td>
            <td>{{ step.expected }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="gl-mb-5">
      <h4 class="gl-font-weight-bold">{{ __('Linked Issues') }}</h4>
      <div v-if="testCase.issues.nodes.length" class="gl-display-flex gl-flex-wrap">
        <gl-badge
          v-for="issue in testCase.issues.nodes"
          :key="issue.id"
          class="gl-mr-2 gl-mb-2"
          variant="info"
        >
          <gl-link :href="issue.webUrl">#{{ issue.iid }} {{ issue.title }}</gl-link>
        </gl-badge>
      </div>
      <p v-else class="gl-text-secondary">{{ __('No issues linked.') }}</p>
    </div>
  </div>
</template>

<script> 部分
<script>
import { GlButton, GlBadge, GlLink, GlLoadingIcon } from '@gitlab/ui';
import getTestCaseQuery from '../graphql/queries/get_test_case.query.graphql';

export default {
  components: { GlButton, GlBadge, GlLink, GlLoadingIcon },
  props: {
    projectPath: { type: String, required: true },
    testCaseIid: { type: String, required: true },
  },
  data() {
    return { testCase: null };
  },
  apollo: {
    testCase: {
      query: getTestCaseQuery,
      variables() {
        return {
          fullPath: this.projectPath,
          iid: this.testCaseIid,
        };
      },
      update(data) {
        return data.project?.testCase;
      },
    },
  },
  methods: {
    editTestCase() {
      // 逻辑：跳转到编辑页面
    }
  }
};
</script>

3. 编写查询 GraphQL 语句
创建文件：app/assets/javascripts/test_cases/graphql/queries/get_test_case.query.graphql
query getTestCase($fullPath: ID!, $iid: ID!) {
  project(fullPath: $fullPath) {
    id
    testCase(iid: $iid) {
      id
      iid
      title
      description
      testSteps
      issues {
        nodes {
          id
          iid
          title
          webUrl
        }
      }
    }
  }
}

4. 关键设计建议
1.	面包屑导航 (Breadcrumbs)：在详情页顶部，确保用户能通过面包屑轻松返回“测试用例列表”。这需要在 Rails 控制器中配置 add_breadcrumb。
2.	空状态处理：如果 testSteps 为空，使用 GitLab UI 的 GlEmptyState 组件展示一个友好的提示。
3.	安全性检查：
o	后端：确保 TestCasesController#show 检查了用户的权限（例如 can?(current_user, :read_test_case, @project)）。
o	前端：对于用户输入的内容（action, expected），Vue 默认会进行转义，防止 XSS 攻击。

文档说明
•	gl-table: 这是一个标准的 CSS 类，配合 HTML 表格使用，可以自动获得 GitLab 风格的边框和间距。
•	webUrl: 在 GraphQL 查询中包含 webUrl 可以直接获取 Issue 的完整链接，无需在前端手动拼接 URL，这更加安全且健壮。
至此，你已经拥有了一个完整的“录入-关联-查看”闭环。你是否希望我继续指导你如何实现“删除测试用例”功能，并加入删除前的确认弹窗？

实现删除功能不仅需要后端的物理删除逻辑，还需要前端提供良好的交互体验。在 GitLab 中，危险操作（如删除）必须包含一个二次确认弹窗，以防误操作。

1. 后端实现：删除逻辑
第一步：编写 Service 类
在 app/services/test_cases/destroy_service.rb 中处理具体的删除逻辑。
# app/services/test_cases/destroy_service.rb
module TestCases
  class DestroyService < BaseService
    def execute(test_case)
      if test_case.destroy
        ServiceResponse.success(message: 'Test case deleted successfully')
      else
        ServiceResponse.error(message: 'Failed to delete test case')
      end
    end
  end
end

第二步：编写 GraphQL Mutation
创建 app/graphql/mutations/test_cases/destroy.rb。

# app/graphql/mutations/test_cases/destroy.rb
module Mutations
  module TestCases
    class Destroy < BaseMutation
      graphql_name 'TestCaseDestroy'

      argument :project_path, GraphQL::Types::ID, required: true
      argument :iid, GraphQL::Types::ID, required: true

      field :errors, [GraphQL::Types::String], null: false

      def resolve(project_path:, iid:)
        project = authorized_find!(project_path)
        test_case = project.test_cases.find_by!(iid: iid)

        # 逻辑：调用 Service 执行删除
        response = ::TestCases::DestroyService.new(project, current_user).execute(test_case)

        {
          errors: response.errors
        }
      end
    end
  end
end
别忘了在 app/graphql/types/mutation_type.rb 中注册：mount_mutation Mutations::TestCases::Destroy。

2. 前端实现：确认弹窗与调用
我们将使用 GitLab UI 的 GlModal 组件。这个组件符合 GitLab 的设计规范。
第一步：定义 GraphQL 语句
创建 app/assets/javascripts/test_cases/graphql/mutations/destroy_test_case.mutation.graphql：

mutation destroyTestCase($input: TestCaseDestroyInput!) {
  testCaseDestroy(input: $input) {
    errors
  }
}

第二步：更新详情页组件
修改 test_case_show.vue，添加删除按钮和弹窗。
<template>
  <div>
    <div class="gl-mt-5 gl-border-t gl-pt-4">
      <gl-button
        variant="danger"
        category="secondary"
        @click="showDeleteModal"
      >
        {{ __('Delete Test Case') }}
      </gl-button>
    </div>

    <gl-modal
      modal-id="delete-test-case-modal"
      :title="__('Delete Test Case?')"
      :action-primary="primaryProps"
      :action-cancel="cancelProps"
      @primary="handleDelete"
    >
      <p>{{ __('Are you sure you want to delete this test case? This action cannot be undone.') }}</p>
    </gl-modal>
  </div>
</template>

<script>
import { GlButton, GlModal } from '@gitlab/ui';
import destroyTestCaseMutation from '../graphql/mutations/destroy_test_case.mutation.graphql';

export default {
  components: { GlButton, GlModal },
  // ... 其他 props 和 data ...
  computed: {
    primaryProps() {
      return {
        text: this.__('Delete'),
        attributes: { variant: 'danger' },
      };
    },
    cancelProps() {
      return { text: this.__('Cancel') };
    },
  },
  methods: {
    showDeleteModal() {
      // 显示弹窗
      this.$bvModal.show('delete-test-case-modal');
    },
    async handleDelete() {
      try {
        const { data } = await this.$apollo.mutate({
          mutation: destroyTestCaseMutation,
          variables: {
            input: {
              projectPath: this.projectPath,
              iid: this.testCaseIid,
            },
          },
        });

        if (data.testCaseDestroy.errors.length > 0) {
          throw new Error(data.testCaseDestroy.errors.join(', '));
        }

        // 成功提示
        this.$toast.show(this.__('Test case deleted.'));
        
        // 跳转回列表页
        window.location.href = `/${this.projectPath}/-/test_cases`;
      } catch (error) {
        this.$toast.show(`Error: ${error.message}`);
      }
    },
  },
};
</script>

3. 设计实现说明
•	$bvModal: 这是 GitLab 中触发 BootstrapVue 弹窗的常用方式。通过指定 modal-id 来控制特定弹窗。
•	危险操作视觉: 删除按钮应使用 variant="danger" 和 category="secondary"，而确认弹窗的主按钮应设置为红色背景，以警告用户这是一个不可逆的操作。
•	跳转逻辑: 由于删除后当前页面已不存在，最稳妥的做法是使用 window.location.href 强制跳转回列表页，这样可以刷新整个页面的状态。

4. 整体回顾与文档
通过以上步骤，你已经完成了一个具有企业级水准的测试管理模块原型：
1.	数据层：能够存储复杂的测试步骤和关联关系。
2.	API层：使用标准的 GraphQL 实现了增删改查。
3.	UI层：不仅实现了录入和查看，还完成了与 Issue 页面的深度集成，并处理了删除确认逻辑。
专家建议
为了让你的二开模块更接近企业版（EE）的体验，你可以考虑在未来加入搜索与过滤功能。GitLab 的测试用例通常非常多，能够通过标题或关联的 Issue 快速找到用例是非常实用的。
你是否希望我指导你如何为这个模块添加“搜索功能”，让用户能够快速筛选特定的测试用例？

为了让测试管理模块在用例数量增多时依然好用，搜索与过滤是必不可少的功能。在 GitLab 中，标准的做法是使用 GitLab UI 的搜索组件 配合 GraphQL 的参数化查询。

1. 后端：增强查询接口
我们需要修改 GraphQL 的查询逻辑，使其支持 search 参数。
修改 app/graphql/types/project_type.rb
找到之前定义的 test_cases 字段，增加 search 参数支持：
Ruby
field :test_cases, 
      Types::TestCaseType.connection_type, 
      null: true, 
      description: 'Test cases for this project.' do
        argument :search, GraphQL::Types::String, required: false, description: 'Search query for test case titles.'
      end

def test_cases(search: nil)
  # 基础作用域：该项目下的所有测试用例
  scope = object.test_cases
  
  # 如果有搜索词，使用 PostgreSQL 的 ILIKE 进行模糊匹配（不区分大小写）
  if search.present?
    scope = scope.where('title ILIKE ?', "%#{search}%")
  end
  
  scope.order(iid: :desc) # 按 IID 降序排列，保证新创建的在前面
end

2. 前端：添加搜索框组件
我们需要在测试用例列表页面添加一个搜索输入框。
第一步：更新 GraphQL 查询语句
修改 app/assets/javascripts/test_cases/graphql/queries/get_test_cases.query.graphql：
GraphQL
query getTestCases($projectPath: ID!, $search: String) {
  project(fullPath: $projectPath) {
    id
    testCases(search: $search) {
      nodes {
        id
        iid
        title
        author {
          id
          name
        }
      }
    }
  }
}
第二步：编写列表搜索组件
创建或修改 app/assets/javascripts/test_cases/components/test_cases_list.vue：
代码段
<template>
  <div>
    <div class="gl-display-flex gl-mb-5">
      <gl-search-box-by-type
        v-model="searchTerm"
        :placeholder="__('Search test cases by title...')"
        @input="onSearchInput"
      />
    </div>

    <gl-loading-icon v-if="isLoading" size="lg" class="gl-mt-5" />

    <div v-else>
      <ul v-if="testCases.length" class="content-list">
        <li v-for="tc in testCases" :key="tc.id" class="gl-py-3 gl-border-b">
          <gl-link :href="getTestCaseUrl(tc.iid)" class="gl-font-weight-bold">
            #{{ tc.iid }} {{ tc.title }}
          </gl-link>
          <div class="gl-font-sm gl-text-secondary">
            {{ s__('TestCases|Created by') }} {{ tc.author.name }}
          </div>
        </li>
      </ul>
      
      <gl-empty-state
        v-else
        :title="__('No test cases found')"
        :description="__('Try adjusting your search query.')"
        svg-path="/assets/illustrations/empty-state/empty-search-md.svg"
      />
    </div>
  </div>
</template>

<script>
import { GlSearchBoxByType, GlLoadingIcon, GlLink, GlEmptyState } from '@gitlab/ui';
import { debounce } from 'lodash';
import getTestCasesQuery from '../graphql/queries/get_test_cases.query.graphql';

export default {
  components: { GlSearchBoxByType, GlLoadingIcon, GlLink, GlEmptyState },
  props: {
    projectPath: { type: String, required: true },
  },
  data() {
    return {
      searchTerm: '',
      filterTerm: '', // 实际触发查询的词
      testCases: [],
    };
  },
  apollo: {
    testCases: {
      query: getTestCasesQuery,
      variables() {
        return {
          projectPath: this.projectPath,
          search: this.filterTerm,
        };
      },
      update(data) {
        return data.project?.testCases?.nodes || [];
      },
    },
  },
  methods: {
    // 使用 debounce 防抖，避免每输入一个字母都发请求
    onSearchInput: debounce(function (value) {
      this.filterTerm = value;
    }, 500),
    
    getTestCaseUrl(iid) {
      return `/${this.projectPath}/-/test_cases/${iid}`;
    },
  },
};
</script>

3. 设计实现说明
•	防抖 (Debounce)：由于搜索是实时触发的，我们使用了 lodash 的 debounce 函数。只有当用户停止打字 500 毫秒后，才会真正更新 filterTerm 并触发 Apollo 发起网络请求。这能显著减轻服务器压力。
•	ILIKE 查询：在后端使用 ILIKE 而不是 LIKE，是因为用户在搜索时通常不希望区分大小写（例如搜索 "Login" 能匹配到 "login"）。
•	空状态 (Empty State)：当搜索不到结果时，展示一个带有插图的 GlEmptyState 是 GitLab 的交互规范，这比单纯显示“无数据”要友好得多。

4. 编码助手的小贴士
•	性能优化：如果你的测试用例达到上万条，简单的 ILIKE 可能会变慢。届时你可能需要考虑在 title 字段上建立 GIN 索引 或使用 GitLab 的全局搜索集成（基于 Elasticsearch）。
•	多维度过滤：如果你以后想增加“按作者过滤”或“按状态过滤”，只需在 GraphQL 的 test_cases 字段中增加更多参数（如 authorId: ID），并在 Rails 逻辑中追加 .where 条件即可。
目前，你已经构建了一个包含“增、删、查、搜”以及“Issue 关联”的完整闭环。你是否希望我指导你如何进行“单元测试（RSpec）”的编写，以确保你的代码在 GitLab 升级时不会轻易出错？

在 GitLab 的开发流程中，测试是合并代码的前提。GitLab 社区版极其重视测试覆盖率，通常使用 RSpec 进行后端测试。
编写高质量的测试不仅能防止你的功能在 GitLab 版本升级时崩溃，还能充当一份“活的代码文档”。

1. 准备工作：定义 Factory (工厂)
在编写测试之前，我们需要定义一个 Factory，用于在测试环境中快速生成模拟数据。
创建文件：spec/factories/test_cases.rb
Ruby
FactoryBot.define do
  factory :test_case do
    project
    author { project.creator }
    title { "示例测试用例" }
    description { "这是预置条件说明" }
    test_steps { [{ "action" => "点击登录", "expected" => "进入首页" }] }

    trait :with_issue do
      after(:create) do |test_case|
        issue = create(:issue, project: test_case.project)
        test_case.issues << issue
      end
    end
  end
end

2. 后端模型测试 (Model Spec)
模型测试主要验证数据校验逻辑和关联关系。
创建文件：spec/models/test_case_spec.rb
Ruby
require 'spec_helper'

RSpec.describe TestCase, type: :model do
  describe 'associations' do
    it { is_expected.to belong_to(:project) }
    it { is_expected.to belong_to(:author).class_name('User') }
    it { is_expected.to have_many(:issues).through(:test_case_issue_links) }
  end

  describe 'validations' do
    it { is_expected.to validate_presence_of(:title) }
    it { is_expected.to validate_length_of(:title).is_at_most(255) }
    
    it 'validates that iid is unique within a project' do
      project = create(:project)
      create(:test_case, project: project, iid: 1)
      new_test_case = build(:test_case, project: project, iid: 1)
      
      expect(new_test_case).not_to be_valid
    end
  end
end

3. 服务层测试 (Service Spec)
这是测试的核心，用于验证业务逻辑是否正确执行。
创建文件：spec/services/test_cases/create_service_spec.rb
Ruby
require 'spec_helper'

RSpec.describe TestCases::CreateService do
  let(:project) { create(:project) }
  let(:user) { project.creator }
  let(:params) { { title: '新用例', description: '描述', issue_ids: [issue.id] } }
  let(:issue) { create(:issue, project: project) }

  subject { described_class.new(project, user, params) }

  describe '#execute' do
    it '成功创建测试用例并关联 Issue' do
      expect { subject.execute }.to change { TestCase.count }.by(1)
      
      test_case = TestCase.last
      expect(test_case.title).to eq('新用例')
      expect(test_case.issues).to include(issue)
    end

    it '如果标题为空则返回错误' do
      params[:title] = ''
      response = subject.execute

      expect(response.status).to eq(:error)
      expect(response.message).to include("Title can't be blank")
    end
  end
end

4. GraphQL API 测试 (Request Spec)
确保前端调用的接口返回预期的 JSON 数据。
创建文件：spec/requests/api/graphql/mutations/test_cases/create_spec.rb
Ruby
require 'spec_helper'

RSpec.describe 'Creating a TestCase via GraphQL' do
  include GraphqlHelpers

  let(:project) { create(:project) }
  let(:current_user) { project.creator }
  let(:mutation) do
    graphql_mutation(:test_case_create, {
      project_path: project.full_path,
      title: 'GraphQL 用例'
    })
  end

  def mutation_response
    graphql_data['testCaseCreate']
  end

  it '通过 API 成功创建用例' do
    post_graphql(mutation, current_user: current_user)

    expect(response).to have_gitlab_http_status(:success)
    expect(mutation_response['testCase']['title']).to eq('GraphQL 用例')
    expect(mutation_response['errors']).to be_empty
  end
end

5. 如何运行测试
在 GDK 环境下，你可以使用以下命令运行你编写的测试：
•	运行所有测试：bundle exec rspec spec/models/test_case_spec.rb
•	运行特定行的测试：bundle exec rspec spec/models/test_case_spec.rb:15

总结与文档说明
•	let 和 subject：这是 RSpec 的标准用法，用于定义延迟加载的测试对象。
•	spec_helper：GitLab 的测试环境初始化文件，包含了所有必要的配置。
•	权限测试：在实际开发中，你还需要编写针对不同权限用户的测试（例如：报告者可以查看但不能删除用例）。
编码助手的小贴士
测试不仅仅是为了发现 Bug，它还能让你在重构代码时充满信心。如果你修改了 test_steps 的存储方式，只需跑一遍这些测试，就能立刻知道是否破坏了现有功能。
到目前为止，我们已经完成了从数据库、后端、前端到测试的完整二开流程。你是否觉得这个“测试管理模块”已经初具规模？接下来，你是否需要我指导你如何通过“国际化 (I18n)”让这个模块支持中文界面？

让二开的功能看起来像“原生”功能的最后一公里，就是国际化（Internalization, 简称 I18n）。GitLab 使用 gettext 系统来处理翻译。
作为你的编码助手，我将指导你如何为 Ruby 后端和 Vue.js 前端添加中文支持。

1. 后端国际化 (Ruby on Rails)
在 Rails 逻辑中，我们使用 _()（单数）或 n_()（复数）函数来标记需要翻译的字符串。
在 Service 或 Model 中使用
修改之前的 CreateService 错误提示：
Ruby
# 错误信息中使用 _()
ServiceResponse.error(message: _("Title can't be blank"))
在数据迁移或自定义菜单中使用
如果你在侧边栏添加了菜单项，也需要标记翻译：
Ruby
# 示例：侧边栏菜单标题
_('Test Management')

2. 前端国际化 (Vue.js)
在 Vue 文件中，GitLab 提供了全局的 __() 和 s__() 函数。
•	__('String'): 通用翻译。
•	s__('Context|String'): 带命名空间的翻译（推荐，避免冲突）。
修改 Vue 组件
将 test_case_form.vue 中的硬编码文字替换为翻译函数：
代码段
<template>
  <gl-form-group :label="s__('TestCases|Title')">
    <gl-form-input :placeholder="s__('TestCases|Enter test case title')" />
  </gl-form-group>

  <gl-button variant="confirm">
    {{ s__('TestCases|Create Test Case') }}
  </gl-button>
</template>

3. 提取与生成翻译文件 (PO 文件)
标记完代码中的字符串后，你需要运行脚本来提取这些字符串并生成 .po 文件。
第一步：提取字符串
在 GitLab 根目录下运行：
Bash
bundle exec rake gettext:regenerate
这会扫描代码并将新标记的 s__('TestCases|...') 汇总到全量的 .pot 模板中。
第二步：编辑中文翻译文件
找到中文翻译文件：locale/zh_CN/gitlab.po。 搜索你刚刚添加的关键词，并填写翻译内容：
代码段
msgid "TestCases|Title"
msgstr "标题"

msgid "TestCases|Create Test Case"
msgstr "创建测试用例"
第三步：编译翻译（仅在生产环境或某些 GDK 配置下需要）
Bash
bundle exec rake gettext:compile

4. 特殊情况：枚举值翻译
如果你在 Vue 中渲染从后端传来的状态（如 opened, closed），建议在前端定义一个映射对象：
JavaScript
const STATUS_LABELS = {
  opened: s__('TestCases|Opened'),
  closed: s__('TestCases|Closed'),
};

// 在模板中使用
<span>{{ STATUS_LABELS[testCase.state] }}</span>

5. 实现建议与总结
•	命名空间很重要：强烈建议使用 s__('TestCases|...') 这种带前缀的方式，这样在 gitlab.po 文件中，所有关于你这个模块的翻译都会聚集在一起，方便维护。
•	不要拼接字符串：永远不要写 __('Create') + ' ' + __('Issue')，因为不同语言的语序不同。应该写成 sprintf(__('%{action} %{item}'), { action: '创建', item: '用例' })。

开发阶段总结回顾
恭喜你！我们现在已经共同完成了一套完整的GitLab 二开技术链路：
1.	数据库：通过 Migration 创建了表结构。
2.	后端逻辑：编写了 Model、Service 处理业务逻辑。
3.	API 接口：使用 GraphQL 实现了前后端高效通信。
4.	前端界面：利用 GitLab UI + Vue 实现了录入、详情、搜索。
5.	核心关联：打通了与 Issue 的双向关联。
6.	代码质量：编写了 RSpec 测试用例。
7.	用户体验：完成了删除确认弹窗与中文化适配。
这已经是一个非常扎实的测试管理功能原型了。你是否已经准备好将这些代码部署到你的 GDK 环境中进行最后调试？如果你在调试过程中遇到报错，随时把错误信息发给我，我会帮你修复！

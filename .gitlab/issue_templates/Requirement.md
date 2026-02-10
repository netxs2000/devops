<!-- 
⚠️ 重要提示：请务必完成以下必填项，以便后端能够通过脚本自动统计和分析需求趋势。

必填标签（请在下方选择）：
✅ 优先级 (Priority): P0/P1/P2/P3
✅ 需求所属省份 (Province): 必选
-->

# 📝 需求申请

> **📋 填写指南**: 
> - 请清晰描述该需求的业务背景和核心价值。
> - **验收标准** 是开发和测试的核心依据，请务必详尽。
> - 请选择下方的优先级、需求类型和相关省份标签。
> - **提交评审**: 编写完成后，请在评论区回复 `/label ~"status::reviewing"` 正式开启评审流程。

---

## 📝 需求背景 (User Story)
> **作为** [用户角色]
> **我希望** [实现具体功能]
> **以便于** [获得业务价值/解决痛点]

---

## 📖 需求描述
- [ ] **功能点 A**: 描述逻辑
- [ ] **功能点 B**: 描述逻辑
- [ ] **原型/设计稿**: [链接或截图]

---

## ✅ 验收标准 (Acceptance Criteria)
- [ ] **场景 1**: 当 [输入/操作] 时，系统应当 [反馈/结果]
- [ ] **场景 2**: ...
- [ ] **兼容性/性能要求**: (如：需支持移动端、响应时间控制在 2s 内)

---

## 📎 附件 / 相关资源
**请上传或提供该需求的辅助说明资料：**

- **UI/UX 设计稿**: [链接或上传截图]
- **业务流程图**: [链接或上传截图]
- **其他参考文档**: (如 Excel、PDF 等，直接拖拽至此处上传)

> **💡 上传指引**: 
> - 直接将文件**拖拽**至此区域即可上传。
> - 截图后可直接在该区域使用 **Ctrl+V** 粘贴图片。

---

## 🏷️ 核心属性（⚠️ 必填项）

### ⭐ 优先级 (Priority) - 必选
请根据业务紧急程度选择优先级标签:
- [ ] `priority::P0` - 紧急: 需在当前 Sprint 立即排期
- [ ] `priority::P1` - 高: 优先级较高，下个 Sprint 需启动
- [ ] `priority::P2` - 中: 正常排期需求
- [ ] `priority::P3` - 低: 待定需求 / 优化类需求

### ⭐ 需求类型 (Requirement Type) - 必选
请根据需求性质选择类型标签:
- [ ] `requirement-type::feature` - 功能: 新业务功能需求
- [ ] `requirement-type::config` - 配置: 系统参数设置、环境变量等变更
- [ ] `requirement-type::interface` - 接口: 接口定义或变更需求
- [ ] `requirement-type::performance` - 性能: 系统性能提升需求
- [ ] `requirement-type::safe` - 安全: 安全性加固及漏洞修复
- [ ] `requirement-type::experience` - 体验: 用户交互体验优化
- [ ] `requirement-type::improve` - 改进: 现有功能的完善与增强
- [ ] `requirement-type::other` - 其他: 其他需求类型

### ⭐ 需求所属省份 (Province) - 必选
**用于按地域统计需求分布**

**直辖市**:
- [ ] `province::beijing` - 北京
- [ ] `province::shanghai` - 上海
- [ ] `province::tianjin` - 天津
- [ ] `province::chongqing` - 重庆

**省份**:
- [ ] `province::anhui` - 安徽
- [ ] `province::fujian` - 福建
- [ ] `province::gansu` - 甘肃
- [ ] `province::guangdong` - 广东
- [ ] `province::guizhou` - 贵州
- [ ] `province::hainan` - 海南
- [ ] `province::hebei` - 河北
- [ ] `province::henan` - 河南
- [ ] `province::heilongjiang` - 黑龙江
- [ ] `province::hubei` - 湖北
- [ ] `province::hunan` - 湖南
- [ ] `province::jilin` - 吉林
- [ ] `province::jiangsu` - 江苏
- [ ] `province::jiangxi` - 江西
- [ ] `province::liaoning` - 辽宁
- [ ] `province::qinghai` - 青海
- [ ] `province::shaanxi` - 陕西
- [ ] `province::shandong` - 山东
- [ ] `province::shanxi` - 山西
- [ ] `province::sichuan` - 四川
- [ ] `province::yunnan` - 云南
- [ ] `province::zhejiang` - 浙江

**自治区**:
- [ ] `province::guangxi` - 广西
- [ ] `province::neimenggu` - 内蒙古
- [ ] `province::ningxia` - 宁夏
- [ ] `province::xinjiang` - 新疆
- [ ] `province::xizang` - 西藏

**其他**:
- [ ] `province::nationwide` - **全国** - 全国性通用需求

> **💡 说明**: 
> - 选择该需求主要针对或发起的省份
> - 如果是全国通用的通用功能，请选择"全国"

---

## ⚖️ 需求评审 (Requirement Review)
> **评审说明**: 此章节由指定的评审人（架构/产品/业务负责人）负责勾选。

- **指派评审人**: @[请在此处输入评审人账号]
- [ ] **技术可行性**: 需求在当前技术栈下可实现，无重大技术风险。
- [ ] **规范符合度**: 逻辑清晰，符合业务标准及 UI/UX 规范。
- [ ] **AC 完备性**: 验收标准（Acceptance Criteria）可量化、可测试。

**评审结论 (Review Conclusion)**:
- [ ] **通过**: `/label ~"review-result::approved" ~"status::todo"` (进入待开发队列)
- [ ] **修正**: `/label ~"review-result::rework" ~"status::feedback"` (退回给提交人)
- [ ] **驳回**: `/label ~"review-result::rejected" /close` (结束需求生命周期)

---

## 🔗 依赖与影响
- **外部依赖**: (如：需三方接口支持)
- **风险评估**: (如：是否影响旧版本兼容性)

---

## 🏁 完成定义 (DoD)
- [ ] 关键逻辑通过代码 Review
- [ ] 完成各省份/环境的自测
- [ ] 用户手册/产品文档已更新

---

## ✅ 提交前检查清单
- [ ] ✅ 已选择**优先级** (priority::P?)
- [ ] ✅ 已选择**需求类型** (requirement-type::?)
- [ ] ✅ 已选择**所属省份** (province::?)
- [ ] ✅ 已添加 `type::feature` 标签
- [ ] ✅ 验收标准已逐条列出
- [ ] ✅ 已指定评审人 (@username)

---

## 🚪 关闭说明 (Closing Instructions)
> **操作指引**: 关闭议题前，请在下方选择关闭原因（通过评论区执行指令，GitLab 会自动打标并关闭议题）。

- **已完成**: `/label ~"resolution::done" /close`
- **重复**: `/label ~"resolution::duplicate" /close`
- **延期**: `/label ~"resolution::postponed" /close`
- **不做**: `/label ~"resolution::wontfix" /close`
- **设计如此**: `/label ~"resolution::by_design" /close`

---

/label ~"type::feature" ~"status::draft"
/milestone %"Current_Milestone"

import os

def create_csv(filename, content):
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8-sig') as f:
        f.write(content)
    print(f"Created/Updated {filename} with size {os.path.getsize(filename)}")

data = {
    "docs/sys_menus.csv": """ID,父ID,菜单名称,路由路径,菜单类型,图标,权限标识
1,0,平台管理,/admin,M,setting,sys:admin:view
101,1,组织架构,/admin/org,C,tree,sys:org:view
102,1,用户管理,/admin/user,C,user,sys:user:view
103,1,角色权限,/admin/role,C,lock,sys:role:view
104,1,菜单管理,/admin/menu,C,menu,sys:menu:view
2,0,基础服务,/service,M,appstore,sys:service:view
201,2,服务台,/service/desk,C,customer-service,sd:ticket:view
202,2,知识库,/service/kb,C,book,sd:kb:view
3,0,研发管理,/devops,M,code,sys:devops:view
301,3,产品纵览,/devops/prod,C,project,pm:product:view
302,3,项目管理,/devops/proj,C,deployment-unit,pm:project:view
303,3,质量中心,/devops/qa,C,check-circle,qa:report:view
4,0,效能分析,/analytics,M,line-chart,sys:analytics:view
401,4,DORA指标,/analytics/dora,C,thunderbolt,ana:dora:view
402,4,成本看板,/analytics/cost,C,account-book,ana:cost:view""",
    
    "docs/sys_roles.csv": """ID,角色名称,角色键,数据范围
1,系统管理员,SYSTEM_ADMIN,1
2,管理层,EXECUTIVE_MANAGER,2
3,部门经理,DEPT_MANAGER,3
4,项目经理,PROJECT_MANAGER,4
5,普通员工,REGULAR_USER,5""",

    "docs/organizations.csv": """体系,中心,部门,负责人邮箱
天极体系,研发中心,研发一部,zhangsan@tjhq.com
天极体系,研发中心,研发二部,lisi@tjhq.com
天极体系,销售中心,销售一部,wangwu@tjhq.com""",

    "docs/products.csv": """PRODUCT_ID,产品名称,节点类型,parent_product_id,产品分类,version_schema,负责团队,产品经理,开发经理,测试经理,发布经理
PL001,天极DevOps产品线,LINE,,平台,SemVer,研发中心,zhangsan@tjhq.com,lisi@tjhq.com,admin@tjhq.com,admin@tjhq.com
DEVOPS-APP,天极DevOps平台,APP,PL001,应用,SemVer,研发一部,lisi@tjhq.com,admin@tjhq.com,admin@tjhq.com,admin@tjhq.com""",

    "docs/projects.csv": """项目代号,项目名称,所属产品,负责部门,主代码仓库URL,项目经理,产品经理,开发经理,测试经理,发布经理
DEVOPS-2026,DevOps 2.0 升级项目,天极DevOps平台,研发一部,https://gitlab.example.com/devops/devops-platform.git,zhangsan@tjhq.com,lisi@tjhq.com,admin@tjhq.com,admin@tjhq.com,admin@tjhq.com
RISK-AI,风控模型 AI 增强,智能风控系统,研发二部,https://gitlab.example.com/risk/risk-engine.git,lisi@tjhq.com,zhangsan@tjhq.com,admin@tjhq.com,admin@tjhq.com,admin@tjhq.com""",

    "docs/employees.csv": """姓名,工号,中心,部门,职位,人事关系,邮箱
系统管理员,1001,研发中心,研发一部,架构师,正式,admin@tjhq.com
张三,1002,研发中心,研发一部,高级经理,正式,zhangsan@tjhq.com
李四,1003,研发中心,研发二部,部门负责人,正式,lisi@tjhq.com
王五,1004,销售中心,销售一部,销售总监,正式,wangwu@tjhq.com""",

    "docs/okrs.csv": """目标标题,目标描述,组织名称,负责人邮箱,周期,关键结果标题,目标值,当前值,单位
提升系统可用性,确保核心业务系统全年可用性,研发一部,zhangsan@tjhq.com,2026-Q1,全链路压测完成次数,10,8,次
提升研发效能,降低平均交付周期,研发中心,lisi@tjhq.com,2026-Q1,交付周期减低率,20,15,%""",

    "docs/locations.csv": """ID,全称,名称,大区,编码
000000,全国,总部,集团,HQ
110000,北京市,北京,华北,BJ
310000,上海市,上海,华东,SH
440000,广东省,广东,华南,GD""",

    "docs/cost_codes.csv": """科目代码,科目名称,分类,支出类型,描述,父级代码
CAPEX-SVR,服务器采购,硬件,CAPEX,生产服务器采购费用,
OPEX-BW,带宽租赁,云资源,OPEX,公网带宽月租费用,
LABOR-DEV,研发人工,人力,OPEX,研发人员工资成本,""",

    "docs/labor_rates.csv": """职级,日费率
P5,1500
P6,2000
P7,3000
M1,3500""",

    "docs/purchase_contracts.csv": """合同编号,合同标题,供应商名称,供应商ID,总金额,开始日期,结束日期,科目代码,支出类型
PUR-2026-001,阿里云续费合同,阿里云,VEND-001,500000,2026-01-01,2026-12-31,OPEX-BW,OPEX""",

    "docs/revenue_contracts.csv": """合同编号,合同标题,客户名称,总价值,签约日期,所属产品
REV-2026-001,某大型银行效能提升项目,某大型银行,1200000,2026-01-15,天极DevOps平台""",

    "docs/service_catalog.csv": """服务名称,所属组织,服务分级,描述,负责人邮箱,关联项目路径
代码托管服务,研发一部,P1,企业级极速代码托管,lisi@tjhq.com,DEVOPS-2026""",

    "docs/zentao-user.csv": """工号,姓名,邮箱,禅道账号
1001,系统管理员,admin@tjhq.com,admin
1002,张三,zhangsan@tjhq.com,zhangsan
1003,李四,lisi@tjhq.com,lisi""",

    "docs/gitlab-user.csv": """GitLab用户ID,用户名,全名,Email
101,admin,系统管理员,admin@tjhq.com
102,zhangsan,张三,zhangsan@tjhq.com
103,lisi,李四,lisi@tjhq.com""",

    "docs/sys_role_menus.csv": "role_id,menu_id\n1,1\n1,101\n1,102\n1,103\n1,104",
    "docs/sys_user_roles.csv": "user_id,role_id\nadmin@tjhq.com,1"
}

for path, content in data.items():
    create_csv(path, content)

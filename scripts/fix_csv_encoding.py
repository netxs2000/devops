import os
import argparse
import sys

# 模板数据字典
TEMPLATES = {
    "docs/sys_menus.csv": """ID,父ID,菜单名称,路由路径,菜单类型,图标,权限标识
1,0,平台管理,/admin,M,setting,sys:admin:view
101,1,组织架构,/admin/org,C,tree,sys:org:view
102,1,用户管理,/admin/user,C,user,sys:user:view
103,1,产品定义,/admin/product,C,shopping-cart,sys:product:view
104,1,项目主表,/admin/project,C,project,sys:project:view
2,0,研发协同,/devops,M,rocket,sys:devops:view
201,2,需求池,/devops/backlog,C,unordered-list,pm:backlog:view
202,2,迭代看板,/devops/iteration,C,dashboard,pm:iteration:view
203,2,质量门禁,/devops/quality,C,safety-certificate,qa:gate:view
3,0,测试管理,/test,M,experiment,sys:test:view
301,3,测试用例,/test/cases,C,container,qa:test:view
302,3,追溯矩阵,/test/rtm,C,deployment-unit,qa:rtm:view
4,0,服务支持,/service,M,customer-service,sys:service:view
401,4,反馈中心,/service/desk,C,message,sd:ticket:view
402,4,知识库,/service/kb,C,read,sd:kb:view
5,0,效能看板,/analytics,M,line-chart,sys:analytics:view
501,5,DORA指标,/analytics/dora,C,thunderbolt,ana:dora:view
502,5,成本分析,/analytics/cost,C,account-book,ana:cost:view""",

    "docs/mdm_systems_registry.csv": """system_code,system_name,system_type,env_tag,base_url,api_version,auth_type,is_active,remarks
gitlab-corp,企业版GitLab,VCS,PROD,https://gitlab.example.com,v4,OAuth2,TRUE,核心代码托管
jenkins-prod,生产环境Jenkins,CI,PROD,https://jenkins.example.com,,Token,TRUE,生产部署流水线
sonarqube-corp,代码质量平台,SONAR,PROD,https://sonar.example.com,,Token,TRUE,代码静态分析""",

    "docs/mdm_services.csv": """服务名称,服务分级,负责组织,描述,组件类型,生命周期,所属业务系统代码
Payment Service,T0,交易中台研发部,核心支付网关,service,production,trade-center
User Center,T1,用户中心研发部,统一用户认证服务,service,production,user-center
Log Library,T2,基础架构部,通用日志组件,library,stable,common-libs"""
}

def fix_encoding(filename):
    """仅修复文件编码为 utf-8-sig，不改变内容。"""
    try:
        with open(filename, 'rb') as f:
            raw_data = f.read()
        
        # 尝试使用各种编码读取
        content = None
        for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb18030']:
            try:
                content = raw_data.decode(enc)
                break
            except:
                continue
        
        if content is not None:
            with open(filename, 'w', encoding='utf-8-sig') as f:
                f.write(content)
            print(f" [Fixed Encoding] {filename}")
        else:
            print(f" [Error] Could not decode {filename}")
    except Exception as e:
        print(f" [Error] Failed to process {filename}: {e}")

def main():
    parser = argparse.ArgumentParser(description="CSV 编码修复与模板管理工具 (安全模式)")
    parser.add_argument("--file", help="指定要处理的文件路径")
    parser.add_argument("--force-template", action="store_true", help="强制使用内置模板覆盖内容")
    parser.add_argument("--all-encoding", action="store_true", help="修复 docs 目录下所有 CSV 的编码，不改变内容")
    
    args = parser.parse_args()

    # 处理单个文件请求（强制刷新）
    if args.file and args.force_template:
        filename = args.file
        if filename in TEMPLATES:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w", encoding="utf-8-sig") as f:
                f.write(TEMPLATES[filename])
            print(f" [Success] Overwritten {filename} with latest template.")
            return

    # 全局编码修复（不改内容）
    if args.all_encoding:
        for root, dirs, files in os.walk("docs"):
            for file in files:
                if file.endswith(".csv"):
                    fix_encoding(os.path.join(root, file))
        return

    # 默认逻辑：只初始化缺失的文件
    print("Checking for missing CSV templates...")
    for path, content in TEMPLATES.items():
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(content)
            print(f" [Initialized] {path}")
        else:
            # 文件已存在，仅修复编码
            fix_encoding(path)

if __name__ == "__main__":
    main()

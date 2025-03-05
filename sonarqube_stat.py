import configparser
import csv
import requests
import logging

# 增加日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', # noqa 注释忽略拼写检查
                    datefmt='%Y-%m-%d %H:%M:%S')


def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    sonar_url = config.get('sonarqube', 'url')
    auth_token = config.get('sonarqube', 'token')
    return sonar_url, auth_token


def get_project_measures(sonar_url, auth_token, project_key):
    headers = {
        'Authorization': f'Bearer {auth_token}'
    }
    params = {
        'component': project_key,
        'metricKeys': 'statements,files,lines,ncloc,classes,functions,bugs,vulnerabilities,security_hotspots,comment_lines_density,coverage,complexity,cognitive_complexity,duplicated_lines_density,sqale_debt_ratio,sqale_index'
    }
    try:
        response = requests.get(f'{sonar_url}/api/measures/component', headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        measures = data['component']['measures']
        measures_dict = {measure['metric']: measure.get('value', 0) for measure in measures}
    except requests.exceptions.HTTPError as http_err:
        logging.error(f'HTTP error occurred for project {project_key}: {http_err}')
        return {}
    except Exception as err:
        logging.error(f'Other error occurred for project {project_key}: {err}')
        return {}

    return measures_dict


def get_project_bug(sonar_url, auth_token, project_key, issue_type='BUG'):
    headers = {
        'Authorization': f'Bearer {auth_token}'
    }
    params = {
        'componentKeys': project_key,
        'types': issue_type,
        'severities': 'BLOCKER,CRITICAL,MAJOR,MINOR,INFO',
        'ps': 500  # Page size
    }
    issues = []
    page = 1
    while True:
        params['p'] = page
        try:
            response = requests.get(f'{sonar_url}/api/issues/search', headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            issues.extend(data['issues'])
            if len(data['issues']) < params['ps']:
                break
            page += 1
        except requests.exceptions.HTTPError as http_err:
            logging.error(f'HTTP error occurred for project {project_key} issues: {http_err}')
            break
        except Exception as err:
            logging.error(f'Other error occurred for project {project_key} issues: {err}')
            break
    return issues


def get_bug_severity_counts(issues):
    severity_mapping = {
        'BLOCKER': 'High',
        'CRITICAL': 'High',
        'MAJOR': 'Medium',
        'MINOR': 'Low',
        'INFO': 'Low'
    }
    severity_counts = {
        'High': 0,
        'Medium': 0,
        'Low': 0
    }
    for issue in issues:
        severity = issue.get('severity', 'INFO')
        mapped_severity = severity_mapping.get(severity, 'Low')
        if mapped_severity in severity_counts:
            severity_counts[mapped_severity] += 1
    return severity_counts


def get_project_vulnerabilities(sonar_url, auth_token, project_key):
    headers = {
        'Authorization': f'Bearer {auth_token}'
    }
    params = {
        'componentKeys': project_key,
        'types': 'VULNERABILITY',
        'severities': 'BLOCKER,CRITICAL,MAJOR,MINOR,INFO',
        'ps': 500  # Page size
    }
    vulnerabilities = []
    page = 1
    while True:
        params['p'] = page
        try:
            response = requests.get(f'{sonar_url}/api/issues/search', headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            vulnerabilities.extend(data['issues'])
            if len(data['issues']) < params['ps']:
                break
            page += 1
        except requests.exceptions.HTTPError as http_err:
            logging.error(f'HTTP error occurred for project {project_key} vulnerabilities: {http_err}')
            break
        except Exception as err:
            logging.error(f'Other error occurred for project {project_key} vulnerabilities: {err}')
            break
    return vulnerabilities


def get_vulnerability_severity_counts(issues):
    severity_mapping = {
        'BLOCKER': 'High',
        'CRITICAL': 'High',
        'MAJOR': 'Medium',
        'MINOR': 'Low',
        'INFO': 'Low'
    }
    severity_counts = {
        'High': 0,
        'Medium': 0,
        'Low': 0
    }
    for issue in issues:
        severity = issue.get('severity', 'INFO')
        mapped_severity = severity_mapping.get(severity, 'Low')
        if mapped_severity in severity_counts:
            severity_counts[mapped_severity] += 1
    return severity_counts


def get_project_security_hotspots(sonar_url, auth_token, project_key):
    headers = {
        'Authorization': f'Bearer {auth_token}'
    }
    params = {
        'componentKeys': project_key,
        'types': 'SECURITY_HOTSPOT',
        'ps': 500  # Page size
    }
    security_hotspots = []
    page = 1
    response = None  # 显式初始化变量
    while True:
        params['p'] = page
        try:
            response = requests.get(f'{sonar_url}/api/issues/search', headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            security_hotspots.extend(data['issues'])
            if len(data['issues']) < params['ps']:
                break
            page += 1
        except requests.exceptions.HTTPError as http_err:
            logging.error(f'HTTP error occurred for project {project_key} security hotspots: {http_err}')
            if response:  # 仅当response存在时记录详细响应
                logging.error(f'Detailed response: {response.text}')
            break
        except Exception as err:
            logging.error(f'Other error occurred for project {project_key} security hotspots: {err}')
            break
    return security_hotspots


def get_projects(sonar_url, auth_token):
    headers = {
        'Authorization': f'Bearer {auth_token}'
    }
    params = {
        'ps': 500,  # Page size
        'qualifiers': 'TRK'  # Specify the component type as project
    }
    projects = []
    page = 1
    while True:
        params['p'] = page
        try:
            response = requests.get(f'{sonar_url}/api/components/search', headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            for component in data['components']:
                project_key = component['key']
                project_measures = get_project_measures(sonar_url, auth_token, project_key)

                # 获取项目中的Bug并按严重程度统计
                bug_issues = get_project_bug(sonar_url, auth_token, project_key)
                bug_severity_counts = get_bug_severity_counts(bug_issues)

                # 获取项目中的Vulnerabilities并按严重程度统计
                vulnerability_issues = get_project_vulnerabilities(sonar_url, auth_token, project_key)
                vulnerability_severity_counts = get_vulnerability_severity_counts(vulnerability_issues)

                projects.append({
                    'key': project_key,
                    'name': component['name'],
                    'statements': project_measures.get('statements', 0),
                    'lines': project_measures.get('lines', 0),
                    'ncloc': project_measures.get('ncloc', 0),
                    'classes': project_measures.get('classes', 0),
                    'functions': project_measures.get('functions', 0),
                    'files': project_measures.get('files', 0),
                    'bugs': project_measures.get('bugs', 0),
                    'vulnerabilities': project_measures.get('vulnerabilities', 0),
                    'security_hotspots': project_measures.get('security_hotspots', 0),
                    'comment_lines_density': project_measures.get('comment_lines_density', 0),
                    'coverage': project_measures.get('coverage', 0),
                    'sqale_debt_ratio': project_measures.get('sqale_debt_ratio', 0),
                    'sqale_index': project_measures.get('sqale_index', 0),
                    'complexity': project_measures.get('complexity', 0),
                    'cognitive_complexity': project_measures.get('cognitive_complexity', 0),
                    'duplicated_lines_density': project_measures.get('duplicated_lines_density', 0),
                    'bug_severity_counts': bug_severity_counts,
                    'vulnerability_severity_counts': vulnerability_severity_counts
                })
        except requests.exceptions.HTTPError as http_err:
            logging.error(f'HTTP error occurred for project search: {http_err}')
            break
        except Exception as err:
            logging.error(f'Other error occurred for project search: {err}')
            break
        if len(data['components']) < params['ps']:
            break
        page += 1
    return projects


def write_projects_to_csv(projects):
    with open('sonarqube-stat.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            'Project Key', 'Project Name', '总行数', '代码行数', '类数量', '方法数量', '语句数量', '文件数',
            'Bugs', '安全漏洞', '安全热点', '注释率%', '覆盖率%', '圈复杂度', '认知复杂度',
            '重复行率%', '债务率%', '开发总工时(人月)', '高Bugs', '中Bugs', '低Bugs',
            '高危漏洞', '中危漏洞', '低危漏洞'
        ])
        for project in projects:
            # 计算圈复杂度
            complexity = float(project['complexity'])  # 将complexity转换为浮点数
            functions = float(project['functions'])  # 将functions转换为浮点数
            circle_complexity = complexity / functions if functions != 0 else 0
            circle_complexity = round(circle_complexity)
            # 计算认知复杂度
            cognitive_complexity = float(project['cognitive_complexity'])  # 将cognitive_complexity转换为浮点数
            cognitive_complexity_new = cognitive_complexity / functions if functions != 0 else 0  # 计算认知复杂度除以方法数量
            cognitive_complexity_new = round(cognitive_complexity_new)  # 四舍五入为整数

            # 获取Bug严重程度统计
            bug_severity_counts = project.get('bug_severity_counts', {
                'High': 0,
                'Medium': 0,
                'Low': 0
            })

            # 获取Vulnerabilities严重程度统计
            vulnerability_severity_counts = project.get('vulnerability_severity_counts', {
                'High': 0,
                'Medium': 0,
                'Low': 0
            })

            # 计算开发总人月
            sqale_index = float(project['sqale_index'])  # 将sqale_index转换为浮点数
            sqale_debt_ratio = float(project['sqale_debt_ratio'])  # 将sqale_debt_ratio转换为浮点数
            # 计算总开发时间（小时）
            total_dev_time_hours = (sqale_index / 60) / (sqale_debt_ratio / 100) if sqale_debt_ratio != 0 else 0
            # 转换为 "人月"（假设每月 21.75 天 × 8 小时/天 = 174 小时）
            dev_cost = total_dev_time_hours / 174
            dev_cost = round(dev_cost)  # 四舍五入为整数

            writer.writerow([
                project['key'], project['name'], project['lines'], project['ncloc'], project['classes'],
                project['functions'], project['statements'], project['files'],
                project['bugs'], project['vulnerabilities'], project['security_hotspots'], project['comment_lines_density'], project['coverage'],
                circle_complexity, cognitive_complexity_new, project['duplicated_lines_density'],
                project['sqale_debt_ratio'], dev_cost, bug_severity_counts['High'], bug_severity_counts['Medium'],
                bug_severity_counts['Low'], vulnerability_severity_counts['High'], vulnerability_severity_counts['Medium'],
                vulnerability_severity_counts['Low']
            ])


def main():
    sonar_url, auth_token = read_config()
    projects = get_projects(sonar_url, auth_token)
    write_projects_to_csv(projects)


if __name__ == '__main__':
    main()
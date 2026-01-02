"""TODO: Add module description."""
import configparser
import requests
from collections import defaultdict
import csv
import concurrent.futures
import threading
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def read_config(config_file):
    '''"""TODO: Add description.

Args:
    config_file: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    try:
        return {'url': config.get('gitlab', 'url').rstrip('/'), 'token': config.get('gitlab', 'token'), 'start_date': config.get('gitlab', 'start_date'), 'end_date': config.get('gitlab', 'end_date'), 'csv_file': config.get('gitlab', 'csv_file'), 'worker_threads': config.getint('performance', 'worker_threads', fallback=10)}
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logging.error(f'配置错误: {e}')
        exit(1)

def get_all_projects(url, token):
    '''"""TODO: Add description.

Args:
    url: TODO
    token: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    api_url = f'{url}/projects'
    projects = []
    page = 1
    while True:
        try:
            response = requests.get(api_url, headers={'PRIVATE-TOKEN': token}, params={'per_page': 100, 'page': page})
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            projects.extend(data)
            page += 1
        except requests.exceptions.RequestException as e:
            logging.error(f'获取项目时出错: {e}')
            break
    logging.info(f'获取所有项目完成，共 {len(projects)} 个项目')
    return projects

def get_commits(project_id, url, token, start_date, end_date):
    '''"""TODO: Add description.

Args:
    project_id: TODO
    url: TODO
    token: TODO
    start_date: TODO
    end_date: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    api_url = f'{url}/projects/{project_id}/repository/commits'
    commits = []
    page = 1
    while True:
        try:
            response = requests.get(api_url, headers={'PRIVATE-TOKEN': token}, params={'since': start_date, 'until': end_date, 'per_page': 100, 'page': page})
            response.raise_for_status()
            data = response.json()
            logging.info(f'项目 {project_id} 获取到 {len(data)} 个提交，当前页: {page}')
            if not data:
                break
            commits.extend(data)
            page += 1
        except requests.exceptions.RequestException as e:
            logging.error(f'获取项目 {project_id} 的提交记录时出错: {e}')
            break
    return commits

def get_commit_details(project_id, commit_id, url, token):
    '''"""TODO: Add description.

Args:
    project_id: TODO
    commit_id: TODO
    url: TODO
    token: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    api_url = f'{url}/projects/{project_id}/repository/commits/{commit_id}'
    try:
        response = requests.get(api_url, headers={'PRIVATE-TOKEN': token})
        response.raise_for_status()
        data = response.json()
        return data.get('stats', {'additions': 0, 'deletions': 0})
    except requests.exceptions.RequestException as e:
        logging.error(f'获取项目 {project_id} 的提交详情时出错: {e}')
        return {'additions': 0, 'deletions': 0}

def get_merge_requests(project_id, url, token, start_date, end_date):
    '''"""TODO: Add description.

Args:
    project_id: TODO
    url: TODO
    token: TODO
    start_date: TODO
    end_date: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    api_url = f'{url}/projects/{project_id}/merge_requests'
    merge_requests = []
    page = 1
    while True:
        try:
            response = requests.get(api_url, headers={'PRIVATE-TOKEN': token}, params={'created_after': start_date, 'created_before': end_date, 'per_page': 100, 'page': page})
            response.raise_for_status()
            data = response.json()
            logging.info(f'项目 {project_id} 获取到 {len(data)} 个合并请求，当前页: {page}')
            if not data:
                break
            merge_requests.extend(data)
            page += 1
        except requests.exceptions.RequestException as e:
            logging.error(f'获取项目 {project_id} 的合并请求时出错: {e}')
            break
    return merge_requests

def get_user_by_email(email, url, token):
    '''"""TODO: Add description.

Args:
    email: TODO
    url: TODO
    token: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    api_url = f'{url}/users'
    try:
        response = requests.get(api_url, headers={'PRIVATE-TOKEN': token}, params={'search': email})
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f'获取用户信息时出错: {e}')
        return None

def get_user_by_username(username, url, token):
    '''"""TODO: Add description.

Args:
    username: TODO
    url: TODO
    token: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    api_url = f'{url}/users'
    try:
        response = requests.get(api_url, headers={'PRIVATE-TOKEN': token}, params={'username': username})
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f'获取用户信息时出错: {e}')
        return None

def build_contributor_mapping(url, token):
    '''"""TODO: Add description.

Args:
    url: TODO
    token: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    mapping = {}
    page = 1
    while True:
        try:
            response = requests.get(f'{url}/users', headers={'PRIVATE-TOKEN': token}, params={'per_page': 100, 'page': page})
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            for user in data:
                email = user.get('email')
                username = user.get('username')
                user_id = user.get('id')
                fullname = user.get('name', 'Unknown')
                if email:
                    mapping[email] = {'id': user_id, 'username': username, 'fullname': fullname}
                if username:
                    mapping[username] = {'id': user_id, 'username': username, 'fullname': fullname}
            page += 1
        except requests.exceptions.RequestException as e:
            logging.error(f'建立提交者映射表时出错: {e}')
            break
    logging.info(f'建立提交者映射表完成，共 {len(mapping)} 个用户')
    return mapping

def process_project(project, url, token, start_date, end_date, stats, lock, contributor_mapping):
    '''"""TODO: Add description.

Args:
    project: TODO
    url: TODO
    token: TODO
    start_date: TODO
    end_date: TODO
    stats: TODO
    lock: TODO
    contributor_mapping: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    project_id = project['id']
    project_name = project['path_with_namespace']
    logging.info(f'处理项目: {project_name} (ID: {project_id})')
    commits = get_commits(project_id, url, token, start_date, end_date)
    logging.info(f'项目 {project_name} 获取到 {len(commits)} 个提交')
    for commit in commits:
        author_email = commit.get('author_email')
        author_name = commit.get('author_name')
        if not author_email and (not author_name):
            logging.warning(f"提交 {commit['id']} 没有作者邮箱和作者名称")
            continue
        user_info = contributor_mapping.get(author_email) if author_email else None
        if not user_info:
            user_info = contributor_mapping.get(author_name) if author_name else None
        if not user_info:
            logging.warning(f"提交 {commit['id']} 无法找到对应的用户信息")
            continue
        author_id = user_info.get('id')
        author_username = user_info.get('username', 'Unknown')
        author_fullname = user_info.get('fullname', 'Unknown')
        commit_id = commit['id']
        commit_stats = get_commit_details(project_id, commit_id, url, token)
        with lock:
            if author_id not in stats:
                stats[author_id] = {'username': author_username, 'fullname': author_fullname, 'commit_count': 0, 'merge_request_count': 0, 'additions': 0, 'deletions': 0, 'projects': set()}
            stats[author_id]['commit_count'] += 1
            stats[author_id]['additions'] += commit_stats.get('additions', 0)
            stats[author_id]['deletions'] += commit_stats.get('deletions', 0)
            stats[author_id]['projects'].add(project_id)
    merge_requests = get_merge_requests(project_id, url, token, start_date, end_date)
    logging.info(f'项目 {project_name} 获取到 {len(merge_requests)} 个合并请求')
    for mr in merge_requests:
        author_id = mr.get('author', {}).get('id')
        author_username = mr.get('author', {}).get('username', 'Unknown')
        author_fullname = mr.get('author', {}).get('name', 'Unknown')
        if not author_id or not author_username:
            logging.warning(f"合并请求 {mr['id']} 无法找到对应的用户信息")
            continue
        with lock:
            if author_id not in stats:
                stats[author_id] = {'username': author_username, 'fullname': author_fullname, 'commit_count': 0, 'merge_request_count': 0, 'additions': 0, 'deletions': 0, 'projects': set()}
            stats[author_id]['merge_request_count'] += 1
            stats[author_id]['projects'].add(project_id)

def main():
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    config = read_config('config.ini')
    url = config['url']
    token = config['token']
    start_date = config['start_date']
    end_date = config['end_date']
    csv_file = config['csv_file']
    worker_threads = config['worker_threads']
    logging.info('获取所有项目...')
    projects = get_all_projects(url, token)
    logging.info('建立提交者映射表...')
    contributor_mapping = build_contributor_mapping(url, token)
    stats = defaultdict(dict)
    lock = threading.Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_threads) as executor:
        futures = [executor.submit(process_project, project, url, token, start_date, end_date, stats, lock, contributor_mapping) for project in projects]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f'处理项目时出错: {e}')
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['GitLab用户ID', '用户名', '全名', '提交次数', '合并请求次数', '增加代码行数', '删除代码行数', '参与项目数'])
        for author_id, counts in sorted(stats.items(), key=lambda x: x[1]['commit_count'], reverse=True):
            writer.writerow([author_id, counts['username'], counts['fullname'], counts['commit_count'], counts['merge_request_count'], counts['additions'], counts['deletions'], len(counts['projects'])])
    logging.info(f'结果已保存到 {csv_file}')
if __name__ == '__main__':
    main()
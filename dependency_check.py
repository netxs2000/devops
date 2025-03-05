import os
import csv
from bs4 import BeautifulSoup
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


def find_html_file(directory):
    """
    在指定目录下查找第一个HTML文件。
    :param directory: 目录路径
    :return: HTML文件路径或None
    """
    for filename in os.listdir(directory):
        if filename.endswith('.html'):
            return os.path.join(directory, filename)
    logging.error("No HTML file found in the directory.")
    return None


def parse_html_report(html_file):
    """
    解析DependencyCheck生成的HTML报告文件。
    :param html_file: HTML报告文件路径
    :return: 包含Dependency, Severity, CVE Count字段的信息列表
    """
    with open(html_file, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    vulnerabilities = []
    # 定位到包含漏洞信息的表格
    vulnerability_table = soup.find('table', id='summaryTable')
    if not vulnerability_table:
        logging.error("Vulnerability table not found in the HTML file.")
        return []

    # 获取表头信息，并处理特殊字符
    headers = [header.text.strip().replace('\xa0', ' ').lower() for header in
               vulnerability_table.find('thead').find_all('th')]
    logging.debug(f"Headers: {headers}")

    # 确定所需字段的位置
    try:
        dependency_idx = headers.index('dependency')
        severity_idx = headers.index('highest severity')
        cve_count_idx = headers.index('cve count')
    except ValueError as e:
        logging.error(f"Missing required header: {e}")
        return []

    # 解析表体中的每一行，跳过表头行
    rows = vulnerability_table.find('tbody').find_all('tr') if vulnerability_table.find(
        'tbody') else vulnerability_table.find_all('tr')[1:]
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != len(headers):
            logging.warning(f"Incomplete vulnerability information: {row}")
            continue

        vuln_info = {}
        for idx, cell in enumerate(cells):
            key = headers[idx]
            value = cell.text.strip().replace('\xa0', ' ')
            vuln_info[key] = value

        # 提取所需字段
        dependency = vuln_info.get(headers[dependency_idx], '')
        severity = vuln_info.get(headers[severity_idx], '')
        cve_count = vuln_info.get(headers[cve_count_idx], '0')

        # 只记录具有完整信息的依赖项
        if dependency and severity and cve_count:
            vulnerabilities.append({
                'Dependency': dependency,
                'Severity': severity,
                'CVE Count': cve_count
            })
        else:
            logging.warning(f"Skipping vulnerability with missing fields: {vuln_info}")

    return vulnerabilities


def write_csv_file(vulnerabilities, output_file):
    """
    将解析后的漏洞信息写入CSV文件。
    :param vulnerabilities: 包含漏洞信息的列表
    :param output_file: 输出文件路径
    """
    with open(output_file, 'w', encoding='utf-8', newline='') as file:
        fieldnames = ['Dependency', 'Severity', 'CVE Count']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        for vuln in vulnerabilities:
            writer.writerow(vuln)


def main():
    # 设置默认的 reports 目录路径
    reports_dir = os.path.join(os.getcwd(), 'reports')

    # 确保 reports 目录存在
    os.makedirs(reports_dir, exist_ok=True)

    # 查找 reports 目录下的第一个 HTML 文件
    html_file_path = find_html_file(reports_dir)
    if not html_file_path:
        logging.error("No HTML file found in the reports directory.")
        return

    # 设置输出 CSV 文件路径
    default_output_file_path = os.path.join(reports_dir, 'DependencyCheck_report.csv')

    # 解析HTML报告
    vulnerabilities = parse_html_report(html_file_path)
    logging.info(f"Found {len(vulnerabilities)} vulnerabilities with complete information.")

    # 写入CSV文件
    write_csv_file(vulnerabilities, default_output_file_path)
    logging.info(f"CSV file written to {default_output_file_path}")


if __name__ == "__main__":
    main()

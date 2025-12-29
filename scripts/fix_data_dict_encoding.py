# -*- coding: utf-8 -*-
"""修复 DATA_DICTIONARY.md 文件的编码问题

从第1011行开始，文件存在编码损坏导致的中文乱码，
本脚本尝试读取原始内容并修复乱码部分。
"""

import re

def fix_encoding():
    file_path = r'docs\api\DATA_DICTIONARY.md'
    
    # 尝试以不同编码读取
    content = None
    for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb18030']:
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            print(f"Successfully read file with {encoding} encoding")
            break
        except Exception as e:
            print(f"Failed to read with {encoding}: {e}")
    
    if not content:
        print("Unable to read file")
        return
    
    lines = content.split('\n')
    print(f"Total lines: {len(lines)}")
    
    # Skip printing potentially corrupt content to avoid console encoding issues
    
    # 修复已知的乱码部分（第1011行附近）
    # 根据上下文推测，这应该是 "认证与服务台域 (Authentication & Service Desk Domain)"
    corrupted_section_start = None
    for i, line in enumerate(lines):
        if '?? 10.' in line or '�֤�̨�' in line:
            corrupted_section_start = i
            print(f"\nFound corrupted section at line: {i+1}")
            break
    
    if corrupted_section_start is not None:
        # 替换乱码章节标题
        lines[corrupted_section_start] = "## 📦 10. 认证与服务台域 (Authentication & Service Desk Domain)"
        
        # 修复后续几行的乱码（基于上下文推测）
        for i in range(corrupted_section_start, min(corrupted_section_start + 20, len(lines))):
            line = lines[i]
            
            # 修复表格定义行的乱码
            if '�֤�' in line and "'auth_tokens'" in line:
                lines[i] = "### 10.1 认证令牌表 ('auth_tokens') 📋 (New)"
            elif '�ڹ�û�¼״̬' in line:
                lines[i] = "用于管理用户登录状态及 API 调用授权 (OAuth2 Bearer Token)。"
            elif '�ֶ�' in line and '�' in line and 'ҵ�˵�' in line:
                lines[i] = "| 字段名 | 类型 | 约束 | 必填 | 默认值 | 示例值 | 业务说明 |"
            elif "'token'" in line and '�ɵ�' in line:
                lines[i] = "| 'token' | String(64) | PK | 是 | - | 'atk_...' | 自动生成的 Token 字符串 |"
            elif "'user_id'" in line and '�û�' in line:
                lines[i] = "| 'user_id' | Integer | FK | 是 | - | '10086' | 关联用户 ID |"
            elif "'created_at'" in line and '�ʱ�' in line:
                lines[i] = "| 'created_at' | DateTime | | 是 | Now | '2025-12-28 10:00:00' | 创建时间 |"
    
    # 写回文件
    fixed_content = '\n'.join(lines)
    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(fixed_content)
    
    print(f"\nFile fixed and saved as UTF-8 encoding")

if __name__ == '__main__':
    fix_encoding()

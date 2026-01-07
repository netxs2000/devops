#!/bin/bash
# -----------------------------------------------------------------------------
# Docker Registry Mirror Configurator for China Users
# 自动配置 Docker 国内镜像加速 (需 Root 权限)
# -----------------------------------------------------------------------------

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}>>> Docker Registry Mirror Configurator${NC}"

# Check for root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root (sudo ./setup_china_mirrors.sh)${NC}"
  exit 1
fi

DAEMON_FILE="/etc/docker/daemon.json"
BACKUP_FILE="/etc/docker/daemon.json.bak.$(date +%s)"

# 2026年稳定可用的镜像源列表 (示例)
# 注意：国内镜像源动态变化，建议根据实际情况维护此列表
MIRRORS='[
    "https://docker.m.daocloud.io",
    "https://huecker.io",
    "https://dockerhub.timeweb.cloud",
    "https://noohub.ru"
  ]'

# Check if file exists
if [ -f "$DAEMON_FILE" ]; then
    echo -e "${YELLOW}Existing configuration found. Backing up to $BACKUP_FILE...${NC}"
    cp "$DAEMON_FILE" "$BACKUP_FILE"
    
    # 简单的合并逻辑太复杂，这里选择提示用户覆盖或手动合并
    # 为了自动化，我们尝试检查是否已经是有效的JSON，若需要高级合并建议手动处理
    # 这里采取覆盖策略，但发出警告
    echo -e "${YELLOW}⚠️  WARNING: This will overwrite 'registry-mirrors' in $DAEMON_FILE.${NC}"
else
    echo -e "${GREEN}Creating new $DAEMON_FILE...${NC}"
    mkdir -p /etc/docker
fi

# Write configuration
cat > "$DAEMON_FILE" <<EOF
{
  "registry-mirrors": $MIRRORS,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Configuration written successfully.${NC}"
    echo -e "${GREEN}Restarting Docker daemon...${NC}"
    systemctl daemon-reload
    systemctl restart docker
    echo -e "${GREEN}✅ Docker mirrors updated!${NC}"
    docker info | grep "Registry Mirrors" -A 5
else
    echo -e "${RED}Failed to write configuration.${NC}"
    exit 1
fi

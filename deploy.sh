#!/bin/bash
set -e
# -----------------------------------------------------------------------------
# DevOps Application Platform - Server Deployment Script
# 傻瓜式一键部署脚本 (Linux/Mac)
# -----------------------------------------------------------------------------

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}===== DevOps Platform One-Click Deployment =====${NC}"

# 1. 检查 Docker 环境
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Warning: docker-compose not found, trying 'docker compose'...${NC}"
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}Error: Docker Compose is not installed.${NC}"
        exit 1
    fi
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# 2. 只有 make 环境存在时才使用 make，否则使用原始命令
if command -v make &> /dev/null; then
    echo -e "${GREEN}Detected 'make', using Makefile workflow...${NC}"
    # 检查网络连接 (Docker Hub)
    echo -e "${YELLOW}Checking connectivity to Docker Hub...${NC}"
    if ! curl -s --connect-timeout 5 https://hub.docker.com > /dev/null; then
        echo -e "${YELLOW}⚠️  Warning: Cannot connect to Docker Hub. You might be in a restricted network region (e.g., China).${NC}"
        echo -e "${YELLOW}💡 Suggestion: Run 'sudo bash scripts/setup_china_mirrors.sh' to configure registry mirrors.${NC}"
        read -p "Do you want to run the mirror setup script now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo bash scripts/setup_china_mirrors.sh
        fi
    else
        echo -e "${GREEN}Connectivity looks good.${NC}"
    fi
    
    make deploy-prod
else
    echo -e "${YELLOW}'make' not found. Executing manual deployment steps...${NC}"
    
    # 检查网络连接 (Docker Hub) - Manual mode
    if ! curl -s --connect-timeout 5 https://hub.docker.com > /dev/null; then
        echo -e "${YELLOW}⚠️  Warning: Cannot connect to Docker Hub.${NC}"
        echo -e "${YELLOW}💡 Suggestion: Run 'sudo bash scripts/setup_china_mirrors.sh' to configure registry mirrors.${NC}"
        read -p "Do you want to run the mirror setup script now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo bash scripts/setup_china_mirrors.sh
        fi
    fi
    
    # 检查 .env
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Creating .env from example...${NC}"
        cp .env.example .env
        echo -e "${RED}IMPORTANT: Please edit .env with your credentials and run this script again!${NC}"
        exit 1
    fi

    # 执行部署
    echo -e "${GREEN}Stopping old services...${NC}"
    # 执行部署
    echo -e "${GREEN}Stopping old services...${NC}"
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml down --remove-orphans
    
    echo -e "${GREEN}Building images...${NC}"
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml build
    
    echo -e "${GREEN}Starting services...${NC}"
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml up -d --wait
    
    echo -e "${GREEN}Initializing data...${NC}"
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml exec -T api python scripts/init_discovery.py
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml exec -T api python scripts/init_cost_codes.py
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml exec -T api python scripts/init_labor_rates.py
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml exec -T api python scripts/init_purchase_contracts.py
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml exec -T api python scripts/init_revenue_contracts.py
    
    echo -e "${GREEN}Deployment Complete!${NC}"
fi

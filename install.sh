#!/bin/bash
# Ansible 自动化流程编排平台 - 本地安装脚本
# 运行前请确保已安装 Python 3.10+ 和 Node.js 18+

set -e

# 使用清华镜像源
PIP_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"

echo "======================================"
echo "  Ansible 自动化平台 - 本地安装"
echo "======================================"

# 检查 Python 版本
check_python() {
    echo "[1/7] 检查 Python 版本..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo "  Python 版本: $PYTHON_VERSION"
    else
        echo "  错误: 未安装 Python3"
        exit 1
    fi
}

# 检查 Node.js 版本
check_node() {
    echo "[2/7] 检查 Node.js 版本..."
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version 2>&1)
        echo "  Node.js 版本: $NODE_VERSION"
    else
        echo "  错误: 未安装 Node.js"
        exit 1
    fi
}

# 检查 PostgreSQL
check_postgres() {
    echo "[3/7] 检查 PostgreSQL..."
    if command -v psql &> /dev/null; then
        echo "  PostgreSQL 已安装"
        # 检查服务是否运行
        if ! pgrep -x "postgres" > /dev/null; then
            echo "  警告: PostgreSQL 未运行，尝试启动..."
            sudo systemctl start postgresql 2>/dev/null || \
            sudo service postgresql start 2>/dev/null || \
            echo "  请手动启动 PostgreSQL 服务"
        else
            echo "  PostgreSQL 服务运行中"
        fi
    else
        echo "  警告: 未检测到 PostgreSQL"
        echo "  请使用以下命令安装:"
        echo "    Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
        echo "    CentOS/RHEL:   sudo yum install postgresql-server"
        echo "    macOS:         brew install postgresql"
    fi
}

# 检查 Redis
check_redis() {
    echo "[4/7] 检查 Redis..."
    if command -v redis-cli &> /dev/null; then
        echo "  Redis 已安装"
        # 检查服务是否运行
        if ! pgrep -x "redis-server" > /dev/null; then
            echo "  警告: Redis 未运行，尝试启动..."
            sudo systemctl start redis 2>/dev/null || \
            sudo service redis start 2>/dev/null || \
            sudo systemctl start redis-server 2>/dev/null || \
            echo "  请手动启动 Redis 服务"
        else
            echo "  Redis 服务运行中"
        fi
    else
        echo "  警告: 未检测到 Redis"
        echo "  请使用以下命令安装:"
        echo "    Ubuntu/Debian: sudo apt install redis-server"
        echo "    CentOS/RHEL:   sudo yum install redis"
        echo "    macOS:         brew install redis"
    fi
}

# 检查 Ansible
check_ansible() {
    echo "[5/7] 检查 Ansible..."
    if command -v ansible &> /dev/null; then
        ANSIBLE_VERSION=$(ansible --version | head -1)
        echo "  $ANSIBLE_VERSION"
    else
        echo "  警告: 未检测到 Ansible，将自动安装"
        pip install ansible paramiko -i "$PIP_MIRROR" --timeout 300
    fi
}

# 配置 PostgreSQL 数据库
setup_postgres() {
    echo "[6/7] 配置 PostgreSQL 数据库..."
    
    # 检测 PostgreSQL 安装类型
    if command -v pg_isready &> /dev/null; then
        # 设置 postgres 用户密码
        echo "  设置 postgres 用户密码..."
        sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';" 2>/dev/null || \
        psql -h localhost -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';" 2>/dev/null || \
        echo "  密码设置可能已存在或需要手动配置"
        
        # 创建数据库
        echo "  创建数据库 automation_platform..."
        sudo -u postgres psql -c "CREATE DATABASE automation_platform;" 2>/dev/null || \
        psql -h localhost -U postgres -c "CREATE DATABASE automation_platform;" 2>/dev/null || \
        echo "  数据库可能已存在，跳过创建"
        
        # 配置 pg_hba.conf 允许本地连接
        echo "  配置 PostgreSQL 认证..."
        PG_HBA=$(sudo -u postgres psql -t -c "SHOW hba_file;" 2>/dev/null | tr -d ' ')
        if [ -n "$PG_HBA" ] && [ -f "$PG_HBA" ]; then
            # 备份
            sudo cp "$PG_HBA" "${PG_HBA}.bak" 2>/dev/null
            # 确保有本地认证规则
            if ! grep -q "local.*all.*all.*peer\|local.*all.*all.*trust" "$PG_HBA" 2>/dev/null; then
                echo "host all all 127.0.0.1/32 md5" | sudo tee -a "$PG_HBA" > /dev/null
                echo "  已添加 MD5 认证规则"
                # 重载配置
                sudo -u postgres psql -c "SELECT pg_reload_conf();" 2>/dev/null || \
                sudo systemctl reload postgresql 2>/dev/null || \
                echo "  请重载 PostgreSQL 配置"
            fi
        fi
        
        echo "  PostgreSQL 配置完成"
    else
        echo "  警告: 未检测到 PostgreSQL 客户端"
    fi
}

# 创建虚拟环境并安装依赖
setup_venv() {
    echo "[7/7] 创建 Python 虚拟环境并安装依赖..."
    
    cd "$(dirname "$0")"
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "  虚拟环境已创建: venv/"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装后端依赖（使用清华镜像）
    echo "  安装后端依赖 (使用清华镜像)..."
    cd backend
    pip install -r requirements.txt -i "$PIP_MIRROR" --timeout 300
    cd ..
    
    # 安装前端依赖
    echo "  安装前端依赖..."
    cd frontend
    npm install
    
    cd ..
    
    echo ""
    echo "======================================"
    echo "  安装完成!"
    echo "======================================"
}

# 安装前端依赖
setup_frontend() {
    echo "  安装前端依赖..."
    cd "$(dirname "$0")"
    cd ../frontend
    npm install
}

# 主流程
main() {
    check_python
    check_node
    check_postgres
    check_redis
    check_ansible
    setup_postgres
    setup_venv
    
    echo ""
    echo "======================================"
    echo "  安装完成!"
    echo "======================================"
    echo ""
    echo "后续步骤:"
    echo "  1. 配置并初始化数据库: ./setup.sh all"
    echo "  2. 或分步执行:"
    echo "     ./setup.sh config   # 配置数据库"
    echo "     ./setup.sh init     # 初始化数据库"
    echo "     ./setup.sh start    # 启动服务"
    echo ""
    echo "默认账号:"
    echo "  用户名: admin"
    echo "  密码: admin123"
    echo ""
}

main "$@"


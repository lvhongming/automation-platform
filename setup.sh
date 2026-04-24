#!/bin/bash
# 数据库和服务配置脚本

set -e

echo "======================================"
echo "  Ansible 自动化平台 - 配置向导"
echo "======================================"

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 加载虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 确保 PostgreSQL 运行并设置密码
ensure_postgres() {
    echo ""
    echo "[检查 PostgreSQL 服务]"
    echo ""
    
    # 检查 PostgreSQL 是否安装
    if ! command -v psql &> /dev/null; then
        echo "  错误: 未安装 PostgreSQL"
        echo "  请先运行 install.sh 安装依赖"
        exit 1
    fi
    
    # 检查服务是否运行
    if ! pgrep -x "postgres" > /dev/null; then
        echo "  PostgreSQL 未运行，尝试启动..."
        sudo systemctl start postgresql 2>/dev/null || \
        sudo service postgresql start 2>/dev/null || \
        sudo pg_ctlcluster 15 main start 2>/dev/null || \
        (echo "  无法自动启动 PostgreSQL" && exit 1)
        sleep 2
    fi
    
    echo "  PostgreSQL 服务运行中"
}

# 设置 PostgreSQL postgres 用户密码
setup_postgres_user() {
    echo ""
    echo "[设置 PostgreSQL 用户密码]"
    echo ""
    
    # 使用 postgres 用户设置密码
    echo "  设置 postgres 用户密码为 'postgres'..."
    
    # 方法1: 使用 ALTER USER
    sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';" 2>/dev/null && {
        echo "  密码设置成功"
        return 0
    }
    
    # 方法2: 如果上面失败，使用 psql 直接修改
    echo "  尝试备用方法..."
    sudo -u postgres psql << EOF 2>/dev/null || true
\password postgres
postgres
postgres
postgres
\q
EOF
    
    # 方法3: 使用 sed 直接修改 pg_shadow
    sudo -u postgres psql -c "SELECT 1 FROM pg_authid WHERE rolname='postgres';" 2>/dev/null | grep -q 1 && {
        sudo -u postgres psql -c "UPDATE pg_authid SET rolpassword = 'md5320f74961c71e1c5e91a4a0559ab891' WHERE rolname = 'postgres';" 2>/dev/null
        sudo -u postgres psql -c "SELECT pg_reload_conf();" 2>/dev/null || true
    }
    
    echo "  postgres 用户密码已设置"
}

# 配置数据库
setup_database() {
    echo ""
    echo "[数据库配置]"
    echo ""
    
    # 确保 PostgreSQL 运行
    ensure_postgres
    setup_postgres_user
    
    # 读取配置
    source backend/.env 2>/dev/null || true
    
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
    DB_USER="${DB_USER:-postgres}"
    DB_PASS="${DB_PASS:-postgres}"
    DB_NAME="${DB_NAME:-automation_platform}"
    
    # 显示当前配置
    echo "当前配置:"
    echo "  数据库主机: $DB_HOST"
    echo "  数据库端口: $DB_PORT"
    echo "  数据库用户: $DB_USER"
    echo "  数据库密码: ********"
    echo "  数据库名称: $DB_NAME"
    echo ""
    
    read -p "是否使用默认配置? [Y/n]: " use_default
    use_default="${use_default:-Y}"
    
    if [[ "$use_default" =~ ^[Nn]$ ]]; then
        read -p "数据库主机 [$DB_HOST]: " input
        DB_HOST="${input:-$DB_HOST}"
        
        read -p "数据库端口 [$DB_PORT]: " input
        DB_PORT="${input:-$DB_PORT}"
        
        read -p "数据库用户 [$DB_USER]: " input
        DB_USER="${input:-$DB_USER}"
        
        read -p "数据库密码 [$DB_PASS]: " input
        DB_PASS="${input:-$DB_PASS}"
        
        read -p "数据库名称 [$DB_NAME]: " input
        DB_NAME="${input:-$DB_NAME}"
    fi
    
    # 创建数据库
    echo ""
    echo "创建/验证数据库..."
    
    # 检查数据库是否存在
    DB_EXISTS=$(sudo -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$DB_NAME" && echo "yes" || echo "no")
    
    if [ "$DB_EXISTS" = "no" ]; then
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null && \
        echo "  数据库 $DB_NAME 创建成功" || \
        echo "  数据库创建失败，请检查权限"
    else
        echo "  数据库 $DB_NAME 已存在"
    fi
    
    # 测试连接
    echo "  测试数据库连接..."
    sudo -u postgres PGPASSWORD='postgres' psql -h localhost -p 5432 -U postgres -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1 && \
    echo "  数据库连接测试成功" || \
    echo "  警告: 数据库连接测试失败，请检查配置"
    
    # 更新 .env 文件
    cat > backend/.env << EOF
# 数据库配置
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# JWT 配置
SECRET_KEY=your-secret-key-change-in-production-$(date +%s)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 应用配置
DEBUG=true
APP_NAME=Ansible Automation Platform
EOF
    
    echo "  数据库配置已保存到 backend/.env"
}

# 初始化数据库
init_database() {
    echo ""
    echo "[初始化数据库]"
    echo ""
    
    # 确保虚拟环境已激活
    if [ ! -d "venv" ]; then
        echo "  错误: 未找到虚拟环境，请先运行 install.sh"
        exit 1
    fi
    
    source venv/bin/activate
    
    # 检查 .env 文件
    if [ ! -f "backend/.env" ]; then
        echo "  警告: 未找到 .env 文件，请先运行 ./setup.sh config"
        read -p "是否现在配置数据库? [y/N]: " do_config
        if [[ "$do_config" =~ ^[Yy]$ ]]; then
            setup_database
        else
            exit 1
        fi
    fi
    
    cd "$SCRIPT_DIR/backend"
    
    # 加载环境变量
    source ../venv/bin/activate 2>/dev/null || true
    export PYTHONPATH="$SCRIPT_DIR/backend"
    
    # 执行数据库初始化
    echo "执行数据库初始化..."
    python scripts/init_db.py
    
    echo ""
    echo "创建管理员账号..."
    python scripts/create_admin.py
    
    echo ""
    echo "数据库初始化完成!"
}

# 启动服务
start_services() {
    echo ""
    echo "[启动服务]"
    echo ""
    
    # 创建日志目录
    mkdir -p logs
    
    # 加载虚拟环境
    if [ ! -d "venv" ]; then
        echo "  错误: 未找到虚拟环境，请先运行 install.sh"
        exit 1
    fi
    source venv/bin/activate
    
    # 启动后端
    echo "启动后端服务 (端口 8000)..."
    cd "$SCRIPT_DIR/backend"
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "  后端 PID: $BACKEND_PID"
    
    # 等待后端启动
    sleep 3
    
    # 检查后端是否成功启动
    if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "  错误: 后端启动失败，请查看 logs/backend.log"
        exit 1
    fi
    
    # 启动前端
    echo "启动前端服务 (端口 3000)..."
    cd "$SCRIPT_DIR/frontend"
    nohup npm run dev -- --host > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "  前端 PID: $FRONTEND_PID"
    
    # 等待前端启动
    sleep 3
    
    # 检查前端是否成功启动
    if ! ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "  错误: 前端启动失败，请查看 logs/frontend.log"
    fi
    
    # 保存 PID
    cat > .services.pid << EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
EOF
    
    echo ""
    echo "======================================"
    echo "  服务启动完成!"
    echo "======================================"
    echo ""
    echo "访问地址:"
    echo "  前端: http://localhost:3000"
    echo "  后端: http://localhost:8000"
    echo "  API文档: http://localhost:8000/docs"
    echo ""
    echo "默认账号:"
    echo "  用户名: admin"
    echo "  密码: admin123"
    echo ""
    echo "日志文件:"
    echo "  后端: logs/backend.log"
    echo "  前端: logs/frontend.log"
    echo ""
}

# 停止服务
stop_services() {
    echo ""
    echo "[停止服务]"
    echo ""
    
    if [ -f .services.pid ]; then
        source .services.pid
        
        [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null && echo "  后端已停止"
        [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null && echo "  前端已停止"
        
        rm -f .services.pid
    else
        pkill -f "uvicorn app.main:app" 2>/dev/null && echo "  后端已停止"
        pkill -f "vite" 2>/dev/null && echo "  前端已停止"
    fi
    
    echo "  服务已停止"
}

# 显示状态
show_status() {
    echo ""
    echo "[服务状态]"
    echo ""
    
    if [ -f .services.pid ]; then
        source .services.pid
        
        echo "后端 (端口 8000):"
        [ -n "$BACKEND_PID" ] && ps -p $BACKEND_PID > /dev/null 2>&1 && echo "  运行中 (PID: $BACKEND_PID)" || echo "  未运行"
        
        echo "前端 (端口 3000):"
        [ -n "$FRONTEND_PID" ] && ps -p $FRONTEND_PID > /dev/null 2>&1 && echo "  运行中 (PID: $FRONTEND_PID)" || echo "  未运行"
    else
        echo "  服务未管理 (请使用 start 命令启动)"
    fi
    
    echo ""
    echo "进程检查:"
    pgrep -f "uvicorn" > /dev/null && echo "  后端进程: 运行中" || echo "  后端进程: 未运行"
    pgrep -f "vite" > /dev/null && echo "  前端进程: 运行中" || echo "  前端进程: 未运行"
    
    echo ""
    echo "数据库状态:"
    if pgrep -x "postgres" > /dev/null; then
        echo "  PostgreSQL: 运行中"
        sudo -u postgres psql -c "SELECT datname FROM pg_database WHERE datname='automation_platform';" 2>/dev/null | grep -q automation_platform && \
        echo "  数据库 automation_platform: 存在" || echo "  数据库 automation_platform: 不存在"
    else
        echo "  PostgreSQL: 未运行"
    fi
}

# 帮助信息
show_help() {
    echo ""
    echo "用法: ./setup.sh <命令>"
    echo ""
    echo "命令:"
    echo "  config     配置数据库连接"
    echo "  init       初始化数据库"
    echo "  start      启动所有服务"
    echo "  stop       停止所有服务"
    echo "  restart    重启所有服务"
    echo "  status     查看服务状态"
    echo "  all        执行完整配置 (config + init + start)"
    echo "  help       显示帮助信息"
    echo ""
    echo "示例:"
    echo "  ./setup.sh all      # 一键安装配置"
    echo "  ./setup.sh status   # 查看服务状态"
    echo ""
}

# 主流程
COMMAND="${1:-help}"

case "$COMMAND" in
    config)
        setup_database
        ;;
    init)
        init_database
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_services
        ;;
    status)
        show_status
        ;;
    all)
        setup_database
        init_database
        start_services
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "未知命令: $COMMAND"
        show_help
        exit 1
        ;;
esac


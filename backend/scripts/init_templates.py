"""初始化预置模板数据"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker
from app.models.flow import PlaybookTemplate, ScriptTemplate


async def create_default_templates():
    """创建预置模板"""
    async with async_session_maker() as session:
        # 预置 Playbook 模板
        playbooks = [
            {
                "name": "Nginx 安装与配置",
                "description": "在目标主机上安装 Nginx Web 服务器并配置基本的虚拟主机",
                "category": "Web服务",
                "content": """- name: 安装并配置 Nginx
  hosts: all
  become: yes
  vars:
    nginx_port: 80
    server_name: example.com
  tasks:
    - name: 安装 Nginx
      package:
        name: nginx
        state: present

    - name: 配置 Nginx
      template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      notify: 重启 Nginx

    - name: 启动 Nginx
      service:
        name: nginx
        state: started
        enabled: yes

  handlers:
    - name: 重启 Nginx
      service:
        name: nginx
        state: restarted
""",
                "variables_schema": {
                    "nginx_port": {"type": "integer", "default": 80},
                    "server_name": {"type": "string", "default": "example.com"}
                },
                "tags": ["nginx", "web", "安装"]
            },
            {
                "name": "MySQL 主从配置",
                "description": "配置 MySQL 主从复制环境",
                "category": "数据库",
                "content": """- name: MySQL 主从配置
  hosts: mysql_servers
  become: yes
  vars:
    mysql_root_password: "your_password"
  tasks:
    - name: 安装 MySQL
      package:
        name: "{{ item }}"
        state: present
      loop:
        - mysql-server
        - mysql-client

    - name: 配置主服务器
      when: "'master' in group_names"
      template:
        src: my.cnf.j2
        dest: /etc/my.cnf
      notify: 重启 MySQL

    - name: 配置从服务器
      when: "'slave' in group_names"
      template:
        src: my-slave.cnf.j2
        dest: /etc/my.cnf
      notify: 重启 MySQL

  handlers:
    - name: 重启 MySQL
      service:
        name: mysqld
        state: restarted
""",
                "tags": ["mysql", "主从", "数据库"]
            },
            {
                "name": "服务器安全加固",
                "description": "对服务器进行基本的安全加固，包括防火墙配置、SSH 安全设置等",
                "category": "安全",
                "content": """- name: 服务器安全加固
  hosts: all
  become: yes
  tasks:
    - name: 更新系统软件包
      yum:
        name: "*"
        state: latest

    - name: 配置防火墙规则
      firewalld:
        service: "{{ item }}"
        permanent: yes
        state: enabled
      loop:
        - ssh
        - http
        - https

    - name: 禁用不必要的服务
      service:
        name: "{{ item }}"
        state: stopped
        enabled: no
      loop:
        - telnet
        - rsh
        - rlogin

    - name: 配置 SSH 密钥认证
      authorized_key:
        user: root
        key: "{{ lookup('file', '~/.ssh/id_rsa.pub') }}"
        state: present
""",
                "tags": ["安全", "加固", "防火墙"]
            },
            {
                "name": "Docker 安装",
                "description": "在目标主机上安装 Docker 引擎",
                "category": "容器",
                "content": """- name: 安装 Docker
  hosts: all
  become: yes
  tasks:
    - name: 安装必要依赖
      package:
        name:
          - yum-utils
          - device-mapper-persistent-data
          - lvm2
        state: present

    - name: 添加 Docker 仓库
      get_url:
        url: https://get.docker.com/
        dest: /tmp/get-docker.sh
        mode: '0755'

    - name: 安装 Docker
      command: sh /tmp/get-docker.sh
      creates: /usr/bin/docker

    - name: 启动 Docker
      service:
        name: docker
        state: started
        enabled: yes

    - name: 添加用户到 docker 组
      user:
        name: "{{ ansible_user }}"
        groups: docker
        append: yes
""",
                "tags": ["docker", "容器", "安装"]
            }
        ]

        for pb_data in playbooks:
            # 检查是否已存在
            from sqlalchemy import select
            result = await session.execute(
                select(PlaybookTemplate).where(PlaybookTemplate.name == pb_data["name"])
            )
            if not result.scalar_one_or_none():
                pb = PlaybookTemplate(**pb_data, is_public=True)
                session.add(pb)
                print(f"创建 Playbook: {pb_data['name']}")

        # 预置脚本模板
        scripts = [
            {
                "name": "服务器巡检脚本",
                "description": "检查服务器 CPU、内存、磁盘使用情况",
                "script_type": "shell",
                "content": """#!/bin/bash
# 服务器巡检脚本

echo "===== 服务器巡检报告 ====="
echo "巡检时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo "===== 系统信息 ====="
uname -a
echo ""

echo "===== CPU 使用情况 ====="
top -bn1 | head -5
echo ""

echo "===== 内存使用情况 ====="
free -h
echo ""

echo "===== 磁盘使用情况 ====="
df -h | grep -v tmpfs
echo ""

echo "===== 网络连接状态 ====="
netstat -tuln | head -20
echo ""

echo "===== 运行中的服务 ====="
systemctl list-units --type=service --state=running | head -20
echo ""

echo "===== 最近登录记录 ====="
last | head -10
echo ""

echo "===== 巡检完成 ====="
""",
                "category": "运维",
                "tags": ["巡检", "监控"]
            },
            {
                "name": "应用部署脚本",
                "description": "通用的应用部署脚本模板",
                "script_type": "shell",
                "content": """#!/bin/bash
# 应用部署脚本

set -e

# 配置
APP_NAME="{{app_name}}"
APP_DIR="/opt/${APP_NAME}"
BACKUP_DIR="/opt/backup"
TIMESTAMP=$(date +%Y%m%d%H%M%S)

# 颜色输出
RED='\\033[0;31m'
GREEN='\\033[0;32m'
NC='\\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 备份旧版本
backup() {
    if [ -d "$APP_DIR" ]; then
        log_info "备份旧版本..."
        mkdir -p $BACKUP_DIR
        mv $APP_DIR ${BACKUP_DIR}/${APP_NAME}_${TIMESTAMP}
        log_info "备份完成: ${BACKUP_DIR}/${APP_NAME}_${TIMESTAMP}"
    fi
}

# 部署新版本
deploy() {
    log_info "开始部署 ${APP_NAME}..."
    
    mkdir -p $APP_DIR
    
    # 这里添加你的部署命令
    # 例如: cp -r ./dist/* $APP_DIR/
    
    log_info "部署完成"
}

# 重启服务
restart() {
    log_info "重启服务..."
    # systemctl restart ${APP_NAME}
    log_info "服务已重启"
}

# 主流程
main() {
    log_info "开始部署流程..."
    backup
    deploy
    restart
    log_info "部署流程完成!"
}

main
""",
                "category": "部署",
                "tags": ["部署", "发布"]
            },
            {
                "name": "日志清理脚本",
                "description": "清理指定目录下的旧日志文件",
                "script_type": "shell",
                "content": """#!/bin/bash
# 日志清理脚本

# 配置
LOG_DIR="/var/log"
DAYS=${1:-7}
MAX_SIZE=${2:-100}

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 清理指定天数前的日志
clean_old_logs() {
    log_info "清理 ${DAYS} 天前的日志文件..."
    find $LOG_DIR -name "*.log" -type f -mtime +$DAYS -exec rm -f {} \\;
    log_info "清理完成"
}

# 清理大文件日志
clean_large_logs() {
    log_info "清理超过 ${MAX_SIZE}MB 的日志文件..."
    find $LOG_DIR -name "*.log" -type f -size +${MAX_SIZE}M -exec truncate -s 0 {} \\;
    log_info "清理完成"
}

# 清理系统日志
clean_system_logs() {
    log_info "清理系统日志..."
    journalctl --vacuum-time=${DAYS}days
    log_info "清理完成"
}

# 主流程
main() {
    log_info "开始日志清理..."
    clean_old_logs
    clean_large_logs
    clean_system_logs
    log_info "日志清理完成!"
}

main
""",
                "category": "运维",
                "tags": ["日志", "清理", "维护"]
            }
        ]

        for script_data in scripts:
            from sqlalchemy import select
            result = await session.execute(
                select(ScriptTemplate).where(ScriptTemplate.name == script_data["name"])
            )
            if not result.scalar_one_or_none():
                script = ScriptTemplate(**script_data, is_public=True)
                session.add(script)
                print(f"创建脚本: {script_data['name']}")

        await session.commit()
        print("\\n预置模板创建完成!")


if __name__ == "__main__":
    asyncio.run(create_default_templates())

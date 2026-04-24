FROM python:3.11-slim

WORKDIR /app

# 配置 pip 镜像源（使用清华镜像加速）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.timeout 600

# 配置 apt 镜像源（使用阿里云镜像加速）
RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://security.debian.org|https://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    ssh-client \
    && rm -rf /var/lib/apt/lists/*

# 安装 Ansible（指定较稳定的版本）
RUN pip install --no-cache-dir ansible==2.10.7 ansible-core==2.15.12 ansible-runner==1.0.1

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p /app/playbooks /app/inventory /app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

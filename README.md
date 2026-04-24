# Ansible 自动化流程平台 - 功能说明文档

## 一、项目概述

### 1.1 项目简介

Ansible 自动化流程平台是一款可视化的拖放式自动化运维平台，让运维人员无需编写 YAML，即可通过拖拽节点、配置参数，自动执行 Ansible 命令和脚本，实现 IT 运维流程自动化。

### 1.2 核心能力

- **可视化流程编辑**：通过拖拽节点、连接线的方式设计自动化流程
- **多种执行节点**：支持命令、脚本、Playbook、循环、条件分支等丰富节点
- **主机集中管理**：统一管理被控主机及认证凭据
- **实时执行监控**：WebSocket 实时推送执行状态和日志
- **定时任务调度**：支持 Cron 表达式实现复杂的调度策略
- **多渠道通知**：支持邮件、企业微信、钉钉等通知方式

---

## 二、技术架构

### 2.1 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端框架 | Vue 3 + Vite 4 | 现代化前端开发框架 |
| UI 组件库 | Element Plus | 企业级 Vue 3 组件库 |
| 流程图库 | Vue Flow | 基于 Ant Design X6 的流程编辑器 |
| 状态管理 | Pinia | Vue 3 官方推荐的状态管理库 |
| 后端框架 | FastAPI | 高性能 Python Web 框架 |
| 数据库 | PostgreSQL 15+ | 关系型数据库 |
| 异步任务 | Redis + asyncio | 任务队列与缓存 |
| 定时调度 | APScheduler | Python 定时任务库 |
| 自动化引擎 | Ansible Runner | Ansible 执行引擎 |
| 实时通信 | WebSocket | 浏览器与服务器双向通信 |

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 流程编辑器 │  │ 主机管理  │  │ 执行监控  │  │ 定时任务  │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘   │
└────────┼────────────┼────────────┼────────────┼─────────┘
         │            │            │            │
         └────────────┴─────┬──────┴────────────┘
                            │ REST API / WebSocket
┌───────────────────────────┴─────────────────────────────────┐
│                        后端 (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    API Router Layer                   │   │
│  │  auth | flows | hosts | executions | templates | jobs│   │
│  └────────────────────────┬────────────────────────────┘   │
│  ┌────────────────────────┴────────────────────────────┐   │
│  │                 Service Layer                        │   │
│  │  AnsibleExecutor | Scheduler | WebSocket Manager    │   │
│  └────────────────────────┬────────────────────────────┘   │
│  ┌────────────────────────┴────────────────────────────┐   │
│  │              SQLAlchemy ORM + Asyncpg                │   │
│  └────────────────────────┬────────────────────────────┘   │
└───────────────────────────┼─────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────┴────┐       ┌─────┴─────┐      ┌────┴────┐
    │PostgreSQL│       │   Redis   │      │Ansible  │
    │         │       │           │      │ Runner  │
    └─────────┘       └───────────┘      └─────────┘
```

---

## 三、功能模块详解

### 3.1 用户认证与权限

#### 3.1.1 用户管理
- 用户注册与登录（JWT Token 认证）
- 用户信息管理（用户名、邮箱、部门、角色）
- 密码安全管理

#### 3.1.2 角色权限
| 角色 | 权限说明 |
|------|----------|
| 超级管理员 | 系统全部权限 |
| 普通用户 | 创建和管理自己的流程 |

#### 3.1.3 流程权限
- 支持设置用户对特定流程的执行权限
- 流程所有者可授予其他用户执行权限

### 3.2 主机管理

#### 3.2.1 主机组管理
- 创建/编辑/删除主机组
- 主机组用于对主机进行分类管理

#### 3.2.2 主机管理
| 字段 | 说明 |
|------|------|
| 名称 | 主机显示名称 |
| IP地址 | 主机网络地址 |
| 端口 | SSH 端口，默认 22 |
| 主机类型 | server（服务器）/ service（服务） |
| 服务名称 | 如 nginx、mysql、redis 等 |
| 所属主机组 | 主机所属分组 |
| 认证凭据 | 关联的登录凭据 |
| 主机变量 | JSON 格式的自定义变量 |
| 标签 | 用于分类和筛选 |

#### 3.2.3 认证凭据
| 类型 | 说明 |
|------|------|
| 密码认证 | 用户名 + 密码 |
| SSH Key 认证 | 私钥 + （可选）私钥密码 |

### 3.3 流程编辑器

#### 3.3.1 编辑器界面布局

```
┌────────────────────────────────────────────────────────────┐
│ [返回] [流程名称输入框] [状态标签] │ [放大][缩小][适应] │ [校验][保存][执行] │
├────────────────────────────────────────────────────────────┤
│ [执行进度条]                                                │
├──────────┬─────────────────────────────────────────────────┤
│          │                                                 │
│  节点库   │              画布区域                            │
│          │                                                 │
│ ─ 命令   │     ┌─────┐                                    │
│ ─ 脚本   │     │开始 │                                     │
│ ─ Playbook│    └──┬──┘                                    │
│ ─ 文件   │        │                                       │
│ ─ 循环   │        ▼                                       │
│ ─ 条件   │     ┌─────┐                                    │
│ ─ 等待   │     │节点 │                                     │
│ ─ 通知   │     └─────┘                                    │
│ ─ 注释   │                                                 │
│          │                                                 │
│ 主机选择  │                                                 │
│ [下拉框] │                                                 │
├──────────┴─────────────────────────────────────────────────┤
│                    节点配置面板                              │
│  (选中节点后显示配置表单)                                    │
└────────────────────────────────────────────────────────────┘
```

#### 3.3.2 支持的节点类型

| 节点类型 | 图标颜色 | 说明 | 关键配置 |
|----------|----------|------|----------|
| **开始节点** | 蓝色 | 流程入口点，每个流程有且仅有一个 | 无需配置 |
| **结束节点** | 红色 | 流程结束点，触发流程终止 | 无需配置 |
| **命令节点** | 蓝色 | 执行单个 Ansible 命令 | 命令内容、Sudo 执行、超时时间 |
| **脚本节点** | 绿色 | 执行 Shell/Python 脚本 | 脚本类型、脚本内容、参数 |
| **Playbook节点** | 橙色 | 执行 Ansible Playbook | Playbook 内容/模板、额外变量 |
| **文件节点** | 灰色 | 推送/拉取文件 | 操作类型、源路径、目标路径 |
| **循环节点** | 紫色 | 遍历执行循环体 | 循环类型（次数/数组/主机）、循环变量名 |
| **条件分支** | 红色 | 条件判断分支执行 | 条件表达式（字段/操作符/值） |
| **等待节点** | 灰色 | 延时等待 | 等待秒数 |
| **通知节点** | 橙色 | 发送执行通知 | 通知渠道（邮件/企业微信/钉钉）、收件人、消息模板 |
| **变量节点** | 青色 | 设置流程变量 | 变量定义（key=value 格式） |
| **并行节点** | 青色 | 并行执行多个分支 | 最大并发数、失败策略 |
| **注释节点** | 绿色 | 添加流程说明 | 注释内容（不参与执行） |

#### 3.3.3 节点配置详解

**命令节点配置**
```
- 命令内容: 需要执行的命令，支持变量替换 {{variable}} 或 ${variable}
- Sudo 执行: 是否使用 sudo 权限执行
- 超时时间: 命令执行超时时间（秒）
```

**脚本节点配置**
```
- 脚本类型: Shell / Python / PowerShell
- 脚本内容: 脚本代码内容
- 执行参数: 传递给脚本的参数
- 超时时间: 脚本执行超时时间（秒）
```

**Playbook 节点配置**
```
- Playbook 来源: 选择已保存的模板或直接输入内容
- Playbook 内容: YAML 格式的 Playbook 内容
- 额外变量: extra_vars，格式为 key=value，每行一个
- 超时时间: Playbook 执行超时时间（秒）
```

**循环节点配置**
```
- 循环类型:
  - 固定次数: 指定循环次数
  - 数组: 指定逗号分隔或换行分隔的数组
  - 主机: 从主机列表中选择
- 循环变量名: 每次循环的变量名，默认 item
- 失败策略: continue（继续）/ break（中断）
- 循环体: 包含一个或多个需要循环执行的子节点
```

**条件分支配置**
```
- 条件列表:
  - 字段: prev_node_status / previous_status 或变量名
  - 操作符: ==（等于）/ !=（不等于）
  - 值: 比较的值
- 支持多条件组合判断
```

**通知节点配置**
```
- 通知渠道: email / wecom（企业微信）/ dingtalk（钉钉）
- 收件人: 邮件地址或企业微信/钉钉用户 ID，多个用逗号分隔
- 消息模板: 支持变量替换，变量包括 ${flow_name}、${result}、${start_time}、${end_time}
```

**变量节点配置**
```
- 变量定义: 格式为 key=value，每行一个
- 变量作用域: 当前执行上下文
- 变量提取: 支持从命令/脚本/Playbook 输出中自动提取变量
```

#### 3.3.4 变量系统

**变量语法**
- `{{variable_name}}` - 双花括号语法
- `${variable_name}` - 美元符号语法

**变量来源**
1. 流程执行时传入的变量
2. 变量节点设置的变量
3. 从执行输出中提取的变量
4. 主机变量

**变量作用域**
- 全局变量：在整个流程执行过程中可用
- 循环变量：在循环体内可用，包含当前循环项的值

### 3.4 执行管理

#### 3.4.1 执行流程

```
用户点击执行
     │
     ▼
API 创建执行记录 (pending)
     │
     ▼
加入执行队列
     │
     ▼
异步执行器取出任务
     │
     ▼
更新状态为 running
     │
     ▼
按拓扑顺序执行节点
     │
     ├──► 命令节点 ──► SSH 执行命令
     ├──► 脚本节点 ──► SSH 执行脚本
     ├──► Playbook ──► Ansible Runner 执行
     ├──► 循环节点 ──► 遍历执行循环体
     ├──► 条件分支 ──► 条件判断
     └──► ...其他节点
     │
     ▼
更新执行状态 (success/failed/stopped)
     │
     ▼
发送通知（如配置）
```

#### 3.4.2 执行状态

| 状态 | 说明 |
|------|------|
| pending | 等待执行 |
| running | 执行中 |
| success | 执行成功 |
| failed | 执行失败 |
| stopped | 已停止 |

#### 3.4.3 实时监控

**WebSocket 推送事件**
- `node_update`: 节点状态更新
- `execution_update`: 执行状态更新
- `log`: 执行日志推送

**推送数据格式**
```json
{
  "type": "node_update",
  "node_id": "node_123",
  "status": "running",
  "output": "正在执行命令..."
}
```

#### 3.4.4 执行记录

- 记录每次执行的完整信息
- 节点执行详情（输入、输出、错误信息）
- 执行时间统计
- 支持查看历史执行记录

### 3.5 模板管理

#### 3.5.1 Playbook 模板

| 字段 | 说明 |
|------|------|
| 模板名称 | 模板显示名称 |
| 描述 | 模板说明 |
| 内容 | YAML 格式的 Playbook 内容 |
| 分类 | 模板分类（如系统管理、应用部署等） |
| 变量定义 | 模板支持的变量 schema |
| 标签 | 用于分类和搜索 |
| 公开性 | 是否公开（其他用户可用） |

#### 3.5.2 脚本模板

| 字段 | 说明 |
|------|------|
| 模板名称 | 模板显示名称 |
| 脚本类型 | Shell / Python / PowerShell |
| 内容 | 脚本代码 |
| 分类 | 模板分类 |
| 标签 | 用于分类和搜索 |

### 3.6 定时任务

#### 3.6.1 Cron 表达式

支持标准 5 位 Cron 表达式：
```
┌───────────── 分钟 (0-59)
│ ┌───────────── 小时 (0-23)
│ │ ┌───────────── 日 (1-31)
│ │ │ ┌───────────── 月 (1-12)
│ │ │ │ ┌───────────── 星期 (0-6, 0=周日)
│ │ │ │ │
* * * * *
```

**常用表达式示例**
| 表达式 | 说明 |
|--------|------|
| `0 * * * *` | 每小时整点执行 |
| `0 9 * * *` | 每天上午9点执行 |
| `0 9 * * 1-5` | 工作日上午9点执行 |
| `*/5 * * * *` | 每5分钟执行 |
| `0 0 * * 0` | 每周日凌晨执行 |

#### 3.6.2 定时任务配置

| 字段 | 说明 |
|------|------|
| 任务名称 | 定时任务名称 |
| 关联流程 | 关联的自动化流程 |
| Cron 表达式 | 执行时间规则 |
| 描述 | 任务说明 |
| 启用状态 | 是否启用定时执行 |
| 下次执行时间 | 自动计算 |
| 上次执行时间 | 最近一次执行时间 |
| 上次执行ID | 最近一次执行记录 ID |

### 3.7 仪表盘

#### 3.7.1 统计数据

- **流程统计**: 流程总数、草稿/已发布数量
- **执行统计**: 总执行次数、今日执行次数、成功/失败率
- **执行趋势**: 每日执行次数趋势图

#### 3.7.2 最近执行

- 显示最近执行的流程列表
- 支持按状态筛选（运行中/成功/失败）

---

## 四、API 接口

### 4.1 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/register | 用户注册 |
| GET | /api/auth/me | 获取当前用户信息 |

### 4.2 流程接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/flows | 获取流程列表 |
| POST | /api/flows | 创建流程 |
| GET | /api/flows/{flow_id} | 获取流程详情 |
| PUT | /api/flows/{flow_id} | 更新流程 |
| DELETE | /api/flows/{flow_id} | 删除流程 |
| PUT | /api/flows/{flow_id}/design | 保存流程设计 |
| POST | /api/flows/{flow_id}/execute | 执行流程 |
| POST | /api/flows/{flow_id}/publish | 发布流程 |
| POST | /api/flows/{flow_id}/unpublish | 取消发布 |

### 4.3 执行接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/executions | 获取执行记录列表 |
| GET | /api/executions/{exec_id} | 获取执行详情 |
| POST | /api/executions/{exec_id}/stop | 停止执行 |
| GET | /api/executions/{exec_id}/nodes | 获取节点执行记录 |
| GET | /api/executions/{exec_id}/logs | 获取执行日志 |

### 4.4 主机接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/hosts | 获取主机列表 |
| POST | /api/hosts | 创建主机 |
| GET | /api/hosts/{host_id} | 获取主机详情 |
| PUT | /api/hosts/{host_id} | 更新主机 |
| DELETE | /api/hosts/{host_id} | 删除主机 |
| GET | /api/hosts/groups | 获取主机组列表 |
| POST | /api/hosts/groups | 创建主机组 |
| PUT | /api/hosts/groups/{group_id} | 更新主机组 |
| DELETE | /api/hosts/groups/{group_id} | 删除主机组 |

### 4.5 定时任务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/scheduled-jobs | 获取定时任务列表 |
| POST | /api/scheduled-jobs | 创建定时任务 |
| GET | /api/scheduled-jobs/{job_id} | 获取定时任务详情 |
| PUT | /api/scheduled-jobs/{job_id} | 更新定时任务 |
| DELETE | /api/scheduled-jobs/{job_id} | 删除定时任务 |
| POST | /api/scheduled-jobs/{job_id}/enable | 启用定时任务 |
| POST | /api/scheduled-jobs/{job_id}/disable | 禁用定时任务 |

### 4.6 模板接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/playbooks | 获取 Playbook 模板列表 |
| POST | /api/playbooks | 创建 Playbook 模板 |
| GET | /api/playbooks/{id} | 获取模板详情 |
| PUT | /api/playbooks/{id} | 更新模板 |
| DELETE | /api/playbooks/{id} | 删除模板 |
| GET | /api/scripts | 获取脚本模板列表 |
| POST | /api/scripts | 创建脚本模板 |

### 4.7 WebSocket 接口

**连接地址**: `ws://host:port/ws/execution/{execution_id}`

**推送消息类型**
- `node_update`: 节点执行状态更新
- `execution_update`: 整体执行状态更新
- `log`: 执行日志

---

## 五、数据模型

### 5.1 核心实体

```
┌─────────────┐       ┌──────────────────┐
│    User     │──────<│   UserFlowPermission│
└─────────────┘       └──────────────────┘
       │
       │ owns
       ▼
┌─────────────┐       ┌──────────────────┐
│    Flow     │──────<│   FlowExecution   │
└─────────────┘       └──────────────────┘
       │                     │
       │                     │
       │              ┌──────┴──────┐
       │              │             │
       │              ▼             ▼
       │       ┌────────────┐  ┌─────────────┐
       └──────>│NodeExecution│  │ExecutionLog │
               └────────────┘  └─────────────┘
                     │
                     ▼
              ┌────────────┐
              │    Host    │
              └────────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
       ┌────────────┐  ┌────────────┐
       │ HostGroup  │  │ Credential │
       └────────────┘  └────────────┘

┌─────────────┐       ┌──────────────────┐
│ScheduledJob │──────<│  FlowExecution   │
└─────────────┘       └──────────────────┘
```

### 5.2 主要数据表

| 表名 | 说明 |
|------|------|
| users | 用户表 |
| roles | 角色表 |
| user_flow_permissions | 用户-流程权限关联表 |
| flows | 流程表 |
| flow_executions | 执行记录表 |
| node_executions | 节点执行记录表 |
| execution_logs | 执行日志表 |
| hosts | 主机表 |
| host_groups | 主机组表 |
| credentials | 认证凭据表 |
| playbook_templates | Playbook 模板表 |
| script_templates | 脚本模板表 |
| scheduled_jobs | 定时任务表 |
| system_settings | 系统设置表 |

---

## 六、使用示例

### 6.1 创建简单的系统巡检流程

**步骤 1: 创建流程**
1. 点击"新建流程"按钮
2. 输入流程名称："服务器巡检"
3. 选择"保存"

**步骤 2: 添加节点**
1. 从左侧节点库拖拽"开始节点"到画布
2. 拖拽"Playbook 节点"连接到开始节点
3. 配置 Playbook 内容：

```yaml
- hosts: all
  gather_facts: yes
  tasks:
    - name: 获取 CPU 使用率
      shell: |
        cpu_idle=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}')
        echo "cpu_usage: $((100-${cpu_idle%.*}))"
        
    - name: 获取内存使用率
      shell: |
        free -m | awk 'NR==2{printf "memory_usage: %s/%sMB (%.2f%%)", $3, $2, $3*100/$2 }'
        
    - name: 获取磁盘使用率
      shell: df -h / | awk 'NR==2{print "disk_usage: " $5}'
```

4. 拖拽"通知节点"连接到 Playbook 节点
5. 配置通知：邮件发送给 admin@example.com

**步骤 3: 配置主机和凭据**
1. 在"主机管理"创建主机组"巡检组"
2. 添加主机，设置 IP 地址和 SSH 凭据
3. 在流程编辑器中选择主机

**步骤 4: 测试执行**
1. 点击"执行"按钮
2. 观察实时执行状态
3. 查看节点输出和通知邮件

### 6.2 创建批量部署流程

**场景**: 同时部署应用到多台服务器

**步骤 1: 添加节点**
1. 开始节点
2. Playbook 节点（部署应用）
3. 循环节点（遍历服务器列表）
4. 条件分支（检查部署结果）
5. 通知节点（发送部署结果）

**步骤 2: 配置循环**
- 循环类型：主机
- 失败策略：continue（单台失败不影响其他）

**步骤 3: 配置条件**
- 检查上一节点状态
- 失败时发送告警通知

### 6.3 创建定时备份流程

**步骤 1: 创建定时任务**
1. 创建备份流程
2. 包含以下节点：
   - 开始节点
   - 脚本节点（执行备份命令）
   - 文件节点（推送备份文件到存储）
   - 通知节点（发送备份结果）

**步骤 2: 配置定时**
1. 进入"定时任务"页面
2. 点击"新建定时任务"
3. 选择关联流程
4. 设置 Cron 表达式：`0 2 * * *`（每天凌晨2点）
5. 点击"保存并启用"

---

## 七、部署说明

### 7.1 Docker Compose 部署

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: automation_platform
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/automation_platform
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
```

### 7.2 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_URL | PostgreSQL 连接地址 | postgresql+asyncpg://postgres:postgres@postgres:5432/automation_platform |
| REDIS_URL | Redis 连接地址 | redis://redis:6379/0 |
| DEBUG | 调试模式 | true |
| SECRET_KEY | JWT 密钥 | auto-generated |

---

## 八、默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 超级管理员 |

---

## 九、常见问题

### Q1: 执行时提示 "ansible-playbook: No such file or directory"
**A**: 确保 Ansible 已正确安装，可通过 `/usr/local/bin/ansible-playbook` 或 `/usr/bin/ansible-playbook` 访问。

### Q2: SSH 连接失败
**A**: 
1. 检查主机 IP 和端口是否正确
2. 确认凭据（用户名/密码或私钥）正确
3. 确认网络可达（防火墙、安全组）

### Q3: 变量未正确替换
**A**: 
1. 检查变量语法是否正确（`{{var}}` 或 `${var}}`)
2. 确认变量已在变量节点或执行时定义
3. 变量节点必须在使用变量的节点之前执行

### Q4: 条件分支判断错误
**A**: 条件判断基于 `prev_node_status`，上一节点执行成功返回 `success`，失败返回 `failed`。

### Q5: 循环节点不执行
**A**: 检查循环项配置：
1. 固定次数：确认 `loop_count > 0`
2. 数组：确认 `loop_items` 有值
3. 主机：确认已添加主机

---

## 十、版本信息

- **当前版本**: 1.0.0
- **最后更新**: 2026-04-18

---

## 十一、高级功能

### 11.1 变量提取系统

系统支持从命令、脚本、Playbook 输出中自动提取变量：

**提取规则**
- 格式: `变量名=值`
- 每行一个变量
- 支持多行输出

**示例**

脚本输出:
```
app_version=1.2.3
deploy_status=success
server_count=5
```

提取后在后续节点可使用:
- `{{app_version}}` → 1.2.3
- `{{deploy_status}}` → success
- `{{server_count}}` → 5

### 11.2 SSH 连接管理

**连接方式**
- **Paramiko**: Python 原生 SSH 库，支持密码和密钥认证
- **SSH Common Args**: 支持自定义 SSH 参数

**连接参数**
```yaml
ansible_user: username
ansible_password: password  # 密码认证
ansible_connection: paramiko
ansible_ssh_common_args: -o StrictHostKeyChecking=no
```

### 11.3 Ansible 执行器

执行器核心功能:
1. 生成临时 inventory 文件
2. 处理变量替换
3. 执行命令/脚本/Playbook
4. 捕获输出和错误
5. 更新执行状态
6. WebSocket 实时推送

**Ansible 路径配置**
```python
ANSIBLE_PLAYBOOK_PATH = "/usr/local/bin/ansible-playbook"
ANSIBLE_PATH = "/usr/local/bin/ansible"
```

---

## 十二、安全说明

### 12.1 密码安全

- 密码使用哈希存储
- 敏感信息不记录日志
- SSH 私钥加密传输

### 12.2 JWT 安全

- Token 有时效性
- 支持 Token 刷新
- 敏感操作需重新验证

### 12.3 权限控制

- 流程级别的权限控制
- 操作审计日志
- 重要操作需要确认

---

## 十三、性能优化

### 13.1 数据库优化

- 异步数据库操作
- 连接池管理
- 索引优化

### 13.2 执行优化

- 异步任务队列
- 并行节点支持
- 执行状态缓存

### 13.3 前端优化

- 组件懒加载
- 请求缓存
- WebSocket 长连接

---

## 十四、开发指南

### 14.1 添加新节点类型

**前端部分**

1. 在 `stores/flow.js` 添加节点定义:
```javascript
custom: {
  label: '自定义节点',
  icon: 'Setting',
  color: '#909399',
  description: '执行自定义任务'
}
```

2. 在 `components/FlowEditor/nodes/` 创建节点组件

3. 在 `NodeConfigPanel.vue` 添加配置表单

**后端部分**

在 `services/executor.py` 的 `_execute_node` 方法添加:
```python
elif node_type == "custom":
    output = await self._execute_custom(
        node_config.get("command"),
        node_config.get("timeout", 60)
    )
```

### 14.2 添加新的通知渠道

在 `services/executor.py` 的 `_send_notification` 方法添加:
```python
elif channel == "custom":
    # 实现自定义通知逻辑
    await self._send_custom_notification(recipients, subject, message)
```

---

## 十五、故障排查

### 15.1 常见错误及解决方案

| 错误信息 | 可能原因 | 解决方案 |
|----------|----------|----------|
| ansible-playbook: No such file or directory | Ansible 未安装或路径错误 | 检查 Ansible 安装位置 |
| Connection refused | SSH 端口未开放 | 检查防火墙和 SSH 服务 |
| Authentication failed | 用户名或密码错误 | 验证凭据配置 |
| Permission denied | 权限不足 | 使用 sudo 或提升权限 |
| Timeout | 网络延迟或命令执行慢 | 增加超时时间 |

### 15.2 日志分析

```bash
# 查看详细执行日志
docker logs automation-backend --tail 200 | grep -E "ERROR|Exception|execute_flow"

# 查看特定执行记录日志
docker logs automation-backend 2>&1 | grep "execution_id"
```

### 15.3 调试模式

启用调试模式查看更多日志:
```bash
# docker-compose.yml
environment:
  DEBUG: "true"
```

---

## 十六、联系方式

- **技术支持**: 如有问题请提交 Issue
- **文档更新**: 持续更新中
- **版本下载**: GitHub Releases

---

*本文档由 CodeBuddy AI 辅助生成*
*文档版本: 2.0*
*最后更新: 2026-04-18*

# Ansible Automation Platform

A visual drag-and-drop automation platform for IT operations. No YAML required - design automation workflows by dragging nodes, connecting them, and configuring parameters.

---

## Features

- **Visual Flow Editor**: Design automation workflows with drag-and-drop nodes
- **Multiple Node Types**: Command, Script, Playbook, Loop, Conditional Branch, Wait, Notify, and more
- **Host Management**: Centralized management of target hosts and authentication credentials
- **Real-time Execution Monitoring**: WebSocket-based live status and log streaming
- **Scheduled Tasks**: Cron expression support for complex scheduling strategies
- **Multi-channel Notifications**: Email, WeChat Work, DingTalk support

---

## Tech Stack

| Layer | Technology | Description |
|-------|------------|-------------|
| Frontend | Vue 3 + Vite 4 | Modern frontend framework |
| UI Components | Element Plus | Enterprise Vue 3 component library |
| Flow Editor | Vue Flow | Visual workflow editor |
| State Management | Pinia | Official Vue 3 state management |
| Backend | FastAPI | High-performance Python web framework |
| Database | PostgreSQL 15+ | Relational database |
| Async Tasks | Redis + asyncio | Task queue and caching |
| Scheduler | APScheduler | Python scheduling library |
| Automation Engine | Ansible Runner | Ansible execution engine |
| Real-time | WebSocket | Bidirectional browser-server communication |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Flow   │  │   Host   │  │Execution │  │ Scheduler│   │
│  │  Editor  │  │ Manager  │  │ Monitor  │  │          │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘   │
└────────┼────────────┼─────────────┼─────────────┼─────────┘
         │            │             │             │
         └────────────┴──────┬──────┴─────────────┘
                             │ REST API / WebSocket
┌────────────────────────────┴──────────────────────────────┐
│                        Backend (FastAPI)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    API Router Layer                   │  │
│  │  auth | flows | hosts | executions | templates | jobs│  │
│  └──────────────────────────┬───────────────────────────┘  │
│  ┌───────────────────────────┴───────────────────────────┐  │
│  │                 Service Layer                           │  │
│  │  AnsibleExecutor | Scheduler | WebSocket Manager        │  │
│  └──────────────────────────┬───────────────────────────┘  │
│  ┌───────────────────────────┴───────────────────────────┐  │
│  │              SQLAlchemy ORM + Asyncpg                   │  │
│  └──────────────────────────┬───────────────────────────┘  │
└─────────────────────────────┼─────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    ┌────┴────┐         ┌─────┴─────┐        ┌────┴────┐
    │PostgreSQL│         │   Redis   │        │ Ansible │
    │         │         │           │        │ Runner  │
    └─────────┘         └───────────┘        └─────────┘
```

---

## Supported Node Types

| Node Type | Color | Description |
|-----------|-------|-------------|
| **Start** | Blue | Flow entry point (one per flow) |
| **End** | Red | Flow termination point |
| **Command** | Blue | Execute single Ansible command |
| **Script** | Green | Execute Shell/Python/PowerShell script |
| **Playbook** | Orange | Execute Ansible Playbook |
| **File** | Gray | Push/pull files |
| **Loop** | Purple | Iterate through items (count/array/hosts) |
| **Condition** | Red | Conditional branching |
| **Wait** | Gray | Delay for specified seconds |
| **Notify** | Orange | Send notifications |
| **Variable** | Cyan | Set flow variables |
| **Parallel** | Cyan | Execute branches in parallel |
| **Comment** | Green | Add annotations (not executed) |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Ansible (on host for local execution)

### Installation

```bash
# Clone the repository
git clone https://github.com/lvhongming/automation-platform.git
cd automation-platform/sourcecode

# Start with Docker Compose
docker-compose up -d

# Initialize database
docker-compose exec backend python scripts/init_db.py

# Create admin user
docker-compose exec backend python scripts/create_admin.py
```

### Default Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Super Admin |

Access the platform at: http://localhost:3000

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | User login |
| POST | /api/auth/register | User registration |
| GET | /api/auth/me | Get current user info |

### Flows
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/flows | List flows |
| POST | /api/flows | Create flow |
| GET | /api/flows/{id} | Get flow details |
| PUT | /api/flows/{id} | Update flow |
| DELETE | /api/flows/{id} | Delete flow |
| POST | /api/flows/{id}/execute | Execute flow |
| POST | /api/flows/{id}/publish | Publish flow |

### Executions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/executions | List execution records |
| GET | /api/executions/{id} | Get execution details |
| POST | /api/executions/{id}/stop | Stop execution |
| GET | /api/executions/{id}/logs | Get execution logs |

### Hosts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/hosts | List hosts |
| POST | /api/hosts | Create host |
| PUT | /api/hosts/{id} | Update host |
| DELETE | /api/hosts/{id} | Delete host |

### Scheduled Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/scheduled-jobs | List scheduled jobs |
| POST | /api/scheduled-jobs | Create scheduled job |
| PUT | /api/scheduled-jobs/{id} | Update scheduled job |
| DELETE | /api/scheduled-jobs/{id} | Delete scheduled job |
| POST | /api/scheduled-jobs/{id}/enable | Enable job |
| POST | /api/scheduled-jobs/{id}/disable | Disable job |

### WebSocket
Connect to: `ws://host:port/ws/execution/{execution_id}`

**Event Types:**
- `node_update`: Node execution status update
- `execution_update`: Overall execution status update
- `log`: Execution logs

---

## Variable System

**Syntax:**
- `{{variable_name}}` - Double curly braces
- `${variable_name}` - Dollar sign syntax

**Sources:**
1. Variables passed during execution
2. Variables set by Variable nodes
3. Variables extracted from execution output
4. Host variables

**Output Extraction:**
```
app_version=1.2.3
deploy_status=success
```
Extract to use as `{{app_version}}`, `{{deploy_status}}`

---

## Cron Expression Examples

| Expression | Description |
|------------|-------------|
| `0 * * * *` | Every hour at minute 0 |
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `*/5 * * * *` | Every 5 minutes |
| `0 0 * * 0` | Every Sunday at midnight |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection | postgresql+asyncpg://postgres:postgres@postgres:5432/automation_platform |
| REDIS_URL | Redis connection | redis://redis:6379/0 |
| DEBUG | Debug mode | true |
| SECRET_KEY | JWT secret key | auto-generated |

---

## Project Structure

```
sourcecode/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Core config, security
│   │   ├── db/           # Database connection
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic
│   ├── scripts/          # Utility scripts
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # Vue components
│   │   ├── pages/        # Page components
│   │   ├── services/    # API services
│   │   ├── stores/      # Pinia stores
│   │   └── styles/      # SCSS styles
│   └── package.json
├── docs/                 # Documentation
├── scripts/              # Shell scripts
├── docker-compose.yml
├── Dockerfile.prod
├── install.sh
└── README.md
```

---

## Troubleshooting

### Q: "ansible-playbook: No such file or directory"
**A**: Ensure Ansible is installed and accessible at `/usr/local/bin/ansible-playbook` or `/usr/bin/ansible-playbook`.

### Q: SSH connection failed
**A**: 
1. Check host IP and port
2. Verify credentials (username/password or private key)
3. Confirm network accessibility (firewall, security groups)

### Q: Variables not replaced correctly
**A**:
1. Check variable syntax (`{{var}}` or `${var}}`)
2. Ensure variable is defined in Variable node or at execution time
3. Variable node must execute before the node using the variable

### Q: Condition branch not working
**A**: Condition checks `prev_node_status` - success returns `success`, failure returns `failed`.

### Q: Loop node not executing
**A**: Check loop configuration:
1. Fixed count: ensure `loop_count > 0`
2. Array: ensure `loop_items` has values
3. Hosts: ensure hosts are added

---

## Development

### Adding a New Node Type

**Frontend:**
1. Add node definition in `stores/flow.js`
2. Create node component in `components/FlowEditor/nodes/`
3. Add config form in `NodeConfigPanel.vue`

**Backend:**
Add execution logic in `services/executor.py` `_execute_node` method:
```python
elif node_type == "custom":
    output = await self._execute_custom(
        node_config.get("command"),
        node_config.get("timeout", 60)
    )
```

---

## License

MIT License

---

## Contact

- **Technical Support**: Submit an Issue on GitHub
- **Documentation**: Continuously updated
- **Releases**: GitHub Releases

---

*Generated with CodeBuddy AI*
*Version: 2.0*
*Last Updated: 2026-04-18*

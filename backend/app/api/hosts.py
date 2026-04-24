from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import json

from app.db.database import get_db
from app.models.host import Host, HostGroup, Credential
from app.models.user import User
from app.schemas.host import (
    HostResponse, HostCreate, HostUpdate,
    HostGroupResponse, HostGroupCreate, HostGroupUpdate,
    CredentialResponse, CredentialCreate, CredentialUpdate,
    HostConnectionTest, CredentialDetailResponse
)
from app.api.deps import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/hosts", tags=["主机管理"])


# ============ 凭据管理 ============

@router.get("/credentials", response_model=List[CredentialDetailResponse])
async def list_credentials(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取凭据列表"""
    result = await db.execute(select(Credential).order_by(Credential.name))
    credentials = result.scalars().all()

    # 获取每个凭据关联的主机数量
    responses = []
    for cred in credentials:
        host_count_result = await db.execute(
            select(func.count(Host.id)).where(Host.credential_id == cred.id)
        )
        hosts_count = host_count_result.scalar() or 0
        resp = CredentialDetailResponse.model_validate(cred)
        resp.hosts_count = hosts_count
        responses.append(resp)

    return responses


@router.post("/credentials", response_model=CredentialResponse)
async def create_credential(
    cred_data: CredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建凭据"""
    # 检查名称是否重复
    result = await db.execute(
        select(Credential).where(Credential.name == cred_data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="凭据名称已存在")

    cred = Credential(**cred_data.model_dump())
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return CredentialResponse.model_validate(cred)


@router.get("/credentials/{credential_id}", response_model=CredentialDetailResponse)
async def get_credential(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取凭据详情"""
    result = await db.execute(select(Credential).where(Credential.id == credential_id))
    cred = result.scalar_one_or_none()

    if not cred:
        raise HTTPException(status_code=404, detail="凭据不存在")

    return CredentialDetailResponse.model_validate(cred)


@router.delete("/credentials/{credential_id}")
async def delete_credential(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除凭据"""
    result = await db.execute(select(Credential).where(Credential.id == credential_id))
    cred = result.scalar_one_or_none()

    if not cred:
        raise HTTPException(status_code=404, detail="凭据不存在")

    await db.delete(cred)
    await db.commit()
    return {"message": "删除成功"}


# ============ 主机组 ============

@router.get("/groups", response_model=List[HostGroupResponse])
async def list_host_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取主机组列表"""
    result = await db.execute(select(HostGroup).order_by(HostGroup.name))
    groups = result.scalars().all()
    return [HostGroupResponse.model_validate(g) for g in groups]


@router.post("/groups", response_model=HostGroupResponse)
async def create_host_group(
    group_data: HostGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建主机组"""
    # 检查名称是否重复
    result = await db.execute(
        select(HostGroup).where(HostGroup.name == group_data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="主机组名称已存在")

    group = HostGroup(**group_data.model_dump())
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return HostGroupResponse.model_validate(group)


@router.put("/groups/{group_id}", response_model=HostGroupResponse)
async def update_host_group(
    group_id: str,
    group_data: HostGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新主机组"""
    result = await db.execute(select(HostGroup).where(HostGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="主机组不存在")

    for key, value in group_data.model_dump(exclude_unset=True).items():
        setattr(group, key, value)

    await db.commit()
    await db.refresh(group)
    return HostGroupResponse.model_validate(group)


@router.delete("/groups/{group_id}")
async def delete_host_group(
    group_id: str,
    move_hosts: bool = Query(False, description="是否将主机移至未分组"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除主机组"""
    result = await db.execute(select(HostGroup).where(HostGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="主机组不存在")

    # 检查是否有主机
    host_result = await db.execute(
        select(Host).where(Host.group_id == group_id)
    )
    hosts = host_result.scalars().all()
    
    if hosts and not move_hosts:
        raise HTTPException(status_code=400, detail="该主机组下有主机，请确认是否将主机移至未分组")
    
    # 将主机移至未分组
    for host in hosts:
        host.group_id = None
    
    await db.delete(group)
    await db.commit()
    return {"message": "删除成功", "moved_hosts": len(hosts)}


# ============ 主机模板 ============

@router.get("/template")
async def download_import_template(
    current_user: User = Depends(get_current_user)
):
    """下载主机导入模板（CSV 格式）"""
    csv_content = """name,ip_address,port,credential_name,group,tags,description
web-01,192.168.1.101,22,,web-servers,web;prod,Web服务器01
web-02,192.168.1.102,22,my-credential,web-servers,web;prod,Web服务器02
db-01,192.168.1.201,22,db-credential,database,db;prod,数据库服务器
"""

    return {
        "content": csv_content,
        "filename": "hosts_import_template.csv",
        "description": {
            "name": "主机名称（必填，唯一）",
            "ip_address": "IP地址（必填）",
            "port": "端口号（默认22）",
            "credential_name": "认证凭据名称（可选，需先在凭据管理中添加）",
            "group": "主机组名称（可选，不存在会自动创建）",
            "tags": "标签（可选，多个用分号分隔）",
            "description": "描述（可选）"
        }
    }


@router.get("/export")
async def export_inventory(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出主机（CSV 格式，与导入模板一致）"""
    # 先获取所有凭据
    creds_result = await db.execute(select(Credential))
    credentials = {c.id: c.name for c in creds_result.scalars().all()}

    # 获取所有主机组
    groups_result = await db.execute(select(HostGroup))
    groups = {g.id: g.name for g in groups_result.scalars().all()}

    # 获取所有主机
    result = await db.execute(select(Host))
    hosts = result.scalars().all()

    # 生成 CSV 格式
    csv_lines = ["name,ip_address,port,credential_name,group,tags,description"]
    for host in hosts:
        credential_name = credentials.get(host.credential_id, '')
        group_name = groups.get(host.group_id, '')
        tags_str = ';'.join(host.tags) if host.tags else ''
        description = host.description or ''
        csv_lines.append(f"{host.name},{host.ip_address},{host.port},{credential_name},{group_name},{tags_str},{description}")

    content = '\n'.join(csv_lines)
    return {"content": content, "filename": "hosts_export.csv"}


@router.post("/{host_id}/move")
async def move_host(
    host_id: str,
    target_group_id: Optional[str] = Query(None, description="目标主机组ID，为空则移至未分组"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """移动主机到指定组"""
    if not host_id:
        raise HTTPException(status_code=400, detail="主机ID不能为空")
    
    # 检查主机存在
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if host is None:
        raise HTTPException(status_code=404, detail="主机不存在")
    
    # 检查目标组存在（如果不是移至未分组）
    if target_group_id:
        group_result = await db.execute(select(HostGroup).where(HostGroup.id == target_group_id))
        if group_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="目标主机组不存在")
    
    # 更新主机组
    host.group_id = target_group_id
    await db.commit()
    await db.refresh(host)
    
    return {"message": "移动成功"}


# ============ 主机 ============

@router.get("", response_model=dict)
async def list_hosts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    group_id: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    tags: Optional[str] = None,  # 标签搜索，逗号分隔
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取主机列表"""
    query = select(Host)
    count_query = select(func.count(Host.id))

    if group_id:
        query = query.where(Host.group_id == group_id)
        count_query = count_query.where(Host.group_id == group_id)

    if status:
        query = query.where(Host.status == status)
        count_query = count_query.where(Host.status == status)

    if keyword:
        query = query.where(
            (Host.name.contains(keyword)) | (Host.ip_address.contains(keyword))
        )
        count_query = count_query.where(
            (Host.name.contains(keyword)) | (Host.ip_address.contains(keyword))
        )

    if tags:
        # 支持多标签搜索，逗号分隔
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        for tag in tag_list:
            # JSON 数组中包含指定标签
            query = query.where(Host.tags.contains(tag))
            count_query = count_query.where(Host.tags.contains(tag))

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    hosts = result.scalars().all()

    # 获取主机组信息
    groups_result = await db.execute(select(HostGroup))
    groups = {g.id: g for g in groups_result.scalars().all()}

    items = []
    for host in hosts:
        item = HostResponse.model_validate(host)
        if host.group_id and host.group_id in groups:
            item.group = HostGroupResponse.model_validate(groups[host.group_id])
        items.append(item)

    return {"total": total, "items": items}


@router.get("/{host_id}", response_model=HostResponse)
async def get_host(
    host_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取主机详情"""
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    return HostResponse.model_validate(host)


@router.post("", response_model=HostResponse)
async def create_host(
    host_data: HostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建主机"""
    # 检查名称是否重复
    result = await db.execute(
        select(Host).where(Host.name == host_data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="主机名称已存在")

    # 验证主机组
    if host_data.group_id:
        group_result = await db.execute(
            select(HostGroup).where(HostGroup.id == host_data.group_id)
        )
        if not group_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="主机组不存在")

    host = Host(**host_data.model_dump())
    db.add(host)
    await db.commit()
    await db.refresh(host)

    # 手动构建响应，避免异步关系加载问题
    response = build_host_response(host, db)

    return response


@router.put("/{host_id}", response_model=HostResponse)
async def update_host(
    host_id: str,
    host_data: HostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新主机"""
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    for key, value in host_data.model_dump(exclude_unset=True).items():
        setattr(host, key, value)

    await db.commit()
    await db.refresh(host)

    # 手动构建响应，避免异步关系加载问题
    response = build_host_response(host, db)

    return response


def build_host_response(host: Host, db: AsyncSession) -> HostResponse:
    """构建主机响应，手动处理关联数据"""
    # 提取主机数据为字典
    host_data = {
        "id": host.id,
        "name": host.name,
        "ip_address": host.ip_address,
        "port": host.port,
        "host_type": host.host_type,
        "service_name": host.service_name,
        "description": host.description,
        "group_id": host.group_id,
        "credential_id": host.credential_id,
        "variables": host.variables or {},
        "tags": host.tags or [],
        "status": host.status,
        "created_at": host.created_at,
        "updated_at": host.updated_at,
    }

    response = HostResponse.model_construct(**host_data)
    return response


@router.delete("/{host_id}")
async def delete_host(
    host_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除主机"""
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    await db.delete(host)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/{host_id}/test-connection", response_model=HostConnectionTest)
async def test_host_connection(
    host_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试主机 SSH 连接"""
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()

    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    # 获取凭据
    credential = None
    if host.credential_id:
        cred_result = await db.execute(select(Credential).where(Credential.id == host.credential_id))
        credential = cred_result.scalar_one_or_none()

    if not credential:
        return HostConnectionTest(
            success=False,
            message="主机未配置认证凭据，请先配置凭据"
        )

    if not credential.username:
        return HostConnectionTest(
            success=False,
            message="凭据中未配置用户名"
        )

    # 使用 paramiko 测试 SSH 连接
    import time
    import paramiko
    from paramiko import SSHClient, AutoAddPolicy

    start_time = time.time()
    try:
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())

        connect_kwargs = {
            'hostname': host.ip_address,
            'port': host.port,
            'username': credential.username,
            'timeout': 10,
            'look_for_keys': False,
            'allow_agent': False
        }

        if credential.type == 'password' and credential.password:
            connect_kwargs['password'] = credential.password
        elif credential.type == 'ssh_key' and credential.private_key:
            try:
                # 尝试解析私钥
                from io import StringIO
                key_io = StringIO(credential.private_key)
                if credential.passphrase:
                    private_key = paramiko.RSAKey.from_private_key(key_io, password=credential.passphrase)
                else:
                    private_key = paramiko.RSAKey.from_private_key(key_io)
                connect_kwargs['pkey'] = private_key
            except paramiko.SSHException:
                # 可能是 ED25519 密钥
                try:
                    from io import StringIO
                    key_io = StringIO(credential.private_key)
                    if credential.passphrase:
                        private_key = paramiko.Ed25519Key.from_private_key(key_io, password=credential.passphrase)
                    else:
                        private_key = paramiko.Ed25519Key.from_private_key(key_io)
                    connect_kwargs['pkey'] = private_key
                except paramiko.SSHException:
                    # 尝试 ECDSA
                    from io import StringIO
                    key_io = StringIO(credential.private_key)
                    if credential.passphrase:
                        private_key = paramiko.ECDSAKey.from_private_key(key_io, password=credential.passphrase)
                    else:
                        private_key = paramiko.ECDSAKey.from_private_key(key_io)
                    connect_kwargs['pkey'] = private_key

        ssh.connect(**connect_kwargs)

        # 连接成功，尝试执行一个简单命令验证
        stdin, stdout, stderr = ssh.exec_command('echo OK', timeout=5)
        output = stdout.read().decode().strip()
        ssh.close()

        response_time = (time.time() - start_time) * 1000

        if output == 'OK':
            return HostConnectionTest(
                success=True,
                message=f"SSH 连接成功 ({credential.username}@{host.ip_address})",
                response_time=round(response_time, 2)
            )
        else:
            return HostConnectionTest(
                success=False,
                message="连接成功但命令执行失败"
            )

    except paramiko.AuthenticationException as e:
        return HostConnectionTest(
            success=False,
            message=f"认证失败: 用户名或密码/密钥错误"
        )
    except paramiko.SSHException as e:
        return HostConnectionTest(
            success=False,
            message=f"SSH 连接失败: {str(e)}"
        )
    except socket.timeout:
        return HostConnectionTest(
            success=False,
            message=f"连接超时 ({host.ip_address}:{host.port})"
        )
    except socket.error as e:
        return HostConnectionTest(
            success=False,
            message=f"无法连接到 {host.ip_address}:{host.port} - {str(e)}"
        )
    except Exception as e:
        return HostConnectionTest(
            success=False,
            message=f"连接错误: {str(e)}"
        )


@router.post("/import")
async def import_inventory(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导入主机（支持 CSV/INI 格式）"""
    content = await file.read()
    filename = file.filename.lower()

    try:
        hosts_data = []
        
        if filename.endswith('.csv'):
            # CSV 格式解析
            import csv
            from io import StringIO
            text = content.decode('utf-8-sig')  # 处理 BOM
            reader = csv.DictReader(StringIO(text))
            
            for row in reader:
                # 支持多种列名格式
                name = row.get('name') or row.get('主机名') or row.get('hostname')
                ip = row.get('ip_address') or row.get('ip') or row.get('IP地址') or row.get('IP')
                port = row.get('port') or row.get('端口') or '22'
                credential_name = row.get('credential_name') or row.get('凭据') or row.get('credential') or ''
                group_name = row.get('group') or row.get('host_group') or row.get('主机组')
                tags_str = row.get('tags') or row.get('标签') or ''
                
                if name and ip:
                    host_info = {
                        'name': name.strip(),
                        'ip_address': ip.strip(),
                        'port': int(port) if port else 22,
                    }
                    if credential_name:
                        host_info['credential_name'] = credential_name.strip()
                    if group_name:
                        host_info['group_name'] = group_name.strip()
                    if tags_str:
                        host_info['tags'] = [t.strip() for t in tags_str.split(';') if t.strip()]
                    hosts_data.append(host_info)
        else:
            # INI 格式解析
            lines = content.decode('utf-8').split('\n')
            current_group = None
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line.startswith('[') and line.endswith(']'):
                    current_group = line[1:-1]
                    if current_group == 'all':
                        current_group = None
                elif current_group is None:
                    parts = line.split()
                    if parts:
                        host_info = {'name': parts[0]}
                        for part in parts[1:]:
                            if '=' in part:
                                key, value = part.split('=', 1)
                                if key == 'ansible_host':
                                    host_info['ip_address'] = value
                        if 'ip_address' not in host_info:
                            host_info['ip_address'] = host_info['name']
                        hosts_data.append(host_info)

        if not hosts_data:
            raise HTTPException(status_code=400, detail="文件中未找到有效的主机数据")

        # 获取所有主机组
        groups_result = await db.execute(select(HostGroup))
        groups = {g.name: g for g in groups_result.scalars().all()}

        # 获取所有凭据
        creds_result = await db.execute(select(Credential))
        credentials = {c.name: c for c in creds_result.scalars().all()}

        # 创建主机
        created_count = 0
        skipped_count = 0
        errors = []
        
        for idx, host_info in enumerate(hosts_data):
            try:
                name = host_info.get('name') or host_info.get('ip_address')
                ip = host_info.get('ip_address') or name
                
                # 检查是否已存在
                result = await db.execute(select(Host).where(Host.name == name))
                if result.scalar_one_or_none():
                    skipped_count += 1
                    continue

                # 查找或创建主机组
                group_id = None
                if host_info.get('group_name'):
                    group_name = host_info['group_name']
                    if group_name in groups:
                        group_id = groups[group_name].id
                    else:
                        # 自动创建主机组
                        new_group = HostGroup(name=group_name)
                        db.add(new_group)
                        await db.flush()
                        groups[group_name] = new_group
                        group_id = new_group.id

                # 查找凭据
                credential_id = None
                if host_info.get('credential_name'):
                    cred_name = host_info['credential_name']
                    if cred_name in credentials:
                        credential_id = credentials[cred_name].id
                    else:
                        errors.append(f"第{idx+1}行: 凭据 '{cred_name}' 不存在，已跳过凭据绑定")

                host = Host(
                    name=name,
                    ip_address=ip,
                    port=host_info.get('port', 22),
                    group_id=group_id,
                    credential_id=credential_id,
                    tags=host_info.get('tags', []),
                    host_type='server'
                )
                db.add(host)
                created_count += 1
            except Exception as e:
                errors.append(f"第{idx+1}行: {str(e)}")

        await db.commit()
        
        result_msg = f"成功导入 {created_count} 台主机"
        if skipped_count > 0:
            result_msg += f"，跳过 {skipped_count} 台已存在的主机"
        if errors:
            result_msg += f"。有 {len(errors)} 个错误"
            
        return {"message": result_msg, "created": created_count, "skipped": skipped_count, "errors": errors}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析失败: {str(e)}")

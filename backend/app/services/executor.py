import asyncio
import json
import tempfile
import os
import shutil
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.flow import Flow, FlowExecution, NodeExecution, ExecutionLog
from app.models.host import Host, Credential
from app.core.config import settings
from app.core.utils import now


def get_ansible_path() -> str:
    """自动检测 ansible-playbook 路径"""
    # 常见的 ansible-playbook 路径
    paths = [
        "/usr/local/bin/ansible-playbook",
        "/usr/bin/ansible-playbook",
        "/bin/ansible-playbook",
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    # 如果都没找到，返回默认路径（让系统报错）
    return "/usr/bin/ansible-playbook"


class AnsibleExecutor:
    """Ansible 执行器 - 支持 WebSocket 实时推送"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ws_manager = None
        self._execution_id = None
        self._last_node_status = {}  # 记录每个节点的执行状态 {node_id: bool}

    def set_ws_manager(self, ws_manager):
        """设置 WebSocket 管理器"""
        self.ws_manager = ws_manager

    async def execute_flow(self, execution_id: str):
        """执行流程"""
        self._execution_id = execution_id
        self._last_node_status = {}  # 重置节点状态记录

        # 获取执行记录
        result = await self.db.execute(
            select(FlowExecution).where(FlowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            return

        # 获取流程数据
        flow_result = await self.db.execute(
            select(Flow).where(Flow.id == execution.flow_id)
        )
        flow = flow_result.scalar_one_or_none()
        if not flow:
            await self._update_execution_status(execution, "failed", "流程不存在")
            return

        # 更新执行状态
        await self._update_execution_status(execution, "running")

        # 初始化全局变量字典
        if not execution.variables:
            execution.variables = {}
            await self.db.commit()
        global_context = dict(execution.variables)  # 初始化全局上下文
        print(f"[DEBUG] 初始化全局变量: {global_context}")

        # 获取节点数据（兼容嵌套结构）
        flow_data = flow.flow_data or {}
        # 兼容前端保存的嵌套结构 flow_data.flow_data.nodes
        if "flow_data" in flow_data:
            flow_inner = flow_data.get("flow_data", {})
            nodes = flow_inner.get("nodes", [])
            edges = flow_inner.get("edges", [])
        else:
            nodes = flow_data.get("nodes", [])
            edges = flow_data.get("edges", [])

        # 构建节点映射
        node_map = {node["id"]: node for node in nodes}

        # 执行结果统计
        total = len([n for n in nodes if n.get("type") != "comment"])
        success = 0
        failed = 0

        # 按拓扑顺序执行
        execution_order = self._topological_sort(nodes, edges)
        print(f"[DEBUG] execution_order: {execution_order}")
        print(f"[DEBUG] 所有节点: {[n['id'] for n in nodes]}")
        
        # 构建边信息用于并行分支识别
        edges_map = {}  # source -> [targets]
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                if source not in edges_map:
                    edges_map[source] = []
                edges_map[source].append(target)

        i = 0
        while i < len(execution_order):
            node_id = execution_order[i]
            if execution.status == "stopped":
                break

            node = node_map.get(node_id)
            if not node or node.get("type") == "comment":
                i += 1
                continue

            # 检查是否是并行节点
            if node.get("type") == "parallel":
                node_config = node.get("data", {}).get("config", {})
                fail_strategy = node_config.get("fail_strategy", "all")
                max_parallel = node_config.get("max_parallel", 0)
                
                # 获取并行分支的所有下游节点
                parallel_branches = self._get_parallel_branches(node_id, edges_map, node_map, execution_order)
                
                if parallel_branches:
                    # 创建并行节点执行记录
                    node_exec = NodeExecution(
                        execution_id=execution.id,
                        node_id=node_id,
                        node_name=node.get("data", {}).get("label", node_id),
                        node_type="parallel",
                        status="running",
                        started_at=now()
                    )
                    self.db.add(node_exec)
                    await self.db.commit()
                    await self.db.refresh(node_exec)
                    
                    # 执行并行分支
                    branch_results = await self._execute_parallel_branches(
                        execution, parallel_branches, node_map, 
                        fail_strategy, max_parallel
                    )
                    
                    # 更新并行节点状态
                    node_exec.finished_at = now()
                    if "failed" in branch_results:
                        node_exec.status = "failed"
                        node_exec.output = f"并行分支执行完成，失败: {branch_results['failed']} 个"
                    else:
                        node_exec.status = "success"
                        node_exec.output = f"并行分支执行完成，成功: {branch_results.get('success', 0)} 个"
                    await self.db.commit()
                    
                    # 更新统计
                    success += branch_results.get("success", 0)
                    failed += branch_results.get("failed", 0)
                    
                    # 根据失败策略决定是否继续
                    if branch_results.get("failed", 0) > 0 and fail_strategy == "all":
                        break
                    
                    # 跳过已执行的并行分支节点
                    executed_ids = set()
                    for branch in parallel_branches:
                        for n in branch:
                            executed_ids.add(n["id"])
                    while i + 1 < len(execution_order) and execution_order[i + 1] in executed_ids:
                        i += 1
                
                i += 1
                continue

            # 检查是否是循环节点
            if node.get("type") == "loop":
                node_config = node.get("data", {}).get("config", {})
                loop_type = node_config.get("loop_type", "count")
                loop_var = node_config.get("loop_var", "item")
                fail_strategy = node_config.get("fail_strategy", "continue")
                
                # 获取循环项
                if loop_type == "count":
                    loop_count = node_config.get("loop_count", 1)
                    items = list(range(loop_count))
                elif loop_type == "hosts":
                    result = await self.db.execute(select(Host))
                    hosts = result.scalars().all()
                    items = [h.ip_address for h in hosts]
                elif loop_type == "array":
                    loop_items = node_config.get("loop_items", "")
                    # 支持逗号分隔或换行分隔
                    if "," in loop_items:
                        items = [item.strip() for item in loop_items.split(",") if item.strip()]
                    else:
                        items = [item.strip() for item in loop_items.split("\n") if item.strip()]
                else:
                    items = node_config.get("items", [])
                
                if not items:
                    print(f"[DEBUG] 循环节点 {node_id} 无循环项，跳过")
                    i += 1
                    continue
                
                # 创建循环节点执行记录
                node_exec = NodeExecution(
                    execution_id=execution.id,
                    node_id=node_id,
                    node_name=node.get("data", {}).get("label", node_id),
                    node_type="loop",
                    status="running",
                    started_at=now()
                )
                self.db.add(node_exec)
                await self.db.commit()
                await self.db.refresh(node_exec)
                
                await self._send_ws_log("info", f"开始循环执行，共 {len(items)} 次")
                
                # 获取循环体节点链（循环节点后的所有节点，直到结束或跳出）
                loop_body_nodes = self._get_loop_body_nodes(node_id, edges, edges_map, node_map, execution_order)
                print(f"[DEBUG] 循环体节点: {loop_body_nodes}")
                
                # 执行每个循环项
                loop_success = 0
                loop_failed = 0
                loop_skipped = 0
                loop_context = {}
                
                for idx, item in enumerate(items):
                    loop_context[loop_var] = item
                    loop_context[f"{loop_var}_index"] = idx
                    
                    print(f"[DEBUG] === 循环 {idx+1}/{len(items)}: {item} ===")
                    await self._send_ws_log("info", f"=== 循环 {idx+1}/{len(items)}: {item} ===")
                    
                    # 执行循环体中的每个节点
                    item_success = True
                    executed_condition_nodes = set()  # 跟踪条件分支中已执行的节点
                    
                    for body_node_id in loop_body_nodes:
                        body_node = node_map.get(body_node_id)
                        if not body_node or body_node.get("type") == "comment":
                            continue
                        
                        # 检查是否是条件分支节点的下游节点（已执行过的）
                        if body_node_id in executed_condition_nodes:
                            print(f"[DEBUG] 跳过条件分支中已执行的节点 {body_node_id}")
                            continue
                        
                        # 创建循环体节点执行记录
                        # 获取并验证 host_id
                        raw_host_id = body_node.get("data", {}).get("config", {}).get("host_id")
                        validated_host_id = None
                        if raw_host_id:
                            try:
                                result = await self.db.execute(
                                    select(Host).where(Host.id == raw_host_id)
                                )
                                host_exists = result.scalar_one_or_none()
                                if host_exists:
                                    validated_host_id = raw_host_id
                            except Exception:
                                pass
                        
                        body_exec = NodeExecution(
                            execution_id=execution.id,
                            node_id=body_node_id,
                            node_name=f"{body_node.get('data', {}).get('label', body_node_id)} [{idx+1}]",
                            node_type=body_node.get("type"),
                            host_id=validated_host_id,
                            status="running",
                            started_at=now()
                        )
                        self.db.add(body_exec)
                        await self.db.commit()
                        await self.db.refresh(body_exec)
                        
                        try:
                            # 执行节点，使用循环上下文，复用已创建的执行记录
                            result = await self._execute_node(
                                execution, body_node, loop_context, [], 0, edges, node_map, existing_exec=body_exec
                            )
                            
                            # 处理条件分支返回的额外节点信息
                            if isinstance(result, tuple):
                                success_flag, executed_ids = result
                                executed_condition_nodes.update(executed_ids)
                            else:
                                success_flag = result
                            
                            # 检查是否是结束节点
                            if success_flag == 'END':
                                await self._send_ws_log("info", "到达结束节点，流程终止")
                                node_exec.finished_at = now()
                                node_exec.status = "success"
                                node_exec.output = f"循环执行到第 {idx+1} 次时被结束节点终止"
                                await self.db.commit()
                                await self._send_ws_update(node_exec.id, node_exec.status, node_exec.output)
                                
                                # 更新统计
                                success += loop_success
                                failed += loop_failed
                                
                                # 跳过已执行的循环体节点
                                i += 1
                                while i < len(execution_order) and execution_order[i] in loop_body_nodes:
                                    i += 1
                                continue
                            
                            if success_flag:
                                loop_success += 1
                            else:
                                loop_failed += 1
                                item_success = False
                                
                                # 根据失败策略决定是否继续
                                if fail_strategy == "stop":
                                    await self._send_ws_log("warning", f"循环第 {idx+1} 次失败，停止循环")
                                    break
                                elif fail_strategy == "skip":
                                    loop_skipped += 1
                                    await self._send_ws_log("warning", f"循环第 {idx+1} 次失败，跳过")
                                    continue
                                # continue 策略：继续执行
                                
                        except Exception as e:
                            loop_failed += 1
                            item_success = False
                            error_msg = str(e)
                            body_exec.status = "failed"
                            body_exec.error = error_msg
                            body_exec.finished_at = now()
                            await self.db.commit()
                            await self._send_ws_update(body_exec.id, "failed", error_msg)
                            
                            if fail_strategy == "stop":
                                await self._send_ws_log("error", f"循环第 {idx+1} 次异常: {error_msg}，停止循环")
                                break
                    
                    # 记录循环上下文中的节点状态
                    self._last_node_status[body_node_id] = item_success
                
                # 更新循环节点状态
                node_exec.finished_at = now()
                if loop_failed > 0 and fail_strategy == "stop":
                    node_exec.status = "failed"
                    node_exec.output = f"循环执行失败，已停止。成功: {loop_success}, 失败: {loop_failed}"
                else:
                    node_exec.status = "success"
                    node_exec.output = f"循环执行完成。成功: {loop_success}, 失败: {loop_failed}, 跳过: {loop_skipped}"
                await self.db.commit()
                await self._send_ws_update(node_exec.id, node_exec.status, node_exec.output)
                
                # 更新统计
                success += loop_success
                failed += loop_failed
                
                # 跳过已执行的循环体节点
                i += 1
                while i < len(execution_order) and execution_order[i] in loop_body_nodes:
                    print(f"[DEBUG] 跳过循环体节点 {execution_order[i]}")
                    i += 1
                continue

            # 检查是否是条件分支节点
            if node.get("type") == "condition":
                print(f"\n[DEBUG] === 条件分支节点 {node_id} ===")
                print(f"[DEBUG] _last_node_status: {self._last_node_status}")
                
                # 打印所有边的数据
                print(f"[DEBUG] 所有边的数据:")
                for edge in edges:
                    if edge.get("source") == node_id:
                        print(f"  边: source={edge.get('source')}, sourceHandle={edge.get('sourceHandle')}, target={edge.get('target')}")
                
                node_config = node.get("data", {}).get("config", {})
                default_branch = node_config.get("default_branch", "success")
                print(f"[DEBUG] 默认分支设置: {default_branch}")
                
                # 从边数据中获取条件分支的成功和失败分支
                condition_branches = self._get_condition_branches_from_edges(node_id, edges)
                
                # 创建条件分支节点执行记录
                node_exec = NodeExecution(
                    execution_id=execution.id,
                    node_id=node_id,
                    node_name=node.get("data", {}).get("label", node_id),
                    node_type="condition",
                    status="running",
                    started_at=now()
                )
                self.db.add(node_exec)
                await self.db.commit()
                await self.db.refresh(node_exec)
                
                # 获取上一个节点（源节点）的状态
                source_nodes = [e.get("source") for e in edges if e.get("target") == node_id]
                prev_node_id = source_nodes[0] if source_nodes else None
                prev_success = self._last_node_status.get(prev_node_id, None)
                
                print(f"[DEBUG] 源节点: {prev_node_id}, 状态: {prev_success}")
                
                # 构建变量上下文
                merged_context = dict(execution.variables or {})
                merged_context.update(execution.execution_data or {})
                print(f"[DEBUG] 条件上下文变量: {merged_context}")
                print(f"[DEBUG] execution.variables: {execution.variables}")
                
                # 根据条件配置决定走哪个分支
                conditions = node_config.get("conditions", [])
                logic = node_config.get("logic", "or")  # 默认 OR
                success_targets = condition_branches.get("success", [])
                failed_targets = condition_branches.get("failed", [])
                default_branch = node_config.get("default_branch", "success")
                
                print(f"[DEBUG] success_targets: {success_targets}, failed_targets: {failed_targets}")
                print(f"[DEBUG] 条件配置: {conditions}, 逻辑关系: {logic}")
                print(f"[DEBUG] 前一个节点状态: {prev_success}, 默认分支: {default_branch}")
                
                # 检查是否有变量条件配置
                has_variable_conditions = any(
                    c.get('field') and c.get('field') not in ['prev_node_status', 'previous_status']
                    for c in conditions
                )
                
                if has_variable_conditions:
                    # 使用变量条件判断
                    condition_result = await self._evaluate_condition(
                        conditions,
                        prev_success if prev_success is not None else True,
                        merged_context,
                        logic
                    )
                    print(f"[DEBUG] 变量条件评估结果: {condition_result}")
                    
                    if condition_result == "条件判断通过":
                        selected_branch = "success"
                        target_nodes = success_targets
                        output = f"变量条件成立，走成功分支"
                    else:
                        selected_branch = "failed"
                        target_nodes = failed_targets
                        output = f"变量条件不成立，走失败分支"
                else:
                    # 没有变量条件，使用前一个节点状态判断
                    if prev_success is True:
                        selected_branch = "success"
                        target_nodes = success_targets
                        output = f"上一个节点成功，走成功分支"
                    elif prev_success is False:
                        selected_branch = "failed"
                        target_nodes = failed_targets
                        output = f"上一个节点失败，走失败分支"
                    else:
                        # 前一个节点状态未知，使用默认行为
                        if default_branch == "success":
                            selected_branch = "success"
                            target_nodes = success_targets
                        elif default_branch == "failed":
                            selected_branch = "failed"
                            target_nodes = failed_targets
                        else:
                            selected_branch = "both"
                            target_nodes = success_targets + failed_targets
                        output = f"无上一节点状态，使用默认分支: {selected_branch}"
                
                print(f"[DEBUG] 选中的分支: {selected_branch}, 目标节点: {target_nodes}", flush=True)
                print(f"[DEBUG] success_targets: {success_targets}, failed_targets: {failed_targets}", flush=True)
                
                # 检查是否同时选择了成功和失败分支（bug 检测）
                if target_nodes and len(target_nodes) > 1:
                    print(f"[WARN] 警告: 同时选择了多个分支 {target_nodes}，只执行第一个")
                    target_nodes = [target_nodes[0]]
                
                # 构建区分 sourceHandle 的边映射（用于分支执行）
                branch_edges_map = {}  # (source, sourceHandle) -> [targets]
                for edge in edges:
                    source = edge.get("source")
                    source_handle = edge.get("sourceHandle") or edge.get("source_handle")
                    target = edge.get("target")
                    key = (source, source_handle)
                    if key not in branch_edges_map:
                        branch_edges_map[key] = []
                    branch_edges_map[key].append(target)
                
                print(f"[DEBUG] branch_edges_map: {branch_edges_map}")
                
                # 执行选中的分支 - 使用递归执行，但只从选中的 handle 往下走
                executed_ids = set()
                branch_success = True
                visited_in_branch = set()  # 分支内访问控制
                flow_ended = False  # 流程是否已结束
                
                async def execute_branch_chain(start_id: str, handle: str):
                    """执行从特定 handle 出发的节点链"""
                    nonlocal executed_ids, branch_success, visited_in_branch, flow_ended
                    
                    if flow_ended:
                        return
                    
                    if start_id in visited_in_branch or start_id not in node_map:
                        return
                    
                    visited_in_branch.add(start_id)
                    
                    # 执行节点
                    target_node = node_map[start_id]
                    if target_node.get("type") != "comment":
                        success_flag = await self._execute_node(
                            execution, target_node, execution.execution_data or {}, execution_order, i, edges, node_map
                        )
                        executed_ids.add(start_id)
                        self._last_node_status[start_id] = success_flag
                        print(f"[DEBUG] 执行分支节点: {start_id}, 结果: {success_flag}")
                        
                        # 检查是否是结束节点
                        if success_flag == 'END':
                            print(f"[DEBUG] 分支到达结束节点 {start_id}，流程终止")
                            flow_ended = True
                            return
                        
                        if not success_flag:
                            branch_success = False
                    
                    # 获取该节点从指定 handle 出发的下游
                    key = (start_id, handle)
                    next_targets = branch_edges_map.get(key, [])
                    
                    # 继续执行下游
                    for next_id in next_targets:
                        if next_id not in visited_in_branch and not flow_ended:
                            await execute_branch_chain(next_id, handle)
                
                # 执行每个目标节点及其下游链
                for target_id in target_nodes:
                    if target_id in node_map:
                        # 确定从哪个 handle 继续（success 或 failed）
                        continue_handle = selected_branch  # "success" 或 "failed"
                        await execute_branch_chain(target_id, continue_handle)
                
                print(f"[DEBUG] 已执行的节点: {executed_ids}")
                
                # 更新条件分支节点状态
                node_exec.finished_at = now()
                node_exec.status = "success" if branch_success else "failed"
                node_exec.output = output
                await self.db.commit()
                
                await self._send_ws_update(node_exec.id, node_exec.status, output)
                
                # 跳过未选中的分支节点
                # 获取条件分支节点的所有下游
                condition_all_targets = set()
                for handle in ['success', 'failed']:
                    key = (node_id, handle)
                    if key in branch_edges_map:
                        condition_all_targets.update(branch_edges_map[key])
                
                # 跳过条件分支节点后面所有的下游节点（只执行选中的分支）
                # 需要跳过所有从条件分支出发的节点，除了已经执行的
                i += 1
                while i < len(execution_order):
                    next_node_id = execution_order[i]
                    
                    # 检查这个节点是否是条件分支节点的直接下游
                    if next_node_id in condition_all_targets:
                        # 检查这个节点是否在成功分支中（已执行）
                        if next_node_id not in executed_ids:
                            # 这个节点在失败分支中，需要跳过
                            print(f"[DEBUG] 跳过未选中的分支节点 {next_node_id}")
                            # 同时跳过这个节点的所有下游
                            nodes_to_skip = self._get_all_downstream_nodes(next_node_id, edges_map, set())
                            for skip_id in nodes_to_skip:
                                print(f"[DEBUG] 跳过下游节点 {skip_id}")
                                i += 1
                                if i >= len(execution_order):
                                    break
                        else:
                            # 已在 executed_ids 中，继续跳过
                            print(f"[DEBUG] 跳过已执行的分支节点 {next_node_id}")
                    else:
                        # 不是条件分支的下游，停止跳过
                        break
                    i += 1
                continue

            # 执行普通节点
            success_flag = await self._execute_node(
                execution, node, execution.execution_data or {}, execution_order, i, edges, node_map
            )
            
            # 检查是否是结束节点
            if success_flag == 'END':
                print(f"[DEBUG] 到达结束节点 {node_id}，流程终止")
                # 更新最终状态
                await self._update_execution_status(
                    execution, "success",
                    result_summary={"total": total, "success": success, "failed": failed}
                )
                await self.db.commit()
                return  # 直接返回，结束流程
            
            # 记录节点执行状态
            self._last_node_status[node_id] = success_flag

            if success_flag:
                success += 1
            else:
                failed += 1
                # 如果节点失败，检查后面是否有条件分支节点
                # 如果有条件分支节点，不立即停止，而是继续执行到条件分支
                has_condition_branch = False
                for j in range(i + 1, len(execution_order)):
                    next_node = node_map.get(execution_order[j])
                    if next_node and next_node.get("type") == "condition":
                        has_condition_branch = True
                        break
                    # 如果遇到结束节点，不停止，继续执行到结束节点
                    if next_node and next_node.get("type") == "end":
                        continue
                    # 如果遇到其他普通节点（非注释），则停止
                    if next_node and next_node.get("type") not in ["comment", "condition", "parallel", "start", "end"]:
                        break
                
                if not has_condition_branch:
                    # 没有条件分支节点，根据配置决定是否继续
                    config = node.get("data", {}).get("config", {})
                    if not config.get("ignore_errors"):
                        break
            
            i += 1

        # 更新最终状态
        if execution.status != "stopped":
            final_status = "failed" if failed > 0 else "success"
            await self._update_execution_status(
                execution, final_status,
                result_summary={"total": total, "success": success, "failed": failed}
            )

        await self.db.commit()

    def _get_parallel_branches(
        self, 
        parallel_node_id: str, 
        edges_map: Dict[str, List[str]],
        node_map: Dict[str, Dict],
        execution_order: List[str]
    ) -> List[List[Dict]]:
        """获取并行分支的所有节点链"""
        # 找出 parallel 节点的所有直接下游
        direct_targets = edges_map.get(parallel_node_id, [])
        if not direct_targets:
            return []
        
        # 为每个下游构建完整的执行链
        branches = []
        for target_id in direct_targets:
            branch = self._build_branch_chain(target_id, edges_map, node_map, set())
            if branch:
                branches.append(branch)
        
        return branches

    def _build_branch_chain(
        self,
        node_id: str,
        edges_map: Dict[str, List[str]],
        node_map: Dict[str, Dict],
        visited: set
    ) -> List[Dict]:
        """构建单个分支的节点链"""
        if node_id in visited or node_id not in node_map:
            return []
        
        visited.add(node_id)
        node = node_map[node_id]
        
        # 跳过注释节点
        if node.get("type") == "comment":
            return []
        
        chain = [node]
        
        # 获取该节点的所有下游
        targets = edges_map.get(node_id, [])
        
        # 如果只有一个下游，递归继续
        if len(targets) == 1:
            next_chain = self._build_branch_chain(targets[0], edges_map, node_map, visited)
            chain.extend(next_chain)
        elif len(targets) > 1:
            # 多个下游，展开所有分支
            for target_id in targets:
                next_chain = self._build_branch_chain(target_id, edges_map, node_map, visited.copy())
                chain.extend(next_chain)
        
        return chain

    def _get_condition_branches(
        self,
        condition_node_id: str,
        edges_map: Dict[str, List[str]],
        node_map: Dict[str, Dict]
    ) -> Dict[str, List[str]]:
        """获取条件分支节点的成功和失败分支的所有下游节点 ID"""
        # 从 edges 中获取连接信息
        # 需要根据 sourceHandle 来区分成功/失败分支
        # 由于 edges_map 只存储了 source->targets，我们需要从原始 edges 中获取 handle 信息
        
        # 这里我们假设边是从 edges 中获取的，条件分支节点有两个输出 handle:
        # - sourceHandle="success" -> 成功分支
        # - sourceHandle="failed" -> 失败分支
        
        # 获取所有从条件分支节点出发的边
        # success_branch_targets 和 failed_branch_targets 需要从边的 sourceHandle 获取
        
        # 返回 { "success": [...], "failed": [...] }
        direct_targets = edges_map.get(condition_node_id, [])
        
        result = {"success": [], "failed": []}
        
        # 由于我们无法直接从 edges_map 获取 handle 信息，
        # 这里采用约定：直接下游的第一个节点属于成功分支
        # 实际使用时，建议在前端根据 handle 来区分
        # 暂时将所有下游节点放入 success 分支
        # 我们将在后面通过边数据来正确区分
        
        # 简化处理：如果只有两个下游，第一个是成功，第二个是失败
        if len(direct_targets) >= 1:
            result["success"] = [direct_targets[0]] if len(direct_targets) >= 1 else []
        if len(direct_targets) >= 2:
            result["failed"] = [direct_targets[1]] if len(direct_targets) >= 2 else []
        elif len(direct_targets) == 1:
            # 只有一个下游时，根据边的 sourceHandle 判断
            # 这种情况需要在外部处理
            pass
        
        return result

    def _get_condition_branches_from_edges(
        self,
        condition_node_id: str,
        edges: List[Dict]
    ) -> Dict[str, List[str]]:
        """从边数据中获取条件分支节点的成功和失败分支"""
        result = {"success": [], "failed": []}
        
        # 调试：打印边的数据
        print(f"[DEBUG] 获取条件分支边数据，condition_node_id={condition_node_id}", flush=True)
        
        for edge in edges:
            if edge.get("source") == condition_node_id:
                # 兼容 sourceHandle 和 source_handle 两种字段名
                source_handle = edge.get("sourceHandle") or edge.get("source_handle") or ""
                target = edge.get("target")
                
                print(f"[DEBUG] 边: source={edge.get('source')}, sourceHandle='{source_handle}', target={target}", flush=True)
                
                # 严格匹配 success/failed，忽略空字符串
                if source_handle == "success":
                    result["success"].append(target)
                    print(f"[DEBUG] 边 {target} 分配到 success 分支", flush=True)
                elif source_handle == "failed":
                    result["failed"].append(target)
                    print(f"[DEBUG] 边 {target} 分配到 failed 分支", flush=True)
                else:
                    # sourceHandle 为空或无效，不分配到任何分支
                    print(f"[DEBUG] 边 {target} sourceHandle='{source_handle}' 无效，跳过", flush=True)
        
        print(f"[DEBUG] 最终分支结果: success={result['success']}, failed={result['failed']}", flush=True)
        return result

    def _get_all_downstream_nodes(
        self,
        node_id: str,
        edges_map: Dict[str, List[str]],
        visited: set
    ) -> set:
        """获取一个节点的所有下游节点（包括自身）"""
        if node_id in visited:
            return set()
        
        visited.add(node_id)
        result = {node_id}
        
        targets = edges_map.get(node_id, [])
        for target in targets:
            result.update(self._get_all_downstream_nodes(target, edges_map, visited))
        
        return result

    def _get_loop_body_nodes(
        self,
        loop_node_id: str,
        edges: List[Dict],
        edges_map: Dict[str, List[str]],
        node_map: Dict[str, Dict],
        execution_order: List[str]
    ) -> List[str]:
        """获取循环体的节点列表（只从 loop-start 开始，不包含循环出口后的节点）"""
        # 找出从 loop-start handle 出发的节点
        loop_start_targets = []
        for edge in edges:
            if edge.get("source") == loop_node_id and edge.get("sourceHandle") == "loop-start":
                loop_start_targets.append(edge.get("target"))
        
        if not loop_start_targets:
            return []
        
        # 循环体是从 loop-start 出发的第一个节点开始的所有后续节点
        result = []
        visited = set()
        
        # 使用队列遍历
        queue = list(loop_start_targets)
        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            result.append(node_id)
            
            # 获取该节点的后续节点（只沿普通 source 边，不沿 loop-end 边）
            for edge in edges:
                if edge.get("source") == node_id:
                    source_handle = edge.get("sourceHandle")
                    target = edge.get("target")
                    # 不跟随 loop-end 边（那是循环返回）
                    if target not in visited and source_handle != "loop-end":
                        queue.append(target)
        
        return result

    async def _execute_branch(
        self,
        execution: FlowExecution,
        start_node_id: str,
        node_map: Dict[str, Dict],
        edges_map: Dict[str, List[str]],
        execution_order: List[str],
        visited: set
    ) -> Dict:
        """执行分支上的所有节点"""
        if start_node_id in visited or start_node_id not in node_map:
            return {"executed_ids": set(), "success": True}
        
        visited.add(start_node_id)
        node = node_map[start_node_id]
        
        # 跳过注释节点
        if node.get("type") == "comment":
            return {"executed_ids": set(), "success": True}
        
        # 跳过条件分支节点（已在主循环中处理）
        if node.get("type") == "condition":
            print(f"[DEBUG] _execute_branch 遇到条件分支节点 {start_node_id}，跳过执行，获取下游继续")
            # 只获取下游继续（条件分支节点自身已在主循环中执行）
            targets = edges_map.get(start_node_id, [])
            all_executed = set()  # 条件分支节点不在这里返回，因为它已在主循环执行
            branch_success = True
            for target_id in targets:
                if target_id in visited:
                    continue
                sub_result = await self._execute_branch(
                    execution, target_id, node_map, edges_map,
                    execution_order, visited
                )
                all_executed.update(sub_result.get("executed_ids", set()))
                if not sub_result.get("success"):
                    branch_success = False
            return {"executed_ids": all_executed, "success": branch_success}
        
        # 跳过并行节点
        if node.get("type") == "parallel":
            # 获取并行分支
            parallel_branches = self._get_parallel_branches(start_node_id, edges_map, node_map, execution_order)
            all_executed = set()
            branch_success = True
            for branch in parallel_branches:
                for branch_node in branch:
                    if branch_node["id"] not in visited:
                        visited.add(branch_node["id"])
                        all_executed.add(branch_node["id"])
                        result = await self._execute_node(
                            execution, branch_node, execution.execution_data or {}, [], 0, edges, node_map
                        )
                        # 处理条件分支返回的元组
                        if isinstance(result, tuple):
                            success_flag = result[0]
                        else:
                            success_flag = result
                        self._last_node_status[branch_node["id"]] = success_flag
                        if not success_flag:
                            branch_success = False
            return {"executed_ids": all_executed, "success": branch_success}
        
        executed_ids = set()
        branch_success = True
        
        # 执行当前节点
        result = await self._execute_node(
            execution, node, execution.execution_data or {}, [], 0, edges, node_map
        )
        # 处理条件分支返回的元组
        if isinstance(result, tuple):
            success_flag = result[0]
        else:
            success_flag = result
        executed_ids.add(start_node_id)
        self._last_node_status[start_node_id] = success_flag
        
        if not success_flag:
            branch_success = False
        
        # 获取当前节点的所有下游
        targets = edges_map.get(start_node_id, [])
        
        # 继续执行下游节点
        for target_id in targets:
            if target_id in visited:
                continue
            
            # 获取该节点的分支
            sub_result = await self._execute_branch(
                execution, target_id, node_map, edges_map,
                execution_order, visited
            )
            executed_ids.update(sub_result.get("executed_ids", set()))
            if not sub_result.get("success"):
                branch_success = False
        
        return {"executed_ids": executed_ids, "success": branch_success}

    async def _execute_parallel_branches(
        self,
        execution: FlowExecution,
        branches: List[List[Dict]],
        node_map: Dict[str, Dict],
        fail_strategy: str,
        max_parallel: int
    ) -> Dict[str, int]:
        """并行执行多个分支"""
        if not branches:
            return {"success": 0, "failed": 0}
        
        results = {"success": 0, "failed": 0}
        
        # 根据并发数限制决定执行方式
        if max_parallel > 0 and len(branches) > max_parallel:
            # 分批执行
            for batch_start in range(0, len(branches), max_parallel):
                batch = branches[batch_start:batch_start + max_parallel]
                batch_results = await self._run_branch_batch(execution, batch, node_map)
                results["success"] += batch_results["success"]
                results["failed"] += batch_results["failed"]
        else:
            # 全部分支同时执行
            results = await self._run_branch_batch(execution, branches, node_map)
        
        return results

    async def _run_branch_batch(
        self,
        execution: FlowExecution,
        branches: List[List[Dict]],
        node_map: Dict[str, Dict]
    ) -> Dict[str, int]:
        """执行一批并行分支"""
        results = {"success": 0, "failed": 0}
        
        async def execute_branch(branch: List[Dict]) -> bool:
            """执行单个分支，返回是否成功"""
            for node in branch:
                if execution.status == "stopped":
                    return False
                
                if node.get("type") == "comment":
                    continue
                
                try:
                    result = await self._execute_node(
                        execution, node, execution.execution_data or {}, [], 0, edges, node_map
                    )
                    # 处理条件分支返回的元组
                    if isinstance(result, tuple):
                        success_flag = result[0]
                    else:
                        success_flag = result
                    if not success_flag:
                        return False
                except Exception as e:
                    print(f"分支执行错误: {e}")
                    return False
            return True
        
        # 创建所有分支的任务
        tasks = [execute_branch(branch) for branch in branches]
        
        # 并行执行
        branch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        for i, result in enumerate(branch_results):
            if isinstance(result, Exception):
                print(f"分支 {i} 执行异常: {result}")
                results["failed"] += 1
            elif result:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results

    def _topological_sort(self, nodes: List[Dict], edges: List[Dict]) -> List[str]:
        """拓扑排序 - 确定节点执行顺序"""
        # 构建入度和邻接表
        in_degree = {node["id"]: 0 for node in nodes}
        adjacency = {node["id"]: [] for node in nodes}

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                adjacency[source].append(target)
                in_degree[target] += 1

        # 找出所有注释节点的 ID
        comment_nodes = {node["id"] for node in nodes if node.get("type") == "comment"}

        # Kahn 算法
        queue = [node_id for node_id, degree in in_degree.items()
                 if degree == 0 and node_id not in comment_nodes]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 如果有环或者有未访问的节点，返回所有非注释节点
        if len(result) < len(nodes) - len(comment_nodes):
            result = [node["id"] for node in nodes if node.get("type") != "comment"]

        return result

    def _parse_variable_definitions(self, var_text: str) -> Dict[str, str]:
        """解析变量定义文本，返回键值对字典
        
        支持格式：
        - key=value
        - key: value
        - 多个变量用换行或分号分隔
        """
        if not var_text:
            return {}
        
        variables = {}
        # 支持换行、分号分隔
        lines = var_text.replace(";", "\n").split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 去除末尾的逗号（常见输入错误）
            if line.endswith(","):
                line = line[:-1].strip()
            
            # 尝试 key=value 格式
            if "=" in line:
                key, value = line.split("=", 1)
                value = value.strip().rstrip(",")
                # 去除首尾的引号（支持双引号和单引号）
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                variables[key.strip()] = value
            # 尝试 key: value 格式
            elif ":" in line:
                key, value = line.split(":", 1)
                value = value.strip().rstrip(",")
                # 去除首尾的引号（支持双引号和单引号）
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                variables[key.strip()] = value
        
        return variables

    def _extract_variables_from_output(self, output: str) -> Dict[str, str]:
        """从脚本输出中提取变量设置
        
        支持格式：
        - __SET_VAR__key=value（单独一行）
        - export key=value（单独一行）
        - RESULT=success（单独一行）
        - JSON 格式输出中的 "stdout": "__SET_VAR__key=value"
        """
        if not output:
            return {}
        
        variables = {}
        lines = output.split("\n")
        
        for line in lines:
            line = line.strip()
            # 检测 __SET_VAR__key=value 格式（单独一行）
            if line.startswith("__SET_VAR__"):
                try:
                    var_str = line[11:]  # 去掉前缀
                    if "=" in var_str:
                        key, value = var_str.split("=", 1)
                        variables[key.strip()] = value.strip()
                except Exception:
                    pass
            # 检测 export key=value 格式
            elif line.startswith("export "):
                try:
                    var_str = line[7:]
                    if "=" in var_str:
                        key, value = var_str.split("=", 1)
                        variables[key.strip()] = value.strip()
                except Exception:
                    pass
            # 检测 JSON 格式中的 stdout 字段（Ansible -v 输出）
            elif '"stdout":' in line or '"stdout_lines":' in line:
                try:
                    import json
                    # 尝试解析为 JSON 对象
                    if line.endswith(',') or line.endswith('}') or line.endswith(']'):
                        # 尝试从行中提取 stdout 值
                        if '"stdout":' in line:
                            # 提取 "stdout": "value" 格式
                            import re
                            match = re.search(r'"stdout":\s*"([^"]*)"', line)
                            if match:
                                stdout_value = match.group(1)
                                # 检查 stdout 中是否包含变量
                                if stdout_value.startswith("__SET_VAR__"):
                                    var_str = stdout_value[11:]
                                    if "=" in var_str:
                                        key, value = var_str.split("=", 1)
                                        variables[key.strip()] = value.strip()
                                elif "=" in stdout_value:
                                    key, value = stdout_value.split("=", 1)
                                    variables[key.strip()] = value.strip()
                except Exception:
                    pass
        
        return variables

    def _resolve_host_id(self, host_id: Optional[str], context: Dict[str, Any]) -> Optional[str]:
        """解析 host_id，支持变量替换
        
        如果 host_id 是变量格式（如 {{item}} 或 ${host}），则从 context 中获取实际值。
        如果解析后的值是 IP 地址，则查找对应的主机 ID。
        """
        if not host_id:
            return None
        
        # 如果 host_id 不是变量，直接返回
        if not (host_id.startswith("{{") or host_id.startswith("${")):
            return host_id
        
        # 尝试从 context 中获取变量值
        resolved_value = host_id
        for key, value in context.items():
            resolved_value = resolved_value.replace(f"{{{{{key}}}}}", str(value))
            resolved_value = resolved_value.replace(f"${{{key}}}", str(value))
        
        # 如果解析后还是变量格式，说明没有找到对应变量
        if resolved_value.startswith("{{") or resolved_value.startswith("${"):
            return host_id
        
        return resolved_value

    async def _get_host_id_from_ip(self, ip_address: str) -> Optional[str]:
        """根据 IP 地址查找主机 ID"""
        try:
            result = await self.db.execute(
                select(Host).where(Host.ip_address == ip_address)
            )
            host = result.scalar_one_or_none()
            return host.id if host else None
        except Exception as e:
            print(f"[DEBUG] 查找主机失败: {e}")
            return None

    async def _execute_single_node(
        self,
        execution: FlowExecution,
        node: Dict[str, Any],
        context: Dict[str, Any],
        edges: List[Dict] = None,
        node_map: Dict[str, Dict] = None
    ) -> bool:
        """执行单个节点（不处理条件分支递归）
        
        用于在条件分支中直接执行节点，避免递归调用 _execute_node
        """
        node_type = node.get("type")
        node_id = node.get("id")
        node_data = node.get("data", {})
        node_config = node_data.get("config", {})
        
        # 合并全局变量到上下文
        merged_context = dict(execution.variables or {})
        merged_context.update(context)
        
        # 解析 host_id
        raw_host_id = node_config.get("host_id")
        resolved_host_id = self._resolve_host_id(raw_host_id, merged_context)
        
        final_host_id = resolved_host_id
        if resolved_host_id:
            try:
                host_id_from_ip = await self._get_host_id_from_ip(resolved_host_id)
                if host_id_from_ip:
                    final_host_id = host_id_from_ip
            except Exception:
                pass
        
        # 创建执行记录
        node_exec = NodeExecution(
            execution_id=execution.id,
            node_id=node_id,
            node_name=node_data.get("label", node_id),
            node_type=node_type,
            host_id=final_host_id,
            status="running",
            started_at=now()
        )
        self.db.add(node_exec)
        await self.db.commit()
        await self.db.refresh(node_exec)
        
        try:
            output = ""
            
            # 处理各种节点类型
            if node_type == "command":
                command = node_config.get("command", "")
                print(f"[DEBUG] 执行命令: {command}")
                print(f"[DEBUG] 主机ID: {final_host_id}")
                print(f"[DEBUG] 上下文: {merged_context}")
                
                if merged_context:
                    for key, value in merged_context.items():
                        command = command.replace(f"{{{{{key}}}}}", str(value))
                        command = command.replace(f"${{{key}}}", str(value))
                
                print(f"[DEBUG] 替换后的命令: {command}")
                result = await self._run_ansible_command(final_host_id, command)
                print(f"[DEBUG] 命令输出: {result}")
                output = result
                
            elif node_type == "script":
                script_content = node_config.get("script_content", "")
                script_type = node_config.get("script_type", "shell")
                if merged_context:
                    for key, value in merged_context.items():
                        script_content = script_content.replace(f"{{{{{key}}}}}", str(value))
                        script_content = script_content.replace(f"${{{key}}}", str(value))
                
                output = await self._run_script(final_host_id, script_content, script_type)
                
            elif node_type == "playbook":
                playbook_content = node_config.get("playbook_content", "")
                extra_vars = node_config.get("extra_vars", {})
                if merged_context:
                    for key, value in merged_context.items():
                        playbook_content = playbook_content.replace(f"{{{{{key}}}}}", str(value))
                        playbook_content = playbook_content.replace(f"${{{key}}}", str(value))
                
                output = await self._run_playbook(final_host_id, None, playbook_content, extra_vars)
                
            elif node_type == "notify":
                recipients = node_config.get("recipients", "")
                subject = node_config.get("subject", "自动化平台通知")
                message = node_config.get("message", "")
                notify_context = {
                    "flow_name": execution.flow.name if execution.flow else "未知流程",
                    "result": "成功",
                    "start_time": execution.started_at.strftime("%Y-%m-%d %H:%M:%S") if execution.started_at else "",
                    "end_time": now().strftime("%Y-%m-%d %H:%M:%S")
                }
                notify_context.update(merged_context)
                output = await self._send_notification(
                    node_config.get("channel", "email"),
                    message,
                    recipients=recipients,
                    subject=subject,
                    context=notify_context
                )
                
            elif node_type == "end":
                output = "流程结束"
                node_exec.status = "success"
                node_exec.output = output
                node_exec.finished_at = now()
                await self.db.commit()
                await self._send_ws_update(node_exec.id, "success", output)
                return 'END'
                
            else:
                output = f"节点类型: {node_type}"
            
            # 更新执行记录
            node_exec.status = "success"
            node_exec.output = output
            node_exec.finished_at = now()
            await self.db.commit()
            await self._send_ws_update(node_exec.id, "success", output)
            
            # 提取变量并追加到输出中显示
            if node_type in ("command", "script", "playbook") and output:
                print(f"[DEBUG] 原始输出: {output}")
                extracted_vars = self._extract_variables_from_output(output)
                print(f"[DEBUG] 提取的变量: {extracted_vars}")
                if extracted_vars:
                    execution.variables = execution.variables or {}
                    execution.variables.update(extracted_vars)
                    print(f"[DEBUG] 更新后的全局变量: {execution.variables}")
                    await self.db.commit()
                    
                    # 将提取的变量追加到节点输出中，便于在执行详情中查看
                    var_lines = ["", "=" * 40]
                    var_lines.append("📊 提取的变量:")
                    for key, value in extracted_vars.items():
                        var_lines.append(f"  {key} = {value}")
                    node_exec.output = output + "\n" + "\n".join(var_lines)
                    await self.db.commit()
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            node_exec.status = "failed"
            node_exec.error = error_msg
            node_exec.finished_at = now()
            await self.db.commit()
            await self._send_ws_update(node_exec.id, "failed", error_msg)
            return False

    async def _execute_node(
        self,
        execution: FlowExecution,
        node: Dict[str, Any],
        context: Dict[str, Any],
        execution_order: List[str] = None,
        node_index: int = 0,
        edges: List[Dict] = None,
        node_map: Dict[str, Dict] = None,
        existing_exec: NodeExecution = None
    ) -> bool:
        """执行单个节点
        
        Args:
            edges: 边的数据列表，用于条件分支执行
            node_map: 节点映射，用于查找节点
            existing_exec: 已存在的执行记录，用于避免重复记录
        """
        node_type = node.get("type")
        node_id = node.get("id")
        node_data = node.get("data", {})
        node_config = node_data.get("config", {})

        # 合并全局变量到上下文（全局变量优先级较低，局部变量可覆盖）
        merged_context = dict(execution.variables or {})  # 基础：全局变量
        merged_context.update(context)  # 覆盖：局部变量（循环变量等）

        # 解析 host_id，支持变量替换
        raw_host_id = node_config.get("host_id")
        resolved_host_id = self._resolve_host_id(raw_host_id, merged_context)
        
        # 如果是 IP 地址，查找对应的主机 ID
        final_host_id = resolved_host_id
        if resolved_host_id and not raw_host_id.startswith("{{") and not raw_host_id.startswith("${"):
            # host_id 是固定值，直接使用
            final_host_id = resolved_host_id
        elif resolved_host_id != raw_host_id:
            # host_id 是变量，尝试查找主机
            host_id_from_ip = await self._get_host_id_from_ip(resolved_host_id)
            if host_id_from_ip:
                final_host_id = host_id_from_ip
            else:
                # 没找到主机，使用 IP 地址作为目标
                final_host_id = resolved_host_id
        
        # 验证 host_id 是否存在于 hosts 表，如果不存在则报错
        if final_host_id:
            try:
                result = await self.db.execute(
                    select(Host).where(Host.id == final_host_id)
                )
                host_exists = result.scalar_one_or_none()
                if not host_exists:
                    # 主机不存在，尝试通过 IP 地址查找
                    ip_result = await self.db.execute(
                        select(Host).where(Host.ip_address == final_host_id)
                    )
                    host_by_ip = ip_result.scalar_one_or_none()
                    if host_by_ip:
                        # 找到了对应的主机，使用其 ID
                        final_host_id = host_by_ip.id
                    else:
                        # 主机确实不存在，抛出错误
                        error_msg = f"主机不存在: {final_host_id}"
                        node_exec = NodeExecution(
                            execution_id=execution.id,
                            node_id=node_id,
                            node_name=node_data.get("label", node_id),
                            node_type=node_type,
                            status="failed",
                            error=error_msg,
                            started_at=now(),
                            finished_at=now()
                        )
                        self.db.add(node_exec)
                        await self.db.commit()
                        await self._add_log(node_exec.id, "error", error_msg)
                        await self._send_ws_update(node_exec.id, "failed", error_msg)
                        return False
            except Exception as e:
                error_msg = f"验证主机失败: {str(e)}"
                node_exec = NodeExecution(
                    execution_id=execution.id,
                    node_id=node_id,
                    node_name=node_data.get("label", node_id),
                    node_type=node_type,
                    status="failed",
                    error=error_msg,
                    started_at=now(),
                    finished_at=now()
                )
                self.db.add(node_exec)
                await self.db.commit()
                await self._add_log(node_exec.id, "error", error_msg)
                await self._send_ws_update(node_exec.id, "failed", error_msg)
                return False

        # 创建节点执行记录（如果已有记录则复用）
        if existing_exec:
            node_exec = existing_exec
            node_exec.status = "running"
            node_exec.started_at = now()
            if final_host_id:
                node_exec.host_id = final_host_id
        else:
            node_exec = NodeExecution(
                execution_id=execution.id,
                node_id=node_id,
                node_name=node_data.get("label", node_id),
                node_type=node_type,
                host_id=final_host_id,
                status="running",
                started_at=now()
            )
            self.db.add(node_exec)
        await self.db.commit()
        await self.db.refresh(node_exec)

        try:
            output = ""

            if node_type == "command":
                command = node_config.get("command", "")
                # 替换命令中的变量
                if merged_context:
                    for key, value in merged_context.items():
                        command = command.replace(f"{{{{{key}}}}}", str(value))
                        command = command.replace(f"${{{key}}}", str(value))
                output = await self._run_ansible_command(
                    final_host_id,
                    command,
                    node_config.get("sudo", False),
                    node_config.get("timeout", 60)
                )

            elif node_type == "script":
                output = await self._run_script(
                    final_host_id,
                    node_config.get("script_type", "shell"),
                    node_config.get("script_content", ""),
                    node_config.get("args", ""),
                    node_config.get("timeout", 300),
                    merged_context  # 传递合并后的上下文
                )

            elif node_type == "playbook":
                extra_vars = node_config.get("extra_vars_text", "")
                # 替换 extra_vars 中的变量
                if merged_context:
                    for key, value in merged_context.items():
                        extra_vars = extra_vars.replace(f"{{{{{key}}}}}", str(value))
                        extra_vars = extra_vars.replace(f"${{{key}}}", str(value))
                output = await self._run_playbook(
                    final_host_id,
                    node_config.get("playbook_id"),
                    node_config.get("playbook_content", ""),
                    extra_vars,
                    node_config.get("timeout", 600)
                )
                # 检查 Playbook 输出是否包含失败信息
                if self._is_playbook_failed(output):
                    node_exec.status = "failed"
                    node_exec.output = output  # 保存完整输出
                    # 截取错误信息作为 error
                    error_lines = [l for l in output.split('\n') if 'failed' in l.lower() or 'error' in l.lower() or 'fatal' in l.lower()]
                    node_exec.error = '\n'.join(error_lines[:5]) if error_lines else "Playbook 执行失败，请查看输出日志"
                    node_exec.finished_at = now()
                    await self.db.commit()
                    await self._add_log(node_exec.id, "error", f"Playbook 执行失败: {node_exec.error[:200]}")
                    await self._send_ws_update(node_exec.id, "failed", node_exec.error)
                    return False

            elif node_type == "wait":
                wait_seconds = node_config.get("wait_seconds", 10)
                output = f"等待了 {wait_seconds} 秒"
                await asyncio.sleep(wait_seconds)

            elif node_type == "notify":
                # 构建变量上下文（包含全局变量和执行时变量）
                notify_context = {
                    "flow_name": execution.flow.name if execution.flow else "未知流程",
                    "result": "成功" if execution.status == "success" else "失败",
                    "start_time": execution.started_at.strftime("%Y-%m-%d %H:%M:%S") if execution.started_at else "",
                    "end_time": now().strftime("%Y-%m-%d %H:%M:%S")
                }
                # 合并流程变量到上下文
                notify_context.update(merged_context)
                output = await self._send_notification(
                    node_config.get("channel", "email"),
                    node_config.get("message", ""),
                    recipients=node_config.get("recipients", ""),
                    subject=node_config.get("subject", ""),
                    context=notify_context
                )

            elif node_type == "loop":
                output = await self._execute_loop(
                    execution, node, node_config, context
                )

            elif node_type == "condition":
                # 检查是否有 edges 数据可用（用于在循环体中执行分支）
                if edges and node_map:
                    # 在循环体中执行条件分支
                    condition_branches = self._get_condition_branches_from_edges(node_id, edges)
                    conditions = node_config.get("conditions", [])
                    logic = node_config.get("logic", "or")
                    success_targets = condition_branches.get("success", [])
                    failed_targets = condition_branches.get("failed", [])
                    
                    # 获取前一个节点状态
                    source_nodes = [e.get("source") for e in edges if e.get("target") == node_id]
                    prev_node_id = source_nodes[0] if source_nodes else None
                    prev_success = self._last_node_status.get(prev_node_id, None)
                    
                    # 检查是否有变量条件
                    has_variable_conditions = any(
                        c.get('field') and c.get('field') not in ['prev_node_status', 'previous_status']
                        for c in conditions
                    )
                    
                    if has_variable_conditions:
                        condition_result = await self._evaluate_condition(
                            conditions,
                            prev_success if prev_success is not None else True,
                            merged_context,
                            logic
                        )
                        print(f"[DEBUG] 条件评估结果: {condition_result}")
                        if condition_result == "条件判断通过":
                            selected_branch = "success"
                            target_nodes = success_targets
                        else:
                            selected_branch = "failed"
                            target_nodes = failed_targets
                    else:
                        if prev_success is True:
                            selected_branch = "success"
                            target_nodes = success_targets
                        elif prev_success is False:
                            selected_branch = "failed"
                            target_nodes = failed_targets
                        else:
                            default_branch = node_config.get("default_branch", "success")
                            selected_branch = default_branch
                            target_nodes = success_targets if default_branch == "success" else failed_targets
                    
                    print(f"[DEBUG] 循环体内条件节点 {node_id} 执行分支: {selected_branch}, 目标: {target_nodes}")
                    
                    # 计算需要跳过的分支（未选择的分支）
                    skipped_branch = "failed" if selected_branch == "success" else "success"
                    skipped_targets = failed_targets if selected_branch == "success" else success_targets
                    
                    # 构建边映射用于获取下游节点
                    branch_edges_map = {}
                    for edge in edges:
                        source = edge.get("source")
                        source_handle = edge.get("sourceHandle") or edge.get("source_handle")
                        target = edge.get("target")
                        key = (source, source_handle)
                        if key not in branch_edges_map:
                            branch_edges_map[key] = []
                        branch_edges_map[key].append(target)
                    
                    # 获取需要跳过的分支的直接下游节点（不递归，因为循环体会处理）
                    skipped_ids = set()
                    
                    # 构建边映射（按 source 索引）
                    source_edges_map = {}
                    for edge in edges:
                        source = edge.get("source")
                        target = edge.get("target")
                        if source not in source_edges_map:
                            source_edges_map[source] = []
                        source_edges_map[source].append(target)
                    
                    # 只跳过未选择分支的**直接**目标节点，不递归
                    # 因为这些节点会在循环的下一次迭代中被重新处理
                    for skipped_target in skipped_targets:
                        skipped_ids.add(skipped_target)
                    
                    print(f"[DEBUG] 需要跳过的分支: {skipped_branch}, 直接跳过节点: {skipped_ids}")
                    
                    # 构建边映射并执行分支
                    branch_edges_map = {}
                    for edge in edges:
                        source = edge.get("source")
                        source_handle = edge.get("sourceHandle") or edge.get("source_handle")
                        target = edge.get("target")
                        key = (source, source_handle)
                        if key not in branch_edges_map:
                            branch_edges_map[key] = []
                        branch_edges_map[key].append(target)
                    
                    executed_ids = set()
                    
                    # 把需要跳过的节点合并到 executed_ids
                    executed_ids.update(skipped_ids)
                    
                    async def execute_branch_chain(start_id: str, handle: str):
                        nonlocal executed_ids
                        if start_id in executed_ids or start_id not in node_map:
                            return
                        
                        executed_ids.add(start_id)
                        branch_node = node_map[start_id]
                        if branch_node.get("type") != "comment":
                            # 直接执行节点，不再递归调用 _execute_node
                            branch_success_flag = await self._execute_single_node(
                                execution, branch_node, merged_context, edges, node_map
                            )
                            self._last_node_status[start_id] = branch_success_flag
                            
                            if branch_success_flag == 'END':
                                return
                        
                        key = (start_id, handle)
                        next_targets = branch_edges_map.get(key, [])
                        for next_id in next_targets:
                            await execute_branch_chain(next_id, handle)
                    
                    for target_id in target_nodes:
                        if target_id in node_map:
                            await execute_branch_chain(target_id, selected_branch)
                    
                    print(f"[DEBUG] 循环体内条件分支执行完成: {executed_ids}")
                    output = f"条件判断结果: {selected_branch} 分支\n已执行分支: {selected_branch}\n执行节点数: {len([x for x in executed_ids if x not in skipped_ids])}"
                    
                    # 更新条件分支节点状态
                    node_exec.status = "success"
                    node_exec.output = output
                    node_exec.finished_at = now()
                    await self.db.commit()
                    await self._send_ws_update(node_exec.id, "success", output)
                    
                    # 返回执行的节点集合，用于循环体跳过这些节点
                    return (True, executed_ids)
                else:
                    # 主循环中的条件节点处理（返回分支信息，让主循环处理）
                    output = "CONDITION_NEEDS_BRANCH"
                
                # 获取上一个节点的状态（默认为True）
                last_status = True
                if execution_order and node_index > 0:
                    prev_node_id = execution_order[node_index - 1]
                    last_status = self._last_node_status.get(prev_node_id, True)
                if output != "CONDITION_NEEDS_BRANCH":
                    await self._evaluate_condition(
                        node_config.get("conditions", []),
                        last_status,
                        merged_context
                    )

            elif node_type == "file":
                output = await self._handle_file(
                    node_config.get("action", "push"),
                    node_config.get("source", ""),
                    node_config.get("destination", ""),
                    node_config.get("host_id")
                )

            elif node_type == "start":
                # 开始节点，直接成功
                output = "流程开始"

            elif node_type == "variable":
                # 变量设置节点
                var_definitions = node_config.get("variables", "")
                set_vars = self._parse_variable_definitions(var_definitions)
                if set_vars:
                    # 更新全局变量
                    execution.variables = execution.variables or {}
                    execution.variables.update(set_vars)
                    await self.db.commit()
                    print(f"[DEBUG] 设置变量: {set_vars}, 全局变量: {execution.variables}")
                    await self._send_ws_log("info", f"设置变量: {set_vars}")
                output = f"变量已设置: {set_vars}" if set_vars else "无变量定义"

            elif node_type == "end":
                # 结束节点，流程终止
                output = "流程结束"
                node_exec.status = "success"
                node_exec.output = output
                node_exec.finished_at = now()
                await self.db.commit()
                await self._add_log(node_exec.id, "info", output)
                await self._send_ws_update(node_exec.id, "success", output)
                # 返回特殊值 'END' 表示流程应该结束
                return 'END'

            else:
                output = f"未知节点类型: {node_type}"

            # 更新节点执行记录
            node_exec.status = "success"
            node_exec.output = output
            node_exec.finished_at = now()
            await self.db.commit()

            # 添加日志
            await self._add_log(node_exec.id, "info", output)

            # WebSocket 推送
            await self._send_ws_update(node_exec.id, "success", output)

            # 从脚本/命令输出中提取变量设置
            if node_type in ("command", "script", "playbook") and output:
                extracted_vars = self._extract_variables_from_output(output)
                if extracted_vars:
                    execution.variables = execution.variables or {}
                    execution.variables.update(extracted_vars)
                    await self.db.commit()
                    print(f"[DEBUG] 从输出提取变量: {extracted_vars}, 全局变量: {execution.variables}")
                    await self._send_ws_log("info", f"提取变量: {extracted_vars}")

            return True

        except Exception as e:
            error_msg = str(e)
            node_exec.status = "failed"
            node_exec.error = error_msg
            node_exec.finished_at = now()
            await self.db.commit()

            await self._add_log(node_exec.id, "error", error_msg)
            await self._send_ws_update(node_exec.id, "failed", error_msg)

            return False

    async def _run_ansible_command(
        self,
        host_id: Optional[str],
        command: str,
        sudo: bool = False,
        timeout: int = 60
    ) -> str:
        """通过 SSH 执行命令"""
        if not command:
            raise ValueError("命令不能为空")

        if not host_id:
            # 本地执行
            process = await asyncio.create_subprocess_exec(
                "bash", "-c", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                output = stdout.decode() + stderr.decode()
                await self._send_ws_log("info", output)
                return output or "命令执行完成"
            except asyncio.TimeoutError:
                process.kill()
                raise Exception(f"命令执行超时（{timeout}秒）")

        # 获取主机和凭据
        result = await self.db.execute(select(Host).where(Host.id == host_id))
        host = result.scalar_one_or_none()
        if not host:
            print(f"[DEBUG] 主机不存在: {host_id}")
            raise ValueError(f"主机不存在: {host_id}")

        # 获取凭据
        credential = None
        if host.credential_id:
            cred_result = await self.db.execute(select(Credential).where(Credential.id == host.credential_id))
            credential = cred_result.scalar_one_or_none()

        if not credential or not credential.username:
            raise ValueError(f"主机 {host.name} 未配置认证凭据或用户名")

        # 使用 paramiko SSH 连接
        import paramiko
        from paramiko import SSHClient, AutoAddPolicy

        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())

        connect_kwargs = {
            "hostname": host.ip_address,
            "port": host.port or 22,
            "username": credential.username,
            "timeout": timeout,
        }

        # 根据认证类型设置密码或密钥
        if credential.type == "password" and credential.password:
            connect_kwargs["password"] = credential.password
        elif credential.type in ["ssh_key", "rsa", "ed25519", "ecdsa"]:
            try:
                pkey = None
                if credential.private_key:
                    import io
                    if credential.type == "rsa":
                        from paramiko import RSAKey
                        pkey = RSAKey.from_private_key(io.StringIO(credential.private_key))
                    elif credential.type == "ed25519":
                        from paramiko import Ed25519Key
                        pkey = Ed25519Key.from_private_key(io.StringIO(credential.private_key))
                    elif credential.type == "ecdsa":
                        from paramiko import ECDSAKey
                        pkey = ECDSAKey.from_private_key(io.StringIO(credential.private_key))
                    else:
                        pkey = paramiko.RSAKey.from_private_key(io.StringIO(credential.private_key))
                    if credential.passphrase:
                        pkey = paramiko.RSAKey.from_private_key(io.StringIO(credential.private_key), password=credential.passphrase)
                connect_kwargs["pkey"] = pkey
            except Exception as e:
                raise ValueError(f"SSH密钥解析失败: {str(e)}")

        try:
            await asyncio.get_event_loop().run_in_executor(None, lambda: ssh.connect(**connect_kwargs))

            # 执行命令
            full_command = command
            if sudo and credential.username != "root":
                full_command = f"sudo {command}"

            stdin, stdout, stderr = ssh.exec_command(full_command, timeout=timeout)

            output = stdout.read().decode()
            error = stderr.read().decode()

            ssh.close()

            result_output = output + error if error else output
            await self._send_ws_log("info", result_output)

            if error and "error" in error.lower():
                raise Exception(error)

            return result_output or "命令执行完成"

        except Exception as e:
            print(f"[DEBUG] SSH执行失败: {str(e)}")
            raise Exception(f"SSH执行失败: {str(e)}")

    async def _run_script(
        self,
        host_id: Optional[str],
        script_type: str,
        content: str,
        args: str,
        timeout: int = 300,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """运行脚本"""
        if not content:
            raise ValueError("脚本内容不能为空")

        # 替换脚本中的变量
        if context:
            for key, value in context.items():
                # 替换 {{key}} 和 ${key} 格式的变量
                content = content.replace(f"{{{{{key}}}}}", str(value))
                content = content.replace(f"${{{key}}}", str(value))
                args = args.replace(f"{{{{{key}}}}}", str(value))
                args = args.replace(f"${{{key}}}", str(value))

        # 构建执行命令
        if script_type == "shell":
            cmd = f"{content}\n{args}"
        elif script_type == "python":
            cmd = f"python3 - << 'PYEOF'\n{content}\nPYEOF\n{args}"
        else:
            cmd = f"bash - << 'SHEOF'\n{content}\nSHEOF\n{args}"

        # 直接执行命令（包含脚本内容）
        output = await self._run_ansible_command(
            host_id, cmd, timeout=timeout
        )

        return output

    def _is_playbook_failed(self, output: str) -> bool:
        """检查 Playbook 输出是否包含失败信息"""
        if not output:
            return True
        
        output_lines = output.split('\n')
        output_lower = output.lower()
        
        # 只在 PLAY RECAP 行中检查失败计数
        import re
        
        # 查找 RECAP 行（包含 failed=X unreachable=X 的行）
        recap_pattern = re.compile(r'(failed|unreachable)\s*=\s*(\d+)', re.IGNORECASE)
        
        # 检查是否有真正的失败
        for line in output_lines:
            line_lower = line.lower()
            # 跳过 RECAP 之前的所有行
            if 'play recap' in line_lower or 'recap' in line_lower:
                # 检查 RECAP 行中的 failed 和 unreachable
                matches = recap_pattern.findall(line_lower)
                for keyword, count in matches:
                    if int(count) > 0:
                        return True
                continue
            
            # 检查严重的错误关键词（不在 RECAP 行中）
            if any(err in line_lower for err in ['error:', 'fatal:', 'syntax error', 'connection failure', 'authentication failure']):
                return True
        
        # 如果没有找到真正的失败，返回 False
        return False

    async def _run_playbook(
        self,
        host_id: Optional[str],
        playbook_id: Optional[str],
        playbook_content: str,
        extra_vars_text: str = "",
        timeout: int = 600
    ) -> str:
        """运行 Playbook - 在本地执行 ansible-playbook，通过 SSH 连接远程主机"""
        if not playbook_content:
            raise ValueError("Playbook 内容不能为空")

        import uuid
        import base64
        import tempfile
        
        playbook_filename = f"/tmp/playbook_{uuid.uuid4().hex[:8]}.yml"
        inventory_filename = f"/tmp/inventory_{uuid.uuid4().hex[:8]}"
        ssh_key_file = ""
        
        # 调试：记录 playbook 内容到文件
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[DEBUG] playbook_content 类型: {type(playbook_content)}")
        logger.warning(f"[DEBUG] playbook_content 长度: {len(playbook_content) if playbook_content else 0}")
        logger.warning(f"[DEBUG] playbook_content 内容: {repr(playbook_content[:500])}")
        
        # 写入 playbook 文件
        with open(playbook_filename, 'w', encoding='utf-8') as f:
            f.write(playbook_content)
        
        # 验证写入的内容
        with open(playbook_filename, 'r', encoding='utf-8') as f:
            written_content = f.read()
        logger.warning(f"[DEBUG] 写入文件后的内容: {repr(written_content[:500])}")
        
        # 构建 ansible-playbook 命令（自动检测路径）
        ansible_playbook_path = get_ansible_path()
        ansible_cmd_parts = [ansible_playbook_path, playbook_filename]
        
        if host_id:
            # 获取主机和凭据
            result = await self.db.execute(select(Host).where(Host.id == host_id))
            host = result.scalar_one_or_none()
            if not host:
                os.remove(playbook_filename)
                raise ValueError(f"主机不存在: {host_id}")
            
            credential = None
            if host.credential_id:
                cred_result = await self.db.execute(select(Credential).where(Credential.id == host.credential_id))
                credential = cred_result.scalar_one_or_none()
            
            if not credential or not credential.username:
                os.remove(playbook_filename)
                raise ValueError(f"主机 {host.name} 未配置认证凭据或用户名")
            
            # 构建 inventory 文件
            ansible_port = host.port or 22
            ansible_user = credential.username
            
            if credential.type == "password":
                # 密码认证 - 使用 paramiko 连接方式（支持密码认证）
                inventory_content = f"{host.ip_address} ansible_port={ansible_port} ansible_user={ansible_user} ansible_password={credential.password} ansible_connection=paramiko ansible_ssh_common_args='-o StrictHostKeyChecking=no'"
            else:
                # 密钥认证 - 写入密钥文件
                if credential.private_key:
                    ssh_key_file = f"/tmp/ssh_key_{uuid.uuid4().hex[:8]}"
                    with open(ssh_key_file, 'w') as f:
                        f.write(credential.private_key)
                    os.chmod(ssh_key_file, 0o600)
                    inventory_content = f"{host.ip_address} ansible_port={ansible_port} ansible_user={ansible_user} ansible_private_key_file={ssh_key_file} ansible_ssh_common_args='-o StrictHostKeyChecking=no'"
                else:
                    inventory_content = f"{host.ip_address} ansible_port={ansible_port} ansible_user={ansible_user} ansible_ssh_common_args='-o StrictHostKeyChecking=no'"
            
            with open(inventory_filename, 'w') as f:
                f.write(inventory_content)
            
            # 使用 paramiko 连接方式（更好的密码认证支持）
            ansible_cmd_parts.extend(["-i", inventory_filename, "-c", "paramiko"])
        else:
            # 本地执行
            ansible_cmd_parts.extend(["-i", "localhost,", "-c", "local"])
        
        # 添加额外变量文件
        if extra_vars_text:
            extra_vars_filename = f"/tmp/extra_vars_{uuid.uuid4().hex[:8]}.yml"
            with open(extra_vars_filename, 'w') as f:
                f.write(extra_vars_text)
            ansible_cmd_parts.extend(["-e", extra_vars_filename])
        
        # 添加详细输出参数（确保显示所有任务的 stdout）
        ansible_cmd_parts.append("-v")
        
        # 本地执行 ansible-playbook
        ansible_cmd = " ".join(ansible_cmd_parts)
        await self._send_ws_log("info", f"执行命令: {ansible_cmd}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                "bash", "-c", ansible_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "ANSIBLE_HOST_KEY_CHECKING": "False"}
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            output = stdout.decode() + stderr.decode()
            await self._send_ws_log("info", output)
        except asyncio.TimeoutError:
            process.kill()
            raise Exception(f"Playbook 执行超时（{timeout}秒）")
        finally:
            # 清理临时文件
            try:
                os.remove(playbook_filename)
                if inventory_filename:
                    os.remove(inventory_filename)
                if ssh_key_file:
                    os.remove(ssh_key_file)
                if extra_vars_text and 'extra_vars_filename' in locals():
                    os.remove(extra_vars_filename)
            except:
                pass
        
        return output or "Playbook 执行完成"

    async def _execute_loop(
        self,
        execution: FlowExecution,
        node: Dict[str, Any],
        config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """执行循环节点 - 遍历循环体节点"""
        loop_type = config.get("loop_type", "count")
        loop_var = config.get("loop_var", "item")
        fail_strategy = config.get("fail_strategy", "continue")  # stop, skip, continue

        if loop_type == "count":
            loop_count = config.get("loop_count", 1)
            items = list(range(loop_count))
        elif loop_type == "hosts":
            # 遍历主机列表
            result = await self.db.execute(select(Host))
            hosts = result.scalars().all()
            items = [h.ip_address for h in hosts]
        else:
            # loop_type == "array"
            loop_items = config.get("loop_items", "")
            if isinstance(loop_items, str):
                # 按换行或逗号分割
                items = [i.strip() for i in loop_items.replace("\n", ",").split(",") if i.strip()]
            else:
                items = loop_items if isinstance(loop_items, list) else []

        if not items:
            return "循环执行完成，共 0 次（无循环项）"

        await self._send_ws_log("info", f"开始循环执行，共 {len(items)} 次")
        
        results = []
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for i, item in enumerate(items):
            # 更新循环上下文
            context[loop_var] = item
            context[f"{loop_var}_index"] = i
            
            await self._send_ws_log("info", f"=== 循环 {i+1}/{len(items)}: {item} ===")
            
            # 注意：循环体的执行由主循环逻辑处理
            # 这里只是发送日志，实际执行在 execute_flow 方法中
            
            results.append({
                "index": i,
                "item": item,
                "status": "pending"
            })

        return f"循环执行完成，共 {len(items)} 次"

    async def _evaluate_condition(self, conditions: List[Dict], last_node_status: bool = True, context: Dict = None, logic: str = "or") -> str:
        """评估条件
        
        参数:
        - conditions: 条件列表
        - last_node_status: 上一个节点的执行状态 (True=成功, False=失败)
        - context: 变量上下文，用于获取变量值
        - logic: 逻辑关系 "and" 或 "or"
        
        返回值:
        - "条件判断通过": 走成功分支
        - "条件判断失败": 走失败分支
        
        支持的操作符:
        - == : 等于
        - != : 不等于
        - >  : 大于
        - <  : 小于
        - >= : 大于等于
        - <= : 小于等于
        """
        print(f"[DEBUG] _evaluate_condition 调用, context: {context}, last_node_status: {last_node_status}")
        if context is None:
            context = {}
            
        if not conditions:
            # 无条件，默认走成功分支
            return "条件判断通过"
        
        # 数值比较操作符
        numeric_operators = ['>', '<', '>=', '<=']
        
        results = []
        
        # 评估每个条件
        for condition in conditions:
            field = condition.get('field', '')
            operator = condition.get('operator', '==')
            value = condition.get('value', '')
            
            # 获取字段值
            if field == 'prev_node_status' or field == 'previous_status':
                field_value = 'success' if last_node_status else 'failed'
            elif field in context:
                # 从上下文变量获取值
                field_value = context[field]
            else:
                field_value = self._last_node_status.get(field)
            
            cond_result = False
            
            try:
                # 尝试数值比较
                if operator in numeric_operators:
                    num_field_value = float(field_value) if field_value is not None else 0
                    num_value = float(value)
                    
                    if operator == '>':
                        cond_result = num_field_value > num_value
                    elif operator == '<':
                        cond_result = num_field_value < num_value
                    elif operator == '>=':
                        cond_result = num_field_value >= num_value
                    elif operator == '<=':
                        cond_result = num_field_value <= num_value
                else:
                    # 字符串比较操作符
                    if operator == '==':
                        cond_result = str(field_value) == str(value)
                    elif operator == '!=':
                        cond_result = str(field_value) != str(value)
            except (ValueError, TypeError):
                # 如果无法转换为数值，回退到字符串比较
                if operator == '==':
                    cond_result = str(field_value) == str(value)
                elif operator == '!=':
                    cond_result = str(field_value) != str(value)
            
            results.append(cond_result)
        
        # 根据逻辑关系判断
        if logic == "and":
            # AND: 所有条件都满足
            if all(results):
                return "条件判断通过"
        else:
            # OR: 任一条件满足（默认）
            if any(results):
                return "条件判断通过"
        
        return "条件判断失败"

    async def _handle_file(
        self,
        action: str,
        source: str,
        destination: str,
        host_id: Optional[str]
    ) -> str:
        """处理文件操作"""
        if action == "push":
            cmd = f"ansible -m copy -a 'src={source} dest={destination}' -c local"
        else:
            cmd = f"ansible -m fetch -a 'src={source} dest={destination}' -c local"

        return await self._run_ansible_command(host_id, cmd)

    def _replace_variables(self, text: str, context: Dict) -> str:
        """替换文本中的变量"""
        if not text:
            return text
        for key, value in context.items():
            placeholder = f"${{{key}}}"
            if placeholder in text:
                text = text.replace(placeholder, str(value))
        return text

    async def _send_notification(self, channel: str, message: str, recipients: str = "", subject: str = "", context: Dict = None) -> str:
        """发送通知"""
        if context is None:
            context = {}
        
        # 替换变量
        message = self._replace_variables(message, context)
        subject = self._replace_variables(subject, context)
        recipients = self._replace_variables(recipients, context)
        
        if channel == "email":
            return await self._send_email(recipients, subject, message)
        elif channel == "wecom":
            return await self._send_wecom(message)
        elif channel == "dingtalk":
            return await self._send_dingtalk(message)
        return f"未知渠道: {channel}"

    async def _send_email(self, recipients: str, subject: str, message: str) -> str:
        """发送邮件"""
        if not recipients:
            return "邮件发送失败: 未配置收件人"
        if not message:
            return "邮件发送失败: 未配置邮件内容"
        
        # 如果没有主题，使用默认主题
        if not subject:
            subject = "流程执行通知"
        
        try:
            # 从系统设置获取 SMTP 配置
            from sqlalchemy import select
            from app.models.settings import SystemSettings
            result = await self.db.execute(select(SystemSettings))
            settings = result.scalar_one_or_none()
            
            if not settings or not settings.email_enabled:
                return "邮件发送失败: 邮件通知未启用或未配置"
            
            # 准备邮件
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = settings.smtp_from_email
            msg['To'] = recipients
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # 发送邮件
            if settings.smtp_use_tls:
                server = smtplib.SMTP_SSL(settings.smtp_host, int(settings.smtp_port))
            else:
                server = smtplib.SMTP(settings.smtp_host, int(settings.smtp_port))
            
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, recipients.split(','), msg.as_string())
            server.quit()
            
            return f"邮件已发送给: {recipients}，主题: {subject}"
        except smtplib.SMTPAuthenticationError as e:
            return "邮件发送失败: 认证错误，请检查用户名和密码（企业邮箱需使用授权码）"
        except smtplib.SMTPException as e:
            return f"邮件发送失败: SMTP错误 - {str(e)}"
        except Exception as e:
            return f"邮件发送失败: {str(e)}"

    async def _send_wecom(self, message: str) -> str:
        """发送企业微信通知"""
        try:
            from sqlalchemy import select
            from app.models.settings import SystemSettings
            result = await self.db.execute(select(SystemSettings))
            settings = result.scalar_one_or_none()
            
            if not settings or not settings.wecom_enabled:
                return "企业微信通知未启用或未配置"
            
            if not message:
                return "企业微信通知失败: 未配置消息内容"
            
            # 发送 WebHook 请求
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {"msgtype": "text", "text": {"content": message}}
                async with session.post(settings.wecom_webhook_url, json=payload) as resp:
                    if resp.status == 200:
                        return "企业微信通知已发送"
                    else:
                        return f"企业微信通知失败: {resp.status}"
        except Exception as e:
            return f"企业微信通知失败: {str(e)}"

    async def _send_dingtalk(self, message: str) -> str:
        """发送钉钉通知"""
        try:
            from sqlalchemy import select
            from app.models.settings import SystemSettings
            result = await self.db.execute(select(SystemSettings))
            settings = result.scalar_one_or_none()
            
            if not settings or not settings.dingtalk_enabled:
                return "钉钉通知未启用或未配置"
            
            if not message:
                return "钉钉通知失败: 未配置消息内容"
            
            # 发送 WebHook 请求
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {"msgtype": "text", "text": {"content": message}}
                async with session.post(settings.dingtalk_webhook_url, json=payload) as resp:
                    if resp.status == 200:
                        return "钉钉通知已发送"
                    else:
                        return f"钉钉通知失败: {resp.status}"
        except Exception as e:
            return f"钉钉通知失败: {str(e)}"

    async def _update_execution_status(
        self,
        execution: FlowExecution,
        status: str,
        message: str = None,
        result_summary: Dict = None
    ):
        """更新执行状态"""
        execution.status = status
        if status in ["success", "failed", "stopped"]:
            execution.finished_at = now()
        if result_summary:
            execution.result_summary = result_summary

        await self.db.commit()

        # WebSocket 推送
        if self.ws_manager and self._execution_id:
            await self.ws_manager.send_execution_update(
                self._execution_id,
                status,
                result_summary
            )

    async def _add_log(
        self,
        node_execution_id: str,
        level: str,
        message: str
    ):
        """添加执行日志"""
        log = ExecutionLog(
            execution_id=self._execution_id,
            node_execution_id=node_execution_id,
            level=level,
            message=message
        )
        self.db.add(log)
        await self.db.commit()

    async def _send_ws_update(
        self,
        node_id: str,
        status: str,
        output: str = None
    ):
        """发送 WebSocket 更新"""
        print(f"[WS] _send_ws_update: ws_manager={self.ws_manager is not None}, execution_id={self._execution_id}")
        if self.ws_manager and self._execution_id:
            await self.ws_manager.send_node_update(
                self._execution_id,
                node_id,
                status,
                output
            )

    async def _send_ws_log(self, level: str, message: str):
        """发送 WebSocket 日志"""
        print(f"[WS] _send_ws_log: ws_manager={self.ws_manager is not None}, execution_id={self._execution_id}, level={level}")
        if self.ws_manager and self._execution_id:
            await self.ws_manager.send_message(self._execution_id, {
                "type": "log",
                "level": level,
                "message": message
            })

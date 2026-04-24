<template>
  <div class="flow-editor">
    <!-- 顶部工具栏 -->
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
        <el-input
          v-model="flowName"
          class="flow-name-input"
          placeholder="输入流程名称"
        />
        <el-tag :type="flowStatusType">{{ flowStatusText }}</el-tag>
        <!-- 执行进度标签 -->
        <el-tag v-if="isExecuting" type="warning" class="execution-tag">
          <el-icon class="is-loading"><Loading /></el-icon>
          执行中
        </el-tag>
        <el-tag v-else-if="executionCompleted" :type="executionSuccess ? 'success' : 'danger'">
          {{ executionSuccess ? '执行成功' : '执行失败' }}
        </el-tag>
      </div>

      <div class="toolbar-center">
        <el-button-group>
          <el-button :icon="ZoomIn" @click="zoomIn">放大</el-button>
          <el-button :icon="ZoomOut" @click="zoomOut">缩小</el-button>
          <el-button :icon="FullScreen" @click="fitView">适应画布</el-button>
        </el-button-group>
        <el-button-group>
          <el-button :icon="RefreshLeft" @click="undo" :disabled="!canUndo">撤销</el-button>
          <el-button :icon="RefreshRight" @click="redo" :disabled="!canRedo">重做</el-button>
        </el-button-group>
      </div>

      <div class="toolbar-right">
        <el-button :icon="Check" @click="validateFlow">校验</el-button>
        <el-button :icon="Document" @click="saveFlow" :loading="saving">保存</el-button>
        <el-button type="primary" :icon="VideoPlay" @click="executeFlow" :loading="executing">
          执行
        </el-button>
        <el-button
          v-if="isExecuting"
          type="danger"
          :icon="Close"
          @click="stopExecution"
        >
          停止
        </el-button>
      </div>
    </div>

    <!-- 执行进度条 -->
    <div class="execution-progress" v-if="executionId">
      <div class="progress-info">
        <span>执行进度</span>
        <span class="progress-stats">
          <span class="stat success">成功: {{ successCount }}</span>
          <span class="stat failed">失败: {{ failedCount }}</span>
          <span class="stat running" v-if="isExecuting">执行中: {{ runningCount }}</span>
        </span>
      </div>
      <el-progress
        :percentage="progressPercentage"
        :status="progressStatus"
        :stroke-width="8"
        class="execution-progress-bar"
      />
    </div>

    <!-- 主体区域 -->
    <div class="editor-body">
      <!-- 左侧节点库 -->
      <div class="node-library">
        <div class="library-header">节点库</div>
        <div class="node-list">
          <div
            v-for="node in nodeLibraryConfig"
            :key="node.type"
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, node.type)"
          >
            <el-icon :style="{ color: node.color }">
              <component :is="node.icon" />
            </el-icon>
            <span>{{ node.label }}</span>
          </div>
        </div>

        <!-- 主机选择 -->
        <div class="library-section">
          <div class="section-header">主机选择</div>
          <el-select
            v-model="selectedHostId"
            placeholder="选择执行主机"
            clearable
            size="small"
          >
            <el-option-group label="主机组">
              <el-option
                v-for="group in hostGroups"
                :key="'group-' + group.id"
                :label="group.name"
                :value="'group-' + group.id"
              >
                <el-icon><Folder /></el-icon> {{ group.name }}
              </el-option>
            </el-option-group>
            <el-option-group label="单独主机">
              <el-option
                v-for="host in hosts"
                :key="host.id"
                :label="host.name"
                :value="host.id"
              >
                <el-icon><Monitor /></el-icon> {{ host.name }} ({{ host.ip_address }})
              </el-option>
            </el-option-group>
          </el-select>
        </div>
      </div>

      <!-- 流程画布 -->
      <div
        class="flow-canvas"
        @drop="onDrop"
        @dragover.prevent
      >
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          :default-viewport="{ zoom: 1 }"
          :connect-on-click="false"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @connect="onConnect"
        >
          <Background pattern-color="#aaa" :gap="16" />
          <Controls />
          <MiniMap />
        </VueFlow>

        <!-- 空状态 -->
        <div v-if="nodes.length === 0" class="empty-canvas">
          <el-icon :size="64"><Connection /></el-icon>
          <p>从左侧拖拽节点到此处开始设计流程</p>
        </div>
      </div>

      <!-- 右侧配置面板 -->
      <div class="config-panel" v-if="selectedNode">
        <div class="panel-header">
          <span>节点配置</span>
          <el-button :icon="Close" text @click="selectedNode = null" />
        </div>

        <el-form :model="selectedNode" label-position="top" class="config-form">
          <el-form-item label="节点名称">
            <el-input v-model="selectedNode.data.label" placeholder="输入节点名称" />
          </el-form-item>

          <el-form-item label="节点描述">
            <el-input
              v-model="selectedNode.data.description"
              type="textarea"
              :rows="2"
              placeholder="可选描述"
            />
          </el-form-item>

          <!-- 命令节点配置 -->
          <template v-if="selectedNode.type === 'command'">
            <el-form-item label="执行主机">
              <el-select 
                v-model="selectedNode.data.config.host_id" 
                placeholder="选择主机或输入变量"
                clearable
                filterable
                allow-create
                default-first-option
                style="width: 100%"
              >
                <el-option
                  v-for="host in hosts"
                  :key="host.id"
                  :label="`${host.name} (${host.ip_address})`"
                  :value="host.id"
                />
              </el-select>
              <div class="form-tip">可选择主机，或输入变量如 {{item}} 或 ${host}</div>
            </el-form-item>

            <el-form-item label="Ansible 命令">
              <el-input
                v-model="selectedNode.data.config.command"
                type="textarea"
                :rows="4"
                placeholder="yum install nginx -y"
              />
            </el-form-item>

            <el-form-item label="执行选项">
              <el-checkbox v-model="selectedNode.data.config.sudo">sudo 权限</el-checkbox>
              <el-checkbox v-model="selectedNode.data.config.ignore_errors">忽略错误</el-checkbox>
            </el-form-item>

            <el-form-item label="超时时间">
              <el-input-number
                v-model="selectedNode.data.config.timeout"
                :min="10"
                :max="3600"
                :step="10"
              />
              <span class="unit">秒</span>
            </el-form-item>
          </template>

          <!-- 脚本节点配置 -->
          <template v-else-if="selectedNode.type === 'script'">
            <el-form-item label="执行主机">
              <el-select 
                v-model="selectedNode.data.config.host_id" 
                placeholder="选择主机或输入变量"
                clearable
                filterable
                allow-create
                default-first-option
                style="width: 100%"
              >
                <el-option
                  v-for="host in hosts"
                  :key="host.id"
                  :label="`${host.name} (${host.ip_address})`"
                  :value="host.id"
                />
              </el-select>
              <div class="form-tip">可选择主机，或输入变量如 {{item}} 或 ${host}</div>
            </el-form-item>

            <el-form-item label="脚本类型">
              <el-select v-model="selectedNode.data.config.script_type">
                <el-option label="Shell" value="shell" />
                <el-option label="Python" value="python" />
                <el-option label="PowerShell" value="powershell" />
              </el-select>
            </el-form-item>

            <el-form-item label="脚本来源">
              <el-radio-group v-model="scriptSource" @change="handleScriptSourceChange">
                <el-radio label="input">手动输入</el-radio>
                <el-radio label="template">从模板选择</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="选择模板" v-if="scriptSource === 'template'">
              <el-select v-model="selectedTemplate" placeholder="选择模板" filterable @change="handleTemplateSelect">
                <el-option
                  v-for="t in scriptTemplates"
                  :key="t.id"
                  :label="t.name"
                  :value="t.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="脚本内容">
              <el-input
                v-model="selectedNode.data.config.script_content"
                type="textarea"
                :rows="8"
                placeholder="#!/bin/bash&#10;echo 'Hello World'"
              />
              <div class="input-tip" v-if="scriptSource === 'template'">已从模板加载，可根据需要修改</div>
            </el-form-item>

            <el-form-item label="脚本参数">
              <el-input
                v-model="selectedNode.data.config.args"
                placeholder="--env production"
              />
            </el-form-item>
          </template>

          <!-- 循环节点配置 -->
          <template v-else-if="selectedNode.type === 'loop'">
            <el-form-item label="循环类型">
              <el-select v-model="selectedNode.data.config.loop_type">
                <el-option label="遍历主机列表" value="hosts" />
                <el-option label="遍历数组" value="array" />
                <el-option label="固定次数" value="count" />
              </el-select>
            </el-form-item>

            <el-form-item label="循环变量名">
              <el-input v-model="selectedNode.data.config.loop_var" placeholder="item" />
              <div class="form-tip">在脚本中使用 &#123;&#123;变量名&#125;&#125; 或 ${变量名}</div>
            </el-form-item>

            <el-form-item label="循环次数" v-if="selectedNode.data.config.loop_type === 'count'">
              <el-input-number
                v-model="selectedNode.data.config.loop_count"
                :min="1"
                :max="100"
              />
            </el-form-item>

            <el-form-item label="主机列表" v-if="selectedNode.data.config.loop_type === 'array'">
              <el-input
                v-model="selectedNode.data.config.loop_items"
                type="textarea"
                :rows="4"
                placeholder="输入主机IP或名称，每行一个，或用逗号分隔
例如：
192.168.1.10
192.168.1.11
192.168.1.12"
              />
              <div class="form-tip">每行一个主机，或用逗号分隔</div>
            </el-form-item>

            <el-form-item label="失败策略">
              <el-select v-model="selectedNode.data.config.fail_strategy">
                <el-option label="失败继续（continue）" value="continue" />
                <el-option label="失败跳过（skip）" value="skip" />
                <el-option label="失败停止（break）" value="stop" />
              </el-select>
              <div class="form-tip">
                <span style="color: #67c23a;">继续</span>：当前次失败后继续执行下次循环<br/>
                <span style="color: #e6a23c;">跳过</span>：当前次失败后跳过本次，进入下次循环<br/>
                <span style="color: #f56c6c;">停止</span>：当前次失败后终止整个循环
              </div>
            </el-form-item>
          </template>

          <!-- 变量设置节点配置 -->
          <template v-else-if="selectedNode.type === 'variable'">
            <el-form-item label="变量定义">
              <el-input
                v-model="selectedNode.data.config.variables"
                type="textarea"
                :rows="6"
                placeholder="定义流程变量，格式: key=value
示例:
host=192.168.1.10
user=admin
port=22

或使用冒号分隔:
host: 192.168.1.10
user: admin"
              />
              <div class="form-tip">
                <b>定义变量格式:</b><br/>
                key=value 或 key: value<br/>
                使用 ${变量名} 或 {{变量名}} 在其他节点中引用
              </div>
              <div class="form-tip" style="margin-top: 12px; background: #fdf6ec; padding: 10px; border-radius: 4px;">
                <b>从命令/脚本输出提取变量格式:</b><br/>
                <code>__SET_VAR__key=value</code><br/>
                <code>export key=value</code><br/>
                <code>RESULT=success</code>
              </div>
            </el-form-item>
          </template>

          <!-- 等待节点配置 -->
          <template v-else-if="selectedNode.type === 'wait'">
            <el-form-item label="等待时间">
              <el-input-number
                v-model="selectedNode.data.config.wait_seconds"
                :min="1"
                :max="3600"
              />
              <span class="unit">秒</span>
            </el-form-item>
          </template>

          <!-- Playbook 节点配置 -->
          <template v-else-if="selectedNode.type === 'playbook'">
            <el-form-item label="执行主机">
              <el-select 
                v-model="selectedNode.data.config.host_id" 
                placeholder="选择主机或输入变量"
                clearable
                filterable
                allow-create
                default-first-option
                style="width: 100%"
              >
                <el-option
                  v-for="host in hosts"
                  :key="host.id"
                  :label="`${host.name} (${host.ip_address})`"
                  :value="host.id"
                />
              </el-select>
              <div class="form-tip">可选择主机，或输入变量如 {{item}} 或 ${host}</div>
            </el-form-item>

            <el-form-item label="Playbook 来源">
              <el-radio-group v-model="playbookSource" @change="handlePlaybookSourceChange">
                <el-radio label="input">手动输入</el-radio>
                <el-radio label="template">从模板选择</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="选择模板" v-if="playbookSource === 'template'">
              <el-select v-model="selectedPlaybook" placeholder="选择 Playbook" filterable @change="handlePlaybookSelect">
                <el-option
                  v-for="pb in playbooks"
                  :key="pb.id"
                  :label="pb.name"
                  :value="pb.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="Playbook 内容">
              <el-input
                v-model="selectedNode.data.config.playbook_content"
                type="textarea"
                :rows="8"
                placeholder="- hosts: all&#10;  tasks:&#10;    - name: 示例任务"
                class="code-input"
              />
              <div class="input-tip" v-if="playbookSource === 'template'">已从模板加载，可根据需要微调</div>
            </el-form-item>

            <el-form-item label="额外变量">
              <el-input
                v-model="selectedNode.data.config.extra_vars_text"
                type="textarea"
                :rows="4"
                placeholder="var1: value1&#10;var2: value2"
                class="code-input"
              />
            </el-form-item>
          </template>

          <!-- 通知节点配置 -->
          <template v-else-if="selectedNode.type === 'notify'">
            <el-form-item label="通知渠道">
              <el-select v-model="selectedNode.data.config.channel">
                <el-option label="邮件" value="email" />
                <el-option label="企业微信" value="wecom" />
                <el-option label="钉钉" value="dingtalk" />
              </el-select>
            </el-form-item>

            <!-- 邮件配置 -->
            <template v-if="selectedNode.data.config.channel === 'email'">
              <el-form-item label="收件人" required>
                <el-input
                  v-model="selectedNode.data.config.recipients"
                  placeholder="user@example.com, user2@example.com"
                />
                <div class="form-tip">多个收件人用逗号分隔</div>
              </el-form-item>
              <el-form-item label="邮件主题" required>
                <el-input
                  v-model="selectedNode.data.config.subject"
                  placeholder="流程执行通知"
                />
              </el-form-item>
              <el-form-item label="邮件内容" required>
                <el-input
                  v-model="selectedNode.data.config.message"
                  type="textarea"
                  :rows="4"
                  placeholder="流程「${flow_name}」执行完成，结果：${result}"
                />
                <div class="form-tip">支持变量：${flow_name}, ${result}, ${start_time}, ${end_time}</div>
              </el-form-item>
            </template>

            <!-- 企业微信配置 -->
            <template v-else-if="selectedNode.data.config.channel === 'wecom'">
              <el-form-item label="通知内容" required>
                <el-input
                  v-model="selectedNode.data.config.message"
                  type="textarea"
                  :rows="3"
                  placeholder="流程「${flow_name}」执行完成"
                />
              </el-form-item>
            </template>

            <!-- 钉钉配置 -->
            <template v-else-if="selectedNode.data.config.channel === 'dingtalk'">
              <el-form-item label="通知内容" required>
                <el-input
                  v-model="selectedNode.data.config.message"
                  type="textarea"
                  :rows="3"
                  placeholder="流程「${flow_name}」执行完成"
                />
              </el-form-item>
            </template>
          </template>

          <!-- 并行分支配置 -->
          <template v-else-if="selectedNode.type === 'parallel'">
            <el-form-item label="说明">
              <span style="color: #909399; font-size: 12px;">
                并行分支会将后续的多条链路同时执行，各链路互不影响，任一链路失败不会中断其他链路。
              </span>
            </el-form-item>
            <el-form-item label="失败策略">
              <el-select v-model="selectedNode.data.config.fail_strategy">
                <el-option label="全部完成" value="all" />
                <el-option label="任一成功即可" value="any" />
                <el-option label="收集结果（不中断）" value="collect" />
              </el-select>
            </el-form-item>
            <el-form-item label="并发数限制">
              <el-input-number 
                v-model="selectedNode.data.config.max_parallel" 
                :min="1" 
                :max="10"
              />
              <div class="form-tip">限制同时执行的分支数量，0 表示不限制</div>
            </el-form-item>
          </template>

          <!-- 条件分支配置 -->
          <template v-else-if="selectedNode.type === 'condition'">
            <el-form-item label="说明">
              <span style="color: #909399; font-size: 12px;">
                条件分支根据变量值或节点执行结果决定走哪个分支：
              </span>
            </el-form-item>
            
            <el-form-item label="变量条件">
              <div class="condition-list">
                <div 
                  v-for="(cond, index) in selectedNode.data.config.conditions" 
                  :key="index"
                  class="condition-item"
                >
                  <el-select 
                    v-model="cond.field" 
                    placeholder="输入变量名"
                    style="width: 120px"
                    clearable
                    filterable
                    allow-create
                    default-first-option
                    :reserve-keyword="false"
                  >
                    <el-option label="prev_status" value="prev_node_status" />
                  </el-select>
                  
                  <el-select 
                    v-model="cond.operator" 
                    placeholder="操作符"
                    style="width: 80px; margin-left: 8px"
                  >
                    <el-option label="==" value="==" title="等于" />
                    <el-option label="!=" value="!=" title="不等于" />
                    <el-option label=">" value=">" title="大于" />
                    <el-option label="<" value="<" title="小于" />
                    <el-option label=">=" value=">=" title="大于等于" />
                    <el-option label="<=" value="<=" title="小于等于" />
                  </el-select>
                  
                  <el-input 
                    v-model="cond.value" 
                    placeholder="值"
                    style="width: 100px; margin-left: 8px"
                  />
                  
                  <el-button 
                    type="danger" 
                    link 
                    @click="removeCondition(index)"
                    style="margin-left: 8px"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                
                <el-button 
                  type="primary" 
                  link 
                  @click="addCondition"
                  style="margin-top: 8px"
                >
                  <el-icon><Plus /></el-icon>
                  添加条件
                </el-button>
              </div>
              <div class="form-tip">
                支持数值比较：> < >= <= 和字符串比较：== !=<br/>
                变量示例：cpu_usage, memory_percent, count 等
              </div>
            </el-form-item>
            
            <el-form-item label="条件逻辑" v-if="selectedNode.data.config.conditions && selectedNode.data.config.conditions.length > 1">
              <el-radio-group v-model="selectedNode.data.config.logic">
                <el-radio value="or">OR (任一满足)</el-radio>
                <el-radio value="and">AND (全部满足)</el-radio>
              </el-radio-group>
              <div class="form-tip">
                <span style="color: #67c23a;">OR</span>: 任一条件满足即可走成功分支<br/>
                <span style="color: #409eff;">AND</span>: 所有条件都满足才走成功分支
              </div>
            </el-form-item>
            
            <el-form-item label="默认行为">
              <el-select v-model="selectedNode.data.config.default_branch">
                <el-option label="走成功分支" value="success" />
                <el-option label="走失败分支" value="failed" />
                <el-option label="都走（无条件）" value="both" />
              </el-select>
              <div class="form-tip">当所有条件都不满足时的默认行为</div>
            </el-form-item>
            
            <el-form-item label="成功分支">
              <div class="branch-hint success">
                <el-icon><CircleCheck /></el-icon>
                <span>连接绿色的成功 Handle</span>
              </div>
            </el-form-item>
            <el-form-item label="失败分支">
              <div class="branch-hint fail">
                <el-icon><CircleClose /></el-icon>
                <span>连接红色的失败 Handle</span>
              </div>
            </el-form-item>
          </template>

          <!-- 注释节点配置 -->
          <template v-else-if="selectedNode.type === 'comment'">
            <el-form-item label="注释内容">
              <el-input
                v-model="selectedNode.data.config.comment"
                type="textarea"
                :rows="4"
                placeholder="添加流程说明..."
              />
            </el-form-item>
          </template>

          <el-divider />

          <el-form-item>
            <el-button type="danger" @click="deleteNode(selectedNode)">删除节点</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, markRaw, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  VueFlow,
  useVueFlow, Position, MarkerType, applyNodeChanges
} from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import {
  ArrowLeft, Check, VideoPlay, Document,
  ZoomIn, ZoomOut, FullScreen, RefreshLeft, RefreshRight, Close,
  Folder, Monitor, Connection, Cpu, Tickets, DocumentCopy,
  Clock, Bell, ChatLineSquare, Refresh, Operation, Loading, VideoPause,
  CircleCheck, CircleClose, CaretRight, Flag, Setting, Delete, Plus
} from '@element-plus/icons-vue'

// 节点库配置（用于显示）
const nodeLibraryConfig = [
  { type: 'start', label: '开始节点', icon: markRaw(CaretRight), color: '#67C23A' },
  { type: 'variable', label: '变量设置', icon: markRaw(Setting), color: '#409EFF' },
  { type: 'command', label: '命令节点', icon: markRaw(Cpu), color: '#409EFF' },
  { type: 'script', label: '脚本节点', icon: markRaw(Document), color: '#67C23A' },
  { type: 'playbook', label: 'Playbook', icon: markRaw(Tickets), color: '#E6A23C' },
  { type: 'loop', label: '循环节点', icon: markRaw(Refresh), color: '#9B59B6' },
  { type: 'condition', label: '条件分支', icon: markRaw(Operation), color: '#F56C6C' },
  { type: 'parallel', label: '并行分支', icon: markRaw(VideoPause), color: '#909399' },
  { type: 'wait', label: '等待节点', icon: markRaw(Clock), color: '#909399' },
  { type: 'notify', label: '通知节点', icon: markRaw(Bell), color: '#E6A23C' },
  { type: 'end', label: '结束节点', icon: markRaw(Flag), color: '#F56C6C' },
  { type: 'comment', label: '注释节点', icon: markRaw(ChatLineSquare), color: '#67C23A' }
]

import { useFlowStore } from '@/stores/flow'
import { getFlow, createFlow, saveFlowDesign, executeFlow as execFlow } from '@/services/flow'
import { getHosts, getHostGroups } from '@/services/host'
import { getPlaybooks, getScripts } from '@/services/templates'
import { useExecutionWebSocket } from '@/services/websocket'
import { stopExecution as stopExecApi } from '@/services/execution'

// 引入自定义节点组件
import CommandNode from '@/components/FlowEditor/nodes/CommandNode.vue'
import ScriptNode from '@/components/FlowEditor/nodes/ScriptNode.vue'
import PlaybookNode from '@/components/FlowEditor/nodes/PlaybookNode.vue'
import LoopNode from '@/components/FlowEditor/nodes/LoopNode.vue'
import ConditionNode from '@/components/FlowEditor/nodes/ConditionNode.vue'
import ParallelNode from '@/components/FlowEditor/nodes/ParallelNode.vue'
import WaitNode from '@/components/FlowEditor/nodes/WaitNode.vue'
import NotifyNode from '@/components/FlowEditor/nodes/NotifyNode.vue'
import CommentNode from '@/components/FlowEditor/nodes/CommentNode.vue'
import StartNode from '@/components/FlowEditor/nodes/StartNode.vue'
import EndNode from '@/components/FlowEditor/nodes/EndNode.vue'
import VariableNode from '@/components/FlowEditor/nodes/VariableNode.vue'

const router = useRouter()
const route = useRoute()
const flowStore = useFlowStore()

const {
  zoomIn: vueFlowZoomIn,
  zoomOut: vueFlowZoomOut,
  fitView,
  canUndo,
  canRedo
} = useVueFlow()

// undo/redo 需要手动实现，vue-flow 默认不提供
const undo = () => {
  ElMessage.info('撤销功能开发中')
}

const redo = () => {
  ElMessage.info('重做功能开发中')
}

// 注册自定义节点类型
const nodeTypes = {
  command: markRaw(CommandNode),
  script: markRaw(ScriptNode),
  playbook: markRaw(PlaybookNode),
  loop: markRaw(LoopNode),
  condition: markRaw(ConditionNode),
  start: markRaw(StartNode),
  end: markRaw(EndNode),
  parallel: markRaw(ParallelNode),
  wait: markRaw(WaitNode),
  notify: markRaw(NotifyNode),
  comment: markRaw(CommentNode),
  variable: markRaw(VariableNode)
}

// 状态
const flowId = ref(route.params.id)
const flowName = ref('')
const flowStatus = ref('draft')
const saving = ref(false)
const executing = ref(false)
const selectedNode = ref(null)
const selectedHostId = ref(null)
const hosts = ref([])
const hostGroups = ref([])
const playbooks = ref([])
const scriptTemplates = ref([])
const scriptSource = ref('input')
const selectedTemplate = ref(null)
const playbookSource = ref('template')
const selectedPlaybook = ref(null)

// 执行状态
const executionId = ref(null)
const executionStatus = ref(null)
const nodeExecutionStatuses = ref({})  // { nodeId: status }

// WebSocket
const { isConnected: wsConnected, connect, disconnect, on, off } = useExecutionWebSocket()

// 节点和连线
const nodes = ref([])
const edges = ref([])

// 计算属性
const flowStatusType = computed(() => {
  const map = { draft: 'info', published: 'success' }
  return map[flowStatus.value] || 'info'
})

const flowStatusText = computed(() => {
  const map = { draft: '草稿', published: '已发布' }
  return map[flowStatus.value] || '草稿'
})

// 执行状态计算属性
const isExecuting = computed(() => executionStatus.value === 'running' || executionStatus.value === 'pending')

const executionCompleted = computed(() => ['success', 'failed', 'stopped'].includes(executionStatus.value))

const executionSuccess = computed(() => executionStatus.value === 'success')

const successCount = computed(() =>
  Object.values(nodeExecutionStatuses.value).filter(s => s === 'success').length
)

const failedCount = computed(() =>
  Object.values(nodeExecutionStatuses.value).filter(s => s === 'failed').length
)

const runningCount = computed(() =>
  Object.values(nodeExecutionStatuses.value).filter(s => s === 'running').length
)

const progressPercentage = computed(() => {
  if (nodes.value.length === 0) return 0
  const completed = Object.values(nodeExecutionStatuses.value).filter(
    s => ['success', 'failed', 'stopped'].includes(s)
  ).length
  return Math.round((completed / nodes.value.length) * 100)
})

const progressStatus = computed(() => {
  if (failedCount.value > 0) return 'exception'
  if (progressPercentage.value === 100) return 'success'
  return undefined
})

// 更新节点执行状态
function updateNodeExecutionStatus(nodeId, status) {
  nodeExecutionStatuses.value[nodeId] = status
  
  // 查找节点
  const nodeIndex = nodes.value.findIndex(n => n.id === nodeId)
  if (nodeIndex !== -1) {
    // 使用 applyNodeChanges 方式更新，确保 Vue-Flow 能正确响应
    const updatedNode = {
      ...nodes.value[nodeIndex],
      data: {
        ...nodes.value[nodeIndex].data,
        status: status
      }
    }
    
    // 创建新数组触发响应式更新
    const newNodes = [...nodes.value]
    newNodes[nodeIndex] = updatedNode
    nodes.value = newNodes
    
    console.log('[FlowEditor] updateNodeExecutionStatus:', nodeId, status)
  }
}

// 清除执行状态
function clearExecutionStatus() {
  executionId.value = null
  executionStatus.value = null
  nodeExecutionStatuses.value = {}
  // 使用新数组触发响应式更新
  nodes.value = nodes.value.map(node => ({
    ...node,
    data: {
      ...node.data,
      status: null
    }
  }))
}

// 处理 WebSocket 消息
function handleWsMessage(data) {
  console.log('[FlowEditor] WS message:', data)
  
  // 兼容后端发送的 node_id 和 nodeId 两种格式
  const nodeId = data.nodeId || data.node_id
  
  if (data.type === 'node_update' && nodeId) {
    // nodeUpdate 事件
    updateNodeExecutionStatus(nodeId, data.status)
  } else if (nodeId && data.status) {
    // 直接发送 nodeId 和 status 的格式
    updateNodeExecutionStatus(nodeId, data.status)
  }
  
  if (data.type === 'execution_update' || (data.status && !nodeId)) {
    // executionUpdate 事件
    executionStatus.value = data.status
    if (data.status === 'success' || data.status === 'failed') {
      ElMessage({
        type: data.status === 'success' ? 'success' : 'error',
        message: data.status === 'success' ? '流程执行成功' : '流程执行失败'
      })
    }
  }
}

// 轮询获取执行状态（备用方案）
let pollInterval = null

async function pollExecutionStatus() {
  if (!executionId.value) return
  
  try {
    const { getExecution, getExecutionNodes } = await import('@/services/execution')
    const [execRes, nodesRes] = await Promise.all([
      getExecution(executionId.value),
      getExecutionNodes(executionId.value)
    ])
    
    console.log('[FlowEditor] Poll response:', { execRes, nodesRes })
    
    // 更新节点状态
    if (nodesRes && Array.isArray(nodesRes)) {
      console.log('[FlowEditor] Updating nodes:', nodesRes.length, 'nodes')
      nodesRes.forEach(node => {
        // 兼容 snake_case 和 camelCase
        const backendNodeId = node.nodeId || node.node_id
        console.log('[FlowEditor] Backend node_id:', backendNodeId, 'status:', node.status)
        
        // 后端返回的是纯数字 ID，前端节点 ID 是 node-xxx 格式
        // 需要尝试两种匹配方式
        let nodeIndex = nodes.value.findIndex(n => n.id === backendNodeId)
        
        // 如果没找到，尝试匹配 node-{backendNodeId}
        if (nodeIndex === -1) {
          nodeIndex = nodes.value.findIndex(n => n.id === `node-${backendNodeId}`)
        }
        
        // 如果还没找到，尝试后端 ID 包含 node- 前缀的情况
        if (nodeIndex === -1 && backendNodeId && backendNodeId.toString().startsWith('node-')) {
          const pureId = backendNodeId.toString().replace('node-', '')
          nodeIndex = nodes.value.findIndex(n => n.id === pureId || n.id === backendNodeId)
        }
        
        console.log('[FlowEditor] Found nodeIndex:', nodeIndex)
        
        if (nodeIndex !== -1) {
          const nodeId = nodes.value[nodeIndex].id
          nodeExecutionStatuses.value[nodeId] = node.status
          
          // 创建新数组触发响应式更新
          const updatedNode = {
            ...nodes.value[nodeIndex],
            data: {
              ...nodes.value[nodeIndex].data,
              status: node.status
            }
          }
          const newNodes = [...nodes.value]
          newNodes[nodeIndex] = updatedNode
          nodes.value = newNodes
          
          console.log('[FlowEditor] Updated node:', nodeId, 'to status:', node.status)
        }
      })
    }
    
    // 更新执行状态
    if (execRes.status !== 'running' && execRes.status !== 'pending') {
      executionStatus.value = execRes.status
      if (execRes.status === 'success' || execRes.status === 'failed') {
        ElMessage({
          type: execRes.status === 'success' ? 'success' : 'error',
          message: execRes.status === 'success' ? '流程执行成功' : '流程执行失败'
        })
      }
      stopPolling()
    }
  } catch (error) {
    console.error('轮询执行状态失败:', error)
  }
}

function startPolling() {
  if (pollInterval) return
  pollInterval = setInterval(pollExecutionStatus, 3000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

// 停止执行
async function stopExecution() {
  if (!executionId.value) return
  try {
    await stopExecApi(executionId.value)
    ElMessage.success('已发送停止指令')
    executionStatus.value = 'stopped'
  } catch (error) {
    ElMessage.error('停止执行失败')
  }
}

const zoomIn = () => vueFlowZoomIn()
const zoomOut = () => vueFlowZoomOut()

function goBack() {
  router.push('/flows')
}

// 条件节点方法
function addCondition() {
  if (!selectedNode.value.data.config.conditions) {
    selectedNode.value.data.config.conditions = []
  }
  selectedNode.value.data.config.conditions.push({
    field: '',
    operator: '==',
    value: ''
  })
}

function removeCondition(index) {
  selectedNode.value.data.config.conditions.splice(index, 1)
}

function onDragStart(event, type) {
  event.dataTransfer.setData('nodeType', type)
  event.dataTransfer.effectAllowed = 'move'
}

function onDrop(event) {
  const type = event.dataTransfer.getData('nodeType')
  if (!type) return

  const rect = event.currentTarget.getBoundingClientRect()
  const position = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }

  const config = flowStore.nodeTypes[type]
  const newNode = {
    id: `node-${Date.now()}`,
    type,
    position,
    data: {
      label: config?.label || type,
      description: '',
      config: {
        host_id: selectedHostId.value,
        ...getDefaultConfig(type)
      }
    },
    sourcePosition: Position.Right,
    targetPosition: Position.Left
  }

  nodes.value.push(newNode)
}

function getDefaultConfig(type) {
  const defaults = {
    command: { command: '', sudo: false, ignore_errors: false, timeout: 60 },
    script: { script_type: 'shell', script_content: '', args: '' },
    playbook: { playbook_id: null, extra_vars: {} },
    file: { action: 'push', source: '', destination: '' },
    loop: { loop_type: 'count', loop_var: 'item', loop_count: 1 },
    condition: { conditions: [], logic: 'or' },
    parallel: { fail_strategy: 'all', max_parallel: 0 },
    wait: { wait_seconds: 10 },
    notify: { channel: 'email', recipients: '', subject: '', message: '' },
    comment: { comment: '' },
    variable: { variables: '' }
  }
  return defaults[type] || {}
}

function onNodeClick(event) {
  selectedNode.value = event.node
}

function onEdgeClick(event) {
  // 可以显示连线配置
}

function onConnect(params) {
  console.log('[DEBUG] onConnect params:', params)
  
  const newEdge = {
    id: `edge-${Date.now()}`,
    source: params.source,
    target: params.target,
    sourceHandle: params.sourceHandle,
    targetHandle: params.targetHandle,
    type: 'smoothstep',
    animated: true,
    markerEnd: MarkerType.ArrowClosed,
    style: { stroke: '#409EFF', strokeWidth: 2 }
  }
  console.log('[DEBUG] 创建新边:', newEdge)
  edges.value.push(newEdge)
}

function onPaneContextMenu(event) {
  // 右键菜单
}

function onNodesChange(changes) {
  // 处理节点变化
}

function onEdgesChange(changes) {
  // 处理连线变化
}

function deleteNode(node) {
  ElMessageBox.confirm('确定要删除该节点吗？', '提示', { type: 'warning' })
    .then(() => {
      nodes.value = nodes.value.filter(n => n.id !== node.id)
      edges.value = edges.value.filter(e => e.source !== node.id && e.target !== node.id)
      selectedNode.value = null
    })
    .catch(() => {})
}

async function validateFlow() {
  if (nodes.value.length === 0) {
    ElMessage.warning('请先添加节点')
    return
  }
  // 简单校验
  const unconfiguredNodes = nodes.value.filter(n => {
    if (n.type === 'comment') return false
    return !n.data.config?.command && !n.data.config?.script_content
  })

  if (unconfiguredNodes.length > 0) {
    ElMessage.error(`有 ${unconfiguredNodes.length} 个节点未配置`)
    return
  }

  ElMessage.success('流程校验通过')
}

// 处理脚本来源变化
function handleScriptSourceChange(source) {
  if (source === 'template') {
    selectedTemplate.value = null
  } else {
    selectedTemplate.value = null
    if (selectedNode.value?.data?.config) {
      selectedNode.value.data.config.template_id = null
    }
  }
}

// 处理模板选择
function handleTemplateSelect(templateId) {
  const template = scriptTemplates.value.find(t => t.id === templateId)
  if (template && selectedNode.value?.data?.config) {
    selectedNode.value.data.config.template_id = templateId
    selectedNode.value.data.config.script_content = template.content || ''
    selectedNode.value.data.config.script_type = template.script_type || 'shell'
  }
}

// 处理 Playbook 来源变化
function handlePlaybookSourceChange(source) {
  if (source === 'template') {
    selectedPlaybook.value = null
  } else {
    selectedPlaybook.value = null
    if (selectedNode.value?.data?.config) {
      selectedNode.value.data.config.playbook_id = null
    }
  }
}

// 处理 Playbook 选择
function handlePlaybookSelect(pbId) {
  const playbook = playbooks.value.find(p => p.id === pbId)
  if (playbook && selectedNode.value?.data?.config) {
    selectedNode.value.data.config.playbook_id = pbId
    selectedNode.value.data.config.playbook_content = playbook.content || ''
  }
}

async function saveFlow() {
  if (!flowName.value) {
    ElMessage.warning('请输入流程名称')
    return
  }

  // 调试：检查边的数据
  console.log('[DEBUG] 保存流程，edges 数据:', JSON.stringify(edges.value, null, 2))

  saving.value = true
  try {
    const flowData = {
      name: flowName.value,
      description: '',
      flow_data: {
        nodes: nodes.value,
        edges: edges.value
      }
    }

    if (flowId.value) {
      // 更新已有流程
      await saveFlowDesign(flowId.value, {
        name: flowName.value,
        flow_data: flowData.flow_data
      })
    } else {
      // 创建新流程
      const res = await createFlow(flowData)
      flowId.value = res.id
      router.replace({ name: 'FlowEditor', params: { id: res.id } })
    }

    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function executeFlow() {
  executing.value = true
  try {
    // 先保存流程
    await saveFlow()
    
    // 执行流程
    const res = await execFlow(flowId.value)
    executionId.value = res.execution_id
    executionStatus.value = 'running'
    
    // 连接 WebSocket 监听执行进度
    connect(executionId.value)
    on('nodeUpdate', handleWsMessage)
    on('executionUpdate', handleWsMessage)
    
    // 启动轮询作为备用
    startPolling()
    
    ElMessage.success('流程已开始执行')
  } catch (error) {
    console.error('执行失败:', error)
    ElMessage.error(error?.response?.data?.detail || '执行失败')
    executionStatus.value = 'failed'
  } finally {
    executing.value = false
  }
}

onMounted(async () => {
  // 加载主机列表和模板
  try {
    const [hostsRes, groupsRes, playbooksRes, scriptsRes] = await Promise.all([
      getHosts(),
      getHostGroups(),
      getPlaybooks({ page_size: 100 }),
      getScripts({ page_size: 100 })
    ])
    hosts.value = hostsRes.items || []
    hostGroups.value = groupsRes.items || []
    playbooks.value = playbooksRes.items || []
    scriptTemplates.value = scriptsRes.items || []
  } catch (error) {
    console.error('加载数据失败', error)
  }

  // 加载流程数据
  if (flowId.value) {
    try {
      const res = await getFlow(flowId.value)
      flowName.value = res.name
      flowStatus.value = res.status
      if (res.flow_data) {
        // 兼容嵌套结构 flow_data.flow_data.nodes
        const flowData = res.flow_data.flow_data || res.flow_data
        // 清除所有节点的状态，确保打开流程时没有残留的执行状态图标
        nodes.value = (flowData.nodes || []).map(node => ({
          ...node,
          data: {
            ...node.data,
            status: null  // 关键：清除执行状态
          }
        }))
        edges.value = flowData.edges || []
        
        // 调试：检查加载的边数据
        console.log('[DEBUG] 加载流程，edges 数据:', JSON.stringify(edges.value, null, 2))
      }
      
      // 检查是否有正在执行的流程
      if (res.current_execution && res.current_execution.status === 'running') {
        executionId.value = res.current_execution.id
        executionStatus.value = res.current_execution.status
        // 连接 WebSocket 继续监听
        connect(executionId.value)
        on('nodeUpdate', handleWsMessage)
        on('executionUpdate', handleWsMessage)
      }
    } catch (error) {
      ElMessage.error('加载流程失败')
    }
  }
})

onUnmounted(() => {
  // 清理 WebSocket 连接
  disconnect()
  off('nodeUpdate', handleWsMessage)
  off('executionUpdate', handleWsMessage)
  stopPolling()
})
</script>

<style lang="scss" scoped>
.flow-editor {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
}

.editor-toolbar {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;

  .toolbar-left,
  .toolbar-center,
  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .flow-name-input {
    width: 200px;
  }

  .execution-tag {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.execution-progress {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  padding: 12px 16px;

  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 13px;
    color: #666;

    .progress-stats {
      display: flex;
      gap: 16px;

      .stat {
        &.success { color: #67c23a; }
        &.failed { color: #f56c6c; }
        &.running { color: #e6a23c; }
      }
    }
  }

  .execution-progress-bar {
    width: 100%;
  }
}

.editor-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.node-library {
  width: 240px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;

  .library-header {
    padding: 16px;
    font-weight: bold;
    border-bottom: 1px solid #e8e8e8;
  }

  .node-list {
    padding: 12px;
    flex: 1;
    overflow-y: auto;

    .node-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      margin-bottom: 8px;
      background: #f5f7fa;
      border-radius: 6px;
      cursor: grab;
      transition: all 0.2s;

      &:hover {
        background: #e8e8e8;
        transform: translateX(4px);
      }

      .el-icon {
        font-size: 18px;
      }

      span {
        font-size: 13px;
      }
    }
  }

  .library-section {
    border-top: 1px solid #e8e8e8;
    padding: 12px;

    .section-header {
      font-weight: bold;
      font-size: 13px;
      margin-bottom: 8px;
    }
  }
}

.flow-canvas {
  flex: 1;
  position: relative;
  background: #fafafa;

  .empty-canvas {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: #999;

    .el-icon {
      font-size: 64px;
      margin-bottom: 16px;
    }
  }
}

.config-panel {
  width: 320px;
  background: #fff;
  border-left: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;

  .panel-header {
    padding: 16px;
    font-weight: bold;
    border-bottom: 1px solid #e8e8e8;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .config-form {
    padding: 16px;
    flex: 1;
    overflow-y: auto;

    .unit {
      margin-left: 8px;
      color: #999;
    }

    .input-tip {
      font-size: 12px;
      color: #67c23a;
      margin-top: 4px;
    }

    .branch-hint {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 12px;

      &.success {
        background: #f0f9eb;
        color: #67c23a;
      }

      &.fail {
        background: #fef0f0;
        color: #f56c6c;
      }
    }

    .condition-list {
      width: 100%;
      
      .condition-item {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        flex-wrap: wrap;
      }
    }

    :deep(.vue-flow__node) {
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 14px;
      border: 2px solid;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      }
    }
  }
}
</style>

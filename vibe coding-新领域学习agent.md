# 📘 领域精通型自适应教学多Agent系统架构设计文档
**架构师视角输出 | 版本：v1.0 | 架构范式：Claude Code 启发 + LangGraph 状态驱动多Agent协同**

---

## 1. 系统定位与核心设计哲学
### 1.1 设计目标
构建一套**项目级、状态可追溯、领域自适应、父子协同**的AI教学架构。用户仅需输入一个领域名称（如 `Rust 高性能编程` / `认知行为疗法` / `量化交易`），系统自动完成：资料搜集 → 领域特征分析 → 动态生成教学大纲 → 分阶段授课 → 实时进度监督 → 实战沙箱 → 参考答案与纠错 → 能力跃迁。

### 1.2 Claude Code 架构映射
本系统深度借鉴 Anthropic Claude Code 的架构思想，并迁移至教学场景：

| Claude Code 特性 | 本系统映射实现 |
| :--- | :--- |
| **项目级文件系统上下文** | 采用 `.learn/` 目录驱动，所有状态、知识、大纲、进度、技能配置均以文件形式持久化，支持透明追溯与人工干预 |
| **工具调用与沙箱执行隔离** | 所有代码/环境实战在 E2B/Docker 沙箱运行，评估结果结构化回写 |
| **显式状态机与检查点** | LangGraph 管理状态流转，每阶段生成 `checkpoint.json`，支持断点续学、进度回滚 |
| **模块化 Prompt/Skill 注入** | 动态生成 `.skills/*.yaml`，运行时热加载至子 Agent，实现“不同领域/阶段不同人格与能力边界” |
| **迭代式规划-执行-反思** | 父 Agent 统筹循环：`Plan → Teach → Practice → Assess → Reflect → NextStage` |

---

## 2. 整体架构设计 (拓扑与数据流)
<!-- 这是一个文本绘图，源码为：graph TD
    UI[学习者交互层] --> WS[WebSocket/Streaming Gateway]
    WS --> Orchestrator[👑 父Agent: MasterTutorOrchestrator]

    subgraph 多Agent协同层
        Orchestrator -->|调度/状态路由| Researcher[🔍 ResearcherAgent]
        Orchestrator -->|调度/状态路由| Curriculum[📐 CurriculumArchitectAgent]
        Orchestrator -->|调度/状态路由| Instructor[📖 InstructorAgent]
        Orchestrator -->|调度/状态路由| Practice[⚙️ PracticeEvaluatorAgent]
        Orchestrator -->|调度/状态路由| SkillForge[🛠️ SkillForgeAgent]
        Orchestrator -->|调度/状态路由| Progress[📈 ProgressMonitorAgent]
    end
    
    subgraph 知识与状态层
        KB[(Vector DB: Qdrant)]
        FS[(.learn/ 项目文件系统)]
        State[(Redis: Session & Checkpoint)]
    end
    
    Researcher -.->|解析/向量化| KB
    Instructor -.->|读取/检索| KB
    Curriculum -.->|读取| KB & FS
    SkillForge -.->|写入| FS/.skills/
    Practice -->|沙箱执行| Sandbox[E2B / Docker]
    Progress -->|更新进度| FS/progress.json
    Progress -->|调度复习| State -->
![](https://cdn.nlark.com/yuque/__mermaid_v3/d5f8f7b5329342727019f5817a625fc7.svg)

---

## 3. Agent 角色定义与协同工作流 (LangGraph State Machine)
### 3.1 父 Agent：`MasterTutorOrchestrator`
**职责**：状态机主控、阶段路由、进度仲裁、异常降级、人机协同接口。  
**输入**：`domain_name`, `learner_profile`  
**状态流转**：  
`INIT → DOMAIN_ANALYSIS → PLAN_GENERATION → LEARNING_LOOP → MASTERY_EVAL`  
其中 `LEARNING_LOOP` 包含：`LoadSkill → Teach → Quiz/Lab → Assess → Reflect → NextStage/Review`

### 3.2 子 Agent 集群
| Agent | 核心职责 | 输入 | 输出 | 工具集 |
| :--- | :--- | :--- | :--- | :--- |
| `ResearcherAgent` | 全网检索、去重、可信度评分、结构化摘要 | 领域词、阶段关键词 | 清洗后的知识块、来源引用、置信度 | Tavily/Firecrawl, Unstructured, LLM Dedup |
| `CurriculumArchitectAgent` | 领域特征识别、教学法映射、里程碑设计 | 领域元数据、学习者画像 | `curriculum.md`、阶段目标矩阵 | 领域分类器、Bloom分类器、Pedagogy Router |
| `InstructorAgent` | 概念讲解、苏格拉底式引导、难点拆解 | 当前阶段大纲、KB检索上下文 | 讲解文本、可视化建议、提问引导 | RAG Retriever, Text-to-Image (可选) |
| `PracticeEvaluatorAgent` | 出题、设计实验、执行评估、生成参考答案 | 阶段目标、学习者作答 | 题目、参考答案、Rubric评分、纠错建议 | 沙箱执行、单元测试框架、LLM Rubric Evaluator |
| `SkillForgeAgent` | 动态生成 Prompt/Skill、权限配置、工具绑定 | 当前阶段、领域特征、评估反馈 | `.skills/*.yaml` | Prompt Template Engine, JSON Schema Validator |
| `ProgressMonitorAgent` | 追踪掌握度、间隔复习调度、学习曲线预测 | `progress.json`、作答记录 | 复习计划、预警信号、阶段跃迁决策 | Spaced Repetition Algorithm, Stats Engine |

---

## 4. 核心技术模块详细实现方案
### 4.1 领域自适应与动态技能注入 (SkillForge 机制)
系统不依赖硬编码 Prompt，而是通过 **领域特征提取 → 教学策略路由 → 动态编译 Skill 配置** 实现自进化。

**流程**：

1. `CurriculumArchitect` 分析领域特征，输出 `domain_meta.json`：

```json
{
  "type": "technical",
  "pedagogy": "project_driven",
  "core_primitives": ["syntax", "type_system", "memory_model", "concurrency"],
  "assessment_style": "code_execution + peer_review",
  "difficulty_curve": "exponential_then_plateau"
}
```

2. `SkillForgeAgent` 读取 `domain_meta.json` 与当前 `stage_level`，动态生成 `.skills/instructor_v2.yaml`：

```yaml
role: |
  你是一位精通 {domain} 的 {stage} 级导师。采用 {pedagogy} 教学法。
  当前目标：掌握 {concept}，避免过早引入 {advanced_concept}。
constraints:
  max_concepts_per_turn: 1
  must_use_socratic_method: true
  forbid_direct_answers_for_quizzes: true
tools:
  allowed: ["retrieve_kb", "generate_diagram", "call_sandbox"]
  blocked: ["write_full_code_solutions", "change_curriculum"]
output_format: |
  {
    "explanation": "...",
    "key_takeaways": ["..."],
    "micro_quiz": {"q": "...", "options": ["..."]},
    "next_step": "..."
  }
```

3. LangGraph 节点在路由前加载该 Skill 配置，实现**按需热插拔能力边界**。

### 4.2 知识采集与结构化存储 (RAG + `.learn/` 文件系统)
遵循 Claude Code 的文件上下文原则，所有资产本地化、版本化。

```plain
.learn/
├── config.yaml             # 领域基础配置、LLM路由、工具开关
├── curriculum.md           # 动态生成的教学大纲（含阶段/里程碑/目标）
├── progress.json           # 学习者进度、掌握度矩阵、下次复习时间
├── knowledge/
│   ├── raw/                # 原始爬取内容（PDF/Markdown/网页）
│   └── indexed/            # 切分后的 Chunk + 元数据
├── skills/                 # 动态生成的 Agent Skill 配置
├── user_uploads/           # 用户自定义资料（高优先级RAG源）
├── labs/                   # 实战项目模板与环境描述
└── checkpoints/            # LangGraph 状态快照
```

**知识处理流水线**：  
`Web Search` → `Firecrawl 抓取` → `Unstructured 解析` → `LLM 去重/事实核查/结构化` → `LlamaIndex 分块` → `Qdrant 向量索引`。用户上传资料自动进入 `user_uploads/` 并覆盖同名概念检索权重。

### 4.3 教学引擎与进度监督 (Bloom + 间隔重复)
+ **认知分层**：所有教学内容按 Bloom 分类映射（记忆→理解→应用→分析→评价→创造）。`ProgressMonitor` 维护 `mastery_matrix: {concept_id: {level, last_practice, next_review, confidence_score}}`。
+ **间隔重复调度**：基于 SM-2 改进算法计算下次复习时间。`ProgressMonitorAgent` 定时触发 `Instructor` 推送“闪卡式”微练习。
+ **实时监督**：若连续两次评估得分 `<60%`，触发 `Intervention Loop`：降级难度 → 切换教学范式（如代码→图解） → 请求人工辅助标记。

### 4.4 实战沙箱与参考答案评估
**架构设计**：

1. **题目生成**：`PracticeEvaluatorAgent` 根据当前 `stage` 生成结构化 Lab 需求（如 `实现一个线程安全的 LRU 缓存`）。
2. **参考答案生成**：同步生成标准答案、边界用例、常见错误模式、评分 Rubric。
3. **安全执行**：
    - 代码类：`E2B Sandbox` 或 `Docker` 隔离运行，限制 CPU/内存/网络。
    - 非代码类：基于 LLM 逻辑推演、步骤验证、文本相似度+关键得分点匹配。
4. **评估反馈**：
    - 通过单元测试/静态分析 → 生成 `pass/fail` + 堆栈。
    - LLM 结合 Rubric 进行语义评估，输出：`strength`, `weakness`, `fix_suggestion`, `ref_code`（带详细注释）。

---

## 5. 状态管理与数据流设计 (LangGraph)
### 5.1 核心状态 Schema (TypeScript/Pydantic 风格)
```python
class LearnerState(BaseModel):
    session_id: str
    domain: str
    learner_profile: dict  # 背景/目标/可用时间/偏好
    current_stage: int     # 1-5 (入门/进阶/熟练/专家/精通)
    mastery_matrix: dict   # {concept_id: {score: float, reviews: int, next_due: iso}}
    curriculum_version: int
    active_skills: list[str]
    logs: list[Event]      # 所有交互/评估/状态变更事件

class AgentContext(BaseModel):
    current_node: str
    pending_tasks: list[Task]
    knowledge_context: str # RAG 召回上下文摘要
    sandbox_result: dict | None
```

### 5.2 图路由示例 (伪代码)
```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(LearnerState)
builder.add_node("analyze_domain", CurriculumArchitectAgent.run)
builder.add_node("forge_skill", SkillForgeAgent.run)
builder.add_node("teach", InstructorAgent.run)
builder.add_node("practice", PracticeEvaluatorAgent.run)
builder.add_node("assess", PracticeEvaluatorAgent.evaluate)
builder.add_node("update_progress", ProgressMonitorAgent.run)

def route_by_score(state):
    if state.assess.score >= 80: return "update_progress"
    elif state.assess.score >= 60: return "teach"
    else: return "remedial_teach"

builder.add_conditional_edges("assess", route_by_score)
builder.add_edge("update_progress", "forge_skill") # 阶段升级或切换技能包
```

---

## 6. 技术栈与工程部署架构
| 层级 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **Agent 编排** | `LangGraph` + `Pydantic` | 显式状态图、检查点、条件边、子图嵌套 |
| **LLM 路由** | `LiteLLM` / `OpenAI SDK` | 支持多模型 fallback、成本路由、延迟优化 |
| **向量检索** | `Qdrant` + `sentence-transformers` | 混合检索（向量 + BM25 + 元数据过滤） |
| **网络采集** | `Firecrawl` + `Tavily` + `Crawl4AI` | 深度解析、JS 渲染、结构化提取 |
| **沙箱执行** | `E2B` (代码) / `Docker Compose` (通用) | 安全隔离、资源限制、自动清理 |
| **存储/缓存** | `PostgreSQL` (持久化) + `Redis` (会话/队列) | 进度归档、间隔重复调度、热状态 |
| **前端交互** | `Next.js` + `WebSocket` + `CodeMirror` | 流式输出、多面板（讲解/代码/进度/沙箱） |
| **部署架构** | `FastAPI` + `Celery` + `K8s/Helm` | 异步任务队列、弹性扩缩、GPU/CPU 分离调度 |

---

## 7. 实施路线图与里程碑
| Phase | 交付物 | 核心验证指标 |
| :--- | :--- | :--- |
| **P0: 骨架与KB** | LangGraph 基础图、`.learn/` 文件系统、RAG 流水线、用户上传解析 | 知识召回准确率 >85%，文件读写延迟 <200ms |
| **P1: 课程与监督** | CurriculumArchitect、ProgressMonitor、Bloom 映射、间隔重复引擎 | 大纲合理性评分 >4.5/5，进度状态无损断点恢复 |
| **P2: 动态技能与教学** | SkillForge、Instructor 注入机制、Socratic 约束、多风格输出 | 跨领域 Prompt 切换成功率 >95%，幻觉率 <3% |
| **P3: 实战与沙箱** | PracticeEvaluator、E2B 沙箱、Rubric 评估、参考答案生成 | 代码执行通过率 100%，评估一致性 (Kappa >0.8) |
| **P4: 产品化** | Next.js 前端、WebSocket 流式、监控告警、成本优化 | 端到端首字延迟 <1.5s，并发 50+ 稳定运行 |

---

## 8. 关键风险与架构级缓解策略
| 风险点 | 架构缓解方案 |
| :--- | :--- |
| **领域知识幻觉/错误** | 强制 RAG 引用溯源 + `ResearcherAgent` 事实交叉验证 + 低置信度拦截转人工/标记 |
| **上下文爆炸** | 状态压缩：仅保留 `active_concepts` + 摘要日志；滑动窗口 + 关键 Checkpoint 快照 |
| **沙箱逃逸/资源滥用** | E2B 隔离网络、只读根目录、超时杀进程、CPU/Mem 硬限制；非代码类采用逻辑推演替代执行 |
| **多Agent 目标漂移** | 严格 Tool 权限矩阵 + `SkillForge` 约束块 + 父节点 `Pre-flight Validation` 拦截非法工具调用 |
| **进度监督失效** | 显式 `mastery_matrix` + 间隔重复算法 + 连续低分自动降级难度 + 触发 `Reflect` 节点重规划 |

---

## 9. 交付物清单 (开发启动前必备)
1. `LangGraph State Definition` (Pydantic/TS 接口)
2. `Agent Tool & Skill Schema` (JSON Schema + YAML 模板)
3. `.learn/ 目录规范` (Git 版本控制策略、冲突合并规则)
4. `评估 Rubric 引擎` (代码/文本/逻辑通用打分器)
5. `沙箱安全策略文档` (网络/文件系统/权限基线)

> 💡 **架构师建议**：首期建议以**强技术栈领域**（如 `Python 异步编程` 或 `前端状态管理`）跑通闭环。技术类领域具备明确的执行环境与客观评估标准，能快速验证 `沙箱+Rubric+进度监督` 核心链路。非技术类（如文学/管理）可二期接入 `结构化辩论`、`案例推演`、`角色扮演` 评估范式。
>

如需输出某个子模块的**详细 API 设计、LangGraph 完整节点代码、或 **`.skills/*.yaml`** 动态编译器实现**，可提供具体方向，我将直接交付可粘贴到 IDE 的生产级代码。



## 核心提示：

### 大模型配置文件位置

D:\ai-agent\learn-new\config\llm.yaml
"""
透平机械原理课程智能体 Agent
基于 LangGraph 构建的教育领域专用 Agent
功能：
1. 专业问答 - 回答透平机械相关问题
2. 生成练习题 - 根据章节内容生成问答/选择题
3. 作业批改 - 评估学生答案并给出反馈
4. 知识检索 - 从课件和教材中检索相关内容
"""
import random
import os
import json
import logging
import operator
from typing import List, Dict, Any, Optional, TypedDict, Annotated, Literal, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import re
import base64
# LangGraph 核心组件
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_deepseek import ChatDeepSeek
# LangChain 组件
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from common.turbine_core.multimodel_rag import MultiDocumentKnowledgeBase
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ================================
# 1. 状态定义
# ================================
class QuestionOutput(BaseModel):
    question_type: str = Field(description="题型，如 choice, fill_blank, short_answer, calculation 等")
    question: str = Field(description="题目内容")
    options: Optional[List[str]] = Field(default_factory=list, description="选择题的选项（如 ['A. xxx', 'B. xxx']），非选择题留空")
    answer: str = Field(description="标准答案")
    explanation: str = Field(description="答案解析")
    difficulty: str = Field(description="难度: easy/medium/hard")
    knowledge_point: str = Field(description="考查的知识点")

class QuestionListOutput(BaseModel):
    questions: List[QuestionOutput] = Field(description="生成的练习题列表")

class IntentType(str, Enum):
    """用户意图类型"""
    QA = "qa"  # 问答
    GENERATE_QUESTIONS = "generate"  # 生成练习题
    GRADE_HOMEWORK = "grade"  # 批改作业
    SUMMARY = "summary"  # 章节总结
    UNKNOWN = "unknown"  # 未知意图


@dataclass
class QuestionItem:
    """练习题数据结构"""
    question_type: str  # 题型: choice/fill_blank/short_answer/calculation
    question: str  # 题目内容
    options: List[str] = field(default_factory=list)  # 选择题选项
    answer: str = ""  # 标准答案
    explanation: str = ""  # 答案解析
    difficulty: str = "medium"  # 难度: easy/medium/hard
    knowledge_point: str = ""  # 知识点


@dataclass
class GradingResult:
    """批改结果数据结构"""
    score: float  # 得分 (0-100)
    feedback: str  # 反馈意见
    correct_points: List[str]  # 正确的点
    wrong_points: List[str]  # 错误的点
    suggestions: List[str]  # 改进建议
    reference_answer: str = ""  # 参考答案


class AgentState(TypedDict):
    """Agent 状态定义"""
    # 输入
    user_input: str  # 用户输入
    session_id: str  # 会话ID

    # 意图识别
    intent: IntentType  # 识别的意图
    intent_confidence: float  # 意图置信度

    # 上下文
    chat_history: Annotated[List[BaseMessage], operator.add]  # 对话历史
    retrieved_docs: List[Dict[str, Any]]  # 检索到的文档
    retrieved_images: List[str]  # 检索到的图片路径

    # 问答相关
    qa_answer: str  # 问答回答
    qa_confidence: float  # 回答置信度
    qa_sources: List[Dict[str, Any]]  # 回答来源

    # 练习题生成相关
    chapter_info: str  # 章节信息
    question_type: str  # 题目类型
    question_count: int  # 题目数量
    difficulty: str  # 难度要求
    generated_questions: List[Dict[str, Any]]  # 生成的练习题

    # 作业批改相关
    student_answer: str  # 学生答案
    reference_content: str  # 参考内容/标准答案
    student_images: List[str]
    reference_images: List[str]
    grading_result: Dict[str, Any]  # 批改结果

    # 输出
    final_response: str  # 最终回复
    error_message: str  # 错误信息

    # 【新增】重试机制状态
    retry_count: int

    # 【新增】用户画像与长期记忆
    # 结构示例:
    # {
    #    "skill_level": "beginner",  # beginner/intermediate/advanced
    #    "weak_points": ["离心式压缩机", "速度三角形"],
    #    "interests": ["热力学公式"],
    #    "long_term_memory": "用户之前重点询问了多级透平的效率计算..."
    # }
    user_profile: Dict[str, Any]


# ================================
# 2. 知识库接口适配器
# ================================

class KnowledgeBaseAdapter:
    """
    知识库适配器 - 封装与现有 RAG 系统的交互
    可以替换为用户自己的微调模型和知识库
    """
    def __init__(self, knowledge_base=None, custom_llm=None):
        """
        初始化知识库适配器
        Args:
            knowledge_base: 用户提供的知识库实例 (MultiDocumentKnowledgeBase)
            custom_llm: 用户微调的大模型实例
        """
        self.kb = knowledge_base
        self.custom_llm = custom_llm

    def search(self, question: str, k: int = 8) -> List[Document]:
        """检索相关文档"""
        if self.kb is None:
            logger.warning("知识库未初始化")
            return []

        try:
            # 修正：调用 search (返回List[Document])，并移除多余参数
            return self.kb.search(question, k=k)
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []

    def query_with_rerank(self, question: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """执行带重排序的查询"""
        if self.kb is None:
            return {"answer": "", "sources": [], "confidence": 0.0}

        try:
            return self.kb.query(question, session_id=session_id, **kwargs)
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return {"answer": f"查询出错: {e}", "sources": [], "confidence": 0.0}

    def get_chapter_content(self, chapter_name: str) -> str:
        """获取指定章节的内容"""
        if self.kb is None:
            return ""

        # 检索章节相关内容
        docs = self.search(f"{chapter_name} 内容 概述", k=10)
        if docs:
            return "\n\n".join([doc.page_content for doc in docs])
        return ""

    def get_llm(self):
        """获取LLM实例（优先使用用户自定义的微调模型）"""
        if self.custom_llm:
            return self.custom_llm
        # 返回None，由调用方处理
        return None


# ================================
# 3. Agent 节点实现
# ================================

class TurbineCourseAgent:
    """透平机械原理课程智能体"""

    def __init__(
            self,
            knowledge_base=None,
            llm: Optional[ChatOpenAI] = None,
            custom_fine_tuned_llm=None
    ):
        """
        初始化 Agent
        Args:
            knowledge_base: MultiDocumentKnowledgeBase 实例
            llm: 默认 LLM (如 ChatOpenAI)
            custom_fine_tuned_llm: 用户微调的专业领域模型
        """
        # 知识库适配器
        self.kb_adapter = KnowledgeBaseAdapter(knowledge_base, custom_fine_tuned_llm)

        # LLM 配置（优先使用微调模型）
        if custom_fine_tuned_llm:
            self.llm = custom_fine_tuned_llm
            logger.info("使用用户提供的微调模型")
        elif llm:
            self.llm = llm
            logger.info("使用默认 LLM")
        else:
            raise ValueError("必须提供 llm 或 custom_fine_tuned_llm 参数")

        # 【新增持久化】用户画像存储路径
        if knowledge_base and hasattr(knowledge_base, 'kb_path'):
            self.profile_file = knowledge_base.kb_path / "user_profiles.json"
        else:
            self.profile_file = Path("./user_profiles.json")
        # 构建 Graph
        self.graph = self._build_graph()
        # 检查点保存器（用于对话持久化）
        self.memory = MemorySaver()
        # 编译 Graph
        self.app = self.graph.compile(checkpointer=self.memory)
        logger.info("透平机械原理课程智能体初始化完成")

    # 【新增】默认画像生成
    def _default_profile(self):
            return {
                "skill_level": "beginner",
                "weak_points": [],
                "interests": [],
                "long_term_memory": "",
                "elo_rating": 1200,
                "recent_scores": []
            }

    # 【新增】从本地加载画像
    def load_profile(self, session_id: str) -> Dict[str, Any]:
            if self.profile_file.exists():
                try:
                    with open(self.profile_file, 'r', encoding='utf-8') as f:
                        profiles = json.load(f)
                        return profiles.get(session_id, self._default_profile())
                except Exception as e:
                    logger.error(f"读取用户画像失败: {e}")
            return self._default_profile()

    # 【新增】保存画像到本地
    def save_profile(self, session_id: str, profile: Dict[str, Any]):
            profiles = {}
            if self.profile_file.exists():
                try:
                    with open(self.profile_file, 'r', encoding='utf-8') as f:
                        profiles = json.load(f)
                except Exception:
                    pass
            profiles[session_id] = profile
            try:
                with open(self.profile_file, 'w', encoding='utf-8') as f:
                    json.dump(profiles, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存用户画像失败: {e}")

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        # 创建状态图
        workflow = StateGraph(AgentState)
        # 添加节点
        workflow.add_node("profile_manager", self._profile_manager_node)
        workflow.add_node("intent_classifier", self._intent_classifier_node)
        workflow.add_node("retriever", self._retriever_node)
        workflow.add_node("question_generator", self._question_generator_node)
        workflow.add_node("qa_node", self._qa_node)
        workflow.add_node("homework_grader", self._homework_grader_node)
        workflow.add_node("summary_node", self._summary_node)
        workflow.add_node("response_formatter", self._response_formatter_node)
        workflow.add_node("error_handler", self._error_handler_node)
        # 2. 设置入口 (Set Entry Point)
        workflow.set_entry_point("intent_classifier")
        # 3. 添加普通边 (Add Edges)
        # 确保节点已存在后再添加边
        workflow.add_edge("qa_node", "profile_manager")
        workflow.add_edge("summary_node", "profile_manager")
        workflow.add_edge("profile_manager", "response_formatter")

        # 设置入口
        workflow.set_entry_point("intent_classifier")

        # 添加条件边 - 根据意图路由
        workflow.add_conditional_edges(
            "intent_classifier",
            self._route_by_intent,
            {
                "qa": "retriever",
                "generate": "retriever",
                "grade": "retriever",
                "grade_direct": "homework_grader",
                "summary": "retriever",
                "error": "error_handler"
            }
        )

        # 检索后的路由
        workflow.add_conditional_edges(
            "retriever",
            self._route_after_retrieval,
            {
                "qa": "qa_node",
                "generate": "question_generator",
                "summary": "summary_node",
                "grade": "homework_grader"
            }
        )

        # 【修改】添加重试路由逻辑
        # question_generator -> (check retry) -> question_generator OR response_formatter
        workflow.add_conditional_edges(
            "question_generator",
            self._check_retry_generate,
            {
                "retry": "question_generator",
                "continue": "profile_manager"  # 成功后先去更新画像
            }
        )

        # homework_grader -> (check retry) -> homework_grader OR response_formatter
        workflow.add_conditional_edges(
            "homework_grader",
            self._check_retry_grade,
            {
                "retry": "homework_grader",
                "continue": "profile_manager"  # 成功后先去更新画像
            }
        )

        # 各节点到格式化输出
        workflow.add_edge("error_handler", "response_formatter")
        workflow.add_edge("profile_manager", "response_formatter")
        # 格式化输出到结束
        workflow.add_edge("response_formatter", END)

        return workflow

    # --------------------------------
    # 辅助方法：重试判断
    # --------------------------------
    def _check_retry_generate(self, state: AgentState) -> str:
        """检查是否需要重试生成题目"""
        retry_count = state.get("retry_count", 0)
        error_msg = state.get("error_message", "")
        # 如果有错误且重试次数小于3次，则重试
        if error_msg and retry_count < 3:
            logger.warning(f"检测到生成格式错误，尝试第 {retry_count + 1} 次重试...")
            return "retry"
        return "continue"

    def _check_retry_grade(self, state: AgentState) -> str:
        """检查是否需要重试批改"""
        retry_count = state.get("retry_count", 0)
        error_msg = state.get("error_message", "")
            # 如果有错误且重试次数小于3次，则重试
        if error_msg and retry_count < 3:
            logger.warning(f"检测到批改格式错误，尝试第 {retry_count + 1} 次重试...")
            return "retry"
        return "continue"


    # --------------------------------
    # 节点实现
    # --------------------------------
    def _intent_classifier_node(self, state: AgentState) -> AgentState:
        """意图识别节点"""
        """意图识别节点"""
        # ✅ 新增拦截逻辑：如果已经明确了意图，直接跳过大模型识别
        if state.get("intent") and state["intent"] != IntentType.UNKNOWN:
            logger.info(f"🎯 按钮直接触发，使用预设意图: {state['intent'].value}，跳过大模型猜想")
            return state
        user_input = state["user_input"]

        # 意图分类提示词
        intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个透平机械原理课程的教学助手，负责识别用户的意图。
请根据用户输入，判断其意图类型，只能返回以下JSON格式：

```json
{{
    "intent": "意图类型",
    "confidence": 置信度(0-1),
    "extracted_info": {{
        "chapter": "提取的章节信息（如有）",
        "question_type": "题目类型（如有）: choice/fill_blank/short_answer/calculation",
        "count": 题目数量（如有）,
        "difficulty": "难度（如有）: easy/medium/hard",
        "student_answer": "学生答案（如有）"
    }}
}}
```

意图类型说明：
- "qa": 用户在提问或询问知识点（如：什么是透平？轴流式压缩机的工作原理？）
- "generate": 用户要求生成练习题（如：给我出5道选择题、生成第三章的计算题）
- "grade": 用户要求批改作业或评估答案（如：帮我批改这道题、我的答案对吗）
- "summary": 用户要求总结章节内容（如：总结第二章、归纳知识点）
- "unknown": 无法识别的意图

注意：只返回JSON，不要有其他内容。"""),
            ("user", "{input}")
        ])

        try:
            chain = intent_prompt | self.llm | StrOutputParser()
            result = chain.invoke({"input": user_input})

            # 【修改开始】使用正则提取 JSON，增强健壮性
            import re
            try:
                # 尝试匹配大括号 {} 包裹的内容
                match = re.search(r"(\{.*\})", result, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    parsed = json.loads(json_str)
                else:
                    # 兜底：尝试直接解析
                    parsed = json.loads(result)
            except json.JSONDecodeError:
                logger.warning(f"JSON 解析失败，原始结果: {result}")
                # 解析失败时，默认设为 QA 模式，避免流程中断
                parsed = {"intent": "qa", "confidence": 0.5}

            intent_str = parsed.get("intent", "unknown")
            confidence = parsed.get("confidence", 0.5)
            extracted = parsed.get("extracted_info", {})

            # 映射意图
            intent_map = {
                "qa": IntentType.QA,
                "generate": IntentType.GENERATE_QUESTIONS,
                "grade": IntentType.GRADE_HOMEWORK,
                "summary": IntentType.SUMMARY,
                "unknown": IntentType.UNKNOWN
            }

            intent = intent_map.get(intent_str, IntentType.UNKNOWN)
            logger.info(f"识别意图: {intent.value}, 置信度: {confidence}")
            # 【修复代码开始】
            # 逻辑说明：优先保留 state 中已有的 student_answer（那是完整的），
            # 只有当 state 中没有时，才使用意图识别从 prompt 提取的片段。
            existing_student_answer = state.get("student_answer", "")
            extracted_student_answer = extracted.get("student_answer", "")
            # 如果已有答案且不为空，就用已有的；否则尝试用提取的
            final_student_answer = existing_student_answer if existing_student_answer else extracted_student_answer
            # 【修复代码结束】

            return {
                **state,
                "intent": intent,
                "intent_confidence": confidence,
                "chapter_info": extracted.get("chapter", ""),
                "question_type": extracted.get("question_type", "short_answer"),
                "question_count": extracted.get("count", 5),
                "difficulty": extracted.get("difficulty", "medium"),
                "student_answer": final_student_answer
            }

        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            return {
                **state,
                "intent": IntentType.QA,  # 默认当作问答
                "intent_confidence": 0.3,
                "error_message": f"意图识别出现问题: {str(e)}"
            }

    def _profile_manager_node(self, state: AgentState) -> AgentState:
        """用户画像管理与记忆压缩节点"""
        user_profile = state.get("user_profile", {
            "skill_level": "beginner",
            "weak_points": [],
            "interests": [],
            "long_term_memory": ""
        })

        if "elo_rating" not in user_profile: user_profile["elo_rating"] = 1200
        # 最近战绩队列 (用于滑动窗口/连胜判定)
        if "recent_scores" not in user_profile: user_profile["recent_scores"] = []
        # 等级标签
        if "skill_level" not in user_profile: user_profile["skill_level"] = "beginner"
        intent = state.get("intent")
        grading = state.get("grading_result", {})

        chat_history = state.get("chat_history", [])
        # 仅在批改作业时更新长期画像
        if intent == IntentType.GRADE_HOMEWORK and grading:
            current_score = grading.get("score", 0)  # 0-100分
            # --- 策略融合：获取大模型评判的实际作业难度 ---
            # 优先从批改结果获取大模型对难度的评判，兜底使用默认值
            evaluated_difficulty = grading.get("difficulty", state.get("difficulty", "medium")).lower()
            if evaluated_difficulty not in ["easy", "medium", "hard"]:
                evaluated_difficulty = "medium"
            question_difficulty_map = {"easy": 1000, "medium": 1400, "hard": 1800}
            difficulty_rating = question_difficulty_map.get(evaluated_difficulty, 1400)
            # --- 策略2融合：滑动窗口 (计算连胜/连败趋势) ---
            user_profile["recent_scores"].append(current_score)
            if len(user_profile["recent_scores"]) > 5:
                user_profile["recent_scores"].pop(0)

            # --- 策略融合：Elo 等级分计算 ---
            current_rating = user_profile["elo_rating"]
            current_level = user_profile["skill_level"]
            # 1. 计算期望胜率 (Expectation)
            expected_score = 1 / (1 + 10 ** ((difficulty_rating - current_rating) / 400))
            # 2. 归一化实际得分 (将 0-100 分映射到 0-1)
            actual_score = current_score / 100.0
            # 得分差值，如果 > 0 表示表现超预期（需要加分），< 0 表示表现低于预期（需要减分）
            delta = actual_score - expected_score
            # 3. 动态 K 值判定规则：根据用户当前等级、题目实际难度、是否做对(得分是否超预期)来判定
            k_factor = 30  # 基础 K 值
            is_correct = delta > 0  # 表现好于预期即为“做对/加分趋势”
            if current_level == "beginner":
                # 等级较低时
                if evaluated_difficulty == "hard" or "medium":
                    k_factor = 50 if is_correct else 10  # 对难题：做对加较多的分，做错减较少的分
                elif evaluated_difficulty == "easy":
                    k_factor = 10 if is_correct else 50  # 对简单题：做对加较少的分，做错减较多的分
            elif current_level == "advanced":
                # 等级较高时
                if evaluated_difficulty == "hard":
                    k_factor = 30 if is_correct else 10  # 对难题：做对加一般的分，做错减较少的分
                elif evaluated_difficulty == "easy" or "medium":
                    k_factor = 10 if is_correct else 50  # 对简单题：做对加较少的分，做错减较多的分
            else:
                # 中级水平 (intermediate) 可以采用更平滑的过渡
                if evaluated_difficulty == "hard" or "medium":
                    k_factor = 40 if is_correct else 20
                elif evaluated_difficulty == "easy":
                    k_factor = 20 if is_correct else 40

            # 4. 更新 Elo 分数
            new_rating = current_rating + k_factor * delta
            user_profile["elo_rating"] = round(new_rating, 1)
            logger.info(
            f"📊 Elo 更新: {current_rating} -> {new_rating} (大模型评定难度: {evaluated_difficulty}, 难度分: {difficulty_rating}, 动态K值: {k_factor})")
            # --- 根据 Elo 分数映射回 skill_level ---
            if new_rating < 1300:
                new_level = "beginner"
            elif 1300 <= new_rating < 1700:
                new_level = "intermediate"
            else:
                new_level = "advanced"
            if new_level != user_profile["skill_level"]:
                logger.info(f"🆙 用户等级变更为: {new_level}")
                user_profile["skill_level"] = new_level

            # --- 维护薄弱点 (原逻辑保留) ---
            current_topic = state.get("chapter_info", "未知考点")
            if current_score < 60 and current_topic not in user_profile.get("weak_points", []):
                user_profile.setdefault("weak_points", []).append(current_topic)
            elif current_score > 85 and current_topic in user_profile.get("weak_points", []):
                user_profile["weak_points"].remove(current_topic)

        # 2. 兴趣捕捉 (QA模式)
        if intent == IntentType.QA:
            # 简单实现：将 chapter_info 加入兴趣列表
            topic = state.get("chapter_info")
            if topic and topic not in user_profile["interests"]:
                user_profile["interests"].append(topic)

        # 3. 记忆压缩 (Memory Compression)
        # 如果历史记录超过阈值 (例如 10 轮)，触发总结
        if len(chat_history) > 10:
            logger.info("🧠 触发长期记忆压缩...")
            try:
                # 使用 LLM 总结最近的对话重点
                summary_prompt = ChatPromptTemplate.from_messages([
                    ("system",
                     "你是一个记忆管家。请简要总结以下师生对话中的【用户关注点】和【已解决的问题】，以便存入长期记忆。保留关键技术术语。"),
                    ("user", "{history}")
                ])
                chain = summary_prompt | self.llm | StrOutputParser()
                # 仅总结最近的交互，避免 token 爆炸
                recent_summary = chain.invoke({"history": chat_history[-6:]})

                # 更新长期记忆 (追加模式)
                timestamp = "Recent"
                user_profile["long_term_memory"] += f"\n[{timestamp}] {recent_summary}"

                # 保持 long_term_memory 不过长 (可进一步优化)
                if len(user_profile["long_term_memory"]) > 2000:
                    user_profile["long_term_memory"] = user_profile["long_term_memory"][-2000:]

            except Exception as e:
                logger.error(f"记忆压缩失败: {e}")
        # 【新增】将画像保存到磁盘持久化存储
        session_id = state.get("session_id", "default_session")
        self.save_profile(session_id, user_profile)

        return {
            **state,
            "user_profile": user_profile
        }

    def _retriever_node(self, state: AgentState) -> AgentState:
        """检索节点 - 从知识库检索相关内容"""
        user_input = state["user_input"]
        chapter_info = state.get("chapter_info", "")
        intent = state.get("intent", IntentType.UNKNOWN)  # 获取当前意图

        # 1. 动态设置检索数量 k
        # 默认为 10 (保证 QA 速度)
        search_k = 10

        # 如果是生成题目，我们需要更大的文档池来保证多样性
        if intent == IntentType.GENERATE_QUESTIONS:
            search_k = 60  # 检索 60 个片段，提供足够大的随机池
        # 如果是总结，需要覆盖更多内容
        elif intent == IntentType.SUMMARY:
            search_k = 100

        # 构建检索查询
        if chapter_info:
            query = f"{chapter_info} {user_input}"
        else:
            query = user_input

        try:
            # 使用知识库检索
            docs = self.kb_adapter.search(query, k=search_k)

            retrieved_docs = []
            retrieved_images = []

            for doc in docs:
                doc_info = {
                    "content": doc.page_content,
                    "source": doc.metadata.get("file_name", "Unknown"),
                    "page": doc.metadata.get("page_number", "N/A"),
                    "chunk_id": doc.metadata.get("chunk_id", "")
                }
                retrieved_docs.append(doc_info)

                # 提取图片路径
                img_paths = doc.metadata.get("image_paths", [])
                if isinstance(img_paths, str):
                    try:
                        import ast
                        img_paths = ast.literal_eval(img_paths)
                    except:
                        img_paths = []

                for img_path in img_paths:
                    if img_path and Path(img_path).exists():
                        retrieved_images.append(img_path)

            logger.info(f"检索到 {len(retrieved_docs)} 个文档片段, {len(retrieved_images)} 张图片")

            return {
                **state,
                "retrieved_docs": retrieved_docs,
                "retrieved_images": retrieved_images[:3]  # 限制图片数量
            }

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return {
                **state,
                "retrieved_docs": [],
                "retrieved_images": [],
                "error_message": f"知识检索失败: {str(e)}"
            }

    def _qa_node(self, state: AgentState) -> AgentState:
        """问答节点 - 回答用户问题"""
        user_input = state["user_input"]
        retrieved_docs = state.get("retrieved_docs", [])
        chat_history = state.get("chat_history", [])
        user_profile = state.get("user_profile", {})
        # 获取长期等级
        base_skill_level = user_profile.get("skill_level", "beginner")

        # --- 策略2融合：实时感知 (复杂度检测) ---
        # 定义一些高阶词汇 (实际项目中可以用 LLM 预判断或更丰富的词库)
        advanced_keywords = [
            "纳维", "斯托克斯", "偏微分", "三维流", "边界层", "湍流",
            "多变效率", "激波", "喘振裕度", "熵", "焓", "基元",
            "定理", "喘", "冲角", "马赫数"
        ]
        # 简单判断：如果包含高阶词汇，或问题长度较长且包含"如何计算/推导"，则视为复杂问题
        is_complex = any(kw in user_input for kw in advanced_keywords)
        is_derivation = "推导" in user_input or "计算公式" in user_input
        # 确定“有效等级” (Effective Level)
        effective_level = base_skill_level
        if (is_complex or is_derivation) and base_skill_level == "beginner":
            effective_level = "intermediate"  # 新手问难题，临时拔高一级，避免回答太幼稚
            logger.info(f"🚀 检测到复杂提问，临时提升等级: Beginner -> Intermediate")
        elif not is_complex and base_skill_level == "advanced":
            # 专家问基础定义 (例如"什么是焓")，可能需要直接精准的定义，而不是长篇大论的推导
            # 这里可以保持 advanced，或者微调 prompt
            pass
        # --- 动态构建 Prompt ---
        adaptive_instruction = ""
        if effective_level == "beginner":
            adaptive_instruction = "用户是初学者，请用通俗易懂的语言解释，多打比方，避免过多晦涩的公式。"
        elif effective_level == "intermediate":
            adaptive_instruction = "用户具备一定基础，请结合专业术语、工程实例和必要的公式进行讲解。"
        elif effective_level == "advanced":
            adaptive_instruction = "用户是专家，请直接从数学物理原理、热力学底层逻辑进行深入推导，无需解释基础名词。"
        # 构建上下文
        context_parts = []
        for doc in retrieved_docs[:7]:  # 取前7个文档
            source_info = f"[来源: {doc['source']}, 页码: {doc['page']}]"
            context_parts.append(f"{doc['content']}\n{source_info}")

        context = "\n\n---\n\n".join(context_parts)

        user_profile = state.get("user_profile", {})
        skill_level = user_profile.get("skill_level", "beginner")
        long_term_mem = user_profile.get("long_term_memory", "")

        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是透平机械原理课程的专业教学助手。

        【用户画像与记忆】
        - 学习阶段: {skill_level}
        - 长期记忆: {memory}
        - 适应性指令: {adaptive_instruction}

        【回答原则】
1. **严格基于上下文**：请优先依据提供的【检索资料】回答。
2. **适应性讲解**：根据用户的学习阶段调整讲解深度。
3. **关联记忆**：结合长期记忆中的关注点进行关联讲解。
4. **诚实原则**：如果【检索资料】中没有答案，请明确告知，不要编造。
       【检索资料】
{context}
"""),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{question}")
        ])

        try:
            chain = qa_prompt | self.llm | StrOutputParser()
            answer = chain.invoke({
                "context": context if context else "（暂无相关资料，将基于通用知识回答）",
                "history": chat_history[-6:] if chat_history else [],
                "question": user_input,
                "skill_level": skill_level,          # 新增
                "memory": long_term_mem,             # 新增 (对应模板中的 {memory})
                "adaptive_instruction": adaptive_instruction # 新增
            })

            if not answer:
                answer = "错误：LLM 返回了空内容，请检查 API Key 或 模型名称是否正确。"

            # 计算置信度
            confidence = 0.8 if retrieved_docs else 0.4

            # 整理来源
            sources = []
            seen = set()
            for doc in retrieved_docs[:5]:
                key = f"{doc['source']}_{doc['page']}"
                if key not in seen:
                    sources.append({
                        "file": doc['source'],
                        "page": doc['page']
                    })
                    seen.add(key)

            logger.info(f"问答完成，置信度: {confidence}")

            return {
                **state,
                "qa_answer": answer,
                "qa_confidence": confidence,
                "qa_sources": sources,
                "chat_history": chat_history + [
                    HumanMessage(content=user_input),
                    AIMessage(content=answer)
                ]
            }

        except Exception as e:
            logger.error(f"问答失败: {e}")
            return {
                **state,
                "qa_answer": f"抱歉，回答您的问题时出现错误: {str(e)}",
                "qa_confidence": 0.0,
                "qa_sources": []
            }

    def _question_generator_node(self, state: AgentState) -> AgentState:
            """练习题生成节点"""
            chapter_info = state.get("chapter_info", "透平机械原理")
            question_type = state.get("question_type", "short_answer")
            question_count = state.get("question_count", 5)
            difficulty = state.get("difficulty", "medium")
            retrieved_docs = state.get("retrieved_docs", [])
            retry_count = state.get("retry_count", 0)
            last_error = state.get("error_message", "")

            # === 【核心修改开始】 ===
            # 随机采样策略：从大量检索结果中随机选取一部分作为上下文
            # 这样每次生成题目时，参考的侧重点都会不同
            # 设定 LLM 上下文能容纳的片段数 (例如 8 个)
            context_window_size = 5
            if len(retrieved_docs) > context_window_size:
                # 从检索到的文档池中随机采样
                selected_docs = random.sample(retrieved_docs, context_window_size)
                logger.info(f"🎲 已从 {len(retrieved_docs)} 个文档中随机采样 {context_window_size} 个用于出题")
            else:
                selected_docs = retrieved_docs
            # 构建上下文
            context = "\n\n".join([doc["content"] for doc in selected_docs])

            user_profile = state.get("user_profile", {})
            weak_points = user_profile.get("weak_points", [])

            # 自适应出题指令
            adaptive_focus = ""
            if weak_points:
                adaptive_focus = f"注意：用户在以下知识点存在薄弱：{', '.join(weak_points)}。请在生成的题目中重点考察这些内容，帮助用户巩固。"

            # 题型说明
            type_instructions = {
                "choice": "选择题（单选），需要提供4个选项A/B/C/D",
                "fill_blank": "填空题，用___表示空白处",
                "short_answer": "简答题，需要简短回答（50-150字）",
                "calculation": "计算题，需要给出计算步骤和答案"
            }

            difficulty_desc = {
                "easy": "基础概念题，直接考查定义和基本原理",
                "medium": "中等难度，需要理解和简单应用",
                "hard": "较难，需要综合分析和灵活运用"
            }

            parser = PydanticOutputParser(pydantic_object=QuestionListOutput)

            # 生成提示词
            gen_prompt = ChatPromptTemplate.from_messages([
                ("system", """你是透平机械原理课程的出题专家。请根据给定的课程内容和要求，生成高质量的练习题。
            【出题要求】
            - 章节/知识点: {chapter}
            - 题型: {type_desc}
            - 数量: {count}道
            - 难度: {difficulty_desc}

            【参考资料】
            {context}

            【自适应出题要求】
            {adaptive_focus}
            【输出格式要求】
             {format_instructions}
             ⚠️ 注意：你必须且只能返回合法的 JSON 格式数据！不要包含任何 Markdown 标记（如 ```json），也不要包含任何前言、后语或解释性文字！
    """),
                ("user",
                 "请生成{count}道关于{chapter}的{type_name}，难度为{difficulty}。\n\n(请务必按照上方要求的 JSON 格式输出结果)")
            ])
            try:
                # 3. 将解析器加入 Chain
                chain = gen_prompt | self.llm | parser

                diff_text = difficulty_desc.get(difficulty, "中等难度，需要理解和简单应用")

                # 4. 传入 format_instructions
                parsed_result = chain.invoke({
                    "chapter": chapter_info,
                    "type_desc": type_instructions.get(question_type, "简答题"),
                    "type_name": question_type,
                    "count": question_count,
                    "difficulty": difficulty,
                    "context": context if context else "（无额外参考资料，请基于透平机械原理通用知识出题）",
                    "difficulty_desc": diff_text,
                    "adaptive_focus": adaptive_focus,
                    "format_instructions": parser.get_format_instructions()  # 新增参数
                })

                questions = []
                if parsed_result and parsed_result.questions:
                    for q in parsed_result.questions:
                        q_dict = getattr(q, "model_dump", q.dict)()
                        questions.append(q_dict)

                logger.info(f"成功生成 {len(questions)} 道练习题 (尝试次数: {retry_count + 1})")

                return {
                    **state,
                    "generated_questions": questions,
                    "error_message": "",
                    "difficulty": difficulty,
                    "retry_count": 0
                }

            except Exception as e:
                error_msg = str(e)
                logger.error(f"生成练习题结构化解析失败 (第 {retry_count + 1} 次): {error_msg}")
                # 【新增容错机制】尝试抢救纯文本
                if "Invalid json output:" in error_msg:
                    extracted_text = error_msg.split("Invalid json output:", 1)[1].strip()
                    if "For troubleshooting" in extracted_text:
                        extracted_text = extracted_text.split("For troubleshooting")[0].strip()

                    return {
                        **state,
                        # 将纯文本塞入 raw_text，后续的 formatter 节点会自动将其直接显示给用户
                        "generated_questions": [{"raw_text": extracted_text}],
                        "error_message": "",  # 清空错误，视为抢救成功，不再重试
                        "difficulty": difficulty,
                        "retry_count": 0
                    }

                return {
                    **state,
                    "generated_questions": [{"raw_text": f"生成失败", "parse_error": error_msg}],
                    "error_message": f"结构化解析错误: {error_msg}",
                    "retry_count": retry_count + 1
                }

    def _homework_grader_node(self, state: AgentState) -> AgentState:
            """作业批改节点"""
            user_input = state["user_input"]
            student_answer = state.get("student_answer", "")
            reference_content = state.get("reference_content", "")
            student_images = state.get("student_images", [])  # 获取图片路径
            reference_images = state.get("reference_images", [])  # 获取图片路径
            # 【新增】获取重试状态
            retry_count = state.get("retry_count", 0)
            last_error = state.get("error_message", "")

            # 【新增逻辑开始】处理检索到的标准答案/参考资料
            retrieved_docs = state.get("retrieved_docs", [])
            retrieved_context = ""
            if retrieved_docs:
                doc_texts = []
                # 选取最相关的几个片段
                for doc in retrieved_docs[:4]:
                    source_name = doc.get('source', '未知来源')
                    content = doc.get('content', '')
                    doc_texts.append(f"【参考片段 (来源: {source_name})】\n{content}")
                retrieved_context = "\n\n".join(doc_texts)
            # 将检索内容合并到 reference_content 中
            if retrieved_context:
                if reference_content:
                    reference_content += f"\n\n=== 知识库检索到的参考资料 ===\n{retrieved_context}"
                else:
                    reference_content = f"=== 知识库检索到的参考资料 ===\n{retrieved_context}"
            # 【新增逻辑结束】

            # 辅助函数：编码并压缩图片
            def encode_image(image_path, max_size=(1024, 1024), quality=80):
                try:
                    import io
                    from PIL import Image
                    with Image.open(image_path) as img:
                        # 1. 统一转换为 RGB 模式 (解决 PNG 的透明通道转 JPEG 报错的问题)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        # 2. 等比例缩小分辨率 (使用 LANCZOS 算法保证缩放清晰度)
                        # thumbnail 会保持原图比例，只要宽或高超过 1024 就会被缩小
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                        # 3. 将压缩后的图片保存到内存缓冲区 (统一保存为 JPEG 格式)
                        buffered = io.BytesIO()
                        img.save(buffered, format="JPEG", quality=quality)
                        # 4. 读取缓冲区数据并转换为 Base64
                        return base64.b64encode(buffered.getvalue()).decode('utf-8')
                except Exception as e:
                    logger.error(f"图片压缩/编码失败 {image_path}: {e}")
                    return None

            # 如果没有单独的学生答案，尝试从用户输入中提取
            if not student_answer:
                student_answer = user_input

            # 批改提示词 (保持不变)
            system_prompt_text ="""你是透平机械原理课程的作业批改专家。
请综合【参考资料】对【学生作业】进行批改。
    【处理说明】
    1. 如果提供了**图片**，请优先通过视觉识别手写公式、图表和文字。
    2. 如果**未提供图片**但提供了**OCR识别内容**或文本，请基于文本内容进行判断。
    3. 如果是OCR识别内容，请注意可能存在的识别错误（如公式乱码），请结合上下文推断。
    【评分标准】
    1. 概念准确性（40%）: 专业术语使用是否正确，概念理解是否准确
    2. 逻辑完整性（30%）: 答案是否完整，逻辑是否清晰
    3. 表达规范性（20%）: 表达是否清晰，公式符号是否规范
    4. 创新思考（10%）: 是否有独到见解或延伸思考
    【输出格式】
    请以JSON格式输出评价结果：
    ```json
    {{
        "score": 得分(0-100),
        "level": "评级(优秀/良好/中等/及格/不及格)",
        "difficulty": "评估该作业的实际难度，必须是(easy/medium/hard)之一",
        "feedback": "总体评价",
        "correct_points": ["答对的知识点1", "答对的知识点2"],
        "wrong_points": ["错误点1及原因", "错误点2及原因"],
        "suggestions": ["改进建议1", "改进建议2"],
        "reference_answer": "参考答案或补充说明"
    }}
    ```
    【批改原则】
    1. 客观公正，有理有据
    2. 指出问题的同时给予鼓励
    3. 提供具体的改进方向
    4. 如果答案基本正确但表述不完善，也要肯定学生的思路"""

            try:
                messages = [SystemMessage(content=system_prompt_text)]
                content_blocks = []

                # --- 1. 构建参考资料部分 ---
                ref_info = "=== 第一部分：参考资料/标准答案 ===\n"
                if reference_content:
                    ref_info += f"【参考文本/OCR内容】\n{reference_content}\n"
                if reference_images:
                    ref_info += f"【参考图片】 (共 {len(reference_images)} 张，见下方)\n"
                content_blocks.append({"type": "text", "text": ref_info})

                # 🟢 修改点 1：通过图片路径调用 encode_image 函数，对图片进行压缩及 Base64 转换
                for img_path in reference_images[:3]:
                    if img_path:
                        img_base64 = encode_image(img_path)
                        if img_base64:
                            content_blocks.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_base64}", "detail": "auto"}
                            })

                # --- 2. 构建学生作业部分 ---
                stu_info = "\n\n=== 第二部分：学生作业 ===\n"
                if student_answer:
                    stu_info += f"【学生文本/OCR内容】\n{student_answer}\n"
                if student_images:
                    stu_info += f"【学生作业图片】 (共 {len(student_images)} 张，见下方)\n"
                content_blocks.append({"type": "text", "text": stu_info})

                # 🟢 修改点 2：同样调用 encode_image 处理学生作业的图片路径
                for img_path in student_images[:5]:
                    if img_path:
                        img_base64 = encode_image(img_path)
                        if img_base64:
                            content_blocks.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_base64}", "detail": "auto"}
                            })

                # 发送请求
                messages.append(HumanMessage(content=content_blocks))
                response = self.llm.invoke(messages)
                result = response.content

                # JSON 提取逻辑（增强版）
                result = result.strip()
                # 移除思维链标签
                result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()

                grading = None
                # 策略 1: Markdown 代码块
                code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
                matches = re.findall(code_block_pattern, result, re.DOTALL)
                if matches:
                    for match in reversed(matches):
                        try:
                            grading = json.loads(match)
                            break
                        except json.JSONDecodeError:
                            continue

                # 策略 2: 查找 {}
                if grading is None:
                    start_idx = result.find('{')
                    end_idx = result.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        try:
                            grading = json.loads(result[start_idx: end_idx + 1])
                        except json.JSONDecodeError:
                            pass

                if grading is None:
                    raise ValueError(f"无法提取有效JSON, 原始内容: {result[:100]}...")

                logger.info(f"批改完成，得分: {grading.get('score', 'N/A')} (尝试次数: {retry_count + 1})")

                return {
                    **state,
                    "grading_result": grading,
                    "error_message": "",
                    "retry_count": 0
                }

            except Exception as e:
                logger.error(f"批改失败 (第 {retry_count + 1} 次): {e}")
                # 构造一个兜底的 grading_result，以防重试耗尽后 response_formatter 能显示点东西
                fallback_grading = {
                    "score": -1,
                    "feedback": f"解析批改结果失败。错误: {str(e)}。请查看日志或重试。",
                    "correct_points": [],
                    "wrong_points": [],
                    "suggestions": []
                }
                return {
                    **state,
                    "grading_result": fallback_grading,
                    "error_message": str(e),
                    "retry_count": retry_count + 1
                }

    def _summary_node(self, state: AgentState) -> AgentState:
        """章节总结节点"""
        chapter_info = state.get("chapter_info", "")
        retrieved_docs = state.get("retrieved_docs", [])

        # 构建上下文
        context = "\n\n".join([doc["content"] for doc in retrieved_docs])

        # 总结提示词
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是透平机械原理课程的教学助手。请根据提供的资料，对指定章节进行系统性总结。

【总结要求】
1. 提炼核心知识点和重要概念
2. 归纳关键公式和原理
3. 指出学习重点和难点
4. 列出常见考点
5. 提供学习建议

【输出格式】
## {chapter} 知识点总结

### 一、核心概念
- 概念1: 解释
- 概念2: 解释

### 二、重要公式
- 公式1: 含义说明
- 公式2: 含义说明

### 三、学习重点
1. 重点1
2. 重点2

### 四、常见考点
1. 考点1
2. 考点2

### 五、学习建议
- 建议1
- 建议2"""),
            ("user", """【章节信息】
{chapter}

【参考资料】
{context}

请生成该章节的知识点总结。""")
        ])

        try:
            chain = summary_prompt | self.llm | StrOutputParser()
            summary = chain.invoke({
                "chapter": chapter_info if chapter_info else "透平机械原理",
                "context": context if context else "（无额外参考资料）"
            })

            return {
                **state,
                "qa_answer": summary,
                "qa_confidence": 0.85 if retrieved_docs else 0.6
            }

        except Exception as e:
            logger.error(f"总结生成失败: {e}")
            return {
                **state,
                "qa_answer": f"生成总结时出现错误: {str(e)}",
                "qa_confidence": 0.0
            }

    def _original_summary_logic(self, state):
        chapter_info = state.get("chapter_info", "")
        retrieved_docs = state.get("retrieved_docs", [])
        context = "\n\n".join([doc["content"] for doc in retrieved_docs])
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是透平机械原理课程的教学助手...（略）..."""),
            ("user", """【章节信息】{chapter}\n【参考资料】{context}\n请生成该章节的知识点总结。""")
        ])
        try:
            chain = summary_prompt | self.llm | StrOutputParser()
            summary = chain.invoke({
                "chapter": chapter_info if chapter_info else "透平机械原理",
                "context": context if context else "（无额外参考资料）"
            })
            return {
                **state,
                "qa_answer": summary,
                "qa_confidence": 0.85 if retrieved_docs else 0.6
            }
        except Exception as e:
            logger.error(f"总结生成失败: {e}")
            return {
                **state,
                "qa_answer": f"生成总结时出现错误: {str(e)}",
                "qa_confidence": 0.0
            }

    def _response_formatter_node(self, state: AgentState) -> AgentState:
        """响应格式化节点 - 将各节点输出格式化为最终响应"""
        intent = state.get("intent", IntentType.UNKNOWN)
        error_msg = state.get("error_message", "")

        # 如果是重试耗尽导致的错误，显示最终错误信息
        # 注意：GENERATE 和 GRADE 即使有 error_msg 也可能因为重试耗尽进入这里，需要处理

        response = ""

        if intent == IntentType.QA:
            answer = state.get("qa_answer", "")
            sources = state.get("qa_sources", [])
            confidence = state.get("qa_confidence", 0)

            response = f"📚 **回答**\n\n{answer}"

            if sources:
                response += "\n\n---\n📖 **参考来源**"
                for src in sources[:3]:
                    response += f"\n- {src['file']} (第{src['page']}页)"

            if confidence < 0.5:
                response += "\n\n⚠️ *注：相关资料有限，建议查阅教材确认。*"

        elif intent == IntentType.GENERATE_QUESTIONS:
            questions = state.get("generated_questions", [])
            chapter = state.get("chapter_info", "透平机械原理")
            qtype = state.get("question_type", "综合")

            response = f"📝 **{chapter} - {qtype}练习题**\n\n"

            for i, q in enumerate(questions, 1):
                if isinstance(q, dict):
                    if "raw_text" in q:
                        response += q["raw_text"]
                    else:
                        response += f"**第{i}题** ({q.get('difficulty', '中等')})\n"
                        response += f"{q.get('question', '')}\n"

                        if q.get('options'):
                            for opt in q['options']:
                                response += f"  {opt}\n"

                        response += f"\n<details>\n<summary>点击查看答案</summary>\n\n"
                        response += f"**答案**: {q.get('answer', '')}\n\n"
                        response += f"**解析**: {q.get('explanation', '')}\n\n"
                        response += f"**知识点**: {q.get('knowledge_point', '')}\n"
                        response += f"</details>\n\n---\n\n"

        elif intent == IntentType.GRADE_HOMEWORK:
            grading = state.get("grading_result", {})

            score = grading.get("score", -1)
            level = grading.get("level", "未评级")
            feedback = grading.get("feedback", "")
            correct = grading.get("correct_points", [])
            wrong = grading.get("wrong_points", [])
            suggestions = grading.get("suggestions", [])
            ref_answer = grading.get("reference_answer", "")

            if score >= 0:
                # 根据分数选择emoji
                if score >= 90:
                    emoji = "🌟"
                elif score >= 80:
                    emoji = "👍"
                elif score >= 70:
                    emoji = "📈"
                elif score >= 60:
                    emoji = "💪"
                else:
                    emoji = "📚"

                response = f"{emoji} **作业批改结果**\n\n"
                response += f"**得分**: {score}分 ({level})\n\n"
                response += f"**总评**: {feedback}\n\n"

                if correct:
                    response += "✅ **正确之处**:\n"
                    for c in correct:
                        response += f"- {c}\n"
                    response += "\n"

                if wrong:
                    response += "❌ **需要改进**:\n"
                    for w in wrong:
                        response += f"- {w}\n"
                    response += "\n"

                if suggestions:
                    response += "💡 **改进建议**:\n"
                    for s in suggestions:
                        response += f"- {s}\n"
                    response += "\n"

                if ref_answer:
                    response += f"📖 **参考答案**:\n{ref_answer}"
            else:
                response = f"❌ 批改失败: {feedback}"

        elif intent == IntentType.SUMMARY:
            response = state.get("qa_answer", "")

        else:
            response = "🤔 抱歉，我没有理解您的意图。我可以帮您：\n\n"
            response += "1. **回答问题** - 直接提问透平机械相关知识\n"
            response += "2. **生成练习题** - 例如：给我出5道关于轴流式压缩机的选择题\n"
            response += "3. **批改作业** - 例如：帮我批改这道题：[您的答案]\n"
            response += "4. **总结章节** - 例如：总结离心式压缩机的知识点\n"

        return {
            **state,
            "final_response": response
        }

    def _error_handler_node(self, state: AgentState) -> AgentState:
        """错误处理节点"""
        error_msg = state.get("error_message", "未知错误")

        return {
            **state,
            "final_response": f"处理请求时遇到错误: {error_msg}\n请稍后重试或换一种方式提问。"
        }

    # --------------------------------
    # 路由函数
    # --------------------------------

    def _route_by_intent(self, state: AgentState) -> str:
        """根据意图路由"""
        intent = state.get("intent", IntentType.UNKNOWN)
        confidence = state.get("intent_confidence", 0)
        # 获取用户提供的参考内容
        reference_content = state.get("reference_content", "")
        # 【新增】获取用户提供的参考图片（对应视觉模式）
        reference_images = state.get("reference_images", [])

        if confidence < 0.3:
            return "error"
        # 【新增逻辑】如果是批改作业，且用户已提供参考答案，则跳过检索直接批改
        has_user_reference = (reference_content and reference_content.strip()) or (reference_images and len(reference_images) > 0)
        if intent == IntentType.GRADE_HOMEWORK and has_user_reference:
            return "grade_direct"

        route_map = {
            IntentType.QA: "qa",
            IntentType.GENERATE_QUESTIONS: "generate",
            IntentType.GRADE_HOMEWORK: "grade",
            IntentType.SUMMARY: "summary",
            IntentType.UNKNOWN: "qa"  # 默认当作问答
        }
        return route_map.get(intent, "qa")

    def _route_after_retrieval(self, state: AgentState) -> str:
        """检索后路由"""
        intent = state.get("intent", IntentType.QA)

        route_map = {
            IntentType.QA: "qa",
            IntentType.GENERATE_QUESTIONS: "generate",
            IntentType.SUMMARY: "summary",
            IntentType.GRADE_HOMEWORK: "grade"
        }

        return route_map.get(intent, "qa")

    # --------------------------------
    # 公共接口
    # --------------------------------

    def chat(self, user_input: str, session_id: str = "default", **kwargs):
        # 理想情况下，这里应该从数据库读取该 session_id 对应的 profile
        # 由于我们使用 MemorySaver Checkpointer，如果 session_id 相同，
        # LangGraph 会自动加载上一轮的 state (包含 user_profile)，
        # 所以这里的 initial_state 主要是为新会话准备默认值。
        # 初始化状态
        # 【修改】从磁盘读取当前会话的用户画像
        current_profile = self.load_profile(session_id)
        initial_state: AgentState = {
            "user_input": user_input,
            "session_id": session_id,
            "intent": kwargs.get("intent", IntentType.UNKNOWN),
            "intent_confidence": 1.0 if "intent" in kwargs else 0.0,
            "chat_history": [],
            "retrieved_docs": [],
            "retrieved_images": [],
            "qa_answer": "",
            "qa_confidence": 0.0,
            "qa_sources": [],
            "chapter_info": kwargs.get("chapter_info", ""),
            "question_type": kwargs.get("question_type", "short_answer"),
            "question_count": kwargs.get("question_count", 5),
            "difficulty": kwargs.get("difficulty", "medium"),
            "generated_questions": [],
            "student_answer": kwargs.get("student_answer", ""),
            "reference_content": kwargs.get("reference_content", ""),
            "student_images": kwargs.get("student_images", []),
            "reference_images": kwargs.get("reference_images", []),
            "grading_result": {},
            "final_response": "",
            "error_message": "",
            "retry_count": 0 ,
            "user_profile": kwargs.get("user_profile", current_profile),
        }
        # 配置（用于检查点）
        config = {"configurable": {"thread_id": session_id}}
        try:
            final_state = self.app.invoke(initial_state, config)
            # ... return logic ...
            return {
                "response": final_state.get("final_response", ""),
                "intent": final_state.get("intent", IntentType.UNKNOWN).value,
                "confidence": final_state.get("qa_confidence", 0),
                "sources": final_state.get("qa_sources", []),
                "questions": final_state.get("generated_questions", []),
                "grading": final_state.get("grading_result", {}),
                "session_id": session_id
            }
        except Exception as e:
            logger.exception(f"Agent 执行出错: {e}")
            return {
                "response": final_state.get("final_response", ""),
                "intent": final_state.get("intent", IntentType.UNKNOWN).value,
                "confidence": final_state.get("qa_confidence", 0),
                "grading": final_state.get("grading_result", {}),
                "user_profile": final_state.get("user_profile", {}),  # 【新增】返回用户最新画像(含 Elo 等级)
                "session_id": session_id
            }

    def generate_questions(
            self,
            chapter: str,
            question_type: str = "short_answer",
            count: int = 5,
            difficulty: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        直接生成练习题的便捷方法

        Args:
            chapter: 章节名称
            question_type: 题型 (choice/fill_blank/short_answer/calculation)
            count: 题目数量
            difficulty: 难度 (easy/medium/hard)
        """
        prompt = f"请给我出{count}道关于{chapter}的{question_type}，难度为{difficulty}"

        result = self.chat(
            prompt,
            intent=IntentType.GENERATE_QUESTIONS,
            chapter_info=chapter,
            question_type=question_type,
            question_count=count,
            difficulty=difficulty
        )

        return result.get("questions", [])

    def grade_answer(
            self,
            student_answer: str= "",
            student_images: List[str] = None, # 新增参数
            reference: str = "",
            reference_images: List[str] = None,  # 新增参数
            topic: str = ""
    ) -> Dict[str, Any]:
        """
        批改答案的便捷方法 (支持图片)
        """
        if topic:
            prompt = f"请批改关于【{topic}】的作业"
        else:
            prompt = "请批改这份作业"

        result = self.chat(
            prompt,
            intent=IntentType.GRADE_HOMEWORK,
            student_answer=student_answer,
            student_images=student_images if student_images else [], # 传递图片
            reference_images=reference_images if reference_images else [],  # 传递图片
            reference_content=reference,
            chapter_info=topic
        )
        return result

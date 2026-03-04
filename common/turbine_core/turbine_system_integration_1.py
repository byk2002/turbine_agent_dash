"""
透平机械原理课程系统 - 完整整合版
整合 MultiDocumentKnowledgeBase (RAG) + LangGraph Agent

使用方法:
1. 设置环境变量 OPENAI_API_KEY
2. 运行程序
3. 先添加课程文档（PDF、Word等）
4. 然后可以进行问答、生成练习题、批改作业等操作
"""

import os
import sys
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
import zipfile
import tempfile
try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None
# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入原始RAG系统的所有组件
# 注意：以下导入假设用户的原始代码文件在同一目录下
# 用户需要将原始的多模态RAG代码保存为 multimodal_rag.py

try:
    from multimodel_rag import (
        MultiDocumentKnowledgeBase,
        UnstructuredPDFParser,
        ChunkStore,
        ChunkData,
        ChineseBM25Retriever
    )

    RAG_AVAILABLE = True
except ImportError:
    print("警告: 未找到 multimodel_rag.py，RAG功能将不可用")
    print("请将原始的多模态RAG代码保存为 multimodel_rag.py")
    RAG_AVAILABLE = False
    MultiDocumentKnowledgeBase = None

# 导入 LangGraph Agent
from turbine_course_agent_1 import TurbineCourseAgent

# 其他必要的导入
from langchain_openai import ChatOpenAI
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# === 新增：统一的大模型构建函数 ===
def create_llm(provider="openai", base_url=None, model_name=None, temperature=0.2):
    """
    统一生成 LLM 实例的工厂函数
    """
    # 1. DeepSeek 专用 (如果你想用官方库，否则用 OpenAI 兼容模式也可以)
    if provider == "deepseek":
        api_key =os.getenv("DEEPSEEK_API_KEY")
        return ChatDeepSeek(
            api_key=api_key,
            api_base=base_url or "https://api.deepseek.com",
            model=model_name or "deepseek-reasoner",
            temperature=temperature
        )

    # 2. 通用 OpenAI 兼容模式 (支持 DeepSeek, Moonshot, Zhipu, LocalLLM 等)
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        return ChatOpenAI(
            openai_api_key=api_key,
            openai_api_base=base_url or "https://api.zchat.tech/v1",  # 关键：只要改这个地址，就能换任何模型
            model_name= "gpt-5-2",
            temperature=temperature
        )



class TurbineMachinerySystem:
    """
    透平机械原理课程完整系统
    整合了:
    - 多模态RAG知识库
    - LangGraph智能体Agent
    - 问答、练习题生成、作业批改功能
    """

    def __init__(
            self,
            kb_path: str = None,
            model_name: str = None,
            api_base: str = None,
            provider: str = "openai",  # 新增 provider 参数
            custom_llm=None
    ):
        """
        初始化系统

        Args:
            kb_path: 知识库存储路径
            openai_api_key: OpenAI API Key
            openai_api_base: API Base URL (可选，用于代理)
            model_name: 使用的模型名称
            custom_llm: 用户自定义的微调模型 (可选)
        """
        self.kb_path = Path(kb_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)

        # === 修改：使用工厂函数创建 LLM ===
        if custom_llm:
            self.llm = custom_llm
        else:
            self.llm = create_llm(
                provider=provider,
                base_url=api_base,
                model_name=model_name,
                temperature=0.2
            )

        logger.info(f"LLM 初始化完成: Provider={provider}, Model={model_name}")

        deepseek_api_key_rag = os.getenv("DEEPSEEK_API_KEY")
        # 初始化知识库 (如果可用)
        self.knowledge_base = None
        if RAG_AVAILABLE and MultiDocumentKnowledgeBase:
            try:
                self.knowledge_base = MultiDocumentKnowledgeBase(
                    str(self.kb_path ),
                    str(deepseek_api_key_rag)
                )
                logger.info("多模态RAG知识库初始化成功")
            except Exception as e:
                logger.error(f"知识库初始化失败: {e}")
                self.knowledge_base = None

        # 初始化 Agent
        self.agent = TurbineCourseAgent(
            knowledge_base=self.knowledge_base,
            llm= self.llm
        )

        # 当前会话ID
        self.current_session_id = "default_session"

        logger.info("透平机械原理课程系统初始化完成")

    # ========================================
    # 知识库管理功能
    # ========================================

    def add_document(self, file_path: str):
        """添加文档到知识库"""
        if not self.knowledge_base:
            print("❌ 知识库不可用")
            return False

        try:
            self.knowledge_base.add_document(file_path)
            print(f"✅ 文档添加成功: {Path(file_path).name}")
            return True
        except Exception as e:
            print(f"❌ 添加失败: {e}")
            return False

    def add_documents_from_directory(self, directory_path: str):
        """从目录批量添加文档"""
        if not self.knowledge_base:
            print("❌ 知识库不可用")
            return False

        try:
            self.knowledge_base.add_documents_from_directory(directory_path)
            print(f"✅ 目录文档添加完成: {directory_path}")
            return True
        except Exception as e:
            print(f"❌ 添加失败: {e}")
            return False

    def list_documents(self):
        """列出知识库中的所有文档"""
        if not self.knowledge_base:
            print("❌ 知识库不可用")
            return {}

        return self.knowledge_base.list_documents()

    def delete_document(self, file_path: str):
        """删除指定文档"""
        if not self.knowledge_base:
            print("❌ 知识库不可用")
            return False

        try:
            self.knowledge_base.delete_document(file_path)
            print(f"✅ 文档已删除")
            return True
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            return False

    # ========================================
    # Agent 交互功能
    # ========================================

    def chat(self, user_input: str, **kwargs):
        """
        与Agent对话

        Args:
            user_input: 用户输入
            **kwargs: 额外参数

        Returns:
            Agent响应结果
        """
        return self.agent.chat(
            user_input,
            session_id=self.current_session_id,
            **kwargs
        )

    def ask_question(self, question: str):
        """
        提问（问答模式）

        Args:
            question: 问题
        """
        result = self.chat(question)
        return result["response"]

    def generate_questions(
            self,
            chapter: str,
            question_type: str = "short_answer",
            count: int = 5,
            difficulty: str = "medium"
    ):
        """
        生成练习题

        Args:
            chapter: 章节名称
            question_type: 题型 (choice/fill_blank/short_answer/calculation)
            count: 题目数量
            difficulty: 难度 (easy/medium/hard)
        """
        return self.agent.generate_questions(
            chapter=chapter,
            question_type=question_type,
            count=count,
            difficulty=difficulty
        )

    def grade_homework(self, student_answer: str = "", student_file: str = "",
                       reference: str = "", reference_file: str = "",
                       topic: str = "", use_vision_model: bool = True):
        """
        批改作业功能升级版 (支持多模态直接输入)
        Args:
            student_answer: 学生答案文本
            student_file: 学生作业文件路径 (PDF/Word/Image)
            reference: 参考答案文本
            reference_file: 参考答案文件路径 (PDF/Word)
            topic: 作业主题/章节 (用于知识库检索)
        """
        final_student_answer = student_answer
        final_reference = reference
        student_img_paths = []  # 用于存储待输入大模型的图片路径
        reference_img_paths = []  # 参考答案图片

        # 辅助函数：处理文件转图片
        def convert_file_to_images(file_path_str, max_pages=5):
            images = []
            if not file_path_str: return images

            path_obj = Path(file_path_str)
            suffix = path_obj.suffix.lower()

            if suffix in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
                images.append(str(path_obj))
            elif suffix == '.pdf':
                if convert_from_path:
                    try:
                        print(f"⏳ (视觉模式) 正在将PDF转换为图片: {path_obj.name} ...")
                        pdf_images = convert_from_path(str(path_obj))
                        temp_dir = Path(tempfile.gettempdir()) / "turbine_grading_temp"
                        temp_dir.mkdir(parents=True, exist_ok=True)
                        for i, img in enumerate(pdf_images):
                            if i >= max_pages: break
                            temp_img_path = temp_dir / f"{path_obj.stem}_p{i}.jpg"
                            img.save(temp_img_path, "JPEG")
                            images.append(str(temp_img_path))
                    except Exception as e:
                        print(f"⚠️ PDF转图片失败: {e}")
                else:
                    print(f"⚠️ 未安装 pdf2image，无法使用视觉模式。")
                    # --- 新增：专门处理 docx 文件中的图片提取 ---
            elif suffix == '.docx':
                try:
                    print(f"⏳ (视觉模式) 正在从 Word 文档提取图片: {path_obj.name} ...")
                    temp_dir = Path(tempfile.gettempdir()) / "turbine_grading_temp"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    with zipfile.ZipFile(file_path_str, 'r') as docx_zip:
                        for info in docx_zip.infolist():
                                # 提取 word/media/ 目录下的所有图片
                            if info.filename.startswith('word/media/'):
                                extracted_path = docx_zip.extract(info, temp_dir)
                                images.append(str(extracted_path))
                except Exception as e:
                    print(f"⚠️ Docx 图片提取失败: {e}")

            return images

            # 辅助函数：OCR/文本解析
        def parse_file_text(file_path_str, prefix_label):
                text_content = ""
                if not file_path_str: return text_content

                if self.knowledge_base:
                    print(f"⏳ (OCR模式) 正在解析文件文本: {file_path_str} ...")
                    # parse_local_file 内部已经集成了 OCR (Unstructured/Pix2Text/Tesseract)
                    content = self.knowledge_base.parse_local_file(file_path_str)
                    if content:
                        text_content = f"\n\n【{prefix_label}】\n{content}"
                else:
                    print("⚠️ 知识库未初始化，无法进行OCR解析。")
                return text_content

         # --- 逻辑分支 ---
        if use_vision_model:
            # === 模式 A: 多模态视觉 (保留原图，不进行OCR) ===
                if student_file:
                    student_img_paths = convert_file_to_images(student_file, max_pages=5)
                    if not student_img_paths and Path(student_file).suffix not in ['.pdf', '.jpg', '.png', '.docx']:
                        final_student_answer += parse_file_text(student_file, "学生文件文本内容")

                if reference_file:
                    reference_img_paths = convert_file_to_images(reference_file, max_pages=10)
                    if not reference_img_paths and Path(reference_file).suffix not in ['.pdf', '.jpg', '.png', '.docx']:
                        final_reference += parse_file_text(reference_file, "参考文件文本内容")

        else:
                # === 模式 B: OCR文字识别 (强制解析为文本，不传图片) ===
                # 这种模式下，student_img_paths 保持为空列表 []，避免 Agent 发送 image_url 导致报错
                if student_file:
                    final_student_answer += parse_file_text(student_file, "学生文件OCR识别内容")

                if reference_file:
                    final_reference += parse_file_text(reference_file, "参考文件OCR识别内容")

            # 调用 Agent
        return self.agent.grade_answer(
                student_answer=final_student_answer,
                    student_images=student_img_paths,  # OCR模式下为空，Vision模式下有值
                    reference=final_reference,
                    reference_images=reference_img_paths,  # OCR模式下为空，Vision模式下有值
                    topic=topic
                )

    def summarize_chapter(self, chapter_name: str):
        """
        总结章节知识点

        Args:
            chapter_name: 章节名称
        """
        result = self.chat(f"总结{chapter_name}的知识点", chapter_info=chapter_name)
        return result["response"]

    # ========================================
    # 会话管理
    # ========================================

    def switch_session(self, session_id: str):
        """切换会话"""
        self.current_session_id = session_id
        print(f"已切换到会话: {session_id}")

    def clear_session_history(self, session_id: str = None):
        """清空会话历史"""
        sid = session_id or self.current_session_id
        if self.knowledge_base:
            self.knowledge_base.clear_chat_history(session_id=sid)
        print(f"会话 {sid} 历史已清空")




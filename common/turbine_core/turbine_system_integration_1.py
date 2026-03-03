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


def interactive_main():
    """交互式主程序"""

    print("=" * 70)
    print("🔧 透平机械原理课程智能系统")
    print("    基于多模态RAG + LangGraph Agent")
    print("=" * 70)


    # 初始化系统
    print("\n正在初始化系统...")
    try:
        system = TurbineMachinerySystem(
            kb_path="./turbine_machine",
        )
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return

    # 主循环
    current_session = "user_session_1"
    system.switch_session(current_session)

    while True:
        print("\n" + "=" * 70)
        print(f"📚 透平机械原理课程系统 | 会话: {current_session}")
        print("=" * 70)
        print("【知识库管理】")
        print("  1. 添加单个文档")
        print("  2. 从文件夹添加文档")
        print("  3. 查看知识库文档")
        print("  4. 删除文档")
        print()
        print("【智能功能】")
        print("  5. 💬 问答对话")
        print("  6. 📝 生成练习题")
        print("  7. ✏️ 批改作业")
        print("  8. 📖 章节知识点总结")
        print()
        print("【系统设置】")
        print("  9. 切换/新建会话")
        print("  10. 清空当前会话历史")
        print("  0. 退出系统")
        print("=" * 70)

        choice = input("请选择功能 (0-10): ").strip()

        if choice == "0":
            print("\n👋 感谢使用透平机械原理课程系统，再见！")
            break

        elif choice == "1":
            file_path = input("请输入文档路径: ").strip().strip('"')
            if file_path:
                system.add_document(file_path)

        elif choice == "2":
            dir_path = input("请输入文件夹路径: ").strip().strip('"')
            if dir_path:
                system.add_documents_from_directory(dir_path)

        elif choice == "3":
            docs_info = system.list_documents()
            print("\n📚 知识库文档列表")
            print("-" * 50)
            if docs_info.get("documents"):
                for path, meta in docs_info["documents"].items():
                    print(f"  📄 {Path(path).name}")
                    print(f"     类型: {meta.get('doc_type', 'N/A')}")
                    print(f"     片段数: {meta.get('chunk_count', 0)}")
            else:
                print("  (空)")
            print(f"\n总片段数: {docs_info.get('total_chunks_in_memory', 0)}")

        elif choice == "4":
            file_path = input("请输入要删除的文档路径: ").strip().strip('"')
            if file_path:
                confirm = input("确认删除? (yes/no): ").strip().lower()
                if confirm == "yes":
                    system.delete_document(file_path)

        elif choice == "5":
            # 问答对话模式
            print("\n💬 进入问答模式 (输入 'back' 返回主菜单)")
            print("-" * 50)
            while True:
                question = input("\n👤 您的问题: ").strip()
                if question.lower() == 'back':
                    break
                if not question:
                    continue

                print("\n🤖 助手: ", end="")
                result = system.chat(question)
                print(result["response"])
                print(f"\n[置信度: {result.get('confidence', 0):.2f}]")

        elif choice == "6":
            # 生成练习题
            print("\n📝 练习题生成")
            print("-" * 50)
            chapter = input("章节名称 (如: 轴流式压缩机): ").strip() or "透平机械原理"

            print("题型选择:")
            print("  1. choice - 选择题")
            print("  2. fill_blank - 填空题")
            print("  3. short_answer - 简答题")
            print("  4. calculation - 计算题")
            qtype_choice = input("选择题型 (1-4, 默认3): ").strip() or "3"
            qtype_map = {"1": "choice", "2": "fill_blank", "3": "short_answer", "4": "calculation"}
            qtype = qtype_map.get(qtype_choice, "short_answer")

            count = int(input("题目数量 (默认5): ").strip() or "5")

            print("难度选择: 1.easy  2.medium  3.hard")
            diff_choice = input("选择难度 (1-3, 默认2): ").strip() or "2"
            diff_map = {"1": "easy", "2": "medium", "3": "hard"}
            difficulty = diff_map.get(diff_choice, "medium")

            print("\n⏳ 正在生成练习题...")
            result = system.chat(
                f"请生成{count}道关于{chapter}的{qtype}，难度为{difficulty}",
                chapter_info=chapter,
                question_type=qtype,
                question_count=count,
                difficulty=difficulty
            )
            print("\n" + result["response"])


        elif choice == "7":
            # 批改作业 - 交互流程更新
            print("\n✏️ 作业批改")
            print("-" * 50)
            # --- 第一步：获取学生答案 ---
            print("请选择学生作业来源:")
            print("1. 直接输入文本")
            print("2. 上传作业文件 (PDF/Word)")
            stu_choice = input("请输入选择 (1-2): ").strip()
            student_answer_text = ""
            student_file_path = ""
            if stu_choice == "1":
                print("\n请输入学生答案 (输入完成后按两次Enter):")
                lines = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                student_answer_text = "\n".join(lines)
            elif stu_choice == "2":
                student_file_path = input("\n请输入学生作业文件的完整路径: ").strip().strip('"')
            # --- 第二步：获取参考标准 ---
            if student_answer_text or student_file_path:
                print("\n请选择参考答案/评分标准来源:")
                print("1. 直接输入文本")
                print("2. 上传参考文档 (PDF/Word)")
                print("3. 无参考 (自动从知识库检索相关知识)")
                ref_choice = input("请输入选择 (1-3): ").strip()
                reference_text = ""
                reference_file_path = ""
                topic_info = ""
                if ref_choice == "1":
                    reference_text = input("\n请输入参考答案文本: ").strip()
                elif ref_choice == "2":
                    reference_file_path = input("\n请输入参考文档的完整路径: ").strip().strip('"')
                elif ref_choice == "3":
                    topic_info = input("\n请输入作业的主题/章节 (用于辅助检索，如'离心压缩机'): ").strip()
                    if not topic_info:
                        topic_info = "透平机械原理作业"
                print("\n⏳ 正在批改... (如果文件较大，请稍候)")
                result = system.grade_homework(
                    student_answer=student_answer_text,
                    student_file=student_file_path,
                    reference=reference_text,
                    reference_file=reference_file_path,
                    topic=topic_info
                )
                print("\n" + result["response"])
            else:
                print("❌ 未输入答案内容")

        elif choice == "8":
            # 章节总结
            print("\n📖 章节知识点总结")
            print("-" * 50)
            chapter = input("请输入章节名称 (如: 离心式压缩机): ").strip()
            if chapter:
                print("\n⏳ 正在生成总结...")
                summary = system.summarize_chapter(chapter)
                print("\n" + summary)

        elif choice == "9":
            new_session = input(f"请输入新会话ID (当前: {current_session}): ").strip()
            if new_session:
                current_session = new_session
                system.switch_session(current_session)

        elif choice == "10":
            confirm = input("确认清空当前会话历史? (yes/no): ").strip().lower()
            if confirm == "yes":
                system.clear_session_history()

        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    interactive_main()

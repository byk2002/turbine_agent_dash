import os
from pathlib import Path
from common.turbine_core.multimodel_rag import MultiDocumentKnowledgeBase
from common.turbine_core.turbine_course_agent_1 import TurbineCourseAgent
import logging
from langchain_openai import ChatOpenAI
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 1. 目录路径配置 (适配 Dashgo 项目结构)
# 假设 instance.py 位于 common/turbine_core/，我们要定位到根目录下的 user_data
BASE_DIR = Path(__file__).resolve().parent.parent.parent
KB_DIR = BASE_DIR / "user_data" / "knowledge_base"
DOCS_DIR = KB_DIR / "docs"

# 确保目录存在
KB_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

print("正在初始化透平机械原理多模态知识库...")
rag_knowledge_base = MultiDocumentKnowledgeBase(
    kb_path=KB_DIR ,          # 知识库工作目录
    deepseek_api_key="sk-7341b8bb16e14a3bae23fd093182a587"
)


api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
            openai_api_key= api_key,
            openai_api_base= "https://api.zchat.tech/v1",  # 关键：只要改这个地址，就能换任何模型
            model_name= "gpt-5-2",
            temperature= 0.2
        )



# 2. 初始化基础模型 (LLM 和 嵌入模型)
# 注意：配置好您的环境 API KEY，或直接在这里传入 api_key 参数
# 全局单例实例化系统
turbine_system = TurbineCourseAgent( knowledge_base=rag_knowledge_base,
            llm = llm )

def correct_homework_wrapper(**kwargs):
    # 提取文件等参数适配 grade_answer
    # ...
    pass

turbine_system.correct_homework = correct_homework_wrapper


from .turbine_system_integration_1 import TurbineMachinerySystem
import os

# 全局单例实例化系统
turbine_system = TurbineMachinerySystem(
    kb_path="./multimodel_doc_kb",
    openai_api_key=os.getenv("OPENAI_API_KEY", "your-key"),
    model_name="gpt-4o"
)
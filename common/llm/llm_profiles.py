from dataclasses import dataclass

@dataclass(frozen=True)
class LLMProfile:
    key: str
    label: str
    model: str
    base_url: str
    api_key_env: str
    multimodal: bool = False   # 是否允许 image_url / 多模态消息

PROFILES: dict[str, LLMProfile] = {
    # 1) OpenAI / ChatGPT（直连 OpenAI）
    "openai_gpt4o": LLMProfile(
        key="openai_gpt4o",
        label="ChatGPT - gpt-4o (OpenAI)",
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY_1",
        multimodal=True,
    ),

    # 2) DeepSeek（OpenAI 兼容）
    "deepseek_chat": LLMProfile(
        key="deepseek_chat",
        label="DeepSeek - deepseek-chat",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        multimodal=False,  # 保险起见先关掉图片（DeepSeek 文档主推文本对话）
    ),
    "deepseek_reasoner": LLMProfile(
        key="deepseek_reasoner",
        label="DeepSeek - deepseek-reasoner",
        model="deepseek-reasoner",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        multimodal=False,
    ),

    # 3) 通义千问 / DashScope 百炼（OpenAI 兼容）
    "qwen_max": LLMProfile(
        key="qwen_max",
        label="千问 - qwen-max (DashScope)",
        model="qwen-max",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
        multimodal=False,
    ),
    "qwen_vl_plus": LLMProfile(
        key="qwen_vl_plus",
        label="千问VL - qwen-vl-plus (DashScope)",
        model="qwen-vl-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
        multimodal=True,
    ),

    # 4) 你现有的 zchat 代理（按你项目原来的 base_url + key 环境变量）
    "zchat_gpt4o": LLMProfile(
        key="zchat_gpt4o",
        label="ChatGPT - gpt-4o (zchat proxy)",
        model="gpt-4o",
        base_url="https://api.zchat.tech/v1",
        api_key_env="OPENAI_API_KEY",
        multimodal=True,
    ),
}

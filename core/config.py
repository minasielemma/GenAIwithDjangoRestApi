from django.conf import settings
import os

class AgentConfig:
    LLM_MODEL = "gemma3:12b"
    LLM_SYSTEM_PROMPT = """You are an AI assistant. Always answer in this format:

    Question: <the user query>
    Thought: <your reasoning>
    Action: <tool name or Final Answer>
    Action Input: <input for the tool>
    Final Answer: <your final answer to the user>"""

    AGENT_TYPE = "zero-shot-react-description"
    MAX_ITERATIONS = 2
    EARLY_STOPPING_METHOD = "generate"
    MEDIA_ROOT = settings.MEDIA_ROOT
    MEDIA_URL = settings.MEDIA_URL
    GRAPH_FIGSIZE = (8, 5)
    GRAPH_DPI = 100
    GRAPH_COLOR = "#36A2EB"

config = AgentConfig()
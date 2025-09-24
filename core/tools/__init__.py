from .retriever_tool import RetrieverTool
from .summarizer_tool import SummarizerTool
from .question_tool import QuestionTool
from .analysis_tool import AnalysisTool
from .graph_tool import GraphTool
from langchain.agents import Tool

class ToolFactory:
    
    @staticmethod
    def create_tools(retriever, llm):
        """Create all tools for the agent"""
        retriever_tool = RetrieverTool(retriever)
        summarizer_tool = SummarizerTool(retriever, llm)
        question_tool = QuestionTool(retriever, llm)
        analyzer_tool = AnalysisTool(retriever, llm)
        graph_tool = GraphTool(retriever, llm)
        
        return [
            Tool(
                name=tool.name,
                func=tool.execute,
                description=tool.description,
                return_direct=False
            ) for tool in [retriever_tool, summarizer_tool, analyzer_tool, graph_tool, question_tool]
        ]
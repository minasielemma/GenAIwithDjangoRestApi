from .base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)

class SummarizerTool(BaseTool):
    
    def __init__(self, retriever, llm):
        super().__init__(
            name="Summarizer",
            description="Summarize the full document or a specific query. Use 'full' for entire doc."
        )
        self.retriever = retriever
        self.llm = llm
    
    def execute(self, query: str, **kwargs):
        logger.info("Summarizing with query: %s", query)
        try:
            if query.lower() == "full":
                chunks = self.retriever.get_all_chunks()
                text = "\n".join([doc.page_content for doc in chunks])
            else:
                text = self.retriever.query(query)
            
            prompt = f"Summarize the following document content concisely:\n\n{text}"
            summary = self.llm(prompt)
            logger.info("Summary generated successfully.")
            return summary
        except Exception as e:
            logger.error("Error in SummarizerTool: %s", str(e))
            return {
                "action": "Final Answer",
                "action_input": f"Error summarizing: {str(e)}"
            }
from .base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)

class RetrieverTool(BaseTool):
    
    def __init__(self, retriever):
        super().__init__(
            name="Document Retriever",
            description="Fetch relevant information from uploaded document"
        )
        self.retriever = retriever
    
    def execute(self, query: str, **kwargs) -> dict:
        logger.info("Retrieving document content for query: %s", query)
        try:
            text = self.retriever.query(query_text=query, k=3)
            logger.info("Retrieved text successfully.")
            return text
        except Exception as e:
            logger.error("Error in RetrieverTool: %s", str(e))
            return {
                "action": "Final Answer",
                "action_input": f"Error retrieving document context: {str(e)}"
            }
import logging
from langchain.agents import initialize_agent
from langchain.schema import SystemMessage
from langchain_community.llms import Ollama

from .config import config
from .mongo_conversational_memory import MongoConversationMemory
from .tools import ToolFactory
from .rag_service import LocalPDFVectorizer
from langchain_core.exceptions import OutputParserException

logger = logging.getLogger(__name__)

class DocumentAgent:

    def __init__(self, user_id: str, session_id: str = "default", doc_id: int = None):
        logger.info("Initializing DocumentAgent with user_id: %s, session_id: %s, doc_id: %s", 
                   user_id, session_id, doc_id)
        
        self.user_id = user_id
        self.session_id = session_id
        self.doc_id = doc_id
        
        self.llm = self._initialize_llm()
        self.memory = self._initialize_memory()
        self.retriever = self._initialize_retriever()
        self.agent = self._initialize_agent()
        
        logger.info("DocumentAgent initialized successfully.")

    def _initialize_llm(self):
        return Ollama(
            model=config.LLM_MODEL,
            system=config.LLM_SYSTEM_PROMPT,
            temperature=0.7, 
            verbose=True,
            top_p=0.9    
        )

    def _initialize_memory(self):
        return MongoConversationMemory(
            session_id=self.session_id,
            user_id=self.user_id
        )

    def _initialize_retriever(self):
        return LocalPDFVectorizer(self.doc_id)

    def _initialize_agent(self):
        tools = ToolFactory.create_tools(self.retriever, self.llm)
        
        return initialize_agent(
            tools=tools,
            llm=self.llm,
            agent=config.AGENT_TYPE,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=config.MAX_ITERATIONS,
            early_stopping_method=config.EARLY_STOPPING_METHOD,
            agent_kwargs={
                "system_message": SystemMessage(
                    content=(
                        "Please ensure that your response fully and accurately addresses the original query provided by the user. "
                        "Only provide the final answer; do NOT include your internal reasoning, thoughts, or intermediate Action/Thought/Observation steps. "
                        "Do NOT respond like: \n"
                        "    Question: What is TULIP\n"
                        "    Thought: ...\n"
                        "    Action: ...\n"
                        "    Action Input: ...\n"
                        "Instead, reply with a concise, informative, and complete answer relevant to the user’s question."
                    )
                ),
                "return_intermediate_steps": False,
            }
        )

    def ask(self, query: str):
        logger.info("Received ask query: %s", query)
        result = self.agent.invoke({"input": query})
        # Save context using the memory object directly
        self.memory.save_context({"input": query}, result)
        logger.info("Agent response: %s", result)
        
        return {
            "answer": result,
            "session_id": self.session_id,
            "doc_id": self.doc_id,
        }
        # except  OutputParserException as e:
        #     fallback_response = self.llm(f"Please answer this question directly: {query}")
        #     return {
        #         "answer": {"output": fallback_response},
        #         "session_id": self.session_id,
        #         "doc_id": self.doc_id,
        #         "error_handled": True
        #     }

    def clear_memory(self):
        logger.info("Clearing memory for session: %s", self.session_id)
        self.memory.clear()
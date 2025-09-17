from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_community.llms import ollama
from threading import Lock
import logging

import ollama as ollama_client
from  typing import Dict, List, Tuple

from core.mongo_conversational_memory import MongoConversationMemory
logger = logging.getLogger('__name__')

class OllamaChatService:

    def __init__(self, user_id:str) -> None:
        self.llm = ollama.Ollama(model="artifish/llama3.2-uncensored",          
                                 temperature=0.7,
                                 top_p=0.9,
                                 num_ctx=2048
                                 )
        self.memory: Dict[str, MongoConversationMemory] = {}
        self.prompt = PromptTemplate(
            input_variables= ["history", "input"],
            template="""You are a helpful, friendly, and knowledgeable AI assistant. 
            Engage in natural conversation with the user, providing thoughtful and concise responses.

            Conversation History:
            {history}
            Current Interaction:
            User: {input}

            Please respond in a helpful and engaging manner:
            AI:"""
        ) 
        self.user_id = user_id

    def get_memory(self, session_id:str)-> MongoConversationMemory:
        if session_id not in self.memory:
            self.memory[session_id] = MongoConversationMemory(session_id=session_id, user_id=self.user_id)
        return self.memory[session_id]
    
    def get_conversation_history(self, session_id: str)-> str:
        memory = self.get_memory(session_id=session_id)
        history = memory.load_memory_variables({})
        return history.get("history", '')
    
    def get_full_conversation_context(self, session_id: str, user_input: str) -> Tuple[str, str]:
        history = self.get_conversation_history(session_id=session_id)
        context = f"History: {history}\nUser: {user_input}"
        return history, context
    
    def create_conversation_chain(self, session_id: str)-> ConversationChain:
        memory = self.get_memory(session_id)
        return ConversationChain(
            llm = self.llm,
            memory = memory,
            prompt = self.prompt,
            verbose = True
        )
    
    
    def generate_response(self, session_id:str, user_input:str)-> dict:
        # try:
            history, context = self.get_full_conversation_context(session_id, user_input)
            conversation = self.create_conversation_chain(session_id=session_id)
            response = conversation.predict(input=user_input)
            memory = self.get_memory(session_id=session_id)
            memory.save_context(inputs={"input":user_input}, outputs={"output": response})
            return {
                "success": True,
                "response": response,
                "history": history,
                "context_used": context,
                "method": "langchain"
            }

        # except Exception as e:
        #     logger.info(f"Got error generating response with conversation {e}")
        #     return self._fallback_response(session_id, user_input)
        
    def _fallback_response(self, session_id:str, user_input:str) -> dict:
        try:
            memory = self.get_memory(session_id=session_id)
            history = memory.load_memory_variables({}).get('history')
            prompt = f"{history}\nUser: {user_input}\nAI"
            response = ollama_client.generate(
                model="artifish/llama3.2-uncensored",
                prompt=prompt,
                stream=False,
                options={
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'num_ctx': 2048
                },
            )
            memory = self.get_memory(session_id=session_id)
            memory.save_context(inputs={"input": prompt}, outputs={"output":response["response"]})

            return {
                "success":True,
                "response": response['response'],
                "history": history,
                "context_used": prompt,
                "method": "ollama_direct",
                "model_used": response.get('model', 'llama2')                
            }
        except Exception as e:
            return {
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                "error": str(e),
                "method": "fallback",
                "success": False
            }

    def clear_memory(self, session_id:str):
        if session_id in self.memory:
            del self.memory[session_id]

    def clear_all_memories(self) -> dict:
        count = len(self.memory)
        self.memory.clear()
        return {"cleared_count": count, "message": "All memories cleared"}
    
    
    def get_conversation_stats(self, session_id: str) -> dict:
        memory = self.get_memory(session_id)
        history = memory.load_memory_variables({})
        history_text = history.get('history', '')
        turns = history_text.count('Human:') + history_text.count('AI:')

        return {
            "session_id": session_id,
            "turns": turns,
            "memory_size": len(history_text),
            "has_memory": session_id in self.memory
        }
    
class OllamaChatServiceSingleton:
    _instances: Dict[str, OllamaChatService] = {}
    _lock = Lock()

    @classmethod
    def get_service(cls, user_id: str) -> "OllamaChatService":
        with cls._lock:
            if user_id not in cls._instances:
                cls._instances[user_id] = OllamaChatService(user_id=user_id)
            return cls._instances[user_id]
from django.utils import timezone
from langchain_core.memory import BaseMemory
from langchain.memory import ConversationBufferMemory
from mongoengine import get_db

class MongoConversationMemory(BaseMemory):
    def __init__(self, session_id: str, user_id: str, collection_name: str = "conversations"):
        super().__init__()
        self._session_id = session_id
        self._user_id = user_id
        self._buffer = ConversationBufferMemory()
        self._db = get_db(alias='default')
        self._collection = self._db[collection_name]
        self.load_from_mongo()

    @property
    def memory_variables(self):
        return self._buffer.memory_variables

    def save_context(self, inputs: dict, outputs: dict):
        output_content = outputs.get('output',None)
        if not output_content:
            output_content = outputs.get('response')
        self._buffer.save_context(inputs, outputs)
        self._collection.update_one(
            {"session_id": self._session_id, "user_id": self._user_id},
            {
                "$push": {"messages": {"role": "user", "content": inputs["input"]}},
                "$set": {"updated_at": timezone.now()},
                "$setOnInsert": {"created_at": timezone.now()}
            },
            upsert=True
        )
        self._collection.update_one(
            {"session_id": self._session_id, "user_id": self._user_id},
            {"$push": {"messages": {"role": "ai", "content": output_content}}},
            upsert=True
        )

    def load_from_mongo(self):
        doc = self._collection.find_one({"session_id": self._session_id, "user_id": self._user_id})
        if doc and "messages" in doc:
            for msg in doc["messages"]:
                if msg["role"] == "user":
                    self._buffer.chat_memory.add_user_message(msg["content"])
                else:
                    self._buffer.chat_memory.add_ai_message(msg["content"])

    def load_memory_variables(self, inputs):
        return self._buffer.load_memory_variables(inputs)

    def clear(self):
        self._collection.delete_one({"_session_id": self._session_id, "_user_id": self._user_id})
        self._buffer.clear()

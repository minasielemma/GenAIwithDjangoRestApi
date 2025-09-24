from .base_tool import BaseTool
import logging
import json

logger = logging.getLogger(__name__)

class QuestionTool(BaseTool):
    
    def __init__(self, retriever, llm):
        super().__init__(
            name="Question Generator",
            description=(
                "Generate different types of questions (MCQ, true/false, short answer, or open-ended) "
                "from the document or specific query text."
            )
        )
        self.retriever = retriever
        self.llm = llm
    
    def execute(self, query: str, **kwargs) -> dict:
        logger.info("Generating questions for query: %s", query)
        try:
            if query.lower() == "full":
                chunks = self.retriever.get_all_chunks()
                text = "\n".join([doc.page_content for doc in chunks])
            else:
                text = self.retriever.query(query)

            question_prompt = self._build_question_prompt(text)
            llm_response = self.llm(question_prompt).strip()
            questions = self._safe_json_parse(llm_response, context_hint="Question generation")
            
            if not questions:
                return {
                    "action": "Final Answer",
                    "action_input": "Could not generate questions. Try refining the query."
                }

            logger.info("Questions generated successfully.")
            return questions
        except Exception as e:
            logger.error("Error in QuestionTool: %s", str(e))
            return {
                "action": "Final Answer",
                "action_input": f"Error generating questions: {str(e)}"
            }
    
    def _build_question_prompt(self, text: str) -> str:
        return f"""
        You are a question generation assistant.
        From the following text, generate diverse types of questions:

        Text:
        {text}

        Instructions:
        - Create at least 5 questions or by user query.
        - Mix question types: Multiple-choice, True/False, Short answer, and Open-ended.
        - Always provide suggested answers for each question.
        - Return output in strict JSON format:
        {{
          "questions": [
            {{
              "type": "MCQ",
              "question": "What is ...?",
              "options": ["A", "B", "C", "D"],
              "answer": "B"
            }},
            {{
              "type": "True/False",
              "question": "The text says ...",
              "answer": "True"
            }},
            {{
              "type": "Short Answer",
              "question": "Explain ...",
              "answer": "..."
            }},
            {{
              "type": "Open-ended",
              "question": "Discuss ...",
              "answer": "Sample points..."
            }}
          ]
        }}
        """
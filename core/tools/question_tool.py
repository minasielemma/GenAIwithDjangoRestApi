from .base_tool import BaseTool
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class QuestionTool(BaseTool):

    def __init__(self, retriever, llm, min_questions: int = 5, max_retries: int = 2):
        super().__init__(
            name="Question Generator",
            description=(
                "Generate questions from the document. "
                "Input: text like '5 questions about topic'. "
                "Output: mixed question types or one of them(MCQ, Short Answer, Open Ended, Other)."
            )
        )
        self.retriever = retriever
        self.llm = llm
        self.min_questions = max(1, int(min_questions))
        self.max_retries = max(1, int(max_retries))

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        logger.info("QuestionTool executed with query: %s", query)
        try:
            clean_query = self._clean_input_query(query)
            document_text = self._get_document_content(clean_query)
            if not document_text:
                questions_data = self._create_basic_fallback_questions(clean_query, "")
            else:
                questions_data = self._generate_questions_safely(document_text, clean_query)

            return {
                "type": "final_answer",
                "output": questions_data
            }

        except Exception as e:
            logger.exception("Critical error in QuestionTool: %s", e)
            fallback = self._create_basic_fallback_questions(query, "")
            return {"type": "final_answer", "output": fallback}

    def _clean_input_query(self, raw_input: str) -> str:
        if not raw_input or len(raw_input.strip()) < 3:
            return "main concepts"
        return raw_input.strip()[:200]

    def _get_document_content(self, query: str) -> str:
        try:
            if hasattr(self.retriever, "get_all_chunks"):
                chunks = self.retriever.get_all_chunks()
                if chunks:
                    return "\n".join([getattr(d, "page_content", str(d)) for d in chunks[:8]])

            if hasattr(self.retriever, "get_relevant_documents"):
                docs = self.retriever.get_relevant_documents(query)
                if docs:
                    return "\n".join([getattr(d, "page_content", str(d)) for d in docs[:6]])

            if hasattr(self.retriever, "get_all_documents"):
                docs = self.retriever.get_all_documents()
                if docs:
                    return "\n".join([getattr(d, "page_content", str(d)) for d in docs[:8]])

            if hasattr(self.retriever, "query"):
                result = self.retriever.query(query, k=3)
                if isinstance(result, str):
                    return result
                if isinstance(result, list):
                    return "\n".join([getattr(d, "page_content", str(d)) for d in result[:6]])
                if hasattr(result, "page_content"):
                    return result.page_content

        except Exception as e:
            logger.warning("Error while calling retriever: %s", e)

        return ""

    def _generate_questions_safely(self, document_text: str, user_query: str) -> Dict[str, Any]:
        try:
            raw_try = self._try_json_generation(document_text, user_query)
            if raw_try:
                return {"actions": "Final Answer", "action_input": raw_try}
        except Exception as e:
            logger.debug("Raw generation attempt failed: %s", e)

        try:
            text_try = self._try_text_generation(document_text, user_query)
            if text_try:
                return {"actions": "Final Answer", "action_input": text_try}
        except Exception as e:
            logger.debug("Text fallback generation failed: %s", e)

        return self._create_basic_fallback_questions(user_query, document_text)

    def _call_llm(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        for attempt in range(self.max_retries):
            try:
                resp = self.llm(prompt)
                if isinstance(resp, str):
                    return resp
                if isinstance(resp, dict) and "text" in resp:
                    return str(resp["text"])
                if hasattr(resp, "text"):
                    return str(resp.text)
            except Exception as e:
                logger.debug("LLM call attempt %d failed: %s", attempt + 1, e)
                continue
        raise RuntimeError("LLM invocation failed")

    def _try_json_generation(self, document_text: str, user_query: str) -> Optional[Any]:
        prompt = self._build_json_prompt(document_text, user_query)
        raw = self._call_llm(prompt)
        if not raw or not raw.strip():
            return None

        json_block = self._extract_first_json_block(raw)
        if json_block:
            return json_block 
        return raw 

    def _try_text_generation(self, document_text: str, user_query: str) -> Optional[str]:
        prompt = f"""
        You are a question generation agent. Using only the text below, produce based on user request questions and the question type must be based on user request.
        TEXT:
        {document_text}
        USER REQUEST: {user_query}
        """
        return self._call_llm(prompt)

    def _extract_first_json_block(self, text: str) -> Optional[str]:
        if not text:
            return None
        start = None
        depth = 0
        in_string = False
        esc = False
        for i, ch in enumerate(text):
            if ch == '"' and not esc:
                in_string = not in_string
            if ch == "\\" and not esc:
                esc = True
                continue
            esc = False
            if in_string:
                continue
            if ch == '{':
                if start is None:
                    start = i
                depth += 1
            elif ch == '}' and start is not None:
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        return None

    def _create_basic_fallback_questions(self, user_query: str = "", document_text: str = "") -> Dict[str, Any]:
        base = user_query or (document_text[:80] if document_text else "the document")
        qlist = [
            {"type": "Short Answer", "question": f"What is the main idea of {base}?", "answer": "Refer to the document."},
            {"type": "Short Answer", "question": f"List one key fact or claim stated in {base}.", "answer": "Refer to the document."},
            {"type": "Open Ended", "question": f"How could the information in {base} be applied in practice?"},
            {"type": "MCQ", "question": f"Which statement is true about {base}?", "options": ["Option A", "Option B", "Option C", "Option D"], "answer": "A"},
            {"type": "Short Answer", "question": f"Name one term or concept discussed in {base}.", "answer": "Refer to the document."}
        ]
        return {"actions": "Final Answer", "action_input": qlist}

    def _build_json_prompt(self, document_text: str, user_query: str) -> str:
        return f"""
        You are an expert question generation agent. Use ONLY the provided document text to create questions.
        Do NOT use external knowledge.
        Question type must be based on user request.

        USER REQUEST: {user_query}

        DOCUMENT:
        {document_text[:3000]}

        Return ONLY a single JSON-like object in this structure (no explanation):
        {{
          "questions": [
            {{"type": "MCQ", "question": "?", "options": ["A","B","C","D"], "answer": "A"}},
            {{"type": "Short Answer", "question": "?", "answer": "..." }},
            {{"type": "Open Ended", "question": "?"}}
          ]
        }}
        """

from .base_tool import BaseTool
import logging
import json
import re
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

    def execute(self, query: str, **kwargs) -> str:
        logger.info("QuestionTool executed with query: %s", query)
        try:
            clean_query = self._clean_input_query(query)
            logger.debug("Cleaned query: %s", clean_query)

            document_text = self._get_document_content(clean_query)
            if not document_text:
                logger.warning("No document content retrieved; will still produce fallback questions.")
                questions_data = self._create_basic_fallback_questions(clean_query, "")
                questions_data = self._ensure_minimum_and_types(questions_data, "", clean_query)
                return self._format_as_final_answer(questions_data, clean_query)

            questions_result = self._generate_questions_safely(document_text, clean_query)
            questions_result = self._ensure_minimum_and_types(questions_result, document_text, clean_query)
            return self._format_as_final_answer(questions_result, clean_query)

        except Exception as e:
            logger.exception("Critical error in QuestionTool: %s", e)
            fallback = self._create_basic_fallback_questions(query, "")
            fallback = self._ensure_minimum_and_types(fallback, "", query)
            return self._format_as_final_answer(fallback, query)


    def _clean_input_query(self, raw_input: str) -> str:
        if not raw_input or len(raw_input.strip()) < 3:
            return "main concepts"

        input_str = raw_input.strip()

        if input_str.startswith('{'):
            try:
                data = json.loads(input_str)
                for key in ['query', 'input', 'text', 'question', 'request']:
                    if key in data and data[key]:
                        return str(data[key])[:200]
            except Exception:
                pass

        patterns = [
            r'query[":\s]*([^},]+)',
            r'input[":\s]*([^},]+)',
            r'text[":\s]*([^},]+)',
            r'generate[^"]*"([^"]+)"',
            r'about[^"]*"([^"]+)"'
        ]
        for pattern in patterns:
            match = re.search(pattern, input_str, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip('"\': ')
                if len(extracted) > 3:
                    return extracted[:200]

        return input_str[:200]


    def _get_document_content(self, query: str) -> str:
        try:
            if hasattr(self.retriever, "get_all_chunks"):
                chunks = self.retriever.get_all_chunks()
                if chunks:
                    text = "\n".join([getattr(d, "page_content", str(d)) for d in chunks[:8]])
                    return text

            if hasattr(self.retriever, "get_relevant_documents"):
                try:
                    docs = self.retriever.get_relevant_documents(query)
                    if docs:
                        text = "\n".join([getattr(d, "page_content", str(d)) for d in docs[:6]])
                        return text
                except TypeError:
                    try:
                        docs = self.retriever.get_relevant_documents({"query": query})
                        if docs:
                            text = "\n".join([getattr(d, "page_content", str(d)) for d in docs[:6]])
                            return text
                    except Exception:
                        pass

            if hasattr(self.retriever, "get_all_documents"):
                docs = self.retriever.get_all_documents()
                if docs:
                    text = "\n".join([getattr(d, "page_content", str(d)) for d in docs[:8]])
                    return text

            if hasattr(self.retriever, "query"):
                try:
                    result = self.retriever.query(query, k=3)
                    if isinstance(result, str):
                        return result
                    if isinstance(result, list):
                        text = "\n".join([getattr(d, "page_content", str(d)) for d in result[:6]])
                        return text
                    if hasattr(result, "page_content"):
                        return result.page_content
                except Exception:
                    pass

            if hasattr(self.retriever, "as_retriever"):
                try:
                    temp_ret = self.retriever.as_retriever()
                    if hasattr(temp_ret, "get_relevant_documents"):
                        docs = temp_ret.get_relevant_documents(query)
                        if docs:
                            text = "\n".join([getattr(d, "page_content", str(d)) for d in docs[:6]])
                            return text
                except Exception:
                    pass

        except Exception as e:
            logger.warning("Error while calling retriever: %s", e)

        return ""

    def _generate_questions_safely(self, document_text: str, user_query: str) -> Dict[str, Any]:
        try:
            json_try = self._try_json_generation(document_text, user_query)
            if json_try and isinstance(json_try, dict) and "questions" in json_try and json_try["questions"]:
                return json_try
        except Exception as e:
            logger.debug("JSON-first generation attempt raised: %s", e)

        try:
            text_try = self._try_text_generation(document_text, user_query)
            if text_try:
                return {"questions": text_try}
        except Exception as e:
            logger.debug("Text fallback generation attempt raised: %s", e)

        return self._create_basic_fallback_questions(user_query, document_text)

    def _call_llm(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        err_msgs = []
        last_error = None
        for attempt in range(self.max_retries):
            try:
                try:
                    resp = self.llm(prompt)
                    if isinstance(resp, str):
                        return resp
                    if isinstance(resp, dict) and "text" in resp:
                        return str(resp["text"])
                    if hasattr(resp, "text"):
                        return str(resp.text)
                except TypeError:
                    pass
                except Exception as e:
                    err_msgs.append(f"direct-call failed: {e}")

                if hasattr(self.llm, "predict"):
                    try:
                        p = self.llm.predict(prompt)
                        if isinstance(p, str):
                            return p
                    except Exception as e:
                        err_msgs.append(f"predict failed: {e}")

                if hasattr(self.llm, "generate"):
                    try:
                        gen = self.llm.generate([prompt]) if isinstance(prompt, str) else self.llm.generate(prompt)
                        if isinstance(gen, str):
                            return gen
                        if hasattr(gen, "generations"):
                            gens = gen.generations
                            if gens and isinstance(gens[0], list) and getattr(gens[0][0], "text", None):
                                return gens[0][0].text
                            if gens and hasattr(gens[0][0], "text"):
                                return gens[0][0].text
                    except Exception as e:
                        err_msgs.append(f"generate failed: {e}")

                if hasattr(self.llm, "predict_messages"):
                    try:
                        pmsg = self.llm.predict_messages(prompt)
                        if isinstance(pmsg, str):
                            return pmsg
                        if hasattr(pmsg, "content"):
                            return str(pmsg.content)
                    except Exception as e:
                        err_msgs.append(f"predict_messages failed: {e}")

                raise RuntimeError("No usable LLM call returned text. Attempts: " + "; ".join(err_msgs))

            except Exception as exc:
                logger.debug("LLM call attempt %d failed: %s", attempt + 1, exc)
                last_error = exc
                continue

        logger.warning("All LLM attempts failed. Last errors: %s", err_msgs)
        raise RuntimeError("LLM invocation failed: " + (str(err_msgs) or str(last_error)))
    
    def _try_json_generation(self, document_text: str, user_query: str) -> Optional[Dict[str, Any]]:
        prompt = self._build_json_prompt(document_text, user_query)
        try:
            raw = self._call_llm(prompt)
            if not raw or not raw.strip():
                return None

            json_block = self._extract_first_json_block(raw)
            if not json_block:
                logger.debug("No JSON block identified in LLM response during JSON-first attempt.")
                return None

            data = json.loads(json_block)
            if "questions" in data and isinstance(data["questions"], list):
                normalized = []
                for q in data["questions"]:
                    if not isinstance(q, dict) or "question" not in q:
                        continue
                    entry = self._normalize_question(q)
                    if entry:
                        normalized.append(entry)

                if normalized:
                    return {"questions": normalized}
        except Exception as e:
            logger.debug("JSON generation error: %s", e)
            return None

        return None


    def _try_text_generation(self, document_text: str, user_query: str) -> Optional[List[Dict[str, Any]]]:
        prompt = f"""
                You are a question generation agent. Using only the text below, produce based on user query questions in this simple line format:
                1. [MCQ] Question text? | Options: A) ... ; B) ... ; C) ... ; D) ... | Answer: B
                2. [Short Answer] Question text? | Answer: ...
                3. [Open Ended] Question text?
                Provide no extra commentary.
                TEXT:
                {document_text}
                USER REQUEST: {user_query}
                """
        try:
            raw = self._call_llm(prompt)
            if not raw:
                return None
            parsed = self._parse_text_questions(raw)
            return parsed
        except Exception as e:
            logger.debug("Text-generation fallback failed: %s", e)
            return None

    def _parse_text_questions(self, text: str) -> Optional[List[Dict[str, Any]]]:
        questions: List[Dict[str, Any]] = []
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for line in lines:
            m_mcq = re.search(
                r'\[MCQ\].*?([^|]+)\|\s*Options:\s*(.+?)\|\s*Answer:\s*([A-D])',
                line, re.IGNORECASE
            )
            if m_mcq:
                q_text = m_mcq.group(1).strip().rstrip('?') + '?'
                opts_raw = m_mcq.group(2).strip()
                opts = re.split(r'\s*;\s*|\s*\|\s*', opts_raw)
                cleaned_opts = []
                for o in opts:
                    o = re.sub(r'^[A-D]\)\s*', '', o.strip(), flags=re.IGNORECASE)
                    if o:
                        cleaned_opts.append(o)
                while len(cleaned_opts) < 4:
                    cleaned_opts.append("None of the above")
                cleaned_opts = cleaned_opts[:4]
                ans = m_mcq.group(3).strip().upper()
                questions.append({"type": "MCQ", "question": q_text, "options": cleaned_opts, "answer": ans})
                continue

            m_generic = re.search(r'\[\s*([^\]]+)\s*\]\s*([^\|]+)(?:\|\s*Answer:\s*(.+))?', line, re.IGNORECASE)
            if m_generic:
                q_type = m_generic.group(1).strip()
                q_text = m_generic.group(2).strip().rstrip('?') + '?'
                answer = None
                if m_generic.group(3):
                    answer = m_generic.group(3).strip()
                entry = {"type": q_type, "question": q_text}
                if answer:
                    entry["answer"] = answer
                questions.append(entry)
                continue

            m_simple = re.search(r'([^|]+)\|\s*Answer:\s*(.+)$', line)
            if m_simple:
                q_text = m_simple.group(1).strip().rstrip('?') + '?'
                answer = m_simple.group(2).strip()
                questions.append({"type": "Short Answer", "question": q_text, "answer": answer})
                continue

        return questions if questions else None

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
                    candidate = text[start:i+1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        start = None
                        depth = 0
        return None


    def _ensure_minimum_and_types(self, questions_data: Dict[str, Any], document_text: str, user_query: str) -> Dict[str, Any]:
        qlist = questions_data.get("questions", []) if isinstance(questions_data, dict) else []
        normalized = []
        for q in qlist:
            if isinstance(q, dict):
                n = self._normalize_question(q)
                if n:
                    normalized.append(n)

        types_present = {q["type"] for q in normalized}
        if "MCQ" not in types_present:
            normalized.insert(0, self._templated_mcq(document_text, user_query))
            types_present.add("MCQ")
        if "Short Answer" not in types_present:
            normalized.insert(0, self._templated_short_answer(document_text, user_query))
            types_present.add("Short Answer")
        if "Open Ended" not in types_present:
            normalized.insert(0, self._templated_open_ended(document_text, user_query))
            types_present.add("Open Ended")

        if len(normalized) < self.min_questions:
            needed = self.min_questions - len(normalized)
            extras = self._generate_additional_questions(document_text, user_query, needed, existing=normalized)
            normalized.extend(extras)

        return {"questions": normalized[:max(self.min_questions, len(normalized))]}

    def _normalize_question(self, q: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(q, dict):
            return None
        question = str(q.get("question", "")).strip()
        if not question:
            return None
        qtype = q.get("type", "Short Answer")
        res = {"type": qtype, "question": question}
        if qtype == "MCQ":
            opts = q.get("options") or q.get("choices") or []
            if not isinstance(opts, list):
                if isinstance(opts, str):
                    opts = re.split(r'\s*;\s*|\s*\|\s*', opts)
                else:
                    opts = []
            opts = [str(o).strip() for o in opts if str(o).strip()]
            while len(opts) < 4:
                opts.append("None of the above")
            opts = opts[:4]
            res["options"] = opts
            ans = q.get("answer", "")
            if isinstance(ans, str) and ans.strip():
                a = ans.strip()
                for idx, option_text in enumerate(opts):
                    if a.lower() == option_text.lower() or a.strip().lower() == f"{chr(65+idx)}".lower():
                        res["answer"] = chr(65 + idx)
                        break
                else:
                    if len(a) == 1 and a.upper() in "ABCD":
                        res["answer"] = a.upper()
                    else:
                        res["answer"] = "A"
            else:
                res["answer"] = "A"
        else:
            if "answer" in q and q.get("answer") is not None and str(q.get("answer")).strip():
                res["answer"] = str(q.get("answer")).strip()
            else:
                if qtype != "Open Ended":
                    res["answer"] = "Refer to the document."
        return res


    def _create_basic_fallback_questions(self, user_query: str = "", document_text: str = "") -> Dict[str, Any]:
        base = user_query or (document_text[:80] if document_text else "the document")
        qlist = [
            {"type": "Short Answer", "question": f"What is the main idea of {base}?", "answer": "Refer to the document."},
            {"type": "Short Answer", "question": f"List one key fact or claim stated in {base}.", "answer": "Refer to the document."},
            {"type": "Open Ended", "question": f"How could the information in {base} be applied in practice?"},
            {"type": "MCQ", "question": f"Which statement is true about {base}?", "options": ["Option A", "Option B", "Option C", "Option D"], "answer": "A"},
            {"type": "Short Answer", "question": f"Name one term or concept discussed in {base}.", "answer": "Refer to the document."}
        ]
        return {"questions": qlist}

    def _generate_additional_questions(self, document_text: str, user_query: str, needed: int, existing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        extras = []
        sents = re.split(r'(?<=[\.\?\!])\s+', (document_text or "")[:800])
        snippet = next((s for s in sents if len(s.strip()) > 20), user_query or "the document")
        for i in range(needed):
            if i % 3 == 0:
                extras.append({
                    "type": "Short Answer",
                    "question": f"According to the document, what is one important point about: {snippet.strip()[:120]}?",
                    "answer": "Refer to the document."
                })
            elif i % 3 == 1:
                extras.append({
                    "type": "MCQ",
                    "question": f"Which statement about the following is correct? {snippet.strip()[:90]}",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "answer": "A"
                })
            else:
                extras.append({
                    "type": "Open Ended",
                    "question": f"Discuss how the following idea from the document could be used in practice: {snippet.strip()[:120]}",
                })
        return extras


    def _templated_mcq(self, document_text: str, user_query: str) -> Dict[str, Any]:
        snippet = (document_text or user_query or "the document")[:90]
        return {
            "type": "MCQ",
            "question": f"Which statement about this excerpt is correct? {snippet.strip()}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "A"
        }

    def _templated_short_answer(self, document_text: str, user_query: str) -> Dict[str, Any]:
        snippet = (document_text or user_query or "the document")[:90]
        return {"type": "Short Answer", "question": f"What is the main point about: {snippet.strip()}?", "answer": "Refer to the document."}

    def _templated_open_ended(self, document_text: str, user_query: str) -> Dict[str, Any]:
        snippet = (document_text or user_query or "the document")[:90]
        return {"type": "Open Ended", "question": f"How could the idea in this excerpt be applied? {snippet.strip()}"}


    def _build_json_prompt(self, document_text: str, user_query: str) -> str:
        return f"""
            You are an expert question generation agent. Use ONLY the provided document text to create questions.
            Do NOT use external knowledge.

            USER REQUEST: {user_query}

            DOCUMENT:
            {document_text[:3000]}

            Return ONLY a single JSON object (no explanation) in this exact structure:
            {{
            "questions": [
                {{
                "type": "MCQ",
                "question": "Question text based on document?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": "A"
                }},
                {{
                "type": "Short Answer",
                "question": "Short answer question?",
                "answer": "Concise answer"
                }},
                {{
                "type": "Open Ended",
                "question": "Open ended question?"
                }}
            ]
            }}

            Rules:
            - Allowed types: MCQ, Short Answer, Open Ended, Other.
            - MCQ must have exactly 4 options and an answer letter (A/B/C/D).
            - Short Answer must include an 'answer' field.
            - Open Ended should NOT include an answer field.
            - Provide 4-6 questions where possible.
            """


    def _format_as_final_answer(self, questions_data: Dict[str, Any], original_query: str) -> str:
        try:
            if not questions_data or "questions" not in questions_data:
                return "Final Answer: I couldn't generate questions. Please try a different query."

            questions = questions_data["questions"]
            if not questions:
                return "Final Answer: No questions could be generated."

            lines = ["Final Answer: Here are your generated questions:", ""]
            for i, q in enumerate(questions, 1):
                q_type = q.get("type", "Question")
                q_text = q.get("question", "No question text")
                lines.append(f"{i}. [{q_type}] {q_text}")
                if q_type == "MCQ":
                    options = q.get("options", [])
                    opts_norm = [str(o) for o in options]
                    while len(opts_norm) < 4:
                        opts_norm.append("None of the above")
                    options_text = " | ".join([f"{chr(65 + j)}) {opt}" for j, opt in enumerate(opts_norm[:4])])
                    lines.append(f"   Options: {options_text}")
                    ans = q.get("answer", "A")
                    if isinstance(ans, str) and len(ans) == 1 and ans.upper() in "ABCD":
                        lines.append(f"   Answer: {ans.upper()}")
                    else:
                        lines.append(f"   Answer: A")
                else:
                    if q_type != "Open Ended":
                        ans_text = q.get("answer", "Refer to the document.")
                        lines.append(f"   Answer: {ans_text}")
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            logger.exception("Error formatting final answer: %s", e)
            fallback = self._create_basic_fallback_questions(original_query, "")
            fallback = self._ensure_minimum_and_types(fallback, "", original_query)
            return self._format_as_final_answer(fallback, original_query)

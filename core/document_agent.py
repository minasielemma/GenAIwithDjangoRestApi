import json
import os
import uuid
import logging
from django.conf import settings
from langchain.agents import initialize_agent, Tool
from langchain_community.llms import Ollama
from .rag_service import LocalPDFVectorizer
from .mongo_conversational_memory import MongoConversationMemory
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

class DocumentAgent:

    def __init__(self, user_id: str, session_id: str = "default", doc_id: int = None):
        logger.info("Initializing DocumentAgent with user_id: %s, session_id: %s, doc_id: %s", user_id, session_id, doc_id)
        self.user_id = user_id
        self.session_id = session_id
        self.doc_id = doc_id
        self.llm = Ollama(model="artifish/llama3.2-uncensored",    
                          system="You are an AI assistant. Always answer in this format:\n\n"
                                "Question: <the user query>\n"
                                "Thought: <your reasoning>\n"
                                "Action: <tool name or Final Answer>\n"
                                "Action Input: <input for the tool>\n"
                                "Final Answer: <your final answer to the user>")
        self.memory = MongoConversationMemory(
            session_id=session_id,
            user_id=user_id
        )

        self.retriever = LocalPDFVectorizer(doc_id)

        retriever_tool = Tool(
            name="Document Retriever",
            func=self.retriever.query,
            description="Fetch relevant information from uploaded document"
        )
        summarizer_tool = Tool(
            name="Summarizer",
            func=self._summarize,
            description="Summarize the full document or a specific query. Use 'full' for entire doc."
        )
        analyzer_tool = Tool(
            name="Data Analyzer",
            func=self._analyze_data,
            description="Extract and analyze numerical data from the document (e.g., stats like mean, sum)."
        )
        question_tool = Tool(
            name="Question Generator",
            func=self._generate_questions,
            description=(
                "Generate different types of questions (MCQ, true/false, short answer, or open-ended) "
                "from the document or specific query text."
            )
        )
        graph_tool = Tool(
            name="Graph Maker",
            func=self._make_graph,
            description="Create a simple graph (bar/line) from extracted data. Specify type: 'bar' or 'line'."
        )
        tools = [retriever_tool, summarizer_tool, analyzer_tool, graph_tool, question_tool]
        self.agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent="zero-shot-react-description",
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method="generate"
        )
        logger.info("DocumentAgent initialized successfully.")

    def _generate_questions(self, query: str) -> dict:
        logger.info("Generating questions for query: %s", query)
        try:
            if query.lower() == "full":
                chunks = self.retriever.get_all_chunks()
                text = "\n".join([doc.page_content for doc in chunks])
            else:
                text = self.retriever.query(query)

            question_prompt = f"""
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

            llm_response = self.llm(question_prompt).strip()
            questions = self._safe_json_parse(llm_response, context_hint="Question generation")
            if not questions:
                return {
                    "action": "Final Answer",
                    "action_input": "Could not generate questions. Try refining the query."
                }

            logger.info("Questions generated successfully.")
            return {
                "action": "Final Answer",
                "action_input": questions
            }

        except Exception as e:
            logger.error("Error in _generate_questions: %s", str(e))
            return {
                "action": "Final Answer",
                "action_input": f"Error generating questions: {str(e)}"
            }
        
    def _retriever_tool(self, query: str) -> dict:
        logger.info("Retrieving document content for query: %s", query)
        try:
            text = self.retriever.query(query_text=query, k=3)
            logger.info("Retrieved text successfully.")
            return {
                "action": "Final Answer",
                "action_input": text
            }
        except Exception as e:
            logger.error("Error in _retriever_tool: %s", str(e))
            return {
                "action": "Final Answer",
                "action_input": f"Error retrieving document context: {str(e)}"
            }

    def clear_memory(self):
        logger.info("Clearing memory for session: %s", self.session_id)
        self.memory.clear()

    def _summarize(self, query: str) -> dict:
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
            return {
                "action": "Final Answer",
                "action_input": summary
            }
        except Exception as e:
            logger.error("Error in _summarize: %s", str(e))
            return {
                "action": "Final Answer",
                "action_input": f"Error summarizing: {str(e)}"
            }
        
    def _safe_json_parse(self, llm_output: str, context_hint: str = "") -> dict:
        logger.info("Attempting safe JSON parse. Context: %s", context_hint)
        max_retries = 1
        current_output = llm_output

        for attempt in range(max_retries):
            try:
                data = json.loads(current_output)
                if "labels" in data and "values" in data:
                    labels, values = data["labels"], data["values"]
                    if isinstance(labels, list) and isinstance(values, list) and len(labels) != len(values):
                        raise ValueError("Arrays 'labels' and 'values' must have the same length")
                logger.info("JSON parsed successfully on attempt %d.", attempt + 1)
                return data
            except Exception as e:
                logger.warning("JSON parse error on attempt %d: %s", attempt + 1, str(e))
                repair_prompt = f"""
                The following JSON was invalid or inconsistent.
                Error: {str(e)}
                Context: {context_hint}
                Fix it and return valid JSON only. Do not add explanations.

                JSON to fix:
                {current_output}
                """
                current_output = self.llm(repair_prompt).strip()
        logger.error("Failed to safely parse JSON after %d attempts.", max_retries)
        return {}

    def _analyze_data(self, query: str) -> dict:
        if not query:
            query = "full document"
        logger.info("Analyzing data with query: %s", query)
        try:
            text = self.retriever.query(query) if query else self.retriever.get_all_chunks()[0].page_content            
            analysis_prompt = f"""
            You are a data analysis assistant.  
            From the following text, identify numerical data and return both extracted data and a statistical analysis.  

            Instructions:
            1. Always return JSON only, never explanations.  
            2. Use this schema:
            {{
            "labels": ["Label1", "Label2", ...],
            "values": [Number1, Number2, ...],
            "analysis": {{
                "mean": <average>,
                "sum": <total>,
                "min": <minimum>,
                "max": <maximum>,
                "count": <number of values>
            }},
            "suggested_graph": "<bar|line|pie|histogram>"
            }}
            3. "labels" must be strings (e.g., years, names, categories).  
            4. "values" must be numbers (int or float).  
            5. Choose "suggested_graph" type based on data:
            - "line": sequential data (years, timeline, ordered categories)  
            - "bar": categorical comparison  
            - "pie": small sets of categories adding to a whole  
            - "histogram": raw numeric distributions  
            6. If no data is found, return: {{}}

            Text to analyze:
            {text}
            """
            llm_response = self.llm(analysis_prompt).strip()
            logger.info("Analysis prompt response received.")
            data = self._safe_json_parse(llm_response, context_hint="Ensure valid JSON with equal-length labels and values.")

            if not data or "labels" not in data or "values" not in data:
                logger.info("No numerical data found in the document.")
                return {
                    "action": "Final Answer",
                    "action_input": "No numerical data found in the document."
                }

            df = pd.DataFrame({"Label": data["labels"], "Value": data["values"]})
            df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
            df = df.dropna()
            if df.empty:
                logger.info("No valid numerical values found after cleaning DataFrame.")
                return {
                    "action": "Final Answer",
                    "action_input": "No valid numerical values found."
                }
            graph_type = data.get("suggested_graph", "bar")
            fig, ax = plt.subplots(figsize=(8, 5))
            if graph_type == "line":
                ax.plot(df["Label"], df["Value"], marker="o", color="#36A2EB")
            elif graph_type == "pie":
                ax.pie(df["Value"], labels=df["Label"], autopct="%1.1f%%", startangle=90)
            elif graph_type == "histogram":
                ax.hist(df["Value"], bins=10, color="#36A2EB", edgecolor="black")
            else: 
                ax.bar(df["Label"], df["Value"], color="#36A2EB")
            ax.set_title(f"{graph_type.capitalize()} graph")
            if graph_type != "pie":
                ax.set_xlabel("Category")
                ax.set_ylabel("Value")
                plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            filename = f"analysis_graph_{uuid.uuid4().hex}.png"
            file_path = os.path.join(settings.MEDIA_ROOT, filename)
            plt.savefig(file_path, format="png", dpi=100)
            plt.close(fig)
            file_url = os.path.join(settings.MEDIA_URL, filename)
            logger.info("Data analysis complete, graph saved as %s", filename)
            return {
                "action": "Final Answer",
                "action_input": {
                    "description": f"Extracted {len(df)} data points. Suggested graph: {graph_type}.",
                    "analysis": data.get("analysis", {}),
                    "image_url": file_url
                }
            }
        except Exception as e:
            logger.error("Error in _analyze_data: %s", str(e))
            return {
                "action": "Final Answer",
                "action_input": f"Error analyzing data: {str(e)}"
            }

    def _make_graph(self, query: str) -> str:
        if not query:
            query = "full document"
        logger.info("Making graph with query: %s", query)
        try:
            parts = query.lower().strip().split(maxsplit=1)
            graph_type = parts[0] if parts and parts[0] in ["bar", "line"] else "bar"
            data_query = parts[1] if len(parts) > 1 else "numerical data"
            text = self.retriever.query(data_query, k=5)
            extraction_prompt = f"""
            You are a data extraction and analysis assistant.  
            From the following text, identify and extract any numerical data that can be organized as pairs of categories (labels) and numbers (values).  

            Instructions:
            1. Always return your answer in strict JSON format only.  
            2. Use the format:  
            {{
                "labels": ["Label1", "Label2", ...],
                "values": [Number1, Number2, ...],
                "analysis": {{
                    "mean": <average of values>,
                    "sum": <sum of values>,
                    "min": <minimum value>,
                    "max": <maximum value>,
                    "count": <number of data points>
                }}
            }}  
            3. Labels must be strings (e.g., years, names, categories).  
            4. Values must be numbers (integers or floats).  
            5. If no numerical data exists, return: {{}}

            Text to analyze:
            {text}
            """
            llm_response = self.llm(extraction_prompt).strip()
            logger.info("Extraction prompt response received for graph creation.")
            data = self._safe_json_parse(llm_response, context_hint="Ensure valid JSON with equal-length labels and values.")

            if not data or "labels" not in data or "values" not in data:
                logger.info("No numerical data found for graph creation.")
                return json.dumps({
                    "action": "Final Answer",
                    "action_input": "No numerical data found."
                })
            df = pd.DataFrame({"Label": data["labels"], "Value": data["values"]})
            df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
            df = df.dropna()
            if df.empty:
                logger.info("No valid numerical values found in DataFrame for graph.")
                return json.dumps({
                    "action": "Final Answer",
                    "action_input": "No valid numerical values found."
                })
            fig, ax = plt.subplots(figsize=(8, 5))
            if graph_type == "line":
                ax.plot(df["Label"], df["Value"], marker="o", color="#36A2EB")
            else:
                ax.bar(df["Label"], df["Value"], color="#36A2EB")
            ax.set_title(f"{graph_type.capitalize()} graph of {data_query}")
            ax.set_xlabel("Category")
            ax.set_ylabel("Value")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            filename = f"graph_{uuid.uuid4().hex}.png"
            file_path = os.path.join(settings.MEDIA_ROOT, filename)
            plt.savefig(file_path, format="png", dpi=100)
            plt.close(fig)
            file_url = os.path.join(settings.MEDIA_URL, filename)
            description = (
                f"Generated a {graph_type} graph with {len(df)} points. "
                f"X-axis: {', '.join(df['Label'].tolist()[:5])}{'...' if len(df) > 5 else ''}. "
                f"Y-axis from {df['Value'].min():.2f} to {df['Value'].max():.2f}."
            )
            logger.info("Graph created successfully: %s", filename)
            return json.dumps({
                "action": "Final Answer",
                "action_input": {
                    "description": description,
                    "image_url": file_url 
                }
            })
        except Exception as e:
            logger.error("Error in _make_graph: %s", str(e))
            return json.dumps({
                "action": "Final Answer",
                "action_input": f"Graph creation error: {str(e)}"
            })

    def ask(self, query: str):
        logger.info("Received ask query: %s", query)
        result = self.agent.invoke({"input": query})
        logger.info("Agent response: %s", result)
        return {
            "answer": result,
            "session_id": self.session_id,
            "doc_id": self.doc_id,
        }
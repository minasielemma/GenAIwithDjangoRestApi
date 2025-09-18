from langchain.agents import initialize_agent, Tool
from langchain_community.llms import Ollama
from .rag_service import LocalPDFVectorizer
from .mongo_conversational_memory import MongoConversationMemory
import matplotlib.pyplot as plt
import io
import base64

class DocumentAgent:

    def __init__(self, user_id: str, session_id: str = "default", doc_id: int = None):
        self.user_id = user_id
        self.session_id = session_id
        self.doc_id = doc_id
        self.llm = Ollama(model="artifish/llama3.2-uncensored")
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
        
        graph_tool = Tool(
            name="Graph Maker",
            func=self._make_graph,
            description="Create a simple graph (bar/line) from extracted data. Specify type: 'bar' or 'line'."
        )
        tools = [retriever_tool, summarizer_tool, analyzer_tool, graph_tool]
        self.agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent="zero-shot-react-description",
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
    def _retriever_tool(self, query: str) -> str:
        try:
            return self.retriever.query(query_text=query, k=3)
        except Exception as e:
            return f"Error retrieving document context: {str(e)}"


    def clear_memory(self):
        self.memory.clear()

    def _summarize(self, query: str) -> str:
        try:
            if query.lower() == "full":
                chunks = self.retriever.get_all_chunks()
                text = "\n".join([doc.page_content for doc in chunks])
            else:
                text = self.retriever.query(query)
            prompt = f"Summarize the following document content concisely:\n\n{text}"
            return self.llm(prompt)
        except Exception as e:
            return f"Error summarizing: {str(e)}"

    def _analyze_data(self, query: str) -> str:
        try:
            text = self.retriever.query(query) if query else self.retriever.get_all_chunks()[0].page_content
            df = self.retriever.extract_data(text)
            if df.empty:
                return "No numerical data found in the document."
            stats = {
                'mean': df['Value'].mean(),
                'sum': df['Value'].sum(),
                'count': len(df),
                'data_preview': df.head().to_string()
            }
            return f"Extracted Data:\n{stats['data_preview']}\n\nAnalysis:\n{stats}"
        except Exception as e:
            return f"Error analyzing data: {str(e)}"

    def _make_graph(self, query: str) -> str:
        try:
            parts = query.lower().split()
            graph_type = parts[0] if parts else 'bar'
            data_query = ' '.join(parts[1:]) or "numerical data"
            
            text = self.retriever.query(data_query)
            df = self.retriever.extract_data(text)
            if df.empty:
                return "No data available for graphing."
            
            fig, ax = plt.subplots()
            if graph_type == 'line':
                ax.plot(df['Label'], df['Value'])
            else:  
                ax.bar(df['Label'], df['Value'])
            ax.set_xlabel('Labels')
            ax.set_ylabel('Values')
            ax.set_title(f"{graph_type.capitalize()} Graph from Document")
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            
            description = f"Generated a {graph_type} graph with {len(df)} data points. X-axis: {', '.join(df['Label'].tolist()[:5])}... Y-axis values range from {df['Value'].min():.2f} to {df['Value'].max():.2f}."
            return f"{description}\n\nBase64 Image (for display): data:image/png;base64,{img_base64}"
        except Exception as e:
            return f"Error creating graph: {str(e)}"

    def ask(self, query: str):
        response = self.agent.run(query)
        self.memory.save_context(
            {"input": query},
            {"output": response}
        )
        return {
            "answer": response,
            "session_id": self.session_id,
            "doc_id": self.doc_id
        }

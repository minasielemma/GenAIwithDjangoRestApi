from .base_tool import BaseTool
import logging
import pandas as pd
import matplotlib.pyplot as plt
import uuid
import os
from ..config import config

logger = logging.getLogger(__name__)

class AnalysisTool(BaseTool):
    
    def __init__(self, retriever, llm):
        super().__init__(
            name="Data Analyzer",
            description="Extract and analyze numerical data from the document (e.g., stats like mean, sum)."
        )
        self.retriever = retriever
        self.llm = llm
    
    def execute(self, query: str, **kwargs) -> dict:
        if not query:
            query = "full document"
        logger.info("Analyzing data with query: %s", query)
        
        try:
            text = self.retriever.query(query) if query else self.retriever.get_all_chunks()[0].page_content            
            analysis_prompt = self._build_analysis_prompt()
            llm_response = self.llm(analysis_prompt.format(text=text)).strip()
            
            data = self._safe_json_parse(llm_response, context_hint="Ensure valid JSON with equal-length labels and values.")
            
            if not data or "labels" not in data or "values" not in data:
                logger.info("No numerical data found in the document.")
                return {
                    "action": "Final Answer",
                    "action_input": "No numerical data found in the document."
                }

            return self._process_analysis_data(data)
            
        except Exception as e:
            logger.error("Error in AnalysisTool: %s", str(e))
            return {
                "action": "Final Answer",
                "action_input": f"Error analyzing data: {str(e)}"
            }
    
    def _build_analysis_prompt(self) -> str:
        return """
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
    
    def _process_analysis_data(self, data: dict) -> dict:
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
        file_url = self._create_visualization(df, graph_type)
        
        logger.info("Data analysis complete, graph saved as %s", file_url)
        return {
            "action": "Final Answer",
            "action_input": {
                "description": f"Extracted {len(df)} data points. Suggested graph: {graph_type}.",
                "analysis": data.get("analysis", {}),
                "image_url": file_url
            }
        }
    
    def _create_visualization(self, df: pd.DataFrame, graph_type: str) -> str:
        fig, ax = plt.subplots(figsize=config.GRAPH_FIGSIZE)
        
        if graph_type == "line":
            ax.plot(df["Label"], df["Value"], marker="o", color=config.GRAPH_COLOR)
        elif graph_type == "pie":
            ax.pie(df["Value"], labels=df["Label"], autopct="%1.1f%%", startangle=90)
        elif graph_type == "histogram":
            ax.hist(df["Value"], bins=10, color=config.GRAPH_COLOR, edgecolor="black")
        else: 
            ax.bar(df["Label"], df["Value"], color=config.GRAPH_COLOR)
        
        ax.set_title(f"{graph_type.capitalize()} graph")
        if graph_type != "pie":
            ax.set_xlabel("Category")
            ax.set_ylabel("Value")
            plt.xticks(rotation=45, ha="right")
        
        plt.tight_layout()
        filename = f"analysis_graph_{uuid.uuid4().hex}.png"
        file_path = os.path.join(config.MEDIA_ROOT, filename)
        plt.savefig(file_path, format="png", dpi=config.GRAPH_DPI)
        plt.close(fig)
        
        return os.path.join(config.MEDIA_URL, filename)
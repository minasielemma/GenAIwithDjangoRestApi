from .base_tool import BaseTool
import logging
import pandas as pd
import matplotlib.pyplot as plt
import uuid
import os
import json
from ..config import config

logger = logging.getLogger(__name__)

class GraphTool(BaseTool):
    
    def __init__(self, retriever, llm):
        super().__init__(
            name="Graph Maker",
            description="Create a simple graph (bar/line) from extracted data. Specify type: 'bar' or 'line'."
        )
        self.retriever = retriever
        self.llm = llm
    
    def execute(self, query: str, **kwargs) -> str:
        if not query:
            query = "full document"
        logger.info("Making graph with query: %s", query)
        
        try:
            parts = query.lower().strip().split(maxsplit=1)
            graph_type = parts[0] if parts and parts[0] in ["bar", "line"] else "bar"
            data_query = parts[1] if len(parts) > 1 else "numerical data"
            
            text = self.retriever.query(data_query, k=5)
            extraction_prompt = self._build_extraction_prompt()
            llm_response = self.llm(extraction_prompt.format(text=text)).strip()
            
            data = self._safe_json_parse(llm_response, context_hint="Ensure valid JSON with equal-length labels and values.")
            
            if not data or "labels" not in data or "values" not in data:
                logger.info("No numerical data found for graph creation.")
                return json.dumps({
                    "action": "Final Answer",
                    "action_input": "No numerical data found."
                })
            
            return self._create_graph(data, graph_type, data_query)
            
        except Exception as e:
            logger.error("Error in GraphTool: %s", str(e))
            return json.dumps({
                "action": "Final Answer",
                "action_input": f"Graph creation error: {str(e)}"
            })
    
    def _build_extraction_prompt(self) -> str:
        return """
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
    
    def _create_graph(self, data: dict, graph_type: str, data_query: str) -> str:
        df = pd.DataFrame({"Label": data["labels"], "Value": data["values"]})
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
        df = df.dropna()
        
        if df.empty:
            logger.info("No valid numerical values found in DataFrame for graph.")
            return json.dumps({
                "action": "Final Answer",
                "action_input": "No valid numerical values found."
            })
        
        fig, ax = plt.subplots(figsize=config.GRAPH_FIGSIZE)
        
        if graph_type == "line":
            ax.plot(df["Label"], df["Value"], marker="o", color=config.GRAPH_COLOR)
        else:
            ax.bar(df["Label"], df["Value"], color=config.GRAPH_COLOR)
        
        ax.set_title(f"{graph_type.capitalize()} graph of {data_query}")
        ax.set_xlabel("Category")
        ax.set_ylabel("Value")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        
        filename = f"graph_{uuid.uuid4().hex}.png"
        file_path = os.path.join(config.MEDIA_ROOT, filename)
        plt.savefig(file_path, format="png", dpi=config.GRAPH_DPI)
        plt.close(fig)
        
        file_url = os.path.join(config.MEDIA_URL, filename)
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
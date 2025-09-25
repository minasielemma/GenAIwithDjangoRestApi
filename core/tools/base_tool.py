from abc import ABC, abstractmethod
import logging
import json
from typing import Any

logger = logging.getLogger(__name__)

class BaseTool(ABC):    
    def __init__(self, name, description):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, query: str, **kwargs) -> Any:
        pass
    
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
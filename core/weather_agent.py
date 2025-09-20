import json
import logging
import requests
from langchain.agents import initialize_agent, Tool
from langchain_community.llms import Ollama

logger = logging.getLogger(__name__)


class WeatherAgent:
    def __init__(self, user_id: str, session_id: str = "default"):
        logger.info("Initializing WeatherAgent for user: %s, session: %s", user_id, session_id)
        self.user_id = user_id
        self.session_id = session_id
        self.llm = Ollama(model="artifish/llama3.2-uncensored")
        weather_tool = Tool(
            name="Weather Retriever",
            func=self._get_weather,
            description="Get the current weather for a given city. Input should be the city name."
        )
        analyzer_tool = Tool(
            name="Weather Analyzer",
            func=self._analyze_weather,
            description="Analyze the weather data and suggest suitable activities."
        )
        tools = [weather_tool, analyzer_tool]

        self.agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent="zero-shot-react-description",
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method="generate"
        )
        logger.info("WeatherAgent initialized successfully.")

    def _get_weather(self, city: str):
        if not city:
            return {
                "action": "Final Answer",
                "action_input": "City name is required to fetch weather."
            }
        
        try:
            url = f"https://wttr.in/{city.lower()}?format=j1"
            resp = requests.get(url, timeout=10).json()
            current = resp["current_condition"][0]
            desc = current["weatherDesc"][0]["value"]
            temp = current["temp_C"]
            humidity = current["humidity"]
            logger.info("Weather fetched for %s: %s, %s°C, %s%% humidity", city, desc, temp, humidity)
            return {
                "action": "Final Answer",
                "action_input": f"City: {city}, Weather: {desc}, Temp: {temp}°C, Humidity: {humidity}%"
            }
        except Exception as e:
            logger.error("Error fetching weather for %s: %s", city, str(e))
            return {
                "action": "Final Answer",
                "action_input": f"Error fetching weather data: {str(e)}"
            }

    def _analyze_weather(self, weather_text: str):
        prompt = f"""
        You are a weather assistant. Analyze the following weather data:

        {weather_text}

        Provide:
        - A short summary
        - Recommended outdoor/indoor activities
        - Health considerations (hydration, sunscreen, clothing, etc.)

        Return JSON with keys: summary, activities, health_tips.
        """
        try:
            result = self.llm(prompt).strip()
            data = self._safe_json_parse(result, context_hint="weather analysis JSON")
            return {
                "action": "Final Answer",
                "action_input": data
            }
        except Exception as e:
            return {
                "action": "Final Answer",
                "action_input": f"Error analyzing weather data: {str(e)}"
            }

    def _safe_json_parse(self, llm_output: str, context_hint: str = "") -> dict:
        try:
            return {
                "action": "Final Answer",
                "action_input": json.loads(llm_output)
            }
        except Exception:
            repair_prompt = f"""
            The following output was invalid JSON.
            Context: {context_hint}
            Fix it and return valid JSON only.

            Output to fix:
            {llm_output}
            """
            fixed = self.llm(repair_prompt).strip()
            try:
                return json.loads(fixed)
            except Exception:
                return {
                    "action": "Final Answer",
                    "action_input": f"Failed to parse JSON after repair attempt. Original output: {llm_output}"
                }

    def run(self, query: str):
        """Run the agent with a user query"""
        return self.agent.run(query)

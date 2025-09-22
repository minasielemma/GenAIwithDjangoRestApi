import logging
import requests
import json
from typing import Dict, Any, Union, List

from langchain_community.llms import Ollama
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage

from core.mongo_conversational_memory import MongoConversationMemory

WEATHER_API_URL_FORMAT = "https://wttr.in/{city}?format=j1"
WEATHER_API_TIMEOUT = 10  

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeatherAgent:
    def __init__(self, user_id: str, session_id: str = "default", llm_model: str = "artifish/llama3.2-uncensored"):
        logger.info(f"Initializing WeatherAgent for user: {user_id}, session: {session_id} with model: {llm_model}")
        self.user_id = user_id
        self.session_id = session_id
        self.llm = Ollama(model=llm_model, temperature=0.2) 
        
        self.memory =  MongoConversationMemory(
            session_id=session_id,
            user_id=user_id
        )

        tools = self._setup_tools()

        self.agent_executor = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent=AgentType.OPENAI_FUNCTIONS, 
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=7, 
            early_stopping_method="generate",
            memory=self.memory, 
            agent_kwargs={
                "system_message": SystemMessage(
                    content="You are a helpful and friendly weather assistant. "
                            "Use the Weather Retriever tool to get weather, then the Weather Analyzer "
                            "to provide a summary, activity suggestions, and health tips. "
                            "Always aim to provide a comprehensive and user-friendly response."
                )
            }
        )
        logger.info("WeatherAgent initialized successfully.")

    def _setup_tools(self) -> List[Tool]:
        weather_retriever_tool = Tool(
            name="WeatherRetriever", 
            func=self._get_weather,
            description="Useful for getting the current weather for a specified city. "
                        "Input should be the city name (e.g., 'London', 'New York')."
        )
        weather_analyzer_tool = Tool(
            name="WeatherAnalyzer", 
            func=self._analyze_weather_data,
            description="Useful for analyzing detailed weather information and generating "
                        "a summary, suggested activities, and health tips. "
                        "Input should be a string containing detailed weather data (e.g., 'City: London, Weather: Clear, Temp: 15°C, Humidity: 70%')."
        )
        return [weather_retriever_tool, weather_analyzer_tool]

    def _get_weather(self, city: str) -> str:
        if not city:
            logger.warning("WeatherRetriever received an empty city name.")
            return "Error: City name is required to fetch weather."
        url = WEATHER_API_URL_FORMAT.format(city=city.lower())
        resp = requests.get(url, timeout=WEATHER_API_TIMEOUT)
        try:
            
            logger.info(f"Attempting to fetch weather from: {url}")
            
            resp.raise_for_status() 
            data = resp.json()
            logger.info(f"Successfully fetched weather data for {city}. with {data} characters.")
            current = data.get("current_condition", [{}])[0]
            if not current:
                return f"Could not find current weather conditions for {city}. Please check the city name."

            desc = current.get("weatherDesc", [{}])[0].get("value", "N/A")
            temp_c = current.get("temp_C", "N/A")
            feels_like_c = current.get("FeelsLikeC", "N/A")
            humidity = current.get("humidity", "N/A")
            wind_speed_kmph = current.get("windspeedKmph", "N/A")
            pressure_mb = current.get("pressure", "N/A")
            uv_index = current.get("uvIndex", "N/A")

            weather_report = (
                f"City: {city.title()}, " 
                f"Conditions: {desc}, "
                f"Temperature: {temp_c}°C (Feels like {feels_like_c}°C), "
                f"Humidity: {humidity}%, "
                f"Wind: {wind_speed_kmph} Kmph, "
                f"Pressure: {pressure_mb} mb, "
                f"UV Index: {uv_index}. "
                f"Full Data: {json.dumps(current)}" 
            )
            logger.info(f"Weather fetched for {city}: {weather_report}")
            return weather_report
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching weather for {city}: {e.response.status_code} - {e.response.text}")
            return f"Error fetching weather data: HTTP Error {e.response.status_code} for {city}. Details: {e.response.text[:100]}..."
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error fetching weather for {city}: {e}")
            return f"Error: Could not connect to weather service for {city}. Please check your internet connection."
        except requests.exceptions.Timeout:
            logger.error(f"Timeout error fetching weather for {city}.")
            return f"Error: Weather service timed out for {city}. Please try again later."
        except json.JSONDecodeError:
            logger.error(f"JSON decoding error for weather data for {city}. Response: {resp.text}")
            return f"Error: Invalid data received from weather service for {city}."
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching weather for {city}: {e}", exc_info=True)
            return f"An unexpected error occurred: {str(e)}. Please try again."

    def _analyze_weather_data(self, weather_text: str) -> Union[Dict[str, Any], str]:
        if not weather_text:
            return "Error: No weather data provided for analysis."

        prompt = f"""
        You are a highly skilled weather analysis AI. Your task is to interpret the provided weather
        information and offer a comprehensive, user-friendly analysis.

        Here is the weather data to analyze:
        {weather_text}

        Based on this data, provide the following in a STRICTLY VALID JSON object:
        - "summary": A concise and engaging overview of the current weather conditions.
        - "activities": A list of suggested outdoor and indoor activities, appropriate for the conditions.
          Consider temperature, precipitation, wind, and UV index.
        - "health_tips": Practical advice for staying safe and comfortable. This could include
          clothing recommendations, hydration advice, sun protection, or warnings for
          specific conditions (e.g., wind chill, heat index).

        Example JSON structure:
        {{
            "summary": "...",
            "activities": ["...", "..."],
            "health_tips": ["...", "..."]
        }}

        Ensure the output is pure JSON, without any preceding or trailing text.
        """
        try:
            logger.info("Sending weather data to LLM for analysis.")
            llm_raw_output = self.llm.invoke(prompt).strip() 
            parsed_data = self._safe_json_parse(llm_raw_output, context_hint="weather analysis JSON")
            
            if isinstance(parsed_data, dict):
                logger.info("Weather analysis successful.")
                return parsed_data
            else:
                logger.error(f"Failed to parse LLM analysis: {parsed_data}")
                return parsed_data
        except Exception as e:
            logger.error(f"Error during weather analysis by LLM: {e}", exc_info=True)
            return f"An error occurred during weather analysis: {str(e)}"

    def _safe_json_parse(self, llm_output: str, context_hint: str = "") -> Union[Dict[str, Any], str]:
        try:
            return json.loads(llm_output)
        except json.JSONDecodeError:
            logger.warning(f"Initial JSON parsing failed for {context_hint}. Attempting repair.")
            repair_prompt = f"""
            The following text was intended to be a STRICTLY VALID JSON object but failed to parse.
            Context for generation: {context_hint}.
            Please correct the JSON and return only the valid JSON object.
            Ensure it includes the keys: "summary", "activities" (as a list), and "health_tips" (as a list).

            Invalid output to fix:
            ```json
            {llm_output}
            ```
            Return ONLY the corrected JSON object.
            """
            try:
                fixed_json_str = self.llm.invoke(repair_prompt).strip()
                logger.info(f"Attempted JSON repair. Fixed output: {fixed_json_str}")
                return json.loads(fixed_json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON even after repair attempt for {context_hint}. Error: {e}")
                return f"Failed to parse JSON after repair attempt. Original output: {llm_output[:200]}..."
            except Exception as e:
                logger.error(f"An unexpected error occurred during JSON repair for {context_hint}: {e}", exc_info=True)
                return f"An unexpected error occurred during JSON repair: {str(e)}"
        except Exception as e:
            logger.error(f"An unexpected error occurred during safe JSON parse for {context_hint}: {e}", exc_info=True)
            return f"An unexpected error occurred during JSON parsing: {str(e)}"

    def run(self, query: str) -> Any:
        """Run the agent with a user query"""
        logger.info(f"Running agent for user '{self.user_id}' with query: '{query}'")
        try:
            response = self.agent_executor.invoke({"input": query})
            final_output = response.get("output", "No response generated.")
            logger.info(f"Agent finished. Final response: {final_output}")
            return final_output
        except Exception as e:
            logger.error(f"Error running agent for query '{query}': {e}", exc_info=True)
            return f"I encountered an error while processing your request: {str(e)}. Please try again."
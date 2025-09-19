# from fastapi import FastAPI
# from mcp.server.fastmcp import FastMCP
# from mcp.server
# from .tools import TOOLS
# import os
# from dotenv import load_dotenv

# load_dotenv()

# app = FastAPI(title="MCP Ollama Server")

# # Initialize Ollama LLM (your local model)
# llm = Ollama(
#     model="artifish/llama3.2-uncensored",
#     base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# )

# # Create FastMCP server
# mcp = FastMCP("Ollama MCP Server", llm=llm)

# # Register tools
# for tool in TOOLS:
#     mcp.tool(tool)

# # Add MCP routes to FastAPI app
# from mcp.server.fastapi import add_mcp_routes
# add_mcp_routes(app=app, mcp=mcp, prefix="/mcp")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)
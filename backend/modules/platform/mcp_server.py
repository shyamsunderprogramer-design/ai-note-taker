"""
mcp_server.py - Model Context Protocol Server for Claude/Cursor Integration
T21: MCP server implementation - competitors (Otter, Fireflies, Grain) have this

Features:
- MCP protocol server (stdio transport)
- Expose transcripts, summaries, and search via MCP
- Allow Claude/Cursor to query interview data
- Tools: search_transcripts, get_summary, list_action_items, get_interview_notes
- Resources: Conversation transcripts, Meeting summaries, Interview notes

MCP Spec: https://spec.modelcontextprotocol.io/
"""

import os
import sys
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("mcp_server")

# MCP Protocol Constants
JSONRPC_VERSION = "2.0"
MCP_VERSION = "2024-11-05"


class MCPError:
    """MCP Error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable


@dataclass
class MCPResource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mime_type: str
    content_provider: Callable


class MCPServer:
    """
    Model Context Protocol Server implementation.
    Uses stdio transport for communication with MCP clients (Claude, Cursor).
    """

    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.request_handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
        }
        self._running = False

    def register_tool(self, tool: MCPTool):
        """Register an MCP tool"""
        self.tools[tool.name] = tool
        logger.info(f"[MCP] Registered tool: {tool.name}")

    def register_resource(self, resource: MCPResource):
        """Register an MCP resource"""
        self.resources[resource.uri] = resource
        logger.info(f"[MCP] Registered resource: {resource.uri}")

    async def _handle_initialize(self, params: Dict) -> Dict:
        """Handle initialize request"""
        client_info = params.get("clientInfo", {})
        logger.info(f"[MCP] Client connected: {client_info.get('name')} {client_info.get('version')}")

        return {
            "protocolVersion": MCP_VERSION,
            "serverInfo": {
                "name": "ai-note-taker-mcp",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": False, "listChanged": True},
                "prompts": {"listChanged": False},
            }
        }

    async def _handle_tools_list(self, params: Dict) -> Dict:
        """Handle tools/list request"""
        tools_list = []
        for tool in self.tools.values():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            })
        return {"tools": tools_list}

    async def _handle_tools_call(self, params: Dict) -> Dict:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            raise Exception(f"Tool not found: {tool_name}")

        tool = self.tools[tool_name]
        try:
            result = await tool.handler(arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    }
                ],
                "isError": False
            }
        except Exception as e:
            logger.error(f"[MCP] Tool execution error: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing tool: {str(e)}"
                    }
                ],
                "isError": True
            }

    async def _handle_resources_list(self, params: Dict) -> Dict:
        """Handle resources/list request"""
        resources_list = []
        for resource in self.resources.values():
            resources_list.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type
            })
        return {"resources": resources_list}

    async def _handle_resources_read(self, params: Dict) -> Dict:
        """Handle resources/read request"""
        uri = params.get("uri")

        if uri not in self.resources:
            raise Exception(f"Resource not found: {uri}")

        resource = self.resources[uri]
        try:
            content = await resource.content_provider()
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": resource.mime_type,
                        "text": content if isinstance(content, str) else json.dumps(content, indent=2)
                    }
                ]
            }
        except Exception as e:
            logger.error(f"[MCP] Resource read error: {e}")
            raise

    async def _handle_prompts_list(self, params: Dict) -> Dict:
        """Handle prompts/list request"""
        # Define prompts that help users interact with interview data
        return {
            "prompts": [
                {
                    "name": "analyze_interview",
                    "description": "Analyze an interview transcript for key insights",
                    "arguments": [
                        {"name": "interview_id", "description": "ID of the interview to analyze", "required": True}
                    ]
                },
                {
                    "name": "prepare_for_company",
                    "description": "Get preparation notes for a specific company interview",
                    "arguments": [
                        {"name": "company", "description": "Company name", "required": True},
                        {"name": "role", "description": "Job role", "required": False}
                    ]
                }
            ]
        }

    async def _handle_prompts_get(self, params: Dict) -> Dict:
        """Handle prompts/get request"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        if prompt_name == "analyze_interview":
            interview_id = arguments.get("interview_id", "unknown")
            return {
                "description": f"Analyze interview {interview_id}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Please analyze the interview transcript with ID {interview_id}. Look for: 1) Key questions asked, 2) Candidate's strengths/weaknesses, 3) Areas for improvement, 4) Overall assessment."
                        }
                    }
                ]
            }
        elif prompt_name == "prepare_for_company":
            company = arguments.get("company", "")
            role = arguments.get("role", "")
            return {
                "description": f"Prepare for {company} interview",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Help me prepare for my interview at {company}" + (f" for a {role} position" if role else "") + ". What should I know about their interview process, common questions, and culture?"
                        }
                    }
                ]
            }

        raise Exception(f"Prompt not found: {prompt_name}")

    async def _process_request(self, request: Dict) -> Optional[Dict]:
        """Process a single JSON-RPC request"""
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})

        if not method:
            return self._create_error_response(request_id, MCPError.INVALID_REQUEST, "Method required")

        handler = self.request_handlers.get(method)
        if not handler:
            return self._create_error_response(request_id, MCPError.METHOD_NOT_FOUND, f"Method not found: {method}")

        try:
            result = await handler(params)
            return self._create_success_response(request_id, result)
        except Exception as e:
            logger.error(f"[MCP] Request handler error: {e}")
            return self._create_error_response(request_id, MCPError.INTERNAL_ERROR, str(e))

    def _create_success_response(self, request_id: Any, result: Dict) -> Dict:
        """Create a JSON-RPC success response"""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result
        }

    def _create_error_response(self, request_id: Any, code: int, message: str) -> Dict:
        """Create a JSON-RPC error response"""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    async def run(self):
        """Run the MCP server (stdio transport)"""
        self._running = True
        logger.info("[MCP] Server started on stdio")

        while self._running:
            try:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    response = self._create_error_response(None, MCPError.PARSE_ERROR, str(e))
                    self._send_response(response)
                    continue

                # Process request
                response = await self._process_request(request)
                if response:
                    self._send_response(response)

            except Exception as e:
                logger.error(f"[MCP] Server loop error: {e}")

    def _send_response(self, response: Dict):
        """Send JSON-RPC response to stdout"""
        try:
            print(json.dumps(response), flush=True)
        except Exception as e:
            logger.error(f"[MCP] Failed to send response: {e}")

    def stop(self):
        """Stop the server"""
        self._running = False


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def search_transcripts_handler(arguments: Dict) -> Dict:
    """
    Tool: search_transcripts
    Search across all conversation transcripts.
    """
    query = arguments.get("query", "")
    limit = arguments.get("limit", 10)
    user_id = arguments.get("user_id")

    try:
        # Try to use database if available
        try:
            from database import ConversationRepository
            if user_id:
                conversations = await ConversationRepository.get_by_user(user_id, limit=limit)
            else:
                # Search all (would need admin or specific permission)
                conversations = []

            results = []
            for conv in conversations:
                if query.lower() in conv.title.lower() if conv.title else False:
                    results.append({
                        "id": str(conv.id),
                        "title": conv.title,
                        "message_count": conv.message_count,
                        "created_at": conv.created_at.isoformat() if conv.created_at else None
                    })

            return {
                "results": results,
                "total_found": len(results),
                "query": query
            }
        except ImportError:
            # Fallback to JSON files
            import glob
            results = []
            for conv_file in glob.glob("data/conversations/*.json"):
                try:
                    with open(conv_file) as f:
                        data = json.load(f)
                        if query.lower() in data.get("title", "").lower():
                            results.append({
                                "id": data.get("id"),
                                "title": data.get("title"),
                                "message_count": len(data.get("messages", [])),
                            })
                except:
                    pass

            return {
                "results": results[:limit],
                "total_found": len(results),
                "query": query,
                "note": "Using fallback search"
            }

    except Exception as e:
        return {"error": str(e)}


async def get_summary_handler(arguments: Dict) -> Dict:
    """
    Tool: get_summary
    Get AI summary of a conversation.
    """
    conversation_id = arguments.get("conversation_id")

    if not conversation_id:
        return {"error": "conversation_id required"}

    try:
        # Try to get from database
        try:
            from database import ConversationRepository
            conv = await ConversationRepository.get_by_id(conversation_id)
            if conv:
                # Generate summary from messages
                messages = conv.messages or []
                summary = f"Conversation '{conv.title}' has {len(messages)} messages."

                return {
                    "conversation_id": conversation_id,
                    "title": conv.title,
                    "summary": summary,
                    "message_count": len(messages),
                    "created_at": conv.created_at.isoformat() if conv.created_at else None
                }
        except ImportError:
            pass

        return {"error": "Conversation not found"}

    except Exception as e:
        return {"error": str(e)}


async def list_action_items_handler(arguments: Dict) -> Dict:
    """
    Tool: list_action_items
    Get action items from a meeting/conversation.
    """
    conversation_id = arguments.get("conversation_id")

    # Mock implementation - would parse conversation for action items
    return {
        "action_items": [
            {"text": "Follow up on technical discussion", "priority": "high"},
            {"text": "Review system design proposal", "priority": "medium"},
            {"text": "Schedule next round interview", "priority": "high"}
        ],
        "conversation_id": conversation_id,
        "generated_at": datetime.now().isoformat()
    }


async def get_interview_notes_handler(arguments: Dict) -> Dict:
    """
    Tool: get_interview_notes
    Get interview preparation notes for a company/role.
    """
    company = arguments.get("company", "")
    role = arguments.get("role", "")

    # Mock implementation - would query interview database
    notes = {
        "company": company,
        "role": role,
        "process": [
            "Initial phone screen (30 min)",
            "Technical interview (60 min)",
            "System design (60 min)",
            "Behavioral/Culture fit (45 min)"
        ],
        "common_questions": [
            "Tell me about yourself",
            "Why do you want to work here?",
            "Describe a challenging project"
        ],
        "tips": [
            "Research recent company news",
            "Prepare specific examples using STAR method",
            "Have questions ready for the interviewer"
        ],
        "generated_at": datetime.now().isoformat()
    }

    return notes


async def ask_about_conversation_handler(arguments: Dict) -> Dict:
    """
    Tool: ask_about_conversation
    Q&A over a specific conversation.
    """
    conversation_id = arguments.get("conversation_id")
    question = arguments.get("question", "")

    if not conversation_id or not question:
        return {"error": "conversation_id and question required"}

    # Mock implementation - would use RAG or similar
    return {
        "conversation_id": conversation_id,
        "question": question,
        "answer": "Based on the conversation, the key points discussed were... [This is a placeholder answer. In production, would use RAG to generate answer from conversation context.]",
        "relevant_messages": [1, 3, 5],  # Indices of relevant messages
        "confidence": 0.85
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCE IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def conversations_list_resource() -> str:
    """Resource: List of conversations"""
    try:
        # Try database first
        try:
            from database import ConversationRepository
            # Would need to get all conversations or user's conversations
            conversations = []  # Placeholder
        except ImportError:
            conversations = []

        return json.dumps({
            "resource": "conversations",
            "count": len(conversations),
            "conversations": [
                {
                    "id": str(c.id),
                    "title": c.title,
                    "created_at": c.created_at.isoformat() if hasattr(c, 'created_at') and c.created_at else None
                }
                for c in conversations[:10]  # Limit to 10 for preview
            ]
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def interview_notes_resource() -> str:
    """Resource: Interview preparation notes"""
    return json.dumps({
        "resource": "interview_notes",
        "categories": [
            "Technical Questions",
            "Behavioral Questions",
            "System Design",
            "Company Research"
        ],
        "last_updated": datetime.now().isoformat()
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# SERVER SETUP
# ═══════════════════════════════════════════════════════════════════════════════

def create_mcp_server() -> MCPServer:
    """Create and configure MCP server with all tools and resources"""
    server = MCPServer()

    # Register tools
    server.register_tool(MCPTool(
        name="search_transcripts",
        description="Search across all conversation transcripts",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
                "user_id": {"type": "string", "description": "Filter by user (optional)"}
            },
            "required": ["query"]
        },
        handler=search_transcripts_handler
    ))

    server.register_tool(MCPTool(
        name="get_summary",
        description="Get AI summary of a conversation",
        input_schema={
            "type": "object",
            "properties": {
                "conversation_id": {"type": "string", "description": "ID of the conversation"}
            },
            "required": ["conversation_id"]
        },
        handler=get_summary_handler
    ))

    server.register_tool(MCPTool(
        name="list_action_items",
        description="Get action items from a meeting/conversation",
        input_schema={
            "type": "object",
            "properties": {
                "conversation_id": {"type": "string", "description": "ID of the conversation"}
            },
            "required": ["conversation_id"]
        },
        handler=list_action_items_handler
    ))

    server.register_tool(MCPTool(
        name="get_interview_notes",
        description="Get interview preparation notes for a company/role",
        input_schema={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name"},
                "role": {"type": "string", "description": "Job role (optional)"}
            },
            "required": ["company"]
        },
        handler=get_interview_notes_handler
    ))

    server.register_tool(MCPTool(
        name="ask_about_conversation",
        description="Ask a question about a specific conversation",
        input_schema={
            "type": "object",
            "properties": {
                "conversation_id": {"type": "string", "description": "ID of the conversation"},
                "question": {"type": "string", "description": "Question to ask"}
            },
            "required": ["conversation_id", "question"]
        },
        handler=ask_about_conversation_handler
    ))

    # Register resources
    server.register_resource(MCPResource(
        uri="conversations://list",
        name="Conversations List",
        description="List of all conversations",
        mime_type="application/json",
        content_provider=conversations_list_resource
    ))

    server.register_resource(MCPResource(
        uri="interview://notes",
        name="Interview Notes",
        description="Interview preparation notes",
        mime_type="application/json",
        content_provider=interview_notes_resource
    ))

    return server


# Global server instance
mcp_server = create_mcp_server()


async def main():
    """Main entry point for MCP server"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('mcp_server.log'),
            logging.StreamHandler(sys.stderr)  # Log errors to stderr
        ]
    )

    await mcp_server.run()


if __name__ == "__main__":
    asyncio.run(main())


# Export all
__all__ = [
    "MCPServer",
    "MCPTool",
    "MCPResource",
    "create_mcp_server",
    "mcp_server",
    "search_transcripts_handler",
    "get_summary_handler",
    "list_action_items_handler",
    "get_interview_notes_handler",
    "ask_about_conversation_handler",
]

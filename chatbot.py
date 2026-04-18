"""
AI Customer Support Chatbot for E-commerce
Built with Claude API (Anthropic) — handles multi-turn conversations,
order lookups via tool use, and graceful handoff to human agents.

Author: Ihor T.
"""

import os
import json
import logging
from datetime import datetime
from anthropic import Anthropic

# Setup logging for production visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# System prompt — defines bot behavior, tone, and boundaries
SYSTEM_PROMPT = """You are a customer support assistant for ShopEasy, an online store selling electronics and home goods.

Your responsibilities:
- Help customers with order status, shipping, returns, and product questions
- Use the available tools to look up real order information — never make up details
- Keep responses concise (2-4 sentences max) unless the customer asks for detail
- Be warm but professional

Escalation rules:
- If a customer is upset, frustrated, or asks to speak to a human, use the escalate_to_human tool immediately
- If a question is about refunds over $500, legal matters, or account security, escalate immediately
- For any situation outside your defined responsibilities, escalate

Tone: friendly, clear, solution-focused. Never apologize excessively — acknowledge the issue once and move to solving it.

If you don't know something, say so directly and offer to connect the customer with someone who does."""

# Tool definitions — let Claude look up real data
TOOLS = [
    {
        "name": "lookup_order",
        "description": "Retrieves the status and details of a customer order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID, e.g. 'ORD-12345'"
                }
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "get_return_policy",
        "description": "Returns the current return and refund policy for a product category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["electronics", "home_goods", "clothing", "general"]
                }
            },
            "required": ["category"]
        }
    },
    {
        "name": "escalate_to_human",
        "description": "Transfers the conversation to a human support agent. Use when customer is frustrated, has a complex issue, or explicitly asks for a person.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Brief reason for escalation"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"]
                }
            },
            "required": ["reason", "priority"]
        }
    }
]


# Mock functions — in production these would hit real CRM/order DB
def lookup_order(order_id: str) -> dict:
    """Simulated order lookup. In production, connects to order database."""
    logger.info(f"Looking up order: {order_id}")

    # Mock database
    mock_orders = {
        "ORD-12345": {
            "status": "Shipped",
            "tracking": "UPS-1Z999AA10123456784",
            "items": ["Wireless Headphones", "USB-C Cable"],
            "estimated_delivery": "2026-04-23",
            "total": "$124.99"
        },
        "ORD-67890": {
            "status": "Processing",
            "items": ["Coffee Maker"],
            "estimated_ship_date": "2026-04-21",
            "total": "$89.50"
        }
    }

    if order_id in mock_orders:
        return {"success": True, "order": mock_orders[order_id]}
    return {"success": False, "error": f"Order {order_id} not found"}


def get_return_policy(category: str) -> dict:
    """Returns policy details per category."""
    policies = {
        "electronics": "30-day returns, product must be in original packaging. Refund processed within 5-7 business days.",
        "home_goods": "60-day returns for unused items. Refund to original payment method.",
        "clothing": "45-day returns, tags attached. Free return shipping.",
        "general": "Standard 30-day return window. Contact support for specifics."
    }
    return {"policy": policies.get(category, policies["general"])}


def escalate_to_human(reason: str, priority: str) -> dict:
    """Logs escalation event. In production, creates ticket in Zendesk/Intercom."""
    logger.warning(f"ESCALATION [{priority}]: {reason}")
    return {
        "escalated": True,
        "ticket_id": f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "message": f"I've connected you with our team ({priority} priority). A human agent will reach out shortly."
    }


# Tool dispatcher
def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Routes tool calls to the right function and returns JSON result."""
    handlers = {
        "lookup_order": lookup_order,
        "get_return_policy": get_return_policy,
        "escalate_to_human": escalate_to_human
    }

    if tool_name not in handlers:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = handlers[tool_name](**tool_input)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return json.dumps({"error": str(e)})


def chat(user_message: str, conversation_history: list) -> tuple[str, list]:
    """
    Main chat function. Handles multi-turn conversations with tool use.
    Returns (assistant_reply, updated_history).
    """
    # Add the new user message to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    # Call Claude — it may decide to use tools
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history
        )

        # Add Claude's response to history
        conversation_history.append({
            "role": "assistant",
            "content": response.content
        })

        # If Claude wants to use a tool, execute it and loop
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"Claude calling tool: {block.name}")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            conversation_history.append({
                "role": "user",
                "content": tool_results
            })
            continue  # Let Claude process the tool results

        # Otherwise extract and return the text response
        final_text = next(
            (b.text for b in response.content if hasattr(b, "text")),
            "I'm not sure how to help with that. Let me connect you with a human agent."
        )
        return final_text, conversation_history


# Demo runner
if __name__ == "__main__":
    print("ShopEasy Support Bot — Type 'quit' to exit\n")

    history = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit"}:
            break
        if not user_input:
            continue

        try:
            reply, history = chat(user_input, history)
            print(f"\nBot: {reply}\n")
        except Exception as e:
            logger.error(f"Chat error: {e}")
            print(f"\nBot: Sorry, I hit a technical issue. Please try again.\n")

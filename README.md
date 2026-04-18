# AI Customer Support Chatbot

Production-ready AI chatbot for e-commerce customer support, built with Anthropic's Claude API. Handles multi-turn conversations, looks up real order data via tool use, and escalates complex cases to human agents.

## Features

- **Multi-turn conversation memory** — remembers context within a session
- **Tool use integration** — Claude autonomously calls functions to look up orders, return policies, and trigger escalations
- **Smart escalation** — detects frustration, complex issues, or explicit requests for a human and routes them appropriately
- **Production logging** — structured logs for every tool call and escalation event
- **Token-efficient** — keeps responses concise by design (system prompt enforcement)

## Tech stack

- **LLM**: Claude Sonnet 4.5 (Anthropic)
- **Language**: Python 3.10+
- **SDK**: `anthropic` official Python library
- **Deployment-ready**: drop-in for Flask/FastAPI backends, Slack/Telegram bots, or web widgets

## How it works

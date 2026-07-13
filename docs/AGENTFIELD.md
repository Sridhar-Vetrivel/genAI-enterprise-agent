# AgentField Python SDK Reference

This documentation outlines the standard syntax and implementation patterns for building AI agents using the **AgentField** framework.

---

## 1. Agent Initialization
To initialize an agent, use the `Agent` class. This setup connects the agent to the AgentField server and defines the LLM provider via `AIConfig`.

```python
import os
import asyncio
from typing import List, Dict
from agentfield import Agent, AIConfig

# Initialize agent
app = Agent(
    node_id="[agent_name]",
    agentfield_server=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080"),
    ai_config=AIConfig(
        model=os.getenv("AI_MODEL", "[open_router_model_name]")
    ),
)
```
## 2. Core Components
Skills
Skills are deterministic functions used for standard code execution, API calls, or data manipulation.

```python
@app.skill()
async def skill_1(arguments) -> [returntype]:
    # Standard Python logic
    ...
```
## 3. Reasoners
Reasoners handle non-deterministic logic and use LLMs to process information or make decisions.

```python
@app.reasoner()
async def reasoner_1(arguments) -> [pydantic_object]:
    # AI-driven logic
    ...
    response = await app.ai(
        system="[persona or operation]",
        user=f""" [Prompt] """,
        schema=[pydantic_schema_for_return]
    )
    return response
```

## 4. AI Reasoning Syntax
The `app.ai` method is used to fetch responses from the LLM. It supports structured output through Pydantic schemas.

Syntax Template:
```python
app.ai(
    system="[persona or operation]",
    user=f""" [Prompt] """,
    schema=[pydantic_schema_for_return]
)
```
 - [!IMPORTANT] Schema Requirements:

 - Pydantic schemas should be kept simple with basic types.

 - Always include: model_config=ConfigDict(extra="forbid") to ensure strict validation.


## 5. State Management
AgentField uses a memory system to persist data or pass objects between different agents in the workflow.
### Memory Scopes
- **Global:** Shared across all agents/sessions
- **Agent:** Scoped to one agent, all sessions
- **Session:** Scoped to one session (multi-turn conversation)
- **Run:** Scoped to single execution/workflow run

# Set Value
Store an object or data point using a specific key.
```python
await app.memory.set([memory_scope],"[key]", [object])
```
# Get Value
Retrieve a previously stored value by its key.
```python
val = await app.memory.get([memory_scope],"[key]")
```

## 6. Webhooks
Agents that run for hours or days. Webhooks with automatic retries. Backpressure handling when downstream services are slow.
```python
# Fire-and-forget: webhook called when done
result = await app.call(
    "[node_id].[reasoner_name]",
    input={  //JSON PAYLOAD },
    async_config=AsyncConfig(
        webhook_url="[WEBHOOK_URL]",
        timeout_hours=[TIMEOUT_IN_HOURS]
    )
)
```

## 7. Multi-Agent Coordination
Agents that discover and invoke each other through the control plane. Every call tracked. Every workflow visualized as a DAG.
```python
# Agent A calls Agent B—routed through control plane, fully traced
analysis = await app.call("[agent_A_node_id].[reasoner_name]", input={ //JSON PAYLOAD })
report = await app.call("[agent_B_node_id].[reasoner_name]", input={ //JSON PAYLOAD })
```

## 8. Memory Event Listener on memory state change in Agent
Allows functions to automatically respond to changes in the agent's memory system. When memory data matching the specified patterns is modified,
the decorated function will be called with the change event details.
The pattern supports glob-style patterns for flexible matching. Examples: "user.*", ["session.current_user", "workflow.status"]
```python
		@app.on_change("user.preferences.*")
		async def handle_preference_change(event):
			'''React to user preference changes.'''
			log_info(f"User preference changed: {event.key} = {event.data}")

			# Update related systems
			if event.path.endswith("theme"):
				await update_ui_theme(event.data)
			elif event.path.endswith("language"):
				await update_localization(event.data)

		@app.on_change(["session.user_id", "session.permissions"])
		async def handle_session_change(event):
			'''React to session-related changes.'''
			if event.path == "session.user_id":
				# User logged in/out
				await initialize_user_context(event.data)
			elif event.path == "session.permissions":
				# Permissions updated
				await refresh_access_controls(event.data)

		# Memory changes trigger the listeners automatically
		app.memory.set("user.preferences.theme", "dark")  # Triggers handle_preference_change
		app.memory.set("session.user_id", 12345)          # Triggers handle_session_change
```

## 9. Vector embedding storage using AgentField memory fabric
```Python
await app.memory.set_vector(chunk_id, embedding_data, metadata=metadata)
```

## 10. Semantic Similarity search using AgentField
```Python
 results = await app.memory.similarity_search(query_embedding, top_k=top_k)
 # results is a List with each result containing key, score and text as dictionary key
```

## 11. Testing the agent
```bash
curl -X POST http://[control_plane_url]/api/v1/execute/[node_id].[reasoner_name] \
  -H "Content-Type: application/json" \
  -d '{"input": { //JSON Payload for the reasoner}}'
```

**Code Style**
- Use Ruff for linting and formatting (`make fmt` runs `ruff format`)
- Type hints required for public APIs
- Async/await for I/O operations
- Follow PEP 8
- Follow SOLID, YAGNI, DRY, KISS Principles

**Testing Style**
Write tests for [function/component] that cover:
1. Happy path - normal expected inputs
2. Edge cases - empty inputs, null values, boundary conditions
3. Error cases - invalid inputs, network failures, timeouts
4. Integration points - verify mocks are called correctly

**Commit Attribution**
```
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Test Quality Checklist:**
- [ ] Tests actually fail when the code is broken
- [ ] Each test has clear assertions, not just "runs without error"
- [ ] Edge cases are covered (null, empty, boundary values)
- [ ] Error paths are tested, not just happy paths
- [ ] Tests are independent and can run in any order
- [ ] Test names clearly describe what is being tested
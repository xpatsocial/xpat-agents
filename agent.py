"""x/pat AI Agent Team — Core Agent Runner"""

import json
import anthropic
from config import AGENTS, MAX_TOKENS


client = anthropic.Anthropic()


def run_agent(agent_name: str, prompt: str, conversation: list | None = None) -> str:
    """Run a single agent and return its response text."""
    if agent_name not in AGENTS:
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENTS.keys())}")

    agent = AGENTS[agent_name]
    messages = conversation or [{"role": "user", "content": prompt}]

    response = client.messages.create(
        model=agent["model"],
        max_tokens=MAX_TOKENS,
        system=agent["system"],
        messages=messages,
    )

    return response.content[0].text


def run_ceo(goal: str) -> dict:
    """
    Run the CEO orchestrator: it breaks down a goal into tasks,
    delegates to specialist agents, and synthesizes results.
    """
    # Step 1: CEO breaks down the goal
    delegation_prompt = f"""Given this business goal, break it down into specific tasks for the specialist agents.

GOAL: {goal}

Available agents and their roles:
- product: Feature specs, user stories, roadmap prioritization
- frontend: React Native UI code, design system implementation
- backend: Supabase schema, APIs, auth, real-time features
- marketing: Copy, outreach emails, social content, growth strategy
- research: Competitor analysis, market data, partnership leads
- qa: Test plans, code review, security checks

Respond in JSON format:
{{
    "plan": "Brief strategic summary",
    "tasks": [
        {{"agent": "agent_name", "task": "Specific task description"}},
        ...
    ]
}}

Only assign tasks that are relevant to the goal. Be specific in each task description."""

    ceo_response = run_agent("ceo", delegation_prompt)

    # Parse the CEO's delegation plan
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_str = ceo_response
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        plan = json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError):
        return {
            "plan": "CEO provided unstructured response",
            "ceo_raw": ceo_response,
            "results": {},
        }

    # Step 2: Execute each delegated task
    results = {}
    for task in plan.get("tasks", []):
        agent_name = task["agent"]
        task_desc = task["task"]
        print(f"  → Delegating to {AGENTS[agent_name]['name']}: {task_desc[:80]}...")
        results[agent_name] = run_agent(agent_name, task_desc)

    # Step 3: CEO synthesizes all results
    synthesis_prompt = f"""Original goal: {goal}

Your delegation plan: {plan.get('plan', '')}

Results from your team:
"""
    for agent_name, result in results.items():
        synthesis_prompt += f"\n--- {AGENTS[agent_name]['name']} ---\n{result}\n"

    synthesis_prompt += "\nSynthesize these results into a clear, actionable executive summary with next steps."

    synthesis = run_agent("ceo", synthesis_prompt)

    return {
        "plan": plan.get("plan", ""),
        "tasks": plan.get("tasks", []),
        "results": results,
        "synthesis": synthesis,
    }

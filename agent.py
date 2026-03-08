"""x/pat AI Agent Team — Core Agent Runner with Parallel Execution"""

import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def run_agents_parallel(tasks: list[dict]) -> dict:
    """
    Run multiple agents concurrently.

    Args:
        tasks: List of {"agent": "name", "task": "prompt"} dicts

    Returns:
        Dict of {agent_name: response_text}
    """
    results = {}
    start = time.time()

    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = {}
        for t in tasks:
            agent_name = t["agent"]
            task_desc = t["task"]
            print(f"  ⚡ Launching {AGENTS[agent_name]['name']}...")
            future = pool.submit(run_agent, agent_name, task_desc)
            futures[future] = agent_name

        for future in as_completed(futures):
            agent_name = futures[future]
            elapsed = time.time() - start
            try:
                results[agent_name] = future.result()
                print(f"  ✓ {AGENTS[agent_name]['name']} done ({elapsed:.1f}s)")
            except Exception as e:
                results[agent_name] = f"[ERROR] {e}"
                print(f"  ✗ {AGENTS[agent_name]['name']} failed: {e}")

    total = time.time() - start
    print(f"\n  All agents finished in {total:.1f}s")
    return results


def run_all_agents(prompt: str) -> dict:
    """Send the same prompt to ALL specialist agents in parallel."""
    tasks = [{"agent": name, "task": prompt} for name in AGENTS if name != "ceo"]
    return run_agents_parallel(tasks)


def run_ceo(goal: str) -> dict:
    """
    CEO orchestrator: breaks down a goal, delegates to agents IN PARALLEL,
    then synthesizes all results.
    """
    print(f"\n{'='*60}")
    print(f"  CEO ORCHESTRATING: {goal[:70]}...")
    print(f"{'='*60}\n")

    # Step 1: CEO plans the delegation
    print("  [1/3] CEO planning delegation...\n")
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

    # Parse
    try:
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

    # Step 2: Execute ALL delegated tasks in parallel
    tasks = plan.get("tasks", [])
    print(f"  [2/3] Dispatching {len(tasks)} agents in parallel...\n")
    results = run_agents_parallel(tasks)

    # Step 3: CEO synthesizes
    print(f"\n  [3/3] CEO synthesizing results...\n")
    synthesis_prompt = f"""Original goal: {goal}

Your delegation plan: {plan.get('plan', '')}

Results from your team:
"""
    for agent_name, result in results.items():
        synthesis_prompt += f"\n--- {AGENTS[agent_name]['name']} ---\n{result}\n"

    synthesis_prompt += "\nSynthesize these results into a clear, actionable executive summary with prioritized next steps."

    synthesis = run_agent("ceo", synthesis_prompt)

    return {
        "plan": plan.get("plan", ""),
        "tasks": tasks,
        "results": results,
        "synthesis": synthesis,
    }

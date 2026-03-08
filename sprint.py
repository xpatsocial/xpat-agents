"""x/pat AI Agent Team — Sprint Runner with Approval Pipeline"""

import json
import os
import time
from datetime import datetime
from agent import run_agent, run_agents_parallel
from config import AGENTS

SPRINTS_DIR = os.path.join(os.path.dirname(__file__), "sprints")
QUEUE_FILE = os.path.join(os.path.dirname(__file__), "review_queue.json")


def _ensure_dirs():
    os.makedirs(SPRINTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(SPRINTS_DIR, "approved"), exist_ok=True)
    os.makedirs(os.path.join(SPRINTS_DIR, "rejected"), exist_ok=True)


def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r") as f:
            return json.load(f)
    return {"pending": [], "approved": [], "rejected": []}


def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def run_sprint(goal: str, sprint_name: str | None = None):
    """
    Full autonomous sprint:
    1. CEO agent plans and delegates
    2. All agents execute in parallel
    3. Each deliverable goes into the review queue
    4. CEO reviews and approves/rejects
    """
    _ensure_dirs()
    queue = load_queue()

    sprint_id = sprint_name or datetime.now().strftime("sprint-%Y%m%d-%H%M")
    sprint_dir = os.path.join(SPRINTS_DIR, sprint_id)
    os.makedirs(sprint_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  SPRINT: {sprint_id}")
    print(f"  GOAL: {goal}")
    print(f"{'='*60}\n")

    # ── Phase 1: CEO Plans ──
    print("  Phase 1: CEO planning delegation...\n")

    plan_prompt = f"""You are running Sprint "{sprint_id}" for x/pat.

GOAL: {goal}

Break this into CONCRETE deliverables for each agent. Each task should produce a specific output
(code, document, analysis, etc.) — not just a plan or suggestion.

Available agents:
- product: Feature specs, user stories, acceptance criteria, roadmap docs
- frontend: React Native component code, UI implementations
- backend: Supabase SQL schemas, RLS policies, Edge Functions, API specs
- marketing: Landing page copy, email templates, social content, growth plans
- research: Market analysis, competitor breakdowns, partnership recommendations
- qa: Test plans, security audits, review checklists

Respond in JSON:
{{
    "plan": "Strategic summary of this sprint",
    "tasks": [
        {{
            "agent": "agent_name",
            "task": "Specific deliverable description",
            "deliverable": "What the output should be (e.g., 'SQL schema', 'React component', 'email draft')"
        }}
    ]
}}"""

    ceo_response = run_agent("ceo", plan_prompt)

    try:
        json_str = ceo_response
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        plan = json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError):
        # Save raw response if JSON parsing fails
        with open(os.path.join(sprint_dir, "ceo-raw-plan.md"), "w") as f:
            f.write(ceo_response)
        print("  CEO response saved but couldn't auto-parse. Check ceo-raw-plan.md")
        return {"sprint_id": sprint_id, "error": "plan_parse_failed"}

    # Save the plan
    with open(os.path.join(sprint_dir, "plan.json"), "w") as f:
        json.dump(plan, f, indent=2)

    print(f"  Plan: {plan.get('plan', '')[:80]}...")
    print(f"  Tasks: {len(plan.get('tasks', []))} deliverables\n")

    # ── Phase 2: All Agents Execute in Parallel ──
    tasks = plan.get("tasks", [])
    print(f"  Phase 2: Dispatching {len(tasks)} agents in parallel...\n")

    results = run_agents_parallel(tasks)

    # ── Phase 3: Save deliverables + queue for review ──
    print(f"\n  Phase 3: Queuing deliverables for CEO review...\n")

    for task in tasks:
        agent_name = task["agent"]
        result = results.get(agent_name, "[No output]")
        deliverable_type = task.get("deliverable", "document")

        # Save to file
        filename = f"{agent_name}-{deliverable_type.replace(' ', '-').lower()}.md"
        filepath = os.path.join(sprint_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {AGENTS[agent_name]['name']} — {deliverable_type}\n")
            f.write(f"**Sprint:** {sprint_id}\n")
            f.write(f"**Task:** {task['task']}\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n---\n\n")
            f.write(result)

        # Add to review queue
        queue_item = {
            "id": len(queue["pending"]) + len(queue["approved"]) + len(queue["rejected"]) + 1,
            "sprint": sprint_id,
            "agent": agent_name,
            "task": task["task"],
            "deliverable": deliverable_type,
            "file": filepath,
            "status": "pending",
            "created": datetime.now().isoformat(),
        }
        queue["pending"].append(queue_item)
        print(f"  📋 Queued #{queue_item['id']}: [{agent_name}] {deliverable_type}")

    save_queue(queue)

    # ── Phase 4: CEO Synthesis ──
    print(f"\n  Phase 4: CEO generating executive brief...\n")

    brief_prompt = f"""Sprint "{sprint_id}" is complete. Here are the deliverables from your team:

"""
    for agent_name, result in results.items():
        brief_prompt += f"\n--- {AGENTS[agent_name]['name']} ---\n{result[:500]}...\n"

    brief_prompt += """

Write an EXECUTIVE BRIEF with:
1. Sprint summary (2-3 sentences)
2. Key deliverables produced (bulleted list)
3. Decisions needed from CEO (what needs approval/direction)
4. Recommended next sprint goals
5. Risk flags (anything concerning)

Keep it concise — this is a CEO briefing, not a novel."""

    brief = run_agent("ceo", brief_prompt)

    # Save brief
    brief_path = os.path.join(sprint_dir, "executive-brief.md")
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write(f"# Executive Brief — {sprint_id}\n")
        f.write(f"**Goal:** {goal}\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n")
        f.write(brief)

    print(f"\n{'='*60}")
    print(f"  SPRINT COMPLETE: {sprint_id}")
    print(f"{'='*60}")
    print(f"\n{brief}\n")
    print(f"  📁 All deliverables saved to: {sprint_dir}")
    print(f"  📋 {len(tasks)} items in review queue — use 'review' to approve/reject")
    print()

    return {
        "sprint_id": sprint_id,
        "plan": plan,
        "results": results,
        "brief": brief,
        "sprint_dir": sprint_dir,
    }


def show_review_queue():
    queue = load_queue()
    pending = queue.get("pending", [])
    approved = queue.get("approved", [])
    rejected = queue.get("rejected", [])

    print(f"\n{'='*60}")
    print(f"  REVIEW QUEUE")
    print(f"{'='*60}")

    print(f"\n  ⏳ PENDING REVIEW ({len(pending)})")
    print(f"  {'─'*45}")
    if not pending:
        print("  (empty — all caught up)")
    for item in pending:
        print(f"  #{item['id']:3d} [{item['agent']:10s}] {item['deliverable']}")
        print(f"       {item['task'][:55]}...")

    print(f"\n  ✅ APPROVED ({len(approved)})")
    print(f"  {'─'*45}")
    for item in approved[-5:]:  # Show last 5
        print(f"  #{item['id']:3d} [{item['agent']:10s}] {item['deliverable']}")

    print(f"\n  ❌ REJECTED ({len(rejected)})")
    print(f"  {'─'*45}")
    for item in rejected[-5:]:
        print(f"  #{item['id']:3d} [{item['agent']:10s}] {item.get('reason', 'No reason')[:50]}")

    print()


def review_item(item_id: int, action: str, reason: str = ""):
    """Approve or reject a deliverable."""
    queue = load_queue()

    item = None
    for i, p in enumerate(queue["pending"]):
        if p["id"] == item_id:
            item = queue["pending"].pop(i)
            break

    if not item:
        print(f"  Item #{item_id} not found in pending queue.")
        return

    item["reviewed"] = datetime.now().isoformat()

    if action == "approve":
        item["status"] = "approved"
        queue["approved"].append(item)
        print(f"  ✅ Approved #{item_id}: [{item['agent']}] {item['deliverable']}")
    elif action == "reject":
        item["status"] = "rejected"
        item["reason"] = reason
        queue["rejected"].append(item)
        print(f"  ❌ Rejected #{item_id}: {reason}")
    elif action == "revise":
        # Send back to the agent with feedback
        print(f"  🔄 Sending #{item_id} back to {item['agent']} for revision...")
        revision_prompt = f"""Your previous deliverable was sent back for revision.

ORIGINAL TASK: {item['task']}

CEO FEEDBACK: {reason}

Please revise your work based on this feedback. Produce an improved version."""

        revised = run_agent(item["agent"], revision_prompt)

        # Save revised version
        filepath = item["file"].replace(".md", "-revised.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# REVISED — {AGENTS[item['agent']]['name']}\n")
            f.write(f"**Feedback:** {reason}\n\n---\n\n")
            f.write(revised)

        item["file"] = filepath
        item["status"] = "pending"
        item["revision"] = True
        queue["pending"].append(item)
        print(f"  🔄 Revised deliverable re-queued as #{item['id']}")
        print(f"  📄 Saved to: {filepath}")

    save_queue(queue)


def preview_item(item_id: int):
    """Show a deliverable's content for review."""
    queue = load_queue()
    all_items = queue["pending"] + queue["approved"] + queue["rejected"]
    item = next((i for i in all_items if i["id"] == item_id), None)

    if not item:
        print(f"  Item #{item_id} not found.")
        return

    print(f"\n{'='*60}")
    print(f"  DELIVERABLE #{item['id']}")
    print(f"  Agent: {AGENTS[item['agent']]['name']}")
    print(f"  Type: {item['deliverable']}")
    print(f"  Status: {item['status']}")
    print(f"{'='*60}\n")

    if os.path.exists(item["file"]):
        with open(item["file"], "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print("  (file not found)")
    print()


def approve_all():
    """Approve all pending items at once."""
    queue = load_queue()
    count = len(queue["pending"])
    for item in queue["pending"]:
        item["status"] = "approved"
        item["reviewed"] = datetime.now().isoformat()
        queue["approved"].append(item)
    queue["pending"] = []
    save_queue(queue)
    print(f"  ✅ Approved all {count} pending deliverables.")

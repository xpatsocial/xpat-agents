"""x/pat AI Agent Team — CEO Command Center"""

import sys
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from agent import run_agent, run_agents_parallel, run_all_agents, run_ceo
from sprint import run_sprint, show_review_queue, review_item, preview_item, approve_all
from config import AGENTS

TASKS_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")


# ── Task Board ──────────────────────────────────────────────

def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r") as f:
            return json.load(f)
    return []


def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def show_board():
    tasks = load_tasks()
    if not tasks:
        print("\n  No tasks yet. Use 'add <task>' or 'sprint <goal>' to create some.\n")
        return

    statuses = {"todo": [], "in_progress": [], "done": []}
    for t in tasks:
        statuses.get(t.get("status", "todo"), statuses["todo"]).append(t)

    print(f"\n{'='*60}")
    print("  x/pat TASK BOARD")
    print(f"{'='*60}")

    for status, label in [("todo", "TODO"), ("in_progress", "IN PROGRESS"), ("done", "DONE")]:
        items = statuses[status]
        print(f"\n  {label} ({len(items)})")
        print(f"  {'─'*40}")
        if not items:
            print("  (empty)")
        for t in items:
            agent = t.get("agent", "—")
            print(f"  [{t['id']}] ({agent}) {t['task'][:50]}")
    print()


def add_task(agent, task_desc):
    tasks = load_tasks()
    task_id = len(tasks) + 1
    tasks.append({
        "id": task_id,
        "agent": agent,
        "task": task_desc,
        "status": "todo",
        "created": datetime.now().isoformat(),
        "result": None,
    })
    save_tasks(tasks)
    print(f"  + Task #{task_id} added for {agent}: {task_desc[:60]}")
    return task_id


def run_task(task_id):
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        print(f"  Task #{task_id} not found")
        return
    task["status"] = "in_progress"
    save_tasks(tasks)
    print(f"  Running task #{task_id} with {task['agent']}...")
    result = run_agent(task["agent"], task["task"])
    task["status"] = "done"
    task["result"] = result
    task["completed"] = datetime.now().isoformat()
    save_tasks(tasks)
    print(f"\n  Done #{task_id}\n")
    print(result)


def run_all_tasks():
    tasks = load_tasks()
    todo = [t for t in tasks if t["status"] == "todo"]
    if not todo:
        print("  No pending tasks to run.")
        return
    print(f"\n  Running {len(todo)} tasks in parallel...\n")
    for t in todo:
        t["status"] = "in_progress"
    save_tasks(tasks)
    agent_tasks = [{"agent": t["agent"], "task": t["task"]} for t in todo]
    results = run_agents_parallel(agent_tasks)
    for t in todo:
        if t["agent"] in results:
            t["status"] = "done"
            t["result"] = results[t["agent"]]
            t["completed"] = datetime.now().isoformat()
    save_tasks(tasks)
    print(f"\n{'='*60}")
    print("  ALL RESULTS")
    print(f"{'='*60}")
    for t in todo:
        print(f"\n  -- Task #{t['id']} ({t['agent']}) --")
        print(f"  {t.get('result', 'No result')[:200]}...")
    print()


def show_task(task_id):
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        print(f"  Task #{task_id} not found")
        return
    print(f"\n  Task #{task['id']}")
    print(f"  Agent:   {task['agent']}")
    print(f"  Status:  {task['status']}")
    print(f"  Task:    {task['task']}")
    if task.get("result"):
        print(f"\n  Result:\n{task['result']}")
    print()


# ── Output Saving ──────────────────────────────────────────

def save_output(name, content):
    os.makedirs("output", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join("output", f"{name}-{ts}.md")
    with open(path, "w") as f:
        f.write(content)
    print(f"  Saved to {path}")


# ── Main ───────────────────────────────────────────────────

def print_header():
    print(f"\n{'='*60}")
    print("  x/pat — CEO Command Center")
    print(f"{'='*60}")


def print_help():
    print("""
  SPRINTS (Autonomous + Approval)
  ──────────────────────────────────────
  sprint <goal>          CEO plans → all agents work in parallel → deliverables queue for your review
  sprint <name> <goal>   Same but with a custom sprint name

  REVIEW PIPELINE (Your Approval Authority)
  ──────────────────────────────────────
  review                 Show review queue (pending / approved / rejected)
  peek <id>              Preview a deliverable before deciding
  approve <id>           Approve a deliverable
  approve all            Approve everything pending
  reject <id> <reason>   Reject with feedback
  revise <id> <feedback> Send back to agent for revision with your notes

  DIRECT COMMANDS
  ──────────────────────────────────────
  <agent> <prompt>       Talk to one agent (product, frontend, backend, marketing, research, qa)
  ceo <goal>             Quick CEO delegation without approval pipeline
  all <prompt>           Broadcast same prompt to all agents simultaneously
  parallel               Interactive batch: pick agents + tasks, run all at once

  TASK BOARD
  ──────────────────────────────────────
  board                  Show task board
  add <agent> <task>     Queue a task
  run <id>               Run one task
  run all                Run all pending tasks in parallel
  show <id>              Show task result

  OTHER
  ──────────────────────────────────────
  agents                 List all agents and their models
  save <name>            Save last output to file
  status                 Quick overview of everything
  help                   This help
  quit                   Exit
""")


def show_status():
    from sprint import load_queue
    queue = load_queue()
    tasks = load_tasks()

    pending = len(queue.get("pending", []))
    approved = len(queue.get("approved", []))
    todo = len([t for t in tasks if t.get("status") == "todo"])
    done = len([t for t in tasks if t.get("status") == "done"])

    sprints_dir = os.path.join(os.path.dirname(__file__), "sprints")
    sprint_count = len([d for d in os.listdir(sprints_dir) if os.path.isdir(os.path.join(sprints_dir, d)) and d.startswith("sprint")]) if os.path.exists(sprints_dir) else 0

    print(f"\n{'='*60}")
    print(f"  x/pat STATUS")
    print(f"{'='*60}")
    print(f"\n  Sprints completed:    {sprint_count}")
    print(f"  Review queue:         {pending} pending | {approved} approved")
    print(f"  Task board:           {todo} todo | {done} done")
    print(f"  Agents:               {len(AGENTS)} ready")
    print()


def main():
    print_header()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n  [ERROR] ANTHROPIC_API_KEY not set.")
        print("  Copy .env.example to .env and add your key.\n")
        sys.exit(1)

    # Direct CLI mode
    if len(sys.argv) >= 3:
        agent_name = sys.argv[1]
        prompt = " ".join(sys.argv[2:])

        if agent_name == "sprint":
            run_sprint(prompt)
        elif agent_name == "ceo":
            result = run_ceo(prompt)
            print(f"\n{'='*60}")
            print("  EXECUTIVE SUMMARY")
            print(f"{'='*60}\n")
            print(result["synthesis"])
        elif agent_name == "all":
            results = run_all_agents(prompt)
            for name, res in results.items():
                print(f"\n{'─'*40}")
                print(f"  {AGENTS[name]['name']}")
                print(f"{'─'*40}")
                print(res)
        elif agent_name in AGENTS:
            print(f"\n  [{AGENTS[agent_name]['name']}] Processing...\n")
            print(run_agent(agent_name, prompt))
        else:
            print(f"  Unknown: {agent_name}")
        return

    # Interactive mode
    print_help()
    last_output = ""

    while True:
        try:
            user_input = input("\nx/pat> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        # ── Core commands ──
        if cmd in ("quit", "exit", "q"):
            print("  Goodbye!")
            break

        elif cmd == "help":
            print_help()

        elif cmd == "status":
            show_status()

        elif cmd == "agents":
            print()
            for key, agent in AGENTS.items():
                model_tag = "opus" if "opus" in agent["model"] else "sonnet"
                print(f"  {key:12s} — {agent['name']:20s} [{model_tag}]")
            print()

        # ── Sprint commands ──
        elif cmd.startswith("sprint "):
            args = user_input[7:].strip()
            # Check if first word looks like a sprint name (no spaces) followed by goal
            parts = args.split(" ", 1)
            if len(parts) == 2 and len(parts[0]) < 30 and " " not in parts[0]:
                run_sprint(goal=parts[1], sprint_name=parts[0])
            else:
                run_sprint(goal=args)

        # ── Review commands ──
        elif cmd == "review":
            show_review_queue()

        elif cmd.startswith("peek "):
            try:
                preview_item(int(user_input[5:]))
            except ValueError:
                print("  Usage: peek <id>")

        elif cmd == "approve all":
            approve_all()

        elif cmd.startswith("approve "):
            try:
                review_item(int(user_input[8:]), "approve")
            except ValueError:
                print("  Usage: approve <id>")

        elif cmd.startswith("reject "):
            parts = user_input[7:].split(" ", 1)
            try:
                item_id = int(parts[0])
                reason = parts[1] if len(parts) > 1 else "No reason given"
                review_item(item_id, "reject", reason)
            except ValueError:
                print("  Usage: reject <id> <reason>")

        elif cmd.startswith("revise "):
            parts = user_input[7:].split(" ", 1)
            try:
                item_id = int(parts[0])
                feedback = parts[1] if len(parts) > 1 else "Please improve this"
                review_item(item_id, "revise", feedback)
            except ValueError:
                print("  Usage: revise <id> <feedback>")

        # ── Task board ──
        elif cmd == "board":
            show_board()

        elif cmd.startswith("add "):
            parts = user_input[4:].split(" ", 1)
            if len(parts) < 2 or parts[0] not in AGENTS:
                print("  Usage: add <agent> <task description>")
            else:
                add_task(parts[0], parts[1])

        elif cmd == "run all":
            run_all_tasks()

        elif cmd.startswith("run "):
            try:
                run_task(int(user_input[4:]))
            except ValueError:
                print("  Usage: run <task_id> or run all")

        elif cmd.startswith("show "):
            try:
                show_task(int(user_input[5:]))
            except ValueError:
                print("  Usage: show <task_id>")

        elif cmd.startswith("save "):
            name = user_input[5:].strip()
            if last_output:
                save_output(name, last_output)
            else:
                print("  No output to save yet.")

        # ── Agent commands ──
        elif cmd == "parallel":
            print("\n  Enter tasks (one per line as 'agent: task'). Empty line to run:\n")
            batch = []
            while True:
                line = input("  + ").strip()
                if not line:
                    break
                parts = line.split(":", 1)
                if len(parts) == 2 and parts[0].strip() in AGENTS:
                    batch.append({"agent": parts[0].strip(), "task": parts[1].strip()})
                else:
                    print(f"    Invalid. Use: agent: task")
            if batch:
                results = run_agents_parallel(batch)
                for name, res in results.items():
                    print(f"\n{'─'*40}")
                    print(f"  {AGENTS[name]['name']}")
                    print(f"{'─'*40}")
                    print(res)
                    last_output += f"\n## {AGENTS[name]['name']}\n{res}\n"

        elif cmd.startswith("all "):
            prompt = user_input[4:]
            print(f"\n  Broadcasting to all agents...\n")
            results = run_all_agents(prompt)
            for name, res in results.items():
                print(f"\n{'─'*40}")
                print(f"  {AGENTS[name]['name']}")
                print(f"{'─'*40}")
                print(res)
            last_output = "\n".join(f"## {AGENTS[n]['name']}\n{r}" for n, r in results.items())

        elif cmd.startswith("ceo "):
            prompt = user_input[4:]
            result = run_ceo(prompt)
            print(f"\n{'='*60}")
            print("  EXECUTIVE SUMMARY")
            print(f"{'='*60}\n")
            print(result["synthesis"])
            last_output = result["synthesis"]
            for agent_name, res in result.get("results", {}).items():
                last_output += f"\n\n## {AGENTS[agent_name]['name']}\n{res}"

        else:
            parts = user_input.split(" ", 1)
            agent_name = parts[0].lower()
            prompt = parts[1] if len(parts) > 1 else ""

            if not prompt:
                print("  Provide a prompt. Type 'help' for commands.")
                continue

            if agent_name in AGENTS:
                print(f"\n  [{AGENTS[agent_name]['name']}] Processing...\n")
                result = run_agent(agent_name, prompt)
                print(result)
                last_output = result
            else:
                print(f"  Unknown command: '{agent_name}'. Type 'help' for commands.")

    print()


if __name__ == "__main__":
    main()

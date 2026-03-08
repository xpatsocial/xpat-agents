"""x/pat AI Agent Team — CLI Interface"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

from agent import run_agent, run_ceo
from config import AGENTS


def print_header():
    print("\n" + "=" * 60)
    print("  x/pat AI Agent Team")
    print("  Your startup workforce, powered by Claude")
    print("=" * 60)


def print_agents():
    print("\nAvailable agents:")
    for key, agent in AGENTS.items():
        print(f"  {key:12s} — {agent['name']}")
    print(f"  {'ceo':12s} — CEO Orchestrator (delegates to all agents)")
    print()


def main():
    print_header()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n[ERROR] ANTHROPIC_API_KEY not set.")
        print("Copy .env.example to .env and add your key:")
        print("  cp .env.example .env")
        sys.exit(1)

    # Direct agent mode from command line
    if len(sys.argv) >= 3:
        agent_name = sys.argv[1]
        prompt = " ".join(sys.argv[2:])

        if agent_name == "ceo":
            print(f"\nCEO orchestrating: {prompt}\n")
            result = run_ceo(prompt)
            print("\n" + "=" * 60)
            print("EXECUTIVE SUMMARY")
            print("=" * 60)
            print(result["synthesis"])
        elif agent_name in AGENTS:
            print(f"\n[{AGENTS[agent_name]['name']}] Processing...\n")
            result = run_agent(agent_name, prompt)
            print(result)
        else:
            print(f"Unknown agent: {agent_name}")
            print_agents()
        return

    # Interactive mode
    print_agents()
    print("Usage:")
    print("  Type '<agent> <prompt>' to talk to a specific agent")
    print("  Type 'ceo <goal>' to orchestrate across the full team")
    print("  Type 'quit' to exit\n")

    while True:
        try:
            user_input = input("x/pat> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        parts = user_input.split(" ", 1)
        agent_name = parts[0].lower()
        prompt = parts[1] if len(parts) > 1 else ""

        if not prompt:
            print("Please provide a prompt. Example: product Write user stories for the explore tab")
            continue

        if agent_name == "ceo":
            print(f"\nCEO orchestrating: {prompt}\n")
            result = run_ceo(prompt)
            print("\n" + "=" * 60)
            print("EXECUTIVE SUMMARY")
            print("=" * 60)
            print(result["synthesis"])
        elif agent_name in AGENTS:
            print(f"\n[{AGENTS[agent_name]['name']}] Processing...\n")
            result = run_agent(agent_name, prompt)
            print(result)
        else:
            print(f"Unknown agent: '{agent_name}'")
            print_agents()

        print()


if __name__ == "__main__":
    main()

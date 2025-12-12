"""CLI interface for running the Glosses4Learning agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent.main import run_agent_for_situation


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Glosses4Learning agent to fill a situation with content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run agent for a situation
  %(prog)s --situation "eng:cooking-together" --native eng --target deu

  # With custom data directory
  %(prog)s --situation "eng:shopping" --native eng --target spa --data-root /path/to/data

For more information, see the README.md
        """,
    )

    parser.add_argument(
        "--situation",
        required=True,
        help="Situation reference (format: 'lang:slug', e.g., 'eng:cooking-together')",
    )
    parser.add_argument(
        "--native",
        required=True,
        help="Native language code (ISO 639-3, e.g., 'eng', 'deu', 'spa')",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target language code (ISO 639-3, e.g., 'deu', 'arb', 'spa')",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        help="Maximum agent iterations (default: 50)",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        help="Data root directory (defaults to project data/)",
    )

    args = parser.parse_args()

    # Display banner
    print("\n" + "=" * 70)
    print("  GLOSSES4LEARNING AGENT")
    print("  Autonomous Language Learning Content Creation")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Situation:  {args.situation}")
    print(f"  Native:     {args.native}")
    print(f"  Target:     {args.target}")
    print(f"  Max Iterations: {args.max_iterations}")
    if args.data_root:
        print(f"  Data Root:  {args.data_root}")
    print()

    try:
        # Run agent
        result = run_agent_for_situation(
            situation_ref=args.situation,
            native_language=args.native,
            target_language=args.target,
            data_root=args.data_root,
            max_iterations=args.max_iterations,
        )

        # Display results
        if result["success"]:
            print("\n✓ Agent session completed successfully")
            print(f"\nSession ID: {result['session_id']}")
            print(f"Message: {result.get('message')}")

            # Show Flask command to view results
            print("\n" + "=" * 70)
            print("NEXT STEPS:")
            print("=" * 70)
            print("\n1. View results in Flask tree viewer:")
            print("   uv run flask --app src.flask.tree.show_tree run --debug --port 5010")
            print("\n2. Check session logs:")
            print(f"   cat agent/logs/agent_session_{result['session_id']}.log")
            print("\n3. Use TUI flows to manually add more content:")
            print("   uv run python src/tui/main.py")
            print()

            return 0
        else:
            print(f"\n✗ Agent session failed")
            print(f"Error: {result.get('error')}")
            return 1

    except KeyboardInterrupt:
        print("\n\n✗ Agent session interrupted by user")
        return 130
    except Exception as e:
        print(f"\n✗ Error running agent: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

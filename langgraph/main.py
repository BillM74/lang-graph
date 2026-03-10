"""CLI entrypoint for running SOMA LangGraph workflows."""

import argparse
import json

from langgraph.workflows import (
    build_feature_development_workflow,
    build_learning_workflow,
    build_metrics_workflow,
    build_performance_workflow,
)

WORKFLOWS = {
    "feature": build_feature_development_workflow,
    "metrics": build_metrics_workflow,
    "performance": build_performance_workflow,
    "learning": build_learning_workflow,
}


def main():
    parser = argparse.ArgumentParser(description="Run a SOMA LangGraph workflow")
    parser.add_argument("--workflow", choices=list(WORKFLOWS.keys()), required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", default="text", choices=["text", "json"])
    args = parser.parse_args()

    print(f"\nRunning '{args.workflow}' workflow...")
    print(f"Task: {args.task}\n")

    graph = WORKFLOWS[args.workflow]()
    result = graph.invoke({"task_description": args.task, "messages": []})

    if args.output == "json":
        output = {k: v for k, v in result.items() if k != "messages"}
        output["message_count"] = len(result.get("messages", []))
        print(json.dumps(output, indent=2))
    else:
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Artifacts: {result.get('artifacts', [])}")
        for msg in result.get("messages", []):
            print(
                f"\n{msg.content[:500]}"
                f"{'...' if len(msg.content) > 500 else ''}"
            )


if __name__ == "__main__":
    main()

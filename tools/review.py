
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from google import genai


def run_git(*args):
    """Run Git without invoking a shell."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Git command failed")

    return result.stdout


def collect_changes(base, head):
    """Collect the changed files and patch between two revisions."""
    changed_files = run_git(
        "diff", "--name-only", f"{base}...{head}"
    ).splitlines()

    diff = run_git(
        "diff", "--no-ext-diff", "--unified=30",
        f"{base}...{head}", "--", "*.cpp", "*.h"
    )

    return changed_files, diff


def ask_gemini(diff, changed_files):
    """Ask Gemini for structured, evidence-backed bug hypotheses."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    client = genai.Client(api_key=api_key)

    prompt = f"""
You are reviewing a C++ Git change.

Your task is to identify plausible bugs introduced by this change.
Do not report style preferences as bugs.

For each finding:
- Identify the relevant file and changed lines.
- Explain the defect using specific code evidence.
- State the preconditions needed to trigger it.
- Give a concrete input or execution sequence.
- State the expected and predicted actual behavior.
- Explain how the claim could be independently tested.

Do not claim a test was executed.
Do not invent specifications that are not supported by the code.
If there are no defensible findings, return an empty findings array.

Return JSON with this exact structure:
{{
  "summary": "short review summary",
  "findings": [
    {{
      "title": "short bug title",
      "file": "path to file",
      "evidence": "relevant code and reasoning",
      "preconditions": "conditions required",
      "failure_scenario": "concrete inputs or execution sequence",
      "expected_behavior": "expected result",
      "predicted_behavior": "predicted result",
      "validation_idea": "how to test the claim",
      "confidence": "low, medium, or high"
    }}
  ]
}}

Changed files:
{json.dumps(changed_files, indent=2)}

Git diff:
{diff[:30000]}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    text = response.text.strip()

    # Tolerate Markdown code fences if the model adds them.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
        else:
            raise RuntimeError("Malformed JSON code fence in response")

        if text.startswith("json"):
            text = text[4:].lstrip()

    data = json.loads(text)

    if not isinstance(data, dict) or not isinstance(
        data.get("findings"), list
    ):
        raise RuntimeError("Gemini response does not match the expected schema")

    return data


def main():
    parser = argparse.ArgumentParser(
        description="Review C++ changes with Gemini"
    )
    parser.add_argument("base", help="Base branch or commit")
    parser.add_argument("head", help="Feature branch or commit")
    args = parser.parse_args()

    try:
        # Ensure the current directory belongs to a Git repository.
        run_git("rev-parse", "--show-toplevel")

        changed_files, diff = collect_changes(args.base, args.head)

        if not changed_files:
            print("No changes found between the specified revisions.")
            return

        if not diff.strip():
            print("Changed files were found, but no C++ header/source diff was available.")
            return

        review = ask_gemini(diff, changed_files)

        # Never treat a model's confidence as experimental proof.
        for finding in review["findings"]:
            finding["validation_status"] = "unverified"

        report = {
            "base": args.base,
            "head": args.head,
            "changed_files": changed_files,
            "summary": review.get("summary", ""),
            "findings": review["findings"],
            "note": (
                "AI-generated findings are hypotheses. "
                "No independent reproducer has been executed by this tool."
            ),
        }

        output = Path("review-report.json")
        output.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        print(f"Review saved to {output.resolve()}")
        print(json.dumps(report, indent=2))

    except (
        RuntimeError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"Review failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

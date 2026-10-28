
# Evidence-Driven AI Code Reviewer

A learning project that reviews Git changes using an LLM
and produces specific, evidence-backed bug hypotheses.

## Components

- Git: retrieves the changes between revisions.
- Gemini: analyzes the diff and proposes possible defects.
- C++ tests: define expected behavior for the example project.
- Python: orchestrates the review pipeline.

## Current limitations

AI findings are hypotheses, not proof.
The first version does not automatically execute AI-generated tests.
Findings must be independently validated.

## Requirements

- Git
- Python 3
- A C++17 compiler
- A Gemini API key for AI reviews

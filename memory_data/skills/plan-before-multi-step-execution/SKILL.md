---
name: plan-before-multi-step-execution
description: "Use this skill before executing a sequence of 3 or more steps, especially when steps are irreversible, depend on each other, or could leave state in a broken intermediate condition. Decompose into ordered steps, flag irreversible actions for confirmation, and verify each step's output before proceeding to the next."
---

# Plan Before Multi-Step Execution

For complex tasks, plan first and execute second.

**Planning phase:**
1. Decompose the task into concrete, ordered steps.
2. Identify dependencies between steps.
3. Flag irreversible actions that need user confirmation.
4. Identify what can fail and what the recovery path is.

**Execution phase:**
- Follow the plan step by step; update it if you discover new information.
- After each step, verify the expected output before proceeding.
- If a step fails, re-evaluate the remaining plan — don't blindly continue.

**Anti-pattern:** Starting to execute before understanding the full scope of the task.

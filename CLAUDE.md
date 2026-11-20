# CLAUDE.md / AGENTS.md

Project: Parallel 2D Heat Diffusion with MPI over Tailscale (parallel programming course).
The course requires every LLM interaction to be recorded and submitted. The rules below are mandatory.

## Logging rules (required by the course)

For EVERY interaction in this repository, including ones whose output ends up unused:

1. Append one entry to `llm_log/LOG.md` using the template below. It must contain:
   - date and time (with timezone)
   - team member (take it from `git config user.name`; if it is empty, ask before doing anything else)
   - tool and model
   - the user's prompt, verbatim and complete
   - your full response, complete, not a summary
   - every file you created or modified, with line ranges
2. Never edit, reorder or delete existing entries in `llm_log/`. Only append.
3. Commit the log update in the same commit as the code changes it describes.
4. If an interaction changes no files, still log it and commit the log on its own.
5. Write the log entry before telling the user the task is done.

### Entry template

```
---
## YYYY-MM-DD HH:MM (timezone) | <team member>

- Tool: <tool name>
- Model: <model name and version>
- Files created or modified:
  - <path> (lines <start>-<end>)

### Prompt

<the user's prompt, verbatim>

### Response

<your full response>
```

## Folder layout

- `llm_log/LOG.md`: entries written by coding agents (this file's rules).
- `llm_log/chats/`: full exports of conversations held in chat interfaces, added by hand.
  File name: `YYYY-MM-DD_<member>_<tool>_<topic>.md`, with member, tool, model and date at the top.

## Project constraints

- C++17 or later, built with one command (CMake or Makefile).
- Compile with `-O2` or `-O3` and always `-ffp-contract=off`.
- Parallel output must be bit-for-bit identical to `--decomp serial`. Never change the order of
  floating point operations in the update rule.
- The team must be able to explain every line. Prefer simple, readable code and explain what you
  changed and why.
- Do not claim something works unless you ran it. Say what you ran and show the output.

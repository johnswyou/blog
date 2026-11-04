+++
date = '2026-03-02T00:00:00-05:00'
draft = true
title = 'Building Systems Around Language Models'
tags = ['ai', 'agents', 'software-engineering']
math = false
+++

A language model is a function. It takes a sequence of tokens as input and produces a probability distribution over the next token. Sample from that distribution repeatedly and you get text. This much is well understood.

What is less understood is how you build reliable, long-running systems around that function. That is what this post is about.

Anthropic and OpenAI have both published detailed engineering accounts of doing exactly this — building compilers, web applications, and internal developer tools using AI agents running autonomously for hours or days. Reading them together reveals a consistent set of patterns. The goal here is to explain those patterns precisely, from the ground up.


## The agent loop

When people talk about AI agents, they usually mean something specific: a program that runs a language model in a loop, allowing it to take actions between inference calls.

Here is what that loop looks like:

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  build prompt                                       │
│      │                                              │
│      ▼                                              │
│  run inference                                      │
│      │                                              │
│      ├── output is a tool call?                     │
│      │       execute it                             │
│      │       append result to context               │
│      │       go back to inference          ◄───┐    │
│      │                                         │    │
│      └── output is a message?                  │    │
│              deliver to user                   │    │
│              wait for next input               │    │
│              repeat ───────────────────────────┘    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

The model itself does nothing autonomous. It produces either a message or a tool call. If it produces a tool call — say, "run this shell command" or "write this file" — the surrounding program executes it and feeds the result back into the context. The model sees the result on the next inference call and decides what to do next.

This surrounding program — the code that manages the loop, executes tools, and handles the context — is called the **harness**.

The harness is not the model. It is everything around the model. Understanding the distinction between the two, and how they interact, is what makes it possible to build agents that do real work.


## What tool calling actually looks like

Tools are declared to the model as part of the prompt. A tool definition is a structured description: here is a function you can call, here are its parameters, here is what it does. The model does not execute tools directly — it emits a structured response indicating which tool it wants to call and with what arguments. The harness intercepts that response, executes the tool, and appends the result.

This means the model's ability to use tools depends entirely on which tools the harness exposes to it. A model connected to a shell tool can write and run code. A model connected to a web search tool can retrieve information. A model connected to nothing can only produce text.

The choice of tools, and how they are described, is a design decision that belongs to the harness. It is not a property of the model.


## The context management problem

Every inference call consumes context window space. The prompt grows with each tool call and result:

```
call 1:  [system prompt] [user input]
call 2:  [system prompt] [user input] [tool call] [result]
call 3:  [system prompt] [user input] [tool call] [result] [tool call] [result]
...
call N:  [system prompt] [user input] [history...] ← window fills
```

For short tasks this is fine. For long-running tasks — implementing a feature, debugging a complex system, writing a document — the context fills up before the work is done.

The standard mitigation is compaction: summarize the conversation history, replace it with the summary, and continue. This frees up context but loses information. A compacted context is lossy. The model's view of its own prior work becomes less precise after compaction, and errors from early in the session can become invisible.

Compaction addresses the within-session problem. It does not address the multi-session problem.


## The multi-session problem

Production agents do not run in a single continuous session. They run in containers that get torn down and recreated. They restart after failures. They pause and resume. Each new session starts with an empty context — the model has no memory of prior work unless the harness explicitly provides it.

This is the central engineering challenge of long-running agents: **the model is stateless, but the task has state.**

Anthropic's engineering team faced this directly while building a full-stack web application with Claude agents. Their solution is simple and worth understanding precisely because it mirrors how software engineers already manage state: use the file system.

Specifically, they use two types of agents:

```
┌─────────────────────────────────────────────────────┐
│  INITIALIZER  (runs once)                           │
│                                                     │
│  ├── init.sh              how to start the app      │
│  ├── feature_list.json    all features, all failing │
│  ├── claude-progress.txt  running log               │
│  └── initial git commit                             │
└──────────────────────┬──────────────────────────────┘
                       │  state persists in repo
                       ▼
┌─────────────────────────────────────────────────────┐
│  CODING AGENT  (runs every session)                 │
│                                                     │
│  1. read claude-progress.txt + git log              │
│  2. run init.sh — verify app is not broken          │
│  3. pick one failing feature from feature_list.json │
│  4. implement and test it                           │
│  5. mark it passing, commit, update progress        │
└─────────────────────────────────────────────────────┘
```

The feature list is JSON, not Markdown. This matters: a structured file with explicit boolean fields is harder for the model to accidentally corrupt than free-form text. Each feature has a clear pass/fail state. The agent is instructed to mark features passing, never to delete them.

The underlying principle: **the model can only act on what is in its context window. Everything that needs to persist across sessions must be written to a file.** This is not a limitation to work around — it is a design constraint to design for. Treat the repository as the agent's long-term memory.


## Parallelism and coordination

A single agent is sequential. For a project with many independent tasks — fixing twenty bugs, implementing twenty features — sequential execution is unnecessarily slow.

Anthropic demonstrated this by building a C compiler using sixteen parallel Claude instances. Each instance ran in its own Docker container, all working against a shared bare git repository. The question is how to coordinate them without a central orchestrator.

Their answer: git itself.

```
Agent A                    Agent B                 Shared repo
  │                          │                         │
  ├─ claim: fix_parser.txt   ├─ claim: fix_codegen.txt │
  │                          │                         │
  │  (git's atomic write     │  (different file →      │
  │   means only one agent   │   no conflict, both     │
  │   can claim a given      │   proceed in parallel)  │
  │   task)                  │                         │
  ├─ implement               ├─ implement              │
  ├─ pull + merge ───────────┼─────────────────────────┤
  └─ push                    └─ push                   │
```

Each agent writes a file to a `current_tasks/` directory to claim a task. If two agents try to claim the same task simultaneously, git's atomic write ensures only one succeeds — the other detects the conflict and picks a different task.

The outer loop driving each agent is minimal:

```bash
while true; do
    claude --dangerously-skip-permissions -p "$(cat AGENT_PROMPT.md)"
done
```

When one session ends, the next begins immediately. The agents orient themselves by reading shared state files — progress logs, the task list, git history. There is no orchestrator. The repository is the coordination mechanism.

Parallelism also enables specialization. Rather than every agent doing the same kind of work, you can run dedicated agents for deduplication, performance, documentation, and code quality simultaneously. Each contributes to the shared repository within its domain.

One observation from this experiment that deserves emphasis: the test suite is the primary communication channel between engineer and agent. A test defines what "correct" means in a form the agent can verify. If the tests are incomplete or wrong, the agent optimizes for the wrong objective — and it will do so very effectively. Most of the engineering effort in a successful agentic project goes into the environment: tests, feedback mechanisms, state structure. Not the prompts.


## Tool efficiency at scale

As agents are connected to more systems — file storage, databases, APIs, communication tools — the number of available tools grows. Tool definitions are included in the context on every inference call. At scale, this becomes expensive: an agent connected to hundreds of tools might consume a significant fraction of its context window on tool definitions before it processes a single token of the actual task.

There is a second cost. When a tool returns a large result — a long document, a spreadsheet, a transcript — that result enters the context. If the agent then needs to pass that result to another tool, it narrates the full content again. A pipeline step that processes a large document can double the token cost.

Anthropic addressed both problems by changing how tools are exposed to the model. Instead of loading all tool definitions upfront and having the model call tools directly, they expose tools as code files on a filesystem. The model discovers and reads tool definitions on demand, then writes code to call them:

```
─── before (direct tool calls) ──────────────────────────
context load:   all tool definitions        ~150K tokens
model calls:    gdrive.getDocument(id)
result:         full transcript             +50K tokens
model calls:    salesforce.update(notes)
result written: transcript again            +50K tokens
total:          ~250K tokens

─── after (code execution) ───────────────────────────────
model runs:     ls ./servers/              minimal
model reads:    getDocument.ts             one file
model writes:
    const doc = await gdrive.getDocument(id)
    await salesforce.update({notes: doc.content})
code executes in sandbox — transcript never enters context
total:          ~2K tokens
```

The efficiency gain comes from two things. First, the model reads only the tool definitions it actually needs, on demand. Second, large intermediate values flow through the execution environment rather than through the model's context. The model writes the logic; the sandbox handles the data.

This pattern also enables filtering before the model sees any data. A ten-thousand-row spreadsheet never needs to enter context — the agent writes code to filter it first, then surfaces only the relevant rows.


## Knowledge management at scale

OpenAI's engineering team spent five months building a production software product with zero manually-written code — roughly a million lines across application logic, tests, CI configuration, and documentation, driven by a small team using Codex. Their hardest-earned lesson was not about model capability. It was about how to structure knowledge so agents can find and use it.

Their first attempt was a comprehensive `AGENTS.md` — a single file describing the codebase, conventions, and constraints. It failed predictably. A large instruction file crowds out the actual task in the context window. When everything is marked as important, the agent has no basis for prioritizing. The file rots as the codebase evolves, and there is no mechanism to detect or fix staleness.

Their solution treats `AGENTS.md` as a table of contents, not an encyclopedia:

```
AGENTS.md  (~100 lines)
│  pointers to sources of truth, not the truth itself
│
├── docs/architecture.md    domain and layer map
├── docs/design/            indexed design decisions
├── docs/quality.md         grades per domain, gap tracking
└── docs/plans/             active execution plans
```

Each document is scoped and short. The agent reads the map first, then loads only what it needs for the current task. A background "doc-gardening" agent runs on a regular schedule, scanning for stale documentation and opening fix-up pull requests. Linters validate cross-links and structure.

The deeper principle here: from the agent's perspective, information that is not in its context window does not exist. A decision made in a Slack thread, a pattern that "everyone knows," an architectural preference that lives in someone's head — none of it is available to the agent. Everything that should inform the agent's behavior must be written down, versioned, and findable.

This discipline turns out to be good for human engineers as well as agents. It forces explicit documentation of the kind of implicit knowledge that usually lives only in the team's collective memory.


## Architectural constraints as coordination mechanism

OpenAI's team also found that strict architectural constraints are essential in agent-generated codebases, for a reason specific to how agents work: they replicate existing patterns. When the codebase has good patterns, this is a feature. When it has bad patterns, it is a liability — agents will reproduce and spread them.

Their solution was to encode architectural rules mechanically. Within each business domain, code could only depend "forward" through a fixed sequence of layers. Cross-cutting concerns entered through a single explicit interface. These rules were enforced by custom linters — themselves written by Codex — with error messages that included remediation instructions the agent could act on directly.

The same principle applied to technical debt. Rather than periodic manual cleanup, they ran background agents on a regular schedule to scan for deviations from established patterns, update quality grades, and open targeted refactoring pull requests. Technical debt is addressed continuously and automatically rather than accumulating until it becomes painful.

In a human-written codebase, this level of structural enforcement might feel rigid. In an agent-generated codebase, it is what keeps the system coherent over time.


## Putting it together

The model and the harness are both necessary. A weak model produces low-quality outputs regardless of how well it is scaffolded. A weak harness fails to translate model capability into reliable work — it loses state across sessions, fails to coordinate parallel agents, exposes tools inefficiently, and lets the knowledge base rot.

What makes this moment interesting is that the model side has advanced rapidly and visibly, while the harness side has been developed mostly in private. The patterns described here — state management across sessions, git-based coordination, code-execution tool access, knowledge structured for progressive disclosure, mechanical enforcement of architectural constraints — are recent and not yet widely known. They are what the current frontier looks like, past the model weights themselves.

The practical implication: if you are building with language models today, understanding these patterns is as important as understanding the models. The ceiling is set by model capability. How close you get to it is an engineering question.


*This post synthesizes engineering accounts from Anthropic and OpenAI: [Building a C compiler with parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler), [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp), [Harness engineering](https://openai.com/index/harness-engineering/), [Unlocking the Codex harness](https://openai.com/index/unlocking-the-codex-harness/), and [Unrolling the Codex agent loop](https://openai.com/index/unrolling-the-codex-agent-loop/).*

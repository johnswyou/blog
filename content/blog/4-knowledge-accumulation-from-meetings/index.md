+++
date = '2026-10-24T12:45:00-04:00'
draft = false
title = 'My workflow for knowledge accumulation (from meetings)'
categories = ['AI']
+++

Humans can only store so much information from a physical meeting. Things they don't understand will go over their heads. To maximally store the information from a meeting (where expert knowledge is often disseminated), I use the following workflow:

1. Record audio of meeting
2. Transcribe the audio into text. Expect transcription errors (acronyms, company names, abbreviations, internal project names, mispronunciation, etc.)
3. Provide agent harness (e.g., Claude Code, Codex) with access to internal data sources and documentation. This can be done by giving the agent access to:
   - CLI tooling (such as AWS CLI, gh CLI)
   - Documentation (such as the Atlassian MCP for access to Confluence, the Notion MCP for access to Notion, context7 plugin)
4. Ask the agent harness to fix transcription errors. The agent will go off and research/explore and figure out how to correctly fix transcription errors now that it is able to access company context.
5. With the corrected transcript as raw data, ask the agent to synthesize the corrected transcript into a well structured and clearly written document that pulls out the key insights from the meeting.
6. File this final document into a "library" (directory). The library directory should have two subdirectories: raw and synthesis. The raw subdirectory stores the corrected transcription text files and the synthesis subdirectory stores the structured syntheses (i.e., the output of step 5 above). With time this library will grow and become a wealth of expertise that stores the "tribal knowledge" of your team/org.

The above workflow is clearly influenced by Andrej Karpathy's "[LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)" idea but is less general (more specific to capturing knowledge from meetings) and minimalist by design.

As your library grows, your agents should be able to provide better responses over time as they access more high quality context about your team/org.

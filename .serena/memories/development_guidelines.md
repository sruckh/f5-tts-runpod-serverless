# Development Guidelines

## File Editing Preferences
- **Use Serena tools for all file editing operations**
- Prefer `mcp__serena__replace_regex` over Edit/MultiEdit tools
- Use Serena's symbolic editing tools when appropriate
- Only use Claude Code native editing tools when Serena tools are insufficient

## User Preferences
- User prefers Serena tooling for file modifications
- Established on 2025-08-02 during Dockerfile dependency update

## Tool Selection Priority
1. Serena symbolic tools (for symbol-level changes)
2. Serena regex tools (for targeted replacements) 
3. Claude Code tools (as fallback only)
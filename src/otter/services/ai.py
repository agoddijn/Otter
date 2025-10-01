"""AI-powered analysis service.

This service provides AI-powered code analysis features for context compression
and quick sanity checks. All features are stateless, single-shot LLM requests
designed to help agents reduce context usage.
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional, Tuple

from ..llm import LLMClient, LLMConfig, ModelTier
from ..models.responses import (
    ChangeSummary,
    CodeSummary,
    ErrorExplanation,
    ReviewResult,
)

logger = logging.getLogger(__name__)


class AIService:
    """AI-powered code analysis service.
    
    Provides context compression and quick analysis features:
    - summarize_code: Compress large files into brief summaries
    - summarize_changes: Summarize diffs/changes
    - quick_review: Fast code review for sanity checks  
    - explain_error: Interpret cryptic error messages
    - explain_symbol: Semantic explanation using LSP + references
    
    All methods are stateless, one-shot LLM requests optimized for:
    - Fast response times
    - Context compression (not deep analysis)
    - Helping agents avoid bloating their own context
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None, nvim_client=None, project_path: Optional[str] = None):
        """Initialize AI service.
        
        Args:
            llm_client: LLM client. If None, creates from environment.
            nvim_client: Optional Neovim client for LSP integration.
            project_path: Project root path for resolving relative paths.
        """
        if llm_client is None:
            config = LLMConfig.from_env()
            llm_client = LLMClient(config)
        
        self.llm = llm_client
        self.nvim_client = nvim_client  # For LSP-powered explanations
        self.project_path = project_path or str(Path.cwd())
    
    async def summarize_code(
        self,
        file: str,
        detail_level: Literal["brief", "detailed"] = "brief",
    ) -> CodeSummary:
        """Summarize code content.
        
        Compresses large code files into concise summaries. Use this when:
        - File is > 200 lines and you need just the gist
        - Want to understand what code does without reading it all
        - Need to save context window space
        
        Agent just provides file path - we handle reading it.
        
        Args:
            file: File path to summarize (we read it for you)
            detail_level: "brief" (1-3 sentences) or "detailed" (with key components)
        
        Returns:
            CodeSummary with summary text and optional metadata
        
        Example:
            >>> summary = await ai.summarize_code(
            ...     "payment_processor.py",
            ...     detail_level="brief"
            ... )
            >>> print(summary.summary)
            "Payment processing service integrating Stripe and PayPal with 
             retry logic and webhook handling."
        """
        # Resolve file path using centralized utilities
        from pathlib import Path
        from ..utils.path import resolve_workspace_path
        
        file_path = resolve_workspace_path(file, self.project_path)
        
        # Read the file content
        try:
            content = file_path.read_text()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file}")
        except Exception as e:
            raise RuntimeError(f"Failed to read {file}: {e}")
        # Determine model tier and max tokens based on detail level
        if detail_level == "brief":
            tier = ModelTier.CAPABLE
            max_tokens = 2000  # High limit to avoid truncation
            instruction = "Summarize this code in EXACTLY 1-3 sentences. Be concise."
        else:
            # Use advanced model for detailed analysis
            tier = ModelTier.ADVANCED
            max_tokens = 2000  # High limit to avoid truncation
            instruction = (
                "Provide a structured summary:\n"
                "1. Purpose: 2-3 sentences\n"
                "2. Key components: 3-5 items, one line each\n"
                "3. Complexity: One word (low/medium/high) + 1 sentence why"
            )
        
        # Build prompt
        prompt = f"""{instruction}

File: {file}

```
{content[:5000]}  # Limit to avoid token limits
{"..." if len(content) > 5000 else ""}
```

Respond in a clear, technical style. Focus on what the code does, not how it's structured."""
        
        # Get LLM response - trust the model to follow the prompt structure
        summary = await self.llm.complete(
            prompt=prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.3,  # Low temperature for factual summarization
        )
        
        return CodeSummary(
            file=file,
            summary=summary,
            detail_level=detail_level,
        )
    
    async def summarize_changes(
        self,
        file: str,
        git_ref: str = "HEAD~1",
    ) -> ChangeSummary:
        """Summarize code changes (diff).
        
        Compresses diffs into human-readable summaries. Use this when:
        - Reviewing changes without reading full diffs
        - Want to understand impact of changes quickly
        - Need to identify breaking changes
        
        Agent just provides file path and git ref - we handle the diff.
        
        Args:
            file: File path (absolute or relative to project root)
            git_ref: Git reference to compare against (default: HEAD~1, i.e., previous commit)
                    Can be: "HEAD~1", "main", commit hash, etc.
        
        Returns:
            ChangeSummary with summary, change types, and impact analysis
        
        Example:
            >>> summary = await ai.summarize_changes(
            ...     "auth.py",
            ...     git_ref="main"  # Compare current file vs main branch
            ... )
            >>> print(summary.summary)
            "Added JWT authentication middleware. Refactored error handling 
             to use custom exceptions."
            >>> print(summary.breaking_changes)
            ["Removed deprecated /v1/users endpoint"]
        """
        # Resolve file path using centralized utilities
        from pathlib import Path
        import subprocess
        from ..utils.path import resolve_workspace_path
        
        file_path = resolve_workspace_path(file, self.project_path)
        
        # Get current content
        try:
            new_content = file_path.read_text()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file}")
        
        # Get git repository root to make path relative for git command
        try:
            git_root_result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                cwd=file_path.parent
            )
            git_root = Path(git_root_result.stdout.strip())
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Not in a git repository: {file_path.parent}")
        
        # Make file path relative to git root for git show command
        try:
            git_relative_path = file_path.relative_to(git_root)
        except ValueError:
            raise RuntimeError(f"File {file_path} is not in git repository {git_root}")
        
        # Get old content from git using relative path
        try:
            result = subprocess.run(
                ["git", "show", f"{git_ref}:{git_relative_path}"],
                capture_output=True,
                text=True,
                check=True,
                cwd=git_root
            )
            old_content = result.stdout
        except subprocess.CalledProcessError as e:
            # File might not exist in that ref, or git error
            raise RuntimeError(
                f"Failed to get {file} at {git_ref}: {e.stderr or 'File may not exist in that ref'}"
            )
        # Use capable model for change analysis
        tier = ModelTier.CAPABLE
        max_tokens = 2000  # High limit to avoid truncation
        
        # Build prompt
        prompt = f"""Summarize the changes to this file:

File: {file}

OLD VERSION:
```
{old_content[:2500]}
{"..." if len(old_content) > 2500 else ""}
```

NEW VERSION:
```
{new_content[:2500]}
{"..." if len(new_content) > 2500 else ""}
```

Provide exactly these sections:
1. Summary: What changed and why (2-3 sentences)
2. Change types: Comma-separated (e.g., "refactor, bugfix, feature")
3. Breaking changes: List or "None"
4. Affected functionality: 1 sentence

Be concise and technical."""
        
        # Get LLM response - trust the model to follow the prompt structure
        summary = await self.llm.complete(
            prompt=prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        
        return ChangeSummary(
            file=file,
            summary=summary,
            git_ref=git_ref,
        )
    
    async def quick_review(
        self,
        file: str,
        focus: Optional[List[str]] = None,
    ) -> ReviewResult:
        """Quick code review for sanity checks.
        
        Fast, single-shot review focusing on obvious issues. Use this when:
        - Generated code and want a quick sanity check
        - Need a second opinion before committing
        - Want to catch obvious bugs/security issues
        
        NOT a replacement for proper code review or testing.
        Agent just provides file path - we read it for you.
        
        Args:
            file: File path to review (we read it for you)
            focus: Optional focus areas (e.g., ["security", "performance", "bugs"])
        
        Returns:
            ReviewResult with issues found and overall assessment
        
        Example:
            >>> review = await ai.quick_review(
            ...     "auth.py",
            ...     focus=["security"]
            ... )
            >>> for issue in review.issues:
            ...     print(f"{issue.severity}: {issue.message}")
            "critical: Password stored in plaintext (line 45)"
        """
        # Resolve file path using centralized utilities
        from pathlib import Path
        from ..utils.path import resolve_workspace_path
        
        file_path = resolve_workspace_path(file, self.project_path)
        
        # Read the file content
        try:
            content = file_path.read_text()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file}")
        except Exception as e:
            raise RuntimeError(f"Failed to read {file}: {e}")
        # Use capable model for code review
        tier = ModelTier.CAPABLE
        max_tokens = 2000  # High limit to avoid truncation
        
        # Build focus areas
        focus_areas = focus if focus else ["security", "bugs", "performance"]
        focus_str = ", ".join(focus_areas)
        
        # Build prompt - clear format but trust the model to follow it
        prompt = f"""Quick code review focusing on: {focus_str}

File: {file}

```
{content[:4000]}
{"..." if len(content) > 4000 else ""}
```

Review the code and provide:
1. Overall assessment (1-2 sentences)
2. Issues found (if any), formatted as:
   - CRITICAL: [description] (line XX) - for security/correctness issues
   - WARNING: [description] (line XX) - for bugs or bad practices
   - SUGGESTION: [description] (line XX) - for improvements

Keep it concise. Max 5 issues. If code looks good, just say so."""
        
        # Get LLM response - trust the model to structure it properly
        review = await self.llm.complete(
            prompt=prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.2,  # Low temperature for consistent reviews
        )
        
        return ReviewResult(
            file=file,
            review=review,
            focus_areas=focus_areas,
        )
    
    async def explain_error(
        self,
        error_message: str,
        context_file: Optional[str] = None,
        context_content: Optional[str] = None,
        context_lines: Optional[Tuple[int, int]] = None,
    ) -> ErrorExplanation:
        """Explain a cryptic error message.
        
        Interprets error messages and provides actionable fixes.
        
        Args:
            error_message: The error message/traceback
            context_file: Optional file where error occurred
            context_content: Optional code content around error
            context_lines: Optional (start, end) line range
        
        Returns:
            ErrorExplanation with explanation, causes, and fixes
        """
        # Use capable model for error explanation
        tier = ModelTier.CAPABLE
        max_tokens = 2000  # High limit to avoid truncation
        
        # Build prompt
        prompt = f"""Explain this error message clearly and completely.

Error:
```
{error_message}
```
"""
        
        if context_file and context_content:
            prompt += f"""
Context ({context_file}):
```
{context_content[:1000]}
{"..." if len(context_content) > 1000 else ""}
```
"""
        
        prompt += """
Explain in a clear, structured way:
1. What the error means (1-2 sentences)
2. Likely causes (2-3 bullet points)
3. How to fix it (2-3 actionable steps)

Be practical and concise."""
        
        # Get LLM response - trust the model to structure it properly
        explanation = await self.llm.complete(
            prompt=prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        
        return ErrorExplanation(
            explanation=explanation,
            error_message=error_message,
            context_file=context_file,
            context_line=context_lines[0] if context_lines else None,
        )
    
    async def explain_symbol(
        self,
        file: str,
        line: int,
        character: int,
        include_references: bool = True,
    ) -> CodeSummary:
        """Explain a symbol using LSP + LLM.
        
        Uses LSP to find symbol definition and references, then LLM to explain
        what the symbol is, what it does, and how it is used in the codebase.
        This provides semantic understanding beyond just reading code.
        
        Args:
            file: File path
            line: Line number (0-indexed)
            character: Character position (0-indexed)
            include_references: Whether to include usage examples from references
        
        Returns:
            CodeSummary with comprehensive explanation
        
        Example:
            Get explanation for a symbol at a specific position.
        """
        if not self.nvim_client:
            raise RuntimeError("explain_symbol requires nvim_client for LSP integration")
        
        # 1. Get hover info (definition) - use lsp_hover directly
        lsp_hover_result = await self.nvim_client.lsp_hover(file, line, character)
        
        if not lsp_hover_result:
            raise RuntimeError(f"No symbol found at {file}:{line}:{character}")
        
        # Extract hover text
        hover_contents = lsp_hover_result.get("contents", {})
        if isinstance(hover_contents, str):
            hover_info = hover_contents
        elif isinstance(hover_contents, dict):
            hover_info = hover_contents.get("value", str(hover_contents))
        elif isinstance(hover_contents, list):
            parts = []
            for item in hover_contents:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("value", ""))
            hover_info = "\n".join(parts)
        else:
            hover_info = str(hover_contents)
        
        # 2. Optionally get references
        references_context = ""
        if include_references:
            try:
                # Use lsp_references directly from nvim_client
                lsp_references = await self.nvim_client.lsp_references(file, line, character)
                
                if lsp_references:
                    # Get a few reference snippets (limit to avoid context bloat)
                    reference_snippets = []
                    for ref_location in lsp_references[:5]:  # Max 5 references
                        try:
                            from pathlib import Path
                            from urllib.parse import unquote, urlparse
                            
                            # Parse LSP location
                            uri = ref_location.get("uri") or ref_location.get("targetUri")
                            range_data = ref_location.get("range") or ref_location.get("targetRange")
                            
                            if not uri or not range_data:
                                continue
                            
                            # Convert URI to file path
                            if uri.startswith("file://"):
                                parsed = urlparse(uri)
                                ref_file = unquote(parsed.path)
                            else:
                                ref_file = uri
                            
                            ref_line = range_data["start"]["line"] + 1  # Convert to 1-indexed
                            
                            # Read file and get context
                            ref_content = Path(ref_file).read_text().split("\n")
                            # Get 3 lines of context around reference
                            start = max(0, ref_line - 2)
                            end = min(len(ref_content), ref_line + 1)
                            snippet = "\n".join(ref_content[start:end])
                            reference_snippets.append(
                                f"# {ref_file}:{ref_line}\n{snippet}"
                            )
                        except Exception:
                            continue
                    
                    if reference_snippets:
                        references_context = "\n\nUsage examples:\n" + "\n\n".join(reference_snippets)
                        references_context += f"\n\n(Found {len(lsp_references)} total references)"
            except Exception as e:
                logger.warning(f"Failed to get references for symbol explanation: {e}")
        
        # 3. Build prompt
        prompt = f"""Explain this code symbol:

Definition:
{hover_info}
{references_context}

Provide:
1. What it is: 1 sentence (function/class/variable/etc.)
2. What it does: 2-3 sentences
3. How it's used: 1-2 sentences
4. Patterns/conventions: 1 sentence (if applicable)

Total: 4-6 sentences."""
        
        # 4. Get LLM explanation - use advanced model for semantic understanding
        response = await self.llm.complete(
            prompt=prompt,
            tier=ModelTier.ADVANCED,
            max_tokens=2000,  # High limit to avoid truncation
            temperature=0.3,
        )
        
        return CodeSummary(
            file=file,
            summary=response,
            detail_level="detailed",
            key_components=None,
            complexity=None,
        )


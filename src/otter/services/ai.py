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
    ReviewIssue,
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
    
    def __init__(self, llm_client: Optional[LLMClient] = None, nvim_client=None):
        """Initialize AI service.
        
        Args:
            llm_client: LLM client. If None, creates from environment.
            nvim_client: Optional Neovim client for LSP integration.
        """
        if llm_client is None:
            config = LLMConfig.from_env()
            llm_client = LLMClient(config)
        
        self.llm = llm_client
        self.nvim_client = nvim_client  # For LSP-powered explanations
    
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
        # Read the file content
        from pathlib import Path
        try:
            content = Path(file).read_text()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file}")
        except Exception as e:
            raise RuntimeError(f"Failed to read {file}: {e}")
        # Determine model tier and max tokens based on detail level
        if detail_level == "brief":
            tier = ModelTier.FAST
            max_tokens = 150
            instruction = "Summarize this code in 1-3 clear sentences."
        else:
            tier = ModelTier.CAPABLE
            max_tokens = 500
            instruction = (
                "Provide a detailed summary of this code including:\n"
                "1. Main purpose (2-3 sentences)\n"
                "2. Key components (classes, functions, main logic)\n"
                "3. Overall complexity assessment (low/medium/high)"
            )
        
        # Build prompt
        prompt = f"""{instruction}

File: {file}

```
{content[:5000]}  # Limit to avoid token limits
{"..." if len(content) > 5000 else ""}
```

Respond in a clear, technical style. Focus on what the code does, not how it's structured."""
        
        # Get LLM response
        response = await self.llm.complete(
            prompt=prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.3,  # Low temperature for factual summarization
        )
        
        # Parse response for detailed summaries
        key_components: Optional[List[str]] = None
        complexity: Optional[Literal["low", "medium", "high"]] = None
        
        if detail_level == "detailed":
            # Try to extract structured data from response
            lines = response.strip().split("\n")
            if any("low" in line.lower() or "medium" in line.lower() or "high" in line.lower() for line in lines):
                for line in lines:
                    if "complexity" in line.lower():
                        if "low" in line.lower():
                            complexity = "low"
                        elif "high" in line.lower():
                            complexity = "high"
                        else:
                            complexity = "medium"
        
        return CodeSummary(
            file=file,
            summary=response.strip(),
            detail_level=detail_level,
            key_components=key_components,
            complexity=complexity,
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
            file: File path
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
        # Get current content
        from pathlib import Path
        try:
            new_content = Path(file).read_text()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file}")
        
        # Get old content from git
        import subprocess
        try:
            result = subprocess.run(
                ["git", "show", f"{git_ref}:{file}"],
                capture_output=True,
                text=True,
                check=True
            )
            old_content = result.stdout
        except subprocess.CalledProcessError as e:
            # File might not exist in that ref, or git error
            raise RuntimeError(
                f"Failed to get {file} at {git_ref}: {e.stderr or 'File may not exist in that ref'}"
            )
        # Use capable model for change analysis
        tier = ModelTier.CAPABLE
        max_tokens = 400
        
        # Build prompt
        prompt = f"""Summarize the changes made to this code file.

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

Provide:
1. Summary: What changed and why (2-3 sentences)
2. Change types: List types (e.g., "refactor", "bugfix", "feature", "breaking change")
3. Breaking changes: List any breaking changes (or "none")
4. Affected functionality: What functionality is impacted

Be concise and technical. Focus on impact, not implementation details."""
        
        # Get LLM response
        response = await self.llm.complete(
            prompt=prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        
        # Parse response (simple extraction for now)
        lines = response.strip().split("\n")
        summary_text = response.split("Change types:")[0].strip() if "Change types:" in response else response.strip()
        
        # Extract change types
        changes_type: List[str] = []
        if "refactor" in response.lower():
            changes_type.append("refactor")
        if "bugfix" in response.lower() or "bug fix" in response.lower():
            changes_type.append("bugfix")
        if "feature" in response.lower():
            changes_type.append("feature")
        if "breaking" in response.lower():
            changes_type.append("breaking change")
        
        # Extract breaking changes
        breaking_changes: List[str] = []
        if "breaking" in response.lower() and "none" not in response.lower():
            # Try to extract breaking changes section
            for i, line in enumerate(lines):
                if "breaking" in line.lower():
                    # Next few lines might have details
                    for j in range(i+1, min(i+4, len(lines))):
                        if lines[j].strip() and not lines[j].strip().startswith(("Summary", "Change", "Affected")):
                            breaking_changes.append(lines[j].strip())
        
        return ChangeSummary(
            file=file,
            summary=summary_text[:500],  # Limit summary length
            changes_type=changes_type if changes_type else ["unknown"],
            breaking_changes=breaking_changes,
            affected_functionality=[],  # TODO: Extract from response
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
        # Read the file content
        from pathlib import Path
        try:
            content = Path(file).read_text()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file}")
        except Exception as e:
            raise RuntimeError(f"Failed to read {file}: {e}")
        # Use capable model for code review
        tier = ModelTier.CAPABLE
        max_tokens = 600
        
        # Build focus areas
        focus_areas = focus if focus else ["security", "bugs", "performance"]
        focus_str = ", ".join(focus_areas)
        
        # Build prompt
        prompt = f"""Quick code review focusing on: {focus_str}

File: {file}

```
{content[:4000]}
{"..." if len(content) > 4000 else ""}
```

Find obvious issues ONLY. For each issue provide:
- Severity: critical/warning/suggestion
- Category: {focus_str}
- Line number (if applicable)
- Message: What's wrong
- Suggestion: How to fix (brief)

Be concise. Only report clear issues, not style preferences.
If code looks good, say so."""
        
        # Get LLM response
        response = await self.llm.complete(
            prompt=prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.2,  # Low temperature for consistent reviews
        )
        
        # Parse response to extract issues
        issues: List[ReviewIssue] = []
        
        # Simple parsing (look for severity keywords)
        lines = response.strip().split("\n")
        current_issue: Optional[dict] = None
        
        for line in lines:
            line_lower = line.lower()
            
            # Check for severity markers
            if "critical:" in line_lower or "warning:" in line_lower or "suggestion:" in line_lower:
                if current_issue:
                    issues.append(ReviewIssue(**current_issue))
                
                # Start new issue
                if "critical:" in line_lower:
                    severity = "critical"
                elif "warning:" in line_lower:
                    severity = "warning"
                else:
                    severity = "suggestion"
                
                message = line.split(":", 1)[1].strip() if ":" in line else line.strip()
                
                # Extract line number if present
                line_num = None
                if "line" in message.lower():
                    import re
                    match = re.search(r'line\s+(\d+)', message.lower())
                    if match:
                        line_num = int(match.group(1))
                
                # Determine category from focus areas
                category = "general"
                for focus_area in focus_areas:
                    if focus_area.lower() in message.lower():
                        category = focus_area
                        break
                
                current_issue = {
                    "severity": severity,
                    "category": category,
                    "line": line_num,
                    "message": message,
                    "suggestion": None,
                }
            elif current_issue and ("fix:" in line_lower or "suggestion:" in line_lower):
                current_issue["suggestion"] = line.split(":", 1)[1].strip() if ":" in line else line.strip()
        
        # Add last issue
        if current_issue:
            issues.append(ReviewIssue(**current_issue))
        
        # Extract overall assessment
        overall = "No critical issues found."
        if "looks good" in response.lower() or "no issues" in response.lower():
            overall = "Code looks good - no obvious issues found."
        elif issues:
            critical_count = sum(1 for i in issues if i.severity == "critical")
            warning_count = sum(1 for i in issues if i.severity == "warning")
            overall = f"Found {critical_count} critical issue(s) and {warning_count} warning(s)."
        
        return ReviewResult(
            file=file,
            overall_assessment=overall,
            issues=issues,
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
        
        Interprets error messages and provides actionable fixes. Use this when:
        - Error message is cryptic or unclear
        - Want to understand root cause quickly
        - Need suggestions for fixing the error
        
        Args:
            error_message: The error message/traceback
            context_file: Optional file where error occurred
            context_content: Optional code content around error
            context_lines: Optional (start, end) line range
        
        Returns:
            ErrorExplanation with explanation, causes, and fixes
        
        Example:
            >>> explanation = await ai.explain_error(
            ...     "TypeError: 'NoneType' object is not subscriptable",
            ...     context_file="app.py",
            ...     context_content=code_snippet
            ... )
            >>> print(explanation.explanation)
            "You're trying to access an index on a None value."
            >>> print(explanation.suggested_fixes[0])
            "Check if variable is not None before accessing"
        """
        # Use fast model for error explanation
        tier = ModelTier.FAST
        max_tokens = 300
        
        # Build prompt
        prompt = f"""Explain this error message in simple terms.

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
Provide:
1. What the error means (1-2 sentences)
2. Likely causes (2-3 bullet points)
3. How to fix it (2-3 bullet points)

Be practical and actionable."""
        
        # Get LLM response
        response = await self.llm.complete(
            prompt=prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        
        # Parse response
        lines = response.strip().split("\n")
        
        # Extract error type from error message
        error_type = error_message.split(":")[0].strip() if ":" in error_message else "Error"
        
        # Extract explanation (first few lines)
        explanation = response.split("Likely causes")[0].strip() if "Likely causes" in response else response.split("\n\n")[0].strip()
        
        # Extract causes and fixes
        likely_causes = []
        suggested_fixes = []
        
        in_causes = False
        in_fixes = False
        
        for line in lines:
            line_stripped = line.strip()
            
            if "likely cause" in line.lower() or "causes:" in line.lower():
                in_causes = True
                in_fixes = False
                continue
            elif "fix" in line.lower() or "solution" in line.lower():
                in_fixes = True
                in_causes = False
                continue
            
            if in_causes and line_stripped and (line_stripped.startswith(("-", "•", "*")) or line_stripped[0].isdigit()):
                likely_causes.append(line_stripped.lstrip("-•*0123456789. "))
            elif in_fixes and line_stripped and (line_stripped.startswith(("-", "•", "*")) or line_stripped[0].isdigit()):
                suggested_fixes.append(line_stripped.lstrip("-•*0123456789. "))
        
        # Fallback if parsing didn't work
        if not likely_causes:
            likely_causes = ["See explanation above"]
        if not suggested_fixes:
            suggested_fixes = ["See explanation above"]
        
        return ErrorExplanation(
            error_type=error_type,
            explanation=explanation[:500],
            likely_causes=likely_causes[:5],
            suggested_fixes=suggested_fixes[:5],
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
        
        Uses LSP to find symbol definition and references, then LLM to explain:
        - What the symbol is/does
        - Where and how it's used
        - Its role in the codebase
        
        This is smarter than just reading code - it provides semantic understanding.
        
        Args:
            file: File path
            line: Line number (0-indexed)
            character: Character position (0-indexed)
            include_references: Whether to include usage examples from references
        
        Returns:
            CodeSummary with comprehensive explanation
        
        Example:
            >>> explanation = await ai.explain_symbol(
            ...     "server.py",
            ...     line=45,
            ...     character=10,
            ...     include_references=True
            ... )
            >>> print(explanation.summary)
            "handle_request() is the main request handler middleware.
             Called by 15 routes in the API layer. Handles authentication,
             logging, and error wrapping."
        """
        if not self.nvim_client:
            raise RuntimeError("explain_symbol requires nvim_client for LSP integration")
        
        # 1. Get hover info (definition)
        hover_info = await self.nvim_client.get_hover_info(file, line, character)
        
        # 2. Optionally get references
        references_context = ""
        if include_references:
            try:
                references = await self.nvim_client.find_references(file, line, character)
                
                # Get a few reference snippets (limit to avoid context bloat)
                reference_snippets = []
                for ref in references[:5]:  # Max 5 references
                    try:
                        from pathlib import Path
                        ref_content = Path(ref.file).read_text().split("\n")
                        # Get 3 lines of context around reference
                        start = max(0, ref.line - 1)
                        end = min(len(ref_content), ref.line + 2)
                        snippet = "\n".join(ref_content[start:end])
                        reference_snippets.append(
                            f"# {ref.file}:{ref.line}\n{snippet}"
                        )
                    except Exception:
                        continue
                
                if reference_snippets:
                    references_context = "\n\nUsage examples:\n" + "\n\n".join(reference_snippets)
                    references_context += f"\n\n(Found {len(references)} total references)"
            except Exception as e:
                logger.warning(f"Failed to get references for symbol explanation: {e}")
        
        # 3. Build prompt
        prompt = f"""Explain this code symbol in detail:

Definition:
{hover_info}
{references_context}

Provide:
1. What this symbol is (function/class/variable/etc.)
2. What it does / its purpose
3. How and where it's used in the codebase
4. Any important patterns or conventions

Be concise but comprehensive (3-5 sentences)."""
        
        # 4. Get LLM explanation
        response = await self.llm.complete(
            prompt=prompt,
            tier=ModelTier.CAPABLE,
            max_tokens=400,
            temperature=0.3,
        )
        
        return CodeSummary(
            file=file,
            summary=response,
            detail_level="detailed",
            key_components=None,
            complexity=None,
        )


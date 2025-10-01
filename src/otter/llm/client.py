"""LLM client wrapper using LiteLLM for provider-agnostic calls.

This module provides a simple, stateless interface for making one-shot
LLM requests across multiple providers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import litellm

from .config import LLMConfig, ModelTier


class LLMClient:
    """Provider-agnostic LLM client.
    
    Uses LiteLLM under the hood to support all major providers:
    - Anthropic (Claude)
    - OpenAI (GPT-4)
    - Google (Gemini)
    - Azure OpenAI
    - OpenRouter
    - And many more
    
    Features:
    - Automatic provider detection via environment variables
    - Model tier selection (fast/capable/advanced)
    - Fallback support
    - Simple, stateless API
    
    Example:
        >>> config = LLMConfig.from_env()
        >>> client = LLMClient(config)
        >>> 
        >>> # Use fast model for simple task
        >>> response = await client.complete(
        ...     "Summarize this code in one sentence",
        ...     tier=ModelTier.FAST
        ... )
        >>> 
        >>> # Use advanced model for complex task
        >>> response = await client.complete(
        ...     "Analyze the security implications of this code",
        ...     tier=ModelTier.ADVANCED
        ... )
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM client.
        
        Args:
            config: LLM configuration. If None, creates from environment variables.
        """
        self.config = config if config is not None else LLMConfig.from_env()
        
        # Configure LiteLLM
        litellm.suppress_debug_info = True  # Reduce noise in logs
        litellm.drop_params = True  # Drop unsupported params instead of erroring
    
    async def complete(
        self,
        prompt: str,
        tier: ModelTier = ModelTier.CAPABLE,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> str:
        """Make a completion request.
        
        Args:
            prompt: The user prompt/query
            tier: Model tier to use (fast/capable/advanced)
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            **kwargs: Additional arguments passed to LiteLLM
        
        Returns:
            The completion text from the LLM
        
        Raises:
            RuntimeError: If no providers are available or all requests fail
        
        Example:
            >>> response = await client.complete(
            ...     "What does this function do?\\n\\ndef add(a, b):\\n    return a + b",
            ...     tier=ModelTier.FAST,
            ...     max_tokens=50
            ... )
            >>> print(response)
            "This function adds two numbers together and returns the result."
        """
        model = self.config.get_model(tier)
        
        # Build messages
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Call LiteLLM (handles all providers)
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # Extract text from response
            content = response.choices[0].message.content
            return content if content else ""
            
        except Exception as e:
            # If request fails, provide helpful error
            available_providers = self.config.get_available_providers()
            raise RuntimeError(
                f"LLM request failed: {e}\\n"
                f"Model: {model}\\n"
                f"Available providers: {available_providers}"
            ) from e
    
    async def complete_with_fallback(
        self,
        prompt: str,
        tier: ModelTier = ModelTier.CAPABLE,
        fallback_tiers: Optional[List[ModelTier]] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> str:
        """Make a completion request with automatic fallback.
        
        If the primary tier fails, tries fallback tiers in order.
        
        Args:
            prompt: The user prompt/query
            tier: Primary model tier to try
            fallback_tiers: List of fallback tiers if primary fails
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional arguments passed to LiteLLM
        
        Returns:
            The completion text from the LLM
        
        Raises:
            RuntimeError: If all tiers fail
        
        Example:
            >>> # Try advanced, fall back to capable if it fails
            >>> response = await client.complete_with_fallback(
            ...     prompt="Complex analysis task",
            ...     tier=ModelTier.ADVANCED,
            ...     fallback_tiers=[ModelTier.CAPABLE, ModelTier.FAST]
            ... )
        """
        # Build tier list (primary + fallbacks)
        tiers_to_try = [tier]
        if fallback_tiers:
            tiers_to_try.extend(fallback_tiers)
        
        errors: List[str] = []
        
        # Try each tier in order
        for current_tier in tiers_to_try:
            try:
                return await self.complete(
                    prompt=prompt,
                    tier=current_tier,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            except Exception as e:
                errors.append(f"{current_tier}: {str(e)}")
                continue
        
        # All tiers failed
        raise RuntimeError(
            "All LLM tiers failed. Errors:\\n" +
            "\\n".join(f"  - {err}" for err in errors)
        )
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers.
        
        Returns:
            List of provider names with API keys configured
        """
        return self.config.get_available_providers()
    
    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Get the model that will be used for a given tier.
        
        Args:
            tier: Model tier
        
        Returns:
            Model identifier string
        """
        return self.config.get_model(tier)
    
    def __repr__(self) -> str:
        """String representation."""
        providers = self.get_available_providers()
        return f"LLMClient(providers={providers})"


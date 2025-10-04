"""LLM configuration and provider detection.

This module handles:
- Runtime detection of available LLM providers via environment variables
- Model selection based on task requirements
- Provider fallbacks
- Configuration management
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class ModelTier(str, Enum):
    """Model tiers for different use cases.

    - FAST: Quick, cheap models for simple tasks (summaries, quick reviews)
    - CAPABLE: Balanced models for most tasks
    - ADVANCED: Most capable models for complex analysis
    """

    FAST = "fast"
    CAPABLE = "capable"
    ADVANCED = "advanced"


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""

    name: str
    api_key_env: str
    models: Dict[ModelTier, str]
    available: bool = False
    api_key: Optional[str] = None


@dataclass
class LLMConfig:
    """LLM configuration with runtime provider detection.

    Automatically detects which providers are available based on
    environment variables and provides model selection.
    """

    # Provider configurations
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)

    # Default models per tier (can be overridden)
    default_models: Dict[ModelTier, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize providers and detect availability."""
        if not self.providers:
            self.providers = self._get_default_providers()

        # Detect which providers are available
        self._detect_available_providers()

        # Set up default models from available providers
        if not self.default_models:
            self._setup_default_models()

    def _get_default_providers(self) -> Dict[str, ProviderConfig]:
        """Get default provider configurations.

        Covers major providers with their respective API key environment variables.
        Model identifiers are current as of October 2024.

        To verify/update model identifiers:
        - Run: uv run python scripts/validate_claude_4_models.py
        - Check official docs:
          • Anthropic: https://docs.anthropic.com/en/docs/about-claude/models
          • OpenAI: https://platform.openai.com/docs/models
          • Google: https://ai.google.dev/models/gemini
        """
        return {
            "anthropic": ProviderConfig(
                name="anthropic",
                api_key_env="ANTHROPIC_API_KEY",
                models={
                    ModelTier.FAST: "claude-3-5-haiku-20241022",  # Haiku 3.5 (Oct 2024) - fast & affordable
                    ModelTier.CAPABLE: "claude-sonnet-4-5-20250929",  # Sonnet 4.5 (Sept 2025) - best balance
                    ModelTier.ADVANCED: "claude-opus-4-1-20250805",  # Opus 4.1 (Aug 2025) - most capable
                },
            ),
            "openai": ProviderConfig(
                name="openai",
                api_key_env="OPENAI_API_KEY",
                models={
                    ModelTier.FAST: "gpt-4o-mini",  # Fast and affordable
                    ModelTier.CAPABLE: "gpt-4o",  # Latest GPT-4 Omni
                    ModelTier.ADVANCED: "o1",  # Advanced reasoning model
                },
            ),
            "google": ProviderConfig(
                name="google",
                api_key_env="GOOGLE_API_KEY",
                models={
                    ModelTier.FAST: "gemini-1.5-flash-002",  # Latest Flash variant
                    ModelTier.CAPABLE: "gemini-1.5-pro-002",  # Latest Pro variant
                    ModelTier.ADVANCED: "gemini-1.5-pro-002",  # Pro for advanced tasks
                },
            ),
            "azure": ProviderConfig(
                name="azure",
                api_key_env="AZURE_API_KEY",
                models={
                    ModelTier.FAST: "azure/gpt-4o-mini",
                    ModelTier.CAPABLE: "azure/gpt-4o",
                    ModelTier.ADVANCED: "azure/o1",  # If available in your Azure deployment
                },
            ),
            "openrouter": ProviderConfig(
                name="openrouter",
                api_key_env="OPENROUTER_API_KEY",
                models={
                    ModelTier.FAST: "openrouter/anthropic/claude-3.5-haiku",
                    ModelTier.CAPABLE: "openrouter/anthropic/claude-sonnet-4.5",  # Claude 4.5 via OpenRouter
                    ModelTier.ADVANCED: "openrouter/anthropic/claude-opus-4.1",  # Claude 4.1 via OpenRouter
                },
            ),
        }

    def _detect_available_providers(self) -> None:
        """Detect which providers have API keys configured."""
        for provider in self.providers.values():
            api_key = os.getenv(provider.api_key_env)
            if api_key:
                provider.available = True
                provider.api_key = api_key

    def _setup_default_models(self) -> None:
        """Set up default models from the first available provider."""
        # Try to find available providers in priority order
        priority_order = ["anthropic", "openai", "google", "azure", "openrouter"]

        for provider_name in priority_order:
            if (
                provider_name in self.providers
                and self.providers[provider_name].available
            ):
                provider = self.providers[provider_name]
                self.default_models = provider.models.copy()
                return

        # If no providers available, set empty defaults
        # (get_model() will raise error when actually trying to use them)
        if not self.default_models:
            self.default_models = {}

    def get_model(self, tier: ModelTier = ModelTier.CAPABLE) -> str:
        """Get the model to use for a given tier.

        Args:
            tier: The model tier (fast, capable, or advanced)

        Returns:
            Model identifier string (e.g., "claude-3-haiku-20240307")

        Raises:
            RuntimeError: If no providers are configured
        """
        if not self.default_models:
            raise RuntimeError(
                "No LLM providers configured. Please set one of: "
                + ", ".join(f"{p.api_key_env}" for p in self.providers.values())
            )

        if tier not in self.default_models:
            raise ValueError(f"No model configured for tier: {tier}")

        return self.default_models[tier]

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names.

        Returns:
            List of provider names that have API keys configured
        """
        return [name for name, provider in self.providers.items() if provider.available]

    def is_provider_available(self, provider_name: str) -> bool:
        """Check if a specific provider is available.

        Args:
            provider_name: Name of the provider (e.g., "anthropic", "openai")

        Returns:
            True if provider has API key configured, False otherwise
        """
        return (
            provider_name in self.providers and self.providers[provider_name].available
        )

    def get_provider_models(self, provider_name: str) -> Dict[ModelTier, str]:
        """Get all models for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Dictionary mapping tiers to model identifiers

        Raises:
            ValueError: If provider doesn't exist or isn't available
        """
        if not self.is_provider_available(provider_name):
            raise ValueError(f"Provider '{provider_name}' is not available")

        return self.providers[provider_name].models

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Create configuration from environment variables.

        This is the recommended way to create an LLMConfig instance.
        It will automatically detect all available providers.

        Returns:
            LLMConfig instance with detected providers

        Example:
            >>> config = LLMConfig.from_env()
            >>> config.get_available_providers()
            ['anthropic', 'openai']
            >>> config.get_model(ModelTier.FAST)
            'claude-3-haiku-20240307'
        """
        return cls()

    def __repr__(self) -> str:
        """String representation showing available providers."""
        available = self.get_available_providers()
        return f"LLMConfig(available_providers={available})"

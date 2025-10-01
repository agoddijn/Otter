#!/usr/bin/env python3
"""Check LLM provider configuration."""

from otter.llm import LLMConfig, ModelTier


def main():
    """Check which LLM providers are configured."""
    config = LLMConfig.from_env()
    providers = config.get_available_providers()
    
    print("Available providers:", ", ".join(providers) if providers else "None")
    print()
    
    if not providers:
        print("❌ No LLM providers configured!")
        print()
        print("Configure via Doppler:")
        print('  doppler secrets set ANTHROPIC_API_KEY "your-key"')
        print('  doppler secrets set OPENAI_API_KEY "your-key"')
        print('  doppler secrets set GOOGLE_API_KEY "your-key"')
        return 1
    
    print("✅ LLM providers ready!")
    print()
    print("Model configuration:")
    for tier in ModelTier:
        try:
            model = config.get_model(tier)
            print(f"  {tier.value:10s} → {model}")
        except Exception:
            pass
    
    return 0


if __name__ == "__main__":
    exit(main())


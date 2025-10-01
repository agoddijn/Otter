#!/usr/bin/env python3
"""Quick test to verify LLM model identifiers are valid."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.llm.config import LLMConfig, ModelTier

def test_model_identifiers():
    """Test that configured model identifiers are valid."""
    print("🧪 Testing LLM Model Identifiers")
    print("=" * 70)
    
    config = LLMConfig()
    
    print("\n📋 Configured Providers:")
    for provider_name, provider_config in config.providers.items():
        status = "✓ Available" if provider_config.available else "✗ No API key"
        print(f"\n{provider_name}: {status}")
        if provider_config.available or True:  # Show all configs
            for tier, model in provider_config.models.items():
                print(f"  {tier.value:10s} → {model}")
    
    print("\n" + "=" * 70)
    
    # Check if any providers are available
    if not config.get_available_providers():
        print("⚠️  No LLM providers configured (no API keys found)")
        print("   Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY")
        return False
    
    print(f"✓ Active provider models:")
    for tier in [ModelTier.FAST, ModelTier.CAPABLE, ModelTier.ADVANCED]:
        try:
            model = config.get_model(tier)
            print(f"  {tier.value:10s} → {model}")
        except Exception as e:
            print(f"  {tier.value:10s} → ERROR: {e}")
            return False
    
    print("\n✅ All model identifiers loaded successfully!")
    print("   (Note: This only validates config loading, not API compatibility)")
    return True

if __name__ == "__main__":
    success = test_model_identifiers()
    sys.exit(0 if success else 1)


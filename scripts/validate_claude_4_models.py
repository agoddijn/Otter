#!/usr/bin/env python3
"""Validate that Claude 4 model identifiers work with the actual API."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from otter.llm.client import LLMClient
from otter.llm.config import LLMConfig, ModelTier

async def test_claude_4_models():
    """Test Claude 4 model identifiers against the API."""
    print("🧪 Validating Claude 4 Model Identifiers with API")
    print("=" * 70)
    
    config = LLMConfig()
    
    if "anthropic" not in config.get_available_providers():
        print("❌ ANTHROPIC_API_KEY not configured")
        print("   Add your API key to .env file (copy from .env.example)")
        return False
    
    print("✓ Anthropic API key found")
    print(f"\nConfigured models:")
    for tier in [ModelTier.FAST, ModelTier.CAPABLE, ModelTier.ADVANCED]:
        model = config.providers["anthropic"].models[tier]
        print(f"  {tier.value:10s} → {model}")
    
    # Test with a simple completion
    print("\n🔬 Testing CAPABLE tier (Claude Sonnet 4)...")
    client = LLMClient(config)
    
    try:
        response = await client.complete(
            prompt="Say 'Hello from Claude 4!' and nothing else.",
            tier=ModelTier.CAPABLE,
            max_tokens=50,
            temperature=0
        )
        print(f"✅ SUCCESS! Response: {response}")
        
        # Test FAST tier
        print("\n🔬 Testing FAST tier (Claude 3.5 Haiku)...")
        response = await client.complete(
            prompt="Say 'Fast response!' and nothing else.",
            tier=ModelTier.FAST,
            max_tokens=50,
            temperature=0
        )
        print(f"✅ SUCCESS! Response: {response}")
        
        print("\n" + "=" * 70)
        print("✅ All Claude 4 model identifiers are VALID!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 This might mean:")
        print("   1. The model identifier is incorrect")
        print("   2. Claude 4 hasn't been released yet")
        print("   3. Your API key doesn't have access to Claude 4")
        print("\n🔧 Suggested fix: Revert to Claude 3.5 models")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_claude_4_models())
    sys.exit(0 if success else 1)


"""Test script for LLM infrastructure.

This script demonstrates:
1. Provider detection from environment variables
2. Model selection for different tiers
3. Making completion requests (if API keys are available)

Usage:
    # Set API key for your provider
    export ANTHROPIC_API_KEY="your-key-here"
    # or
    export OPENAI_API_KEY="your-key-here"
    
    # Run the test
    python examples/test_llm_infrastructure.py
"""

import asyncio
import os

from otter.llm import LLMClient, LLMConfig, ModelTier


async def main():
    """Test LLM infrastructure."""
    
    print("=" * 60)
    print("LLM Infrastructure Test")
    print("=" * 60)
    
    # 1. Create configuration (detects providers from environment)
    print("\n1. Detecting available providers...")
    config = LLMConfig.from_env()
    
    available_providers = config.get_available_providers()
    if not available_providers:
        print("❌ No providers detected!")
        print("\nTo use LLM features, set one of these environment variables:")
        for provider in config.providers.values():
            print(f"  - {provider.api_key_env}")
        print("\nExample:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        return
    
    print(f"✅ Found {len(available_providers)} provider(s): {', '.join(available_providers)}")
    
    # 2. Show model selection
    print("\n2. Model selection for different tiers:")
    for tier in ModelTier:
        model = config.get_model(tier)
        print(f"  - {tier.value:10s} → {model}")
    
    # 3. Create client
    print("\n3. Creating LLM client...")
    client = LLMClient(config)
    print(f"✅ {client}")
    
    # 4. Test completion (if user confirms)
    print("\n4. Test completion request:")
    print("   This will make a real API call and incur costs.")
    
    # Check if we're in CI or non-interactive mode
    if os.getenv("CI") or not os.isatty(0):
        print("   Skipping (non-interactive mode)")
        return
    
    response = input("   Run test? (y/N): ")
    if response.lower() != 'y':
        print("   Skipped by user")
        return
    
    print("\n   Making request to LLM...")
    try:
        result = await client.complete(
            prompt="Write a one-sentence summary of what Python is.",
            tier=ModelTier.FAST,
            max_tokens=50
        )
        print(f"   ✅ Response: {result}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


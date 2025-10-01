#!/usr/bin/env python3
"""Test AI-powered analysis features.

This script demonstrates the AI features for context compression:
1. summarize_code - Compress large files
2. summarize_changes - Summarize diffs
3. quick_review - Fast code review
4. explain_error - Interpret errors

Usage:
    # Requires LLM API key (configured via .env file)
    # Copy .env.example to .env and add your API keys
    make test-llm  # or
    python examples/test_ai_features.py
"""

import asyncio

from otter.services.ai import AIService


# Sample code for testing
SAMPLE_CODE = '''"""Payment processing module."""

import stripe
from typing import Optional, Dict, Any
from decimal import Decimal


class PaymentProcessor:
    """Handles payment processing via Stripe."""
    
    def __init__(self, api_key: str):
        """Initialize with Stripe API key."""
        self.api_key = api_key
        stripe.api_key = api_key
    
    def process_payment(
        self,
        amount: Decimal,
        currency: str = "usd",
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a payment through Stripe.
        
        Args:
            amount: Payment amount
            currency: Currency code (default: USD)
            customer_id: Optional Stripe customer ID
            metadata: Optional metadata to attach
        
        Returns:
            Payment result with charge ID and status
        
        Raises:
            stripe.StripeError: If payment fails
        """
        try:
            charge = stripe.Charge.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=customer_id,
                metadata=metadata or {},
            )
            
            return {
                "charge_id": charge.id,
                "status": charge.status,
                "amount": amount,
                "currency": currency,
            }
        except stripe.StripeError as e:
            # Log error and re-raise
            print(f"Payment failed: {e}")
            raise
    
    def refund_payment(self, charge_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Refund a payment (full or partial).
        
        Args:
            charge_id: Stripe charge ID to refund
            amount: Optional partial refund amount
        
        Returns:
            Refund result with refund ID and status
        """
        refund_params = {"charge": charge_id}
        if amount:
            refund_params["amount"] = int(amount * 100)
        
        refund = stripe.Refund.create(**refund_params)
        
        return {
            "refund_id": refund.id,
            "status": refund.status,
            "amount": Decimal(refund.amount) / 100,
        }
'''

MODIFIED_CODE = SAMPLE_CODE.replace(
    "print(f\"Payment failed: {e}\")",
    "logger.error(f\"Payment failed: {e}\", exc_info=True)"
)

ERROR_MESSAGE = """
Traceback (most recent call last):
  File "app.py", line 45, in process_order
    user_data = get_user(user_id)
  File "users.py", line 23, in get_user
    return users[user_id]
TypeError: 'NoneType' object is not subscriptable
"""


async def main():
    """Test AI features."""
    print("=" * 70)
    print("Testing AI-Powered Analysis Features")
    print("=" * 70)
    
    # Initialize AI service
    print("\n1. Initializing AI service...")
    try:
        ai = AIService()
        print(f"   ✅ AI service ready (providers: {ai.llm.get_available_providers()})")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        print("\n   Please configure LLM API keys in .env file (copy from .env.example)")
        return
    
    # Test 1: Summarize Code (Brief)
    print("\n2. Testing summarize_code (brief)...")
    try:
        summary = await ai.summarize_code(
            file="payment_processor.py",
            content=SAMPLE_CODE,
            detail_level="brief"
        )
        print(f"   ✅ Brief summary ({len(summary.summary)} chars):")
        print(f"      {summary.summary}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Summarize Code (Detailed)
    print("\n3. Testing summarize_code (detailed)...")
    try:
        summary = await ai.summarize_code(
            file="payment_processor.py",
            content=SAMPLE_CODE,
            detail_level="detailed"
        )
        print(f"   ✅ Detailed summary ({len(summary.summary)} chars):")
        for line in summary.summary.split("\n")[:5]:  # First 5 lines
            if line.strip():
                print(f"      {line}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Summarize Changes
    print("\n4. Testing summarize_changes...")
    try:
        changes = await ai.summarize_changes(
            file="payment_processor.py",
            old_content=SAMPLE_CODE,
            new_content=MODIFIED_CODE
        )
        print(f"   ✅ Change summary:")
        print(f"      {changes.summary}")
        print(f"      Change types: {', '.join(changes.changes_type)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Quick Review
    print("\n5. Testing quick_review...")
    try:
        review = await ai.quick_review(
            file="payment_processor.py",
            content=SAMPLE_CODE,
            focus=["security", "bugs"]
        )
        print(f"   ✅ Review: {review.overall_assessment}")
        if review.issues:
            print(f"      Found {len(review.issues)} issue(s):")
            for issue in review.issues[:3]:  # First 3 issues
                print(f"        - [{issue.severity}] {issue.message}")
        else:
            print(f"      No issues found!")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Explain Error
    print("\n6. Testing explain_error...")
    try:
        explanation = await ai.explain_error(
            error_message=ERROR_MESSAGE,
            context_file="app.py"
        )
        print(f"   ✅ Error explanation:")
        print(f"      Type: {explanation.error_type}")
        print(f"      {explanation.explanation}")
        print(f"      Likely causes:")
        for cause in explanation.likely_causes[:2]:
            print(f"        - {cause}")
        print(f"      Suggested fixes:")
        for fix in explanation.suggested_fixes[:2]:
            print(f"        - {fix}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("AI Features Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())


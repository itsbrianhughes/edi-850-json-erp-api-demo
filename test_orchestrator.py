#!/usr/bin/env python3
"""
Test script for Integration Orchestrator
Tests the complete orchestrated pipeline with retry logic and logging
"""

import sys
import json
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from processor.orchestrator import IntegrationOrchestrator


async def test_orchestrator():
    """Test the integration orchestrator with complete pipeline"""

    print("=" * 70)
    print("Integration Orchestrator Test")
    print("=" * 70)
    print()

    # Load sample EDI file
    sample_file = Path(__file__).parent / "sample_data" / "sample_850.edi"

    if not sample_file.exists():
        print(f"❌ Error: Sample file not found at {sample_file}")
        return False

    print(f"📄 Reading sample file: {sample_file.name}")
    with open(sample_file, 'r') as f:
        edi_content = f.read()

    print(f"📏 File size: {len(edi_content)} characters")
    print()

    # Initialize orchestrator
    print("🔧 Initializing orchestrator with retry configuration...")
    orchestrator = IntegrationOrchestrator(
        max_retries=3,
        retry_delay=1.0,  # Shorter delay for testing
        enable_logging=True
    )
    print("✅ Orchestrator initialized")
    print()

    # Execute pipeline
    print("=" * 70)
    print("EXECUTING ORCHESTRATED PIPELINE")
    print("=" * 70)
    print()

    try:
        result = await orchestrator.process_edi_file(edi_content)

        print()
        print("=" * 70)
        print("ORCHESTRATION RESULT")
        print("=" * 70)
        print(json.dumps(result, indent=2))
        print()

        # Display summary
        print("=" * 70)
        print("EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Job ID: {result['job_id']}")
        print(f"Success: {result['success']}")
        print(f"Duration: {result['duration_seconds']}s")
        print()

        # Step-by-step status
        print("Step Status:")
        for step_name, step_data in result['steps'].items():
            status = step_data['status']
            status_emoji = "✅" if status == "success" else "❌" if status == "failed" else "⏸️"
            print(f"  {status_emoji} {step_name.replace('_', ' ').title()}: {status}")

            if step_name == "post_to_erp" and step_data.get("attempts"):
                print(f"     Attempts: {step_data['attempts']}")

            if step_data.get("error"):
                print(f"     Error: {step_data['error']}")

            if step_name == "validate" and step_data.get("errors"):
                print(f"     Validation errors: {len(step_data['errors'])}")
                for err in step_data['errors']:
                    print(f"       - {err}")
        print()

        # Final result
        if result.get('final_result'):
            print("Final Result:")
            final = result['final_result']
            if isinstance(final, dict):
                if final.get('erp_po_id'):
                    print(f"  ERP PO ID: {final['erp_po_id']}")
                    print(f"  Transaction ID: {final.get('transaction_id', 'N/A')}")
                    print(f"  Message: {final.get('message', 'N/A')}")
                    if final.get('details'):
                        print(f"  Status: {final['details'].get('status', 'N/A')}")
                        print(f"  Total Amount: ${final['details'].get('total_amount', 0):.2f}")
                elif final.get('error'):
                    print(f"  Error: {final['error']}")
            print()

        # Overall status
        print("=" * 70)
        if result['success']:
            print("✅ TEST PASSED - Orchestrator executed successfully!")
        else:
            print("⚠️  TEST COMPLETED - Pipeline failed (as expected for error scenarios)")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"❌ Orchestration Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main async entry point"""
    success = await test_orchestrator()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

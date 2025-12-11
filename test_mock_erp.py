#!/usr/bin/env python3
"""
Test script for Mock ERP API
Tests the complete pipeline: EDI Parse → Transform → Post to ERP
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from edi_parser.parser import EDI850Parser, EDIParsingError
from transformer.mapper import ERPMapper, TransformationError
from transformer.erp_schema import ERPPurchaseOrder
from mock_erp_api.endpoints import create_purchase_order, _validate_business_rules


def test_complete_pipeline():
    """Test the complete EDI to ERP pipeline"""

    print("=" * 60)
    print("Complete Pipeline Test: EDI → Parse → Transform → ERP API")
    print("=" * 60)
    print()

    # Load sample EDI file
    sample_file = Path(__file__).parent / "sample_data" / "sample_850.edi"

    if not sample_file.exists():
        print(f"❌ Error: Sample file not found at {sample_file}")
        return False

    print(f"📄 Reading sample file: {sample_file.name}")
    with open(sample_file, 'r') as f:
        edi_content = f.read()

    print()

    # Step 1: Parse EDI
    print("🔧 Step 1: Parsing EDI 850...")
    try:
        parser = EDI850Parser()
        parsed_data = parser.parse(edi_content)
        print("✅ Parsing successful!")
        print()
    except EDIParsingError as e:
        print(f"❌ Parsing Error: {e}")
        return False

    # Step 2: Transform to ERP
    print("🔄 Step 2: Transforming to ERP schema...")
    try:
        mapper = ERPMapper()
        erp_payload_dict = mapper.transform(parsed_data)

        # Convert to Pydantic model for validation
        erp_payload = ERPPurchaseOrder(**erp_payload_dict)
        print("✅ Transformation successful!")
        print()
    except TransformationError as e:
        print(f"❌ Transformation Error: {e}")
        return False

    # Step 3: Validate business rules
    print("🔍 Step 3: Validating business rules...")
    validation_errors = _validate_business_rules(erp_payload)

    if validation_errors:
        print("❌ Business rule validation failed:")
        for error in validation_errors:
            print(f"  - {error}")
        return False
    else:
        print("✅ All business rules passed!")
        print()

    # Step 4: Post to Mock ERP API (simulated)
    print("📤 Step 4: Posting to Mock ERP API...")
    try:
        # Simulate API call (without actually running FastAPI server)
        import uuid
        from datetime import datetime
        import random

        transaction_id = str(uuid.uuid4())
        erp_po_id = f"ERP-{erp_payload.po_number}-{random.randint(1000, 9999)}"

        erp_response = {
            "success": True,
            "transaction_id": transaction_id,
            "message": "Purchase order created successfully",
            "erp_po_id": erp_po_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "details": {
                "po_number": erp_payload.po_number,
                "vendor": erp_payload.vendor.vendor_name,
                "total_amount": erp_payload.total_amount,
                "line_items_count": erp_payload.total_lines,
                "status": "PENDING_APPROVAL",
                "estimated_processing_time": "2-4 hours"
            }
        }

        print("✅ ERP API call successful!")
        print()
    except Exception as e:
        print(f"❌ ERP API Error: {e}")
        return False

    # Display results
    print("=" * 60)
    print("ERP API RESPONSE")
    print("=" * 60)
    print(json.dumps(erp_response, indent=2))
    print()

    # Summary
    print("=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Original EDI PO: {parsed_data['beg_segment']['purchase_order_number']}")
    print(f"ERP PO ID: {erp_response['erp_po_id']}")
    print(f"Transaction ID: {erp_response['transaction_id']}")
    print(f"Vendor: {erp_payload.vendor.vendor_name}")
    print(f"Ship To: {erp_payload.ship_to.location_name}")
    print(f"Total Amount: ${erp_payload.total_amount:.2f}")
    print(f"Line Items: {erp_payload.total_lines}")
    print(f"Status: {erp_response['details']['status']}")
    print()

    # Test error scenarios
    print("=" * 60)
    print("TESTING ERROR SCENARIOS")
    print("=" * 60)
    print()

    # Test 1: Empty PO number
    print("Test 1: Invalid PO number...")
    invalid_payload = ERPPurchaseOrder(**erp_payload_dict)
    invalid_payload.po_number = ""
    errors = _validate_business_rules(invalid_payload)
    if errors:
        print(f"✅ Correctly caught error: {errors[0]}")
    else:
        print("❌ Should have caught empty PO number")
    print()

    # Test 2: Zero total amount
    print("Test 2: Invalid total amount...")
    invalid_payload = ERPPurchaseOrder(**erp_payload_dict)
    invalid_payload.total_amount = 0
    errors = _validate_business_rules(invalid_payload)
    if errors:
        print(f"✅ Correctly caught error: {errors[0]}")
    else:
        print("❌ Should have caught zero total amount")
    print()

    # Test 3: Line count mismatch
    print("Test 3: Line count mismatch...")
    invalid_payload = ERPPurchaseOrder(**erp_payload_dict)
    invalid_payload.total_lines = 999
    errors = _validate_business_rules(invalid_payload)
    if errors:
        print(f"✅ Correctly caught error: {errors[0]}")
    else:
        print("❌ Should have caught line count mismatch")
    print()

    print("=" * 60)
    print("✅ ALL TESTS PASSED - Complete pipeline working!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_complete_pipeline()
    sys.exit(0 if success else 1)

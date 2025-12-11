#!/usr/bin/env python3
"""
Test script for EDI 850 → ERP Transformation
Tests the complete pipeline: parse → transform
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from edi_parser.parser import EDI850Parser, EDIParsingError
from transformer.mapper import ERPMapper, TransformationError


def test_transformation():
    """Test the complete EDI to ERP transformation pipeline"""

    print("=" * 60)
    print("EDI 850 → ERP Transformation Test")
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
        erp_payload = mapper.transform(parsed_data)
        print("✅ Transformation successful!")
        print()
    except TransformationError as e:
        print(f"❌ Transformation Error: {e}")
        return False

    # Display transformed ERP payload
    print("=" * 60)
    print("ERP PAYLOAD (JSON)")
    print("=" * 60)
    print(json.dumps(erp_payload, indent=2))
    print()

    # Display summary
    print("=" * 60)
    print("TRANSFORMATION SUMMARY")
    print("=" * 60)
    print(f"PO Number: {erp_payload['po_number']}")
    print(f"PO Date: {erp_payload['po_date']}")
    print(f"PO Type: {erp_payload['po_type']}")
    print()

    print(f"Vendor: {erp_payload['vendor']['vendor_name']}")
    print(f"Vendor ID: {erp_payload['vendor']['vendor_id']}")
    print()

    print(f"Ship To: {erp_payload['ship_to']['location_name']}")
    print(f"Ship To ID: {erp_payload['ship_to']['location_id']}")
    print()

    print(f"Line Items: {erp_payload['total_lines']}")
    print(f"Total Amount: ${erp_payload['total_amount']:.2f}")
    print()

    # Line items detail
    print("Line Items Detail:")
    for item in erp_payload['line_items']:
        print(f"  Line {item['line_number']}: {item['quantity']} {item['unit_of_measure']} of {item['sku']}")
        print(f"    @ ${item['unit_price']:.2f} = ${item['total_price']:.2f}")
        if item['description']:
            print(f"    Description: {item['description']}")
    print()

    # Reference numbers
    if erp_payload.get('reference_numbers'):
        print("Reference Numbers:")
        for key, value in erp_payload['reference_numbers'].items():
            print(f"  {key}: {value}")
        print()

    # Validate calculations
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)

    # Verify line totals
    line_totals_correct = True
    for item in erp_payload['line_items']:
        expected = round(item['quantity'] * item['unit_price'], 2)
        if item['total_price'] != expected:
            print(f"❌ Line {item['line_number']} total incorrect: {item['total_price']} != {expected}")
            line_totals_correct = False

    if line_totals_correct:
        print("✅ All line item totals calculated correctly")

    # Verify order total
    calculated_total = sum(item['total_price'] for item in erp_payload['line_items'])
    calculated_total = round(calculated_total, 2)

    if calculated_total == erp_payload['total_amount']:
        print(f"✅ Order total calculated correctly: ${erp_payload['total_amount']:.2f}")
    else:
        print(f"❌ Order total incorrect: {erp_payload['total_amount']:.2f} != {calculated_total:.2f}")
        return False

    # Verify line count
    if len(erp_payload['line_items']) == erp_payload['total_lines']:
        print(f"✅ Line count correct: {erp_payload['total_lines']}")
    else:
        print(f"❌ Line count incorrect: {erp_payload['total_lines']} != {len(erp_payload['line_items'])}")
        return False

    print()
    print("=" * 60)
    print("✅ TEST PASSED - Transformation working correctly!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_transformation()
    sys.exit(0 if success else 1)

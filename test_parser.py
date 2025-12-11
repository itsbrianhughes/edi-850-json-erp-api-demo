#!/usr/bin/env python3
"""
Test script for EDI 850 Parser
Tests the parser with the sample 850 file
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from edi_parser.parser import EDI850Parser, EDIParsingError


def test_parser():
    """Test the EDI 850 parser with sample file"""

    print("=" * 60)
    print("EDI 850 Parser Test")
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

    print(f"📏 File size: {len(edi_content)} characters")
    print()

    # Parse EDI
    print("🔧 Parsing EDI 850...")
    try:
        parser = EDI850Parser()
        parsed_data = parser.parse(edi_content)

        print("✅ Parsing successful!")
        print()

        # Display parsed data
        print("=" * 60)
        print("PARSED EDI DATA (JSON)")
        print("=" * 60)
        print(json.dumps(parsed_data, indent=2))
        print()

        # Summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"PO Number: {parsed_data['beg_segment']['purchase_order_number']}")
        print(f"PO Date: {parsed_data['beg_segment']['date']}")
        print(f"Sender: {parsed_data['isa_header']['sender_id']}")
        print(f"Receiver: {parsed_data['isa_header']['receiver_id']}")
        print(f"Line Items: {len(parsed_data['po1_line_items'])}")
        print(f"Total Line Count (CTT): {parsed_data['ctt_segment']['line_item_count']}")
        print()

        # Line items detail
        print("Line Items Detail:")
        for item in parsed_data['po1_line_items']:
            print(f"  - Line {item['line_number']}: {item['quantity']} {item['unit_of_measure']} of {item['product_id']} @ ${item['unit_price']}")
        print()

        # Name/Address loops
        print(f"Name/Address Loops: {len(parsed_data['n1_loops'])}")
        for n1 in parsed_data['n1_loops']:
            print(f"  - {n1['entity_identifier']}: {n1['name']}")
        print()

        # Reference segments
        print(f"Reference Segments: {len(parsed_data['ref_segments'])}")
        for ref in parsed_data['ref_segments']:
            print(f"  - {ref['reference_qualifier']}: {ref['reference_number']}")
        print()

        print("=" * 60)
        print("✅ TEST PASSED - Parser working correctly!")
        print("=" * 60)
        return True

    except EDIParsingError as e:
        print(f"❌ EDI Parsing Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_parser()
    sys.exit(0 if success else 1)

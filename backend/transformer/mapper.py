"""
EDI JSON → ERP Schema Transformer
Maps parsed EDI 850 JSON to ERP-expected JSON format
"""

from typing import Dict, List, Optional
from .erp_schema import (
    ERPPurchaseOrder, ERPLineItem, ERPVendor, ERPShipTo
)


class ERPMapper:
    """
    Transforms parsed EDI 850 JSON into ERP API payload format
    """

    # EDI entity identifier code mapping
    ENTITY_CODE_MAP = {
        "BY": "Buyer",
        "ST": "Ship To",
        "VN": "Vendor",
        "SE": "Selling Party",
        "BT": "Bill To",
        "RE": "Remit To"
    }

    # EDI purchase order type mapping
    PO_TYPE_MAP = {
        "NE": "New Order",
        "RE": "Reorder",
        "SA": "Stand Alone",
        "CN": "Confirmation",
        "RL": "Release"
    }

    def __init__(self):
        pass

    def transform(self, parsed_edi: dict) -> dict:
        """
        Transform parsed EDI JSON to ERP schema

        Args:
            parsed_edi: Dictionary from EDI850Parser

        Returns:
            Dictionary formatted for ERP API
        """
        try:
            # Extract vendor, ship-to, and buyer information
            vendor = self._extract_vendor(parsed_edi.get("n1_loops", []))
            ship_to = self._extract_ship_to(parsed_edi.get("n1_loops", []))

            # Transform line items
            line_items = self._transform_line_items(parsed_edi.get("po1_line_items", []))

            # Calculate total amount
            total_amount = self._calculate_total_amount(line_items)

            # Extract PO information
            beg = parsed_edi.get("beg_segment", {})
            po_type = self._map_po_type(beg.get("purchase_order_type", ""))

            # Build reference numbers dictionary
            reference_numbers = self._build_reference_numbers(parsed_edi.get("ref_segments", []))

            # Build ERP Purchase Order
            erp_po = ERPPurchaseOrder(
                po_number=beg.get("purchase_order_number", ""),
                po_date=self._format_date(beg.get("date", "")),
                po_type=po_type,
                vendor=vendor,
                ship_to=ship_to,
                line_items=line_items,
                total_amount=total_amount,
                total_lines=len(line_items),
                reference_numbers=reference_numbers
            )

            # Return as dictionary
            return erp_po.model_dump()

        except Exception as e:
            raise TransformationError(f"Failed to transform EDI to ERP schema: {str(e)}")

    def _extract_vendor(self, n1_loops: List[dict]) -> ERPVendor:
        """
        Extract vendor information from N1 loops

        Args:
            n1_loops: List of N1 loop dictionaries

        Returns:
            ERPVendor instance
        """
        for n1 in n1_loops:
            if n1.get("entity_identifier") == "VN":
                return ERPVendor(
                    vendor_id=n1.get("identification_code", "UNKNOWN"),
                    vendor_name=n1.get("name", "Unknown Vendor")
                )

        # Default if no vendor found
        return ERPVendor(
            vendor_id="UNKNOWN",
            vendor_name="Unknown Vendor"
        )

    def _extract_ship_to(self, n1_loops: List[dict]) -> ERPShipTo:
        """
        Extract ship-to information from N1 loops

        Args:
            n1_loops: List of N1 loop dictionaries

        Returns:
            ERPShipTo instance
        """
        for n1 in n1_loops:
            if n1.get("entity_identifier") == "ST":
                return ERPShipTo(
                    location_id=n1.get("identification_code"),
                    location_name=n1.get("name", "Unknown Location")
                )

        # Default if no ship-to found
        return ERPShipTo(
            location_id=None,
            location_name="Unknown Location"
        )

    def _transform_line_items(self, po1_items: List[dict]) -> List[ERPLineItem]:
        """
        Transform EDI PO1 line items to ERP line items

        Args:
            po1_items: List of PO1 line item dictionaries

        Returns:
            List of ERPLineItem instances
        """
        erp_items = []

        for po1 in po1_items:
            # Parse numeric values
            quantity = float(po1.get("quantity", 0))
            unit_price = float(po1.get("unit_price", 0))

            # Calculate line total
            total_price = round(quantity * unit_price, 2)

            # Create ERP line item
            erp_item = ERPLineItem(
                line_number=int(po1.get("line_number", 0)),
                sku=po1.get("product_id", ""),
                description=po1.get("description"),
                quantity=quantity,
                unit_price=unit_price,
                unit_of_measure=po1.get("unit_of_measure", "EA"),
                total_price=total_price
            )

            erp_items.append(erp_item)

        return erp_items

    def _calculate_total_amount(self, line_items: List[ERPLineItem]) -> float:
        """
        Calculate total order amount from line items

        Args:
            line_items: List of ERPLineItem instances

        Returns:
            Total amount as float
        """
        total = sum(item.total_price for item in line_items)
        return round(total, 2)

    def _map_po_type(self, po_type_code: str) -> str:
        """
        Map EDI PO type code to readable description

        Args:
            po_type_code: EDI purchase order type code

        Returns:
            Readable PO type description
        """
        return self.PO_TYPE_MAP.get(po_type_code, po_type_code)

    def _format_date(self, edi_date: str) -> str:
        """
        Format EDI date (YYYYMMDD) to ISO format (YYYY-MM-DD)

        Args:
            edi_date: Date in YYYYMMDD format

        Returns:
            Date in YYYY-MM-DD format
        """
        if len(edi_date) == 8:
            year = edi_date[0:4]
            month = edi_date[4:6]
            day = edi_date[6:8]
            return f"{year}-{month}-{day}"
        return edi_date

    def _build_reference_numbers(self, ref_segments: List[dict]) -> dict:
        """
        Build reference numbers dictionary from REF segments

        Args:
            ref_segments: List of REF segment dictionaries

        Returns:
            Dictionary of reference numbers
        """
        references = {}

        for ref in ref_segments:
            qualifier = ref.get("reference_qualifier", "")
            number = ref.get("reference_number", "")

            # Map common qualifier codes to readable names
            qualifier_map = {
                "DP": "department",
                "CO": "customer_order",
                "CR": "customer_reference",
                "PO": "previous_po",
                "VN": "vendor_order"
            }

            key = qualifier_map.get(qualifier, qualifier.lower())
            references[key] = number

        return references if references else None


class TransformationError(Exception):
    """Custom exception for transformation errors"""
    pass

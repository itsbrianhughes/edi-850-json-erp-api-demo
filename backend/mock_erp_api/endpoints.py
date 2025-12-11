"""
Mock ERP API Endpoints
Simulates a real ERP system's purchase order API
"""

from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, ValidationError
from typing import Optional
import uuid
from datetime import datetime
import random

# Import ERP schema for validation
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from transformer.erp_schema import ERPPurchaseOrder

router = APIRouter(prefix="/api/erp", tags=["Mock ERP API"])


class ERPResponse(BaseModel):
    """Standard ERP API Response"""
    success: bool
    transaction_id: str
    message: str
    erp_po_id: Optional[str] = None
    timestamp: str
    details: Optional[dict] = None


class ERPErrorResponse(BaseModel):
    """ERP API Error Response"""
    success: bool
    transaction_id: str
    error_code: str
    error_message: str
    timestamp: str
    details: Optional[dict] = None


@router.post("/purchase-orders", response_model=ERPResponse)
async def create_purchase_order(
    payload: ERPPurchaseOrder,
    x_simulate_error: Optional[str] = Header(None)
):
    """
    Mock ERP endpoint for creating purchase orders

    This endpoint simulates a real ERP system's purchase order API.
    It accepts ERP-formatted purchase order payloads and returns
    realistic success or error responses.

    Args:
        payload: ERPPurchaseOrder - Validated ERP purchase order
        x_simulate_error: Optional header to simulate specific errors
            - "validation" - Simulate validation error
            - "duplicate" - Simulate duplicate PO error
            - "inventory" - Simulate inventory error
            - "timeout" - Simulate timeout error

    Returns:
        ERPResponse with transaction ID and ERP PO ID
    """

    transaction_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Simulate error scenarios if requested (for testing)
    if x_simulate_error:
        return _simulate_error(x_simulate_error, transaction_id, timestamp, payload)

    # Validate business rules
    validation_errors = _validate_business_rules(payload)
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "transaction_id": transaction_id,
                "error_code": "VALIDATION_ERROR",
                "error_message": "Business rule validation failed",
                "timestamp": timestamp,
                "details": {"errors": validation_errors}
            }
        )

    # Generate ERP PO ID (simulating internal ERP system ID)
    erp_po_id = f"ERP-{payload.po_number}-{random.randint(1000, 9999)}"

    # Successful response
    return ERPResponse(
        success=True,
        transaction_id=transaction_id,
        message="Purchase order created successfully",
        erp_po_id=erp_po_id,
        timestamp=timestamp,
        details={
            "po_number": payload.po_number,
            "vendor": payload.vendor.vendor_name,
            "total_amount": payload.total_amount,
            "line_items_count": payload.total_lines,
            "status": "PENDING_APPROVAL",
            "estimated_processing_time": "2-4 hours"
        }
    )


@router.get("/purchase-orders/{erp_po_id}")
async def get_purchase_order(erp_po_id: str):
    """
    Get purchase order status by ERP PO ID

    Mock endpoint to retrieve PO status
    """
    return {
        "success": True,
        "erp_po_id": erp_po_id,
        "status": "PENDING_APPROVAL",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "message": "Purchase order found"
    }


@router.get("/health")
async def erp_health():
    """
    ERP API health check
    """
    return {
        "status": "healthy",
        "service": "Mock ERP API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def _validate_business_rules(payload: ERPPurchaseOrder) -> list:
    """
    Validate business rules for purchase orders

    Args:
        payload: ERPPurchaseOrder to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Rule 1: Total amount must be positive
    if payload.total_amount <= 0:
        errors.append("Total amount must be greater than zero")

    # Rule 2: Must have at least one line item
    if payload.total_lines < 1:
        errors.append("Purchase order must contain at least one line item")

    # Rule 3: Line items count must match total_lines
    if len(payload.line_items) != payload.total_lines:
        errors.append(f"Line items count mismatch: expected {payload.total_lines}, got {len(payload.line_items)}")

    # Rule 4: Each line item must have valid quantity and price
    for idx, item in enumerate(payload.line_items, 1):
        if item.quantity <= 0:
            errors.append(f"Line {idx}: Quantity must be greater than zero")
        if item.unit_price < 0:
            errors.append(f"Line {idx}: Unit price cannot be negative")
        if item.total_price < 0:
            errors.append(f"Line {idx}: Total price cannot be negative")

    # Rule 5: Vendor must be specified
    if not payload.vendor.vendor_name or payload.vendor.vendor_name == "Unknown Vendor":
        errors.append("Valid vendor information is required")

    # Rule 6: Ship-to location must be specified
    if not payload.ship_to.location_name or payload.ship_to.location_name == "Unknown Location":
        errors.append("Valid ship-to location is required")

    # Rule 7: PO number must not be empty
    if not payload.po_number or payload.po_number.strip() == "":
        errors.append("Purchase order number is required")

    return errors


def _simulate_error(error_type: str, transaction_id: str, timestamp: str, payload: ERPPurchaseOrder):
    """
    Simulate various error scenarios for testing

    Args:
        error_type: Type of error to simulate
        transaction_id: Transaction ID
        timestamp: Timestamp
        payload: Purchase order payload
    """

    error_scenarios = {
        "validation": {
            "status_code": status.HTTP_400_BAD_REQUEST,
            "error_code": "VALIDATION_ERROR",
            "error_message": "Invalid purchase order format",
            "details": {"field": "line_items", "issue": "Missing required SKU"}
        },
        "duplicate": {
            "status_code": status.HTTP_409_CONFLICT,
            "error_code": "DUPLICATE_PO",
            "error_message": f"Purchase order {payload.po_number} already exists in ERP system",
            "details": {"existing_erp_po_id": f"ERP-{payload.po_number}-5678"}
        },
        "inventory": {
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "error_code": "INVENTORY_UNAVAILABLE",
            "error_message": "One or more items are out of stock",
            "details": {
                "unavailable_items": [
                    {"sku": payload.line_items[0].sku if payload.line_items else "UNKNOWN", "available_quantity": 0}
                ]
            }
        },
        "timeout": {
            "status_code": status.HTTP_504_GATEWAY_TIMEOUT,
            "error_code": "TIMEOUT",
            "error_message": "ERP system timeout - please retry",
            "details": {"retry_after": "30 seconds"}
        }
    }

    scenario = error_scenarios.get(error_type, error_scenarios["validation"])

    raise HTTPException(
        status_code=scenario["status_code"],
        detail={
            "success": False,
            "transaction_id": transaction_id,
            "error_code": scenario["error_code"],
            "error_message": scenario["error_message"],
            "timestamp": timestamp,
            "details": scenario["details"]
        }
    )

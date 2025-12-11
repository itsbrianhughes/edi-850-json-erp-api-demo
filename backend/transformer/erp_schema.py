"""
ERP API Payload Schema
Defines the expected structure for the mock ERP system
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ERPLineItem(BaseModel):
    """ERP Line Item"""
    line_number: int
    sku: str
    description: Optional[str] = None
    quantity: float
    unit_price: float
    unit_of_measure: str
    total_price: float


class ERPVendor(BaseModel):
    """Vendor Information"""
    vendor_id: str
    vendor_name: str


class ERPShipTo(BaseModel):
    """Ship To Address"""
    location_id: Optional[str] = None
    location_name: str


class ERPPurchaseOrder(BaseModel):
    """Complete ERP Purchase Order Payload"""
    po_number: str
    po_date: str
    po_type: str
    vendor: ERPVendor
    ship_to: ERPShipTo
    line_items: List[ERPLineItem]
    total_amount: float
    total_lines: int
    reference_numbers: Optional[dict] = None

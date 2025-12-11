"""
Data Models for Parsed EDI 850
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ISAHeader(BaseModel):
    """Interchange Control Header"""
    authorization_info: str
    security_info: str
    sender_id: str
    receiver_id: str
    date: str
    time: str
    control_number: str
    acknowledgment_requested: str
    usage_indicator: str


class GSHeader(BaseModel):
    """Functional Group Header"""
    functional_id_code: str
    sender_code: str
    receiver_code: str
    date: str
    time: str
    control_number: str
    responsible_agency: str
    version: str


class BEGSegment(BaseModel):
    """Beginning Segment for Purchase Order"""
    transaction_set_purpose: str
    purchase_order_type: str
    purchase_order_number: str
    date: str


class REFSegment(BaseModel):
    """Reference Identification"""
    reference_qualifier: str
    reference_number: str


class N1Loop(BaseModel):
    """Name/Address Loop"""
    entity_identifier: str
    name: str
    identification_code_qualifier: Optional[str] = None
    identification_code: Optional[str] = None


class PO1LineItem(BaseModel):
    """Baseline Item Data"""
    line_number: str
    quantity: str
    unit_of_measure: str
    unit_price: str
    product_id_qualifier: str
    product_id: str
    description: Optional[str] = None


class CTTSegment(BaseModel):
    """Transaction Totals"""
    line_item_count: str
    hash_total: Optional[str] = None


class ParsedEDI850(BaseModel):
    """Complete parsed EDI 850 structure"""
    isa_header: ISAHeader
    gs_header: GSHeader
    beg_segment: BEGSegment
    ref_segments: List[REFSegment] = []
    n1_loops: List[N1Loop] = []
    po1_line_items: List[PO1LineItem] = []
    ctt_segment: CTTSegment
    control_numbers: dict

"""
Custom EDI 850 Parser
Lightweight parser focused on key segments: ISA, GS, ST, BEG, REF, N1, PO1, CTT, SE, GE, IEA
"""

from typing import List, Dict, Any, Optional
from .models import (
    ISAHeader, GSHeader, BEGSegment, REFSegment,
    N1Loop, PO1LineItem, CTTSegment, ParsedEDI850
)


class EDI850Parser:
    """
    Parses EDI 850 Purchase Order files into structured JSON
    """

    def __init__(self):
        self.segment_delimiter = "~"
        self.element_delimiter = "*"
        self.subelement_delimiter = ":"

    def parse(self, edi_content: str) -> dict:
        """
        Parse EDI 850 content into JSON structure

        Args:
            edi_content: Raw EDI file content as string

        Returns:
            Dictionary with parsed EDI data
        """
        try:
            # Split into segments
            segments = self._split_segments(edi_content)

            # Parse each segment type
            isa_header = self._parse_isa(segments)
            gs_header = self._parse_gs(segments)
            beg_segment = self._parse_beg(segments)
            ref_segments = self._parse_ref(segments)
            n1_loops = self._parse_n1(segments)
            po1_line_items = self._parse_po1(segments)
            ctt_segment = self._parse_ctt(segments)
            control_numbers = self._parse_control_trailers(segments)

            # Build parsed EDI model
            parsed_edi = ParsedEDI850(
                isa_header=isa_header,
                gs_header=gs_header,
                beg_segment=beg_segment,
                ref_segments=ref_segments,
                n1_loops=n1_loops,
                po1_line_items=po1_line_items,
                ctt_segment=ctt_segment,
                control_numbers=control_numbers
            )

            # Return as dictionary
            return parsed_edi.model_dump()

        except Exception as e:
            raise EDIParsingError(f"Failed to parse EDI 850: {str(e)}")

    def _split_segments(self, edi_content: str) -> List[List[str]]:
        """
        Split EDI content into segments and elements

        Args:
            edi_content: Raw EDI string

        Returns:
            List of segments, where each segment is a list of elements
        """
        # Remove any trailing whitespace/newlines
        edi_content = edi_content.strip()

        # Split by segment delimiter
        segment_strings = edi_content.split(self.segment_delimiter)

        # Split each segment into elements
        segments = []
        for seg_str in segment_strings:
            seg_str = seg_str.strip()
            if seg_str:  # Skip empty segments
                elements = seg_str.split(self.element_delimiter)
                segments.append(elements)

        return segments

    def _find_segment(self, segments: List[List[str]], segment_id: str) -> Optional[List[str]]:
        """Find first segment matching the segment ID"""
        for segment in segments:
            if segment and segment[0] == segment_id:
                return segment
        return None

    def _find_all_segments(self, segments: List[List[str]], segment_id: str) -> List[List[str]]:
        """Find all segments matching the segment ID"""
        return [seg for seg in segments if seg and seg[0] == segment_id]

    def _parse_isa(self, segments: List[List[str]]) -> ISAHeader:
        """Parse ISA - Interchange Control Header"""
        isa = self._find_segment(segments, "ISA")
        if not isa or len(isa) < 17:
            raise EDIParsingError("ISA segment not found or incomplete")

        return ISAHeader(
            authorization_info=isa[2].strip(),
            security_info=isa[4].strip(),
            sender_id=isa[6].strip(),
            receiver_id=isa[8].strip(),
            date=isa[9].strip(),
            time=isa[10].strip(),
            control_number=isa[13].strip(),
            acknowledgment_requested=isa[14].strip(),
            usage_indicator=isa[15].strip()
        )

    def _parse_gs(self, segments: List[List[str]]) -> GSHeader:
        """Parse GS - Functional Group Header"""
        gs = self._find_segment(segments, "GS")
        if not gs or len(gs) < 9:
            raise EDIParsingError("GS segment not found or incomplete")

        return GSHeader(
            functional_id_code=gs[1].strip(),
            sender_code=gs[2].strip(),
            receiver_code=gs[3].strip(),
            date=gs[4].strip(),
            time=gs[5].strip(),
            control_number=gs[6].strip(),
            responsible_agency=gs[7].strip(),
            version=gs[8].strip()
        )

    def _parse_beg(self, segments: List[List[str]]) -> BEGSegment:
        """Parse BEG - Beginning Segment for Purchase Order"""
        beg = self._find_segment(segments, "BEG")
        if not beg or len(beg) < 6:
            raise EDIParsingError("BEG segment not found or incomplete")

        return BEGSegment(
            transaction_set_purpose=beg[1].strip(),
            purchase_order_type=beg[2].strip(),
            purchase_order_number=beg[3].strip(),
            date=beg[5].strip() if len(beg) > 5 else ""
        )

    def _parse_ref(self, segments: List[List[str]]) -> List[REFSegment]:
        """Parse REF - Reference Identification segments"""
        ref_segments = self._find_all_segments(segments, "REF")
        result = []

        for ref in ref_segments:
            if len(ref) >= 3:
                result.append(REFSegment(
                    reference_qualifier=ref[1].strip(),
                    reference_number=ref[2].strip()
                ))

        return result

    def _parse_n1(self, segments: List[List[str]]) -> List[N1Loop]:
        """Parse N1 - Name/Address loops"""
        n1_segments = self._find_all_segments(segments, "N1")
        result = []

        for n1 in n1_segments:
            if len(n1) >= 3:
                result.append(N1Loop(
                    entity_identifier=n1[1].strip(),
                    name=n1[2].strip(),
                    identification_code_qualifier=n1[3].strip() if len(n1) > 3 else None,
                    identification_code=n1[4].strip() if len(n1) > 4 else None
                ))

        return result

    def _parse_po1(self, segments: List[List[str]]) -> List[PO1LineItem]:
        """Parse PO1 - Baseline Item Data (line items)"""
        po1_segments = self._find_all_segments(segments, "PO1")
        result = []

        for po1 in po1_segments:
            if len(po1) >= 7:
                result.append(PO1LineItem(
                    line_number=po1[1].strip(),
                    quantity=po1[2].strip(),
                    unit_of_measure=po1[3].strip(),
                    unit_price=po1[4].strip(),
                    product_id_qualifier=po1[6].strip() if len(po1) > 6 else "",
                    product_id=po1[7].strip() if len(po1) > 7 else "",
                    description=po1[9].strip() if len(po1) > 9 else None
                ))

        return result

    def _parse_ctt(self, segments: List[List[str]]) -> CTTSegment:
        """Parse CTT - Transaction Totals"""
        ctt = self._find_segment(segments, "CTT")
        if not ctt or len(ctt) < 2:
            raise EDIParsingError("CTT segment not found or incomplete")

        return CTTSegment(
            line_item_count=ctt[1].strip(),
            hash_total=ctt[2].strip() if len(ctt) > 2 else None
        )

    def _parse_control_trailers(self, segments: List[List[str]]) -> Dict[str, str]:
        """Parse control trailer segments (SE, GE, IEA)"""
        control = {}

        # SE - Transaction Set Trailer
        se = self._find_segment(segments, "SE")
        if se and len(se) >= 3:
            control["se_segment_count"] = se[1].strip()
            control["se_control_number"] = se[2].strip()

        # GE - Functional Group Trailer
        ge = self._find_segment(segments, "GE")
        if ge and len(ge) >= 3:
            control["ge_transaction_count"] = ge[1].strip()
            control["ge_control_number"] = ge[2].strip()

        # IEA - Interchange Control Trailer
        iea = self._find_segment(segments, "IEA")
        if iea and len(iea) >= 3:
            control["iea_group_count"] = iea[1].strip()
            control["iea_control_number"] = iea[2].strip()

        return control


class EDIParsingError(Exception):
    """Custom exception for EDI parsing errors"""
    pass

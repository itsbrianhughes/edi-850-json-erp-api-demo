"""
Integration Orchestrator
Pipeline: EDI Parse → Transform → API Post → Log
"""

import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import logging
from sqlalchemy.orm import Session

# Import integration components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from edi_parser.parser import EDI850Parser, EDIParsingError
from transformer.mapper import ERPMapper, TransformationError
from transformer.erp_schema import ERPPurchaseOrder
from mock_erp_api.endpoints import create_purchase_order, _validate_business_rules
from processor.logger import setup_logger
from database.service import DatabaseService


class IntegrationOrchestrator:
    """
    Orchestrates the complete integration workflow
    Parse → Transform → Validate → Post → Retry → Log
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        enable_logging: bool = True,
        db: Optional[Session] = None
    ):
        """
        Initialize orchestrator

        Args:
            max_retries: Maximum number of retry attempts for API calls
            retry_delay: Initial delay between retries (seconds)
            enable_logging: Enable detailed logging
            db: Optional database session for persistence
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_logging = enable_logging

        # Initialize components
        self.parser = EDI850Parser()
        self.mapper = ERPMapper()

        # Setup logger
        self.logger = setup_logger("IntegrationOrchestrator") if enable_logging else None

        # Database service (optional)
        self.db_service = DatabaseService(db) if db else None

    async def process_edi_file(self, edi_content: str) -> dict:
        """
        Execute full pipeline: parse → transform → post → log

        Args:
            edi_content: Raw EDI 850 file content

        Returns:
            Dictionary with processing results and logs
        """
        job_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        result = {
            "job_id": job_id,
            "success": False,
            "started_at": start_time.isoformat() + "Z",
            "completed_at": None,
            "duration_seconds": None,
            "steps": {
                "parse": {"status": "pending", "data": None, "error": None},
                "transform": {"status": "pending", "data": None, "error": None},
                "validate": {"status": "pending", "errors": None},
                "post_to_erp": {"status": "pending", "data": None, "error": None, "attempts": 0}
            },
            "final_result": None
        }

        if self.logger:
            self.logger.info(f"Starting integration job {job_id}")

        # Create job record in database
        if self.db_service:
            self.db_service.create_job({
                "job_id": job_id,
                "started_at": start_time,
                "success": False,
                "edi_content": edi_content
            })
            self._log_to_db(job_id, "INFO", f"Integration job {job_id} started")

        try:
            # Step 1: Parse EDI
            if self.logger:
                self.logger.info("Step 1: Parsing EDI 850...")

            parsed_data = await self._parse_edi(edi_content)
            result["steps"]["parse"]["status"] = "success"
            result["steps"]["parse"]["data"] = parsed_data

            po_number = parsed_data.get("beg_segment", {}).get("purchase_order_number", "UNKNOWN")

            if self.logger:
                self.logger.info(f"✓ Parse successful - PO: {po_number}")

            # Save parse step to database
            if self.db_service:
                self.db_service.create_job_step({
                    "job_id": job_id,
                    "step_name": "parse",
                    "status": "success",
                    "data": parsed_data
                })
                self.db_service.update_job(job_id, {"po_number": po_number})
                self._log_to_db(job_id, "INFO", f"Parse successful - PO: {po_number}")

            # Step 2: Transform to ERP schema
            if self.logger:
                self.logger.info("Step 2: Transforming to ERP schema...")

            erp_payload = await self._transform_to_erp(parsed_data)
            result["steps"]["transform"]["status"] = "success"
            result["steps"]["transform"]["data"] = erp_payload

            if self.logger:
                self.logger.info(f"✓ Transform successful - Total: ${erp_payload['total_amount']:.2f}")

            # Save transform step to database
            if self.db_service:
                self.db_service.create_job_step({
                    "job_id": job_id,
                    "step_name": "transform",
                    "status": "success",
                    "data": erp_payload
                })
                vendor_name = erp_payload.get("vendor", {}).get("vendor_name", "")
                self.db_service.update_job(job_id, {
                    "total_amount": erp_payload.get("total_amount"),
                    "vendor_name": vendor_name
                })
                self._log_to_db(job_id, "INFO", f"Transform successful - Total: ${erp_payload['total_amount']:.2f}")

            # Step 3: Validate business rules
            if self.logger:
                self.logger.info("Step 3: Validating business rules...")

            validation_result = await self._validate_payload(erp_payload)
            result["steps"]["validate"]["status"] = "success" if not validation_result else "failed"
            result["steps"]["validate"]["errors"] = validation_result

            if validation_result:
                error_msg = f"Business rule validation failed: {len(validation_result)} errors"
                if self.logger:
                    self.logger.error(f"✗ {error_msg}")
                    for err in validation_result:
                        self.logger.error(f"  - {err}")

                # Save validation failure to database
                if self.db_service:
                    self.db_service.create_job_step({
                        "job_id": job_id,
                        "step_name": "validate",
                        "status": "failed",
                        "error": error_msg,
                        "data": {"errors": validation_result}
                    })
                    self._log_to_db(job_id, "ERROR", error_msg, {"errors": validation_result})

                result["success"] = False
                result["final_result"] = {
                    "error": error_msg,
                    "validation_errors": validation_result
                }
            else:
                if self.logger:
                    self.logger.info("✓ Validation successful")

                # Save validation success to database
                if self.db_service:
                    self.db_service.create_job_step({
                        "job_id": job_id,
                        "step_name": "validate",
                        "status": "success"
                    })
                    self._log_to_db(job_id, "INFO", "Validation successful")

                # Step 4: Post to ERP API (with retries)
                if self.logger:
                    self.logger.info("Step 4: Posting to ERP API...")

                erp_response = await self._post_to_erp_with_retry(erp_payload, result, job_id)
                result["steps"]["post_to_erp"]["status"] = "success"
                result["steps"]["post_to_erp"]["data"] = erp_response

                erp_po_id = erp_response.get("erp_po_id", "UNKNOWN")

                if self.logger:
                    self.logger.info(f"✓ ERP post successful - ERP PO ID: {erp_po_id}")

                # Save post_to_erp step to database
                if self.db_service:
                    self.db_service.create_job_step({
                        "job_id": job_id,
                        "step_name": "post_to_erp",
                        "status": "success",
                        "data": erp_response,
                        "attempts": result["steps"]["post_to_erp"]["attempts"]
                    })
                    self.db_service.update_job(job_id, {"erp_po_id": erp_po_id})
                    self._log_to_db(job_id, "INFO", f"ERP post successful - ERP PO ID: {erp_po_id}")

                result["success"] = True
                result["final_result"] = erp_response

        except EDIParsingError as e:
            error_msg = f"EDI parsing error: {str(e)}"
            result["steps"]["parse"]["status"] = "failed"
            result["steps"]["parse"]["error"] = str(e)
            if self.logger:
                self.logger.error(f"✗ {error_msg}")

            # Save parse failure to database
            if self.db_service:
                self.db_service.create_job_step({
                    "job_id": job_id,
                    "step_name": "parse",
                    "status": "failed",
                    "error": str(e)
                })
                self._log_to_db(job_id, "ERROR", error_msg)

        except TransformationError as e:
            error_msg = f"Transformation error: {str(e)}"
            result["steps"]["transform"]["status"] = "failed"
            result["steps"]["transform"]["error"] = str(e)
            if self.logger:
                self.logger.error(f"✗ {error_msg}")

            # Save transform failure to database
            if self.db_service:
                self.db_service.create_job_step({
                    "job_id": job_id,
                    "step_name": "transform",
                    "status": "failed",
                    "error": str(e)
                })
                self._log_to_db(job_id, "ERROR", error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            if self.logger:
                self.logger.error(f"✗ {error_msg}")
            # Mark the last pending step as failed
            for step_name, step_data in result["steps"].items():
                if step_data["status"] == "pending":
                    step_data["status"] = "failed"
                    step_data["error"] = str(e)

                    # Save failed step to database
                    if self.db_service:
                        self.db_service.create_job_step({
                            "job_id": job_id,
                            "step_name": step_name,
                            "status": "failed",
                            "error": str(e)
                        })
                    break

            # Log error to database
            if self.db_service:
                self._log_to_db(job_id, "ERROR", error_msg)

        finally:
            # Calculate duration
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            result["completed_at"] = end_time.isoformat() + "Z"
            result["duration_seconds"] = round(duration, 2)

            if self.logger:
                status_emoji = "✓" if result["success"] else "✗"
                self.logger.info(f"{status_emoji} Job {job_id} completed in {duration:.2f}s - Success: {result['success']}")

            # Update final job status in database
            if self.db_service:
                self.db_service.update_job(job_id, {
                    "completed_at": end_time,
                    "duration_seconds": round(duration, 2),
                    "success": result["success"]
                })
                completion_msg = f"Job completed in {duration:.2f}s - Success: {result['success']}"
                self._log_to_db(job_id, "INFO", completion_msg)

        return result

    async def _parse_edi(self, edi_content: str) -> dict:
        """Parse EDI content"""
        return self.parser.parse(edi_content)

    async def _transform_to_erp(self, parsed_data: dict) -> dict:
        """Transform parsed EDI to ERP schema"""
        return self.mapper.transform(parsed_data)

    async def _validate_payload(self, erp_payload: dict) -> Optional[List[str]]:
        """
        Validate ERP payload against business rules

        Returns:
            List of error messages if validation fails, None if successful
        """
        # Convert dict to Pydantic model for validation
        try:
            erp_po = ERPPurchaseOrder(**erp_payload)
            errors = _validate_business_rules(erp_po)
            return errors if errors else None
        except Exception as e:
            return [f"Schema validation error: {str(e)}"]

    async def _post_to_erp_with_retry(self, erp_payload: dict, result: dict, job_id: str) -> dict:
        """
        Post to ERP API with retry logic and exponential backoff

        Args:
            erp_payload: ERP-formatted purchase order
            result: Result dictionary to track attempts
            job_id: Job ID for logging

        Returns:
            ERP API response

        Raises:
            Exception: If all retry attempts fail
        """
        last_error = None
        delay = self.retry_delay

        for attempt in range(1, self.max_retries + 1):
            result["steps"]["post_to_erp"]["attempts"] = attempt

            try:
                if self.logger and attempt > 1:
                    self.logger.info(f"  Retry attempt {attempt}/{self.max_retries}...")

                if self.db_service and attempt > 1:
                    self._log_to_db(job_id, "WARNING", f"Retry attempt {attempt}/{self.max_retries}")

                # Convert dict to Pydantic model
                erp_po = ERPPurchaseOrder(**erp_payload)

                # Call mock ERP API
                response = await create_purchase_order(erp_po, x_simulate_error=None)

                # Convert response to dict
                if hasattr(response, 'model_dump'):
                    return response.model_dump()
                elif hasattr(response, 'dict'):
                    return response.dict()
                else:
                    # Response is already a dict or has dict-like attributes
                    return {
                        "success": getattr(response, 'success', True),
                        "transaction_id": getattr(response, 'transaction_id', str(uuid.uuid4())),
                        "message": getattr(response, 'message', 'Purchase order created'),
                        "erp_po_id": getattr(response, 'erp_po_id', None),
                        "timestamp": getattr(response, 'timestamp', datetime.utcnow().isoformat() + "Z"),
                        "details": getattr(response, 'details', None)
                    }

            except Exception as e:
                last_error = e
                if self.logger:
                    self.logger.warning(f"  Attempt {attempt} failed: {str(e)}")

                # If not the last attempt, wait before retrying
                if attempt < self.max_retries:
                    if self.logger:
                        self.logger.info(f"  Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)
                    # Exponential backoff
                    delay *= 2

        # All retries failed
        error_msg = f"All {self.max_retries} retry attempts failed. Last error: {str(last_error)}"
        result["steps"]["post_to_erp"]["status"] = "failed"
        result["steps"]["post_to_erp"]["error"] = error_msg

        # Save failure to database
        if self.db_service:
            self.db_service.create_job_step({
                "job_id": job_id,
                "step_name": "post_to_erp",
                "status": "failed",
                "error": error_msg,
                "attempts": self.max_retries
            })
            self._log_to_db(job_id, "ERROR", error_msg)

        raise Exception(error_msg)

    def _log_to_db(self, job_id: str, level: str, message: str, details: Optional[Dict] = None):
        """
        Helper method to log to database

        Args:
            job_id: Job ID
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message
            details: Optional additional details
        """
        if self.db_service:
            try:
                self.db_service.create_job_log({
                    "job_id": job_id,
                    "level": level,
                    "message": message,
                    "details": details
                })
            except Exception as e:
                # Don't fail the job if logging fails
                if self.logger:
                    self.logger.warning(f"Failed to log to database: {str(e)}")


class OrchestrationError(Exception):
    """Custom exception for orchestration errors"""
    pass

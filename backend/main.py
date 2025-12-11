"""
FastAPI Application Entry Point
EDI 850 → JSON → ERP API Integration Demo
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from edi_parser.parser import EDI850Parser, EDIParsingError
from transformer.mapper import ERPMapper, TransformationError
from mock_erp_api.endpoints import router as erp_router
from processor.orchestrator import IntegrationOrchestrator
from database import init_db, get_db, DatabaseService, Job

app = FastAPI(
    title="EDI 850 Integration Demo",
    description="Parse EDI 850, transform to ERP JSON, and post to mock ERP API",
    version="1.0.0"
)

# CORS middleware for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include mock ERP API router
app.include_router(erp_router)


# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    init_db()
    print("✓ Database initialized")


class EDIParseRequest(BaseModel):
    """Request model for EDI parsing"""
    edi_content: str


class EDIParseResponse(BaseModel):
    """Response model for EDI parsing"""
    success: bool
    parsed_data: Optional[dict] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "EDI 850 Integration Demo",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "components": {
            "parser": "ready",
            "transformer": "ready",
            "mock_erp": "ready",
            "database": "ready"
        }
    }


@app.post("/api/parse", response_model=EDIParseResponse)
async def parse_edi(request: EDIParseRequest):
    """
    Parse EDI 850 content and return structured JSON

    Args:
        request: EDI content in request body

    Returns:
        Parsed EDI data as JSON
    """
    try:
        parser = EDI850Parser()
        parsed_data = parser.parse(request.edi_content)

        return EDIParseResponse(
            success=True,
            parsed_data=parsed_data
        )
    except EDIParsingError as e:
        return EDIParseResponse(
            success=False,
            error=str(e)
        )
    except Exception as e:
        return EDIParseResponse(
            success=False,
            error=f"Unexpected error: {str(e)}"
        )


@app.post("/api/parse/upload")
async def parse_edi_file(file: UploadFile = File(...)):
    """
    Upload and parse an EDI 850 file

    Args:
        file: Uploaded EDI file

    Returns:
        Parsed EDI data as JSON
    """
    try:
        # Read file content
        content = await file.read()
        edi_content = content.decode('utf-8')

        # Parse EDI
        parser = EDI850Parser()
        parsed_data = parser.parse(edi_content)

        return {
            "success": True,
            "filename": file.filename,
            "parsed_data": parsed_data
        }
    except EDIParsingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/transform")
async def transform_parsed_edi(parsed_edi: dict):
    """
    Transform parsed EDI JSON to ERP schema

    Args:
        parsed_edi: Parsed EDI dictionary from parser

    Returns:
        ERP-formatted payload
    """
    try:
        mapper = ERPMapper()
        erp_payload = mapper.transform(parsed_edi)

        return {
            "success": True,
            "erp_payload": erp_payload
        }
    except TransformationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/process")
async def process_edi_to_erp(request: EDIParseRequest):
    """
    Complete pipeline: Parse EDI 850 and transform to ERP schema

    Args:
        request: EDI content in request body

    Returns:
        Both parsed EDI and transformed ERP payload
    """
    try:
        # Step 1: Parse EDI
        parser = EDI850Parser()
        parsed_data = parser.parse(request.edi_content)

        # Step 2: Transform to ERP schema
        mapper = ERPMapper()
        erp_payload = mapper.transform(parsed_data)

        return {
            "success": True,
            "parsed_edi": parsed_data,
            "erp_payload": erp_payload
        }
    except EDIParsingError as e:
        raise HTTPException(status_code=400, detail=f"Parsing error: {str(e)}")
    except TransformationError as e:
        raise HTTPException(status_code=400, detail=f"Transformation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/api/orchestrate")
async def orchestrate_edi_integration(request: EDIParseRequest, db: Session = Depends(get_db)):
    """
    Complete orchestrated pipeline: Parse → Transform → Validate → Post to ERP

    This endpoint uses the IntegrationOrchestrator to execute the full workflow
    with retry logic, comprehensive logging, database persistence, and detailed step-by-step tracking.

    Args:
        request: EDI content in request body
        db: Database session (injected)

    Returns:
        Complete job result with all steps, timings, and outcomes (also saved to database)
    """
    try:
        # Initialize orchestrator with retry configuration and database session
        orchestrator = IntegrationOrchestrator(
            max_retries=3,
            retry_delay=2.0,
            enable_logging=True,
            db=db
        )

        # Execute complete pipeline (will automatically save to database)
        result = await orchestrator.process_edi_file(request.edi_content)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestration error: {str(e)}")


# ========== Database Query Endpoints ==========

@app.get("/api/jobs/stats")
async def get_job_statistics(db: Session = Depends(get_db)):
    """
    Get overall job execution statistics

    Args:
        db: Database session

    Returns:
        Job statistics (total, success rate, average duration, etc.)
    """
    db_service = DatabaseService(db)
    stats = db_service.get_job_stats()

    return {
        "success": True,
        "stats": stats
    }


@app.get("/api/jobs/recent")
async def get_recent_jobs(limit: int = 10, db: Session = Depends(get_db)):
    """
    Get recent jobs (default: 10 most recent)

    Args:
        limit: Maximum number of jobs to return
        db: Database session

    Returns:
        List of recent jobs
    """
    db_service = DatabaseService(db)
    jobs = db_service.get_recent_jobs(limit=limit)

    return {
        "success": True,
        "count": len(jobs),
        "jobs": [
            {
                "job_id": job.job_id,
                "po_number": job.po_number,
                "success": job.success,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "duration_seconds": job.duration_seconds,
                "total_amount": job.total_amount,
                "vendor_name": job.vendor_name,
                "erp_po_id": job.erp_po_id
            }
            for job in jobs
        ]
    }


@app.get("/api/jobs/search")
async def search_jobs(
    po_number: Optional[str] = None,
    vendor_name: Optional[str] = None,
    success: Optional[bool] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Search jobs by various criteria

    Args:
        po_number: Filter by PO number (partial match)
        vendor_name: Filter by vendor name (partial match)
        success: Filter by success status (true/false)
        limit: Maximum number of results
        db: Database session

    Returns:
        Matching jobs
    """
    db_service = DatabaseService(db)
    jobs = db_service.search_jobs(
        po_number=po_number,
        vendor_name=vendor_name,
        success=success,
        limit=limit
    )

    return {
        "success": True,
        "count": len(jobs),
        "jobs": [
            {
                "job_id": job.job_id,
                "po_number": job.po_number,
                "success": job.success,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "total_amount": job.total_amount,
                "vendor_name": job.vendor_name,
                "erp_po_id": job.erp_po_id
            }
            for job in jobs
        ]
    }


@app.get("/api/jobs/{job_id}")
async def get_job_details(job_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific job

    Args:
        job_id: Job UUID
        db: Database session

    Returns:
        Complete job details with steps and logs
    """
    db_service = DatabaseService(db)
    job = db_service.get_job_by_id(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Get steps and logs
    steps = db_service.get_job_steps(job_id)
    logs = db_service.get_job_logs(job_id)

    return {
        "success": True,
        "job": {
            "job_id": job.job_id,
            "po_number": job.po_number,
            "success": job.success,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "duration_seconds": job.duration_seconds,
            "total_amount": job.total_amount,
            "vendor_name": job.vendor_name,
            "erp_po_id": job.erp_po_id
        },
        "steps": [
            {
                "step_name": step.step_name,
                "status": step.status,
                "data": step.data,
                "error": step.error,
                "attempts": step.attempts,
                "created_at": step.created_at.isoformat() if step.created_at else None
            }
            for step in steps
        ],
        "logs": [
            {
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level,
                "message": log.message,
                "details": log.details
            }
            for log in logs
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

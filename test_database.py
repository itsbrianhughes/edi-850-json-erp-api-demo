"""
Database Integration Test
Tests the complete database persistence with orchestrator
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from database import init_db, get_db_session, DatabaseService
from processor.orchestrator import IntegrationOrchestrator


async def test_database_integration():
    """Test complete database integration with orchestrator"""

    print("\n" + "="*70)
    print("DATABASE INTEGRATION TEST")
    print("="*70 + "\n")

    # Initialize database
    print("1. Initializing database...")
    init_db()
    print("   ✓ Database initialized\n")

    # Load sample EDI file
    print("2. Loading sample EDI file...")
    sample_file = Path(__file__).parent / "sample_data" / "sample_850.edi"

    if not sample_file.exists():
        print(f"   ✗ Sample file not found: {sample_file}")
        return

    with open(sample_file, 'r') as f:
        edi_content = f.read()

    print(f"   ✓ Loaded {len(edi_content)} bytes from {sample_file.name}\n")

    # Process EDI with database persistence
    print("3. Processing EDI with database persistence...")

    with get_db_session() as db:
        # Create orchestrator with database session
        orchestrator = IntegrationOrchestrator(
            max_retries=3,
            retry_delay=2.0,
            enable_logging=True,
            db=db
        )

        # Process the file
        result = await orchestrator.process_edi_file(edi_content)

        print(f"   ✓ Processing complete")
        print(f"   Job ID: {result['job_id']}")
        print(f"   Success: {result['success']}")
        print(f"   Duration: {result['duration_seconds']}s\n")

        # Verify database persistence
        print("4. Verifying database persistence...")

        db_service = DatabaseService(db)

        # Check job was saved
        job = db_service.get_job_by_id(result['job_id'])
        if job:
            print(f"   ✓ Job record saved to database")
            print(f"     - PO Number: {job.po_number}")
            print(f"     - Vendor: {job.vendor_name}")
            print(f"     - Total Amount: ${job.total_amount:,.2f}")
            print(f"     - ERP PO ID: {job.erp_po_id}")
        else:
            print(f"   ✗ Job not found in database!")
            return

        # Check steps were saved
        steps = db_service.get_job_steps(result['job_id'])
        print(f"\n   ✓ {len(steps)} steps saved to database:")
        for step in steps:
            status_emoji = "✓" if step.status == "success" else "✗"
            print(f"     {status_emoji} {step.step_name}: {step.status}", end="")
            if step.attempts and step.attempts > 1:
                print(f" ({step.attempts} attempts)", end="")
            print()

        # Check logs were saved
        logs = db_service.get_job_logs(result['job_id'])
        print(f"\n   ✓ {len(logs)} log entries saved to database")

        # Show log breakdown
        log_levels = {}
        for log in logs:
            log_levels[log.level] = log_levels.get(log.level, 0) + 1

        for level, count in sorted(log_levels.items()):
            print(f"     - {level}: {count}")

    # Query database statistics
    print("\n5. Querying database statistics...")
    with get_db_session() as db:
        db_service = DatabaseService(db)
        stats = db_service.get_job_stats()

        print(f"   Total Jobs: {stats['total_jobs']}")
        print(f"   Successful: {stats['successful_jobs']}")
        print(f"   Failed: {stats['failed_jobs']}")
        print(f"   Success Rate: {stats['success_rate']:.1f}%")
        print(f"   Avg Duration: {stats['average_duration_seconds']:.2f}s")
        print(f"   Total Amount: ${stats['total_amount_processed']:,.2f}")

    # Test search functionality
    print("\n6. Testing search functionality...")
    with get_db_session() as db:
        db_service = DatabaseService(db)

        # Search by PO number
        jobs = db_service.search_jobs(po_number="PO-2024")
        print(f"   ✓ Search by PO number: {len(jobs)} results")

        # Search by vendor
        jobs = db_service.search_jobs(vendor_name="QUALITY")
        print(f"   ✓ Search by vendor: {len(jobs)} results")

        # Search successful jobs only
        jobs = db_service.get_successful_jobs(limit=10)
        print(f"   ✓ Successful jobs: {len(jobs)} results")

    print("\n" + "="*70)
    print("✓ ALL DATABASE INTEGRATION TESTS PASSED")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Run async test
    asyncio.run(test_database_integration())

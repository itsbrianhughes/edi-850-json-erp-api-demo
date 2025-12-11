"""
Database Initialization Script
Creates tables and optionally resets the database
"""

import sys
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, reset_db, get_db_session, DatabaseService


def initialize_database():
    """Initialize the database (create tables if they don't exist)"""
    print("Initializing database...")
    init_db()
    print("✓ Database initialization complete")


def reset_database():
    """Reset the database (drop all tables and recreate)"""
    print("⚠️  WARNING: This will delete all existing data!")
    confirm = input("Are you sure you want to reset the database? (yes/no): ")

    if confirm.lower() == "yes":
        print("Resetting database...")
        reset_db()
        print("✓ Database reset complete")
    else:
        print("Database reset cancelled")


def show_stats():
    """Show database statistics"""
    with get_db_session() as db:
        db_service = DatabaseService(db)
        stats = db_service.get_job_stats()

        print("\n" + "="*50)
        print("DATABASE STATISTICS")
        print("="*50)
        print(f"Total Jobs: {stats['total_jobs']}")
        print(f"Successful Jobs: {stats['successful_jobs']}")
        print(f"Failed Jobs: {stats['failed_jobs']}")
        print(f"Success Rate: {stats['success_rate']:.2f}%")
        print(f"Average Duration: {stats['average_duration_seconds']:.2f}s")
        print(f"Total Amount Processed: ${stats['total_amount_processed']:,.2f}")
        print("="*50 + "\n")


def list_recent_jobs(limit=10):
    """List recent jobs"""
    with get_db_session() as db:
        db_service = DatabaseService(db)
        jobs = db_service.get_recent_jobs(limit=limit)

        print(f"\n{limit} Most Recent Jobs:")
        print("-" * 120)
        print(f"{'Job ID':<40} {'PO Number':<20} {'Status':<10} {'Amount':<12} {'Duration':<10}")
        print("-" * 120)

        for job in jobs:
            status = "✓ Success" if job.success else "✗ Failed"
            amount = f"${job.total_amount:,.2f}" if job.total_amount else "N/A"
            duration = f"{job.duration_seconds:.2f}s" if job.duration_seconds else "N/A"

            print(f"{job.job_id:<40} {job.po_number or 'N/A':<20} {status:<10} {amount:<12} {duration:<10}")

        print("-" * 120 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database Management Script")
    parser.add_argument(
        "action",
        choices=["init", "reset", "stats", "list"],
        help="Action to perform: init (initialize), reset (drop and recreate), stats (show statistics), list (show recent jobs)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of jobs to list (default: 10)"
    )

    args = parser.parse_args()

    if args.action == "init":
        initialize_database()
    elif args.action == "reset":
        reset_database()
    elif args.action == "stats":
        show_stats()
    elif args.action == "list":
        list_recent_jobs(limit=args.limit)

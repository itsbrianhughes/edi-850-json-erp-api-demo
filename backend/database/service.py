"""
Database Service Layer
Provides CRUD operations for jobs, steps, and logs
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import Job, JobStep, JobLog


class DatabaseService:
    """
    Service layer for database operations
    """

    def __init__(self, db: Session):
        self.db = db

    # ========== Job Operations ==========

    def create_job(self, job_data: Dict[str, Any]) -> Job:
        """
        Create a new job record
        """
        job = Job(**job_data)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job_by_id(self, job_id: str) -> Optional[Job]:
        """
        Get job by UUID
        """
        return self.db.query(Job).filter(Job.job_id == job_id).first()

    def get_job_by_po_number(self, po_number: str) -> Optional[Job]:
        """
        Get job by PO number
        """
        return self.db.query(Job).filter(Job.po_number == po_number).first()

    def get_all_jobs(self, limit: int = 100, offset: int = 0) -> List[Job]:
        """
        Get all jobs with pagination
        """
        return self.db.query(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset).all()

    def get_recent_jobs(self, limit: int = 10) -> List[Job]:
        """
        Get most recent jobs
        """
        return self.db.query(Job).order_by(Job.started_at.desc()).limit(limit).all()

    def get_successful_jobs(self, limit: int = 100) -> List[Job]:
        """
        Get successful jobs only
        """
        return self.db.query(Job).filter(Job.success == True).order_by(Job.started_at.desc()).limit(limit).all()

    def get_failed_jobs(self, limit: int = 100) -> List[Job]:
        """
        Get failed jobs only
        """
        return self.db.query(Job).filter(Job.success == False).order_by(Job.started_at.desc()).limit(limit).all()

    def update_job(self, job_id: str, update_data: Dict[str, Any]) -> Optional[Job]:
        """
        Update job record
        """
        job = self.get_job_by_id(job_id)
        if job:
            for key, value in update_data.items():
                setattr(job, key, value)
            job.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(job)
        return job

    def delete_job(self, job_id: str) -> bool:
        """
        Delete job and all related steps/logs (cascade)
        """
        job = self.get_job_by_id(job_id)
        if job:
            self.db.delete(job)
            self.db.commit()
            return True
        return False

    # ========== Job Step Operations ==========

    def create_job_step(self, step_data: Dict[str, Any]) -> JobStep:
        """
        Create a new job step record
        """
        step = JobStep(**step_data)
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_job_steps(self, job_id: str) -> List[JobStep]:
        """
        Get all steps for a job
        """
        return self.db.query(JobStep).filter(JobStep.job_id == job_id).order_by(JobStep.created_at).all()

    def update_job_step(self, step_id: int, update_data: Dict[str, Any]) -> Optional[JobStep]:
        """
        Update job step
        """
        step = self.db.query(JobStep).filter(JobStep.id == step_id).first()
        if step:
            for key, value in update_data.items():
                setattr(step, key, value)
            self.db.commit()
            self.db.refresh(step)
        return step

    # ========== Job Log Operations ==========

    def create_job_log(self, log_data: Dict[str, Any]) -> JobLog:
        """
        Create a new job log entry
        """
        log = JobLog(**log_data)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_job_logs(self, job_id: str, level: Optional[str] = None) -> List[JobLog]:
        """
        Get all logs for a job, optionally filtered by level
        """
        query = self.db.query(JobLog).filter(JobLog.job_id == job_id)
        if level:
            query = query.filter(JobLog.level == level)
        return query.order_by(JobLog.timestamp).all()

    def create_bulk_logs(self, logs_data: List[Dict[str, Any]]) -> List[JobLog]:
        """
        Create multiple log entries at once
        """
        logs = [JobLog(**log_data) for log_data in logs_data]
        self.db.add_all(logs)
        self.db.commit()
        return logs

    # ========== Statistics & Analytics ==========

    def get_job_stats(self) -> Dict[str, Any]:
        """
        Get overall job statistics
        """
        total_jobs = self.db.query(Job).count()
        successful_jobs = self.db.query(Job).filter(Job.success == True).count()
        failed_jobs = self.db.query(Job).filter(Job.success == False).count()

        avg_duration = self.db.query(Job).filter(Job.duration_seconds.isnot(None)).with_entities(
            Job.duration_seconds
        ).all()
        avg_duration_value = sum([d[0] for d in avg_duration]) / len(avg_duration) if avg_duration else 0

        total_amount = self.db.query(Job).filter(Job.total_amount.isnot(None)).with_entities(
            Job.total_amount
        ).all()
        total_amount_value = sum([a[0] for a in total_amount]) if total_amount else 0

        return {
            "total_jobs": total_jobs,
            "successful_jobs": successful_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0,
            "average_duration_seconds": round(avg_duration_value, 2),
            "total_amount_processed": round(total_amount_value, 2)
        }

    def search_jobs(
        self,
        po_number: Optional[str] = None,
        vendor_name: Optional[str] = None,
        success: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Job]:
        """
        Advanced job search with multiple filters
        """
        query = self.db.query(Job)

        if po_number:
            query = query.filter(Job.po_number.like(f"%{po_number}%"))
        if vendor_name:
            query = query.filter(Job.vendor_name.like(f"%{vendor_name}%"))
        if success is not None:
            query = query.filter(Job.success == success)
        if start_date:
            query = query.filter(Job.started_at >= start_date)
        if end_date:
            query = query.filter(Job.started_at <= end_date)

        return query.order_by(Job.started_at.desc()).limit(limit).all()

"""
Database Models for EDI Integration Jobs
Stores job execution history, steps, and logs
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Job(Base):
    """
    Main job record storing overall execution details
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), unique=True, nullable=False, index=True)  # UUID
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    success = Column(Boolean, default=False)

    # EDI/Business Data
    edi_content = Column(Text)  # Store original EDI for audit
    po_number = Column(String(50), index=True)  # For easy querying
    total_amount = Column(Float)
    erp_po_id = Column(String(100))  # ERP system's PO ID
    vendor_name = Column(String(200))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    steps = relationship("JobStep", back_populates="job", cascade="all, delete-orphan")
    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job(job_id={self.job_id}, po_number={self.po_number}, success={self.success})>"


class JobStep(Base):
    """
    Individual pipeline step execution details
    """
    __tablename__ = "job_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey("jobs.job_id"), nullable=False, index=True)
    step_name = Column(String(50), nullable=False)  # parse, transform, validate, post_to_erp
    status = Column(String(20), nullable=False)  # success, failed, pending
    data = Column(JSON)  # Step output data (if successful)
    error = Column(Text)  # Error message (if failed)
    attempts = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="steps")

    def __repr__(self):
        return f"<JobStep(job_id={self.job_id}, step={self.step_name}, status={self.status})>"


class JobLog(Base):
    """
    Detailed logs for each job execution
    """
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey("jobs.job_id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    details = Column(JSON)  # Additional structured data

    # Relationships
    job = relationship("Job", back_populates="logs")

    def __repr__(self):
        return f"<JobLog(job_id={self.job_id}, level={self.level}, message={self.message[:50]})>"

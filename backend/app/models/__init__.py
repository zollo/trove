"""ORM models. Importing this package registers every table on Base.metadata."""
from app.models.api_key import ApiKey
from app.models.document import Document, DocumentKind
from app.models.job import EmploymentType, Job, JobStatus, WorkMode
from app.models.profile import CandidateProfile, SalaryPeriod
from app.models.user import User, UserRole

__all__ = [
    "ApiKey",
    "CandidateProfile",
    "Document",
    "DocumentKind",
    "EmploymentType",
    "Job",
    "JobStatus",
    "SalaryPeriod",
    "User",
    "UserRole",
    "WorkMode",
]

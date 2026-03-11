from __future__ import annotations

import datetime
import logging
from typing import Optional

from sqlalchemy import Column, Table, types, Boolean, Integer, DateTime

from ckan.model import meta

log = logging.getLogger(__name__)

HEARTBEAT_TIMEOUT = datetime.timedelta(minutes=5)

link_check_result_table = Table(
    "link_check_result",
    meta.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("resource_id", types.UnicodeText, index=True, nullable=False),
    Column("package_id", types.UnicodeText, index=True, nullable=False),
    Column("package_name", types.UnicodeText, nullable=True),
    Column("url", types.UnicodeText, nullable=False),
    Column("status_code", Integer, nullable=True),
    Column("error", types.UnicodeText, nullable=True),
    Column("checked_at", DateTime, default=datetime.datetime.utcnow),
    Column("is_broken", Boolean, default=False),
)

link_check_job_table = Table(
    "link_check_job",
    meta.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("job_id", types.UnicodeText, nullable=False),
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
    Column("heartbeat_at", DateTime, nullable=True),
)


class LinkCheckResult:
    id: int
    resource_id: str
    package_id: str
    package_name: Optional[str]
    url: str
    status_code: Optional[int]
    error: Optional[str]
    checked_at: datetime.datetime
    is_broken: bool


class LinkCheckJob:
    id: int
    job_id: str
    created_at: datetime.datetime
    heartbeat_at: Optional[datetime.datetime]


meta.registry.map_imperatively(LinkCheckResult, link_check_result_table)
meta.registry.map_imperatively(LinkCheckJob, link_check_job_table)


def upsert_result(
    resource_id: str,
    package_id: str,
    url: str,
    status_code: Optional[int],
    error: Optional[str],
    is_broken: bool,
    package_name: Optional[str] = None,
):
    session = meta.Session
    result = (
        session.query(LinkCheckResult)
        .filter_by(resource_id=resource_id)
        .first()
    )
    if result is None:
        result = LinkCheckResult()
        result.resource_id = resource_id
        session.add(result)

    result.package_id = package_id
    result.package_name = package_name
    result.url = url
    result.status_code = status_code
    result.error = error
    result.is_broken = is_broken
    result.checked_at = datetime.datetime.utcnow()
    session.commit()


def get_results(
    page: int = 1,
    per_page: int = 20,
    broken_only: bool = False,
) -> list[LinkCheckResult]:
    q = meta.Session.query(LinkCheckResult)
    if broken_only:
        q = q.filter(LinkCheckResult.is_broken.is_(True))
    q = q.order_by(LinkCheckResult.checked_at.desc())
    offset = (page - 1) * per_page
    return q.offset(offset).limit(per_page).all()


def count_results(broken_only: bool = False) -> int:
    q = meta.Session.query(LinkCheckResult)
    if broken_only:
        q = q.filter(LinkCheckResult.is_broken.is_(True))
    return q.count()


def get_summary() -> dict:
    total = count_results(broken_only=False)
    broken = count_results(broken_only=True)
    last_checked = (
        meta.Session.query(LinkCheckResult.checked_at)
        .order_by(LinkCheckResult.checked_at.desc())
        .first()
    )
    return {
        "total": total,
        "broken": broken,
        "ok": total - broken,
        "last_checked": last_checked[0] if last_checked else None,
    }


def clear_results():
    meta.Session.query(LinkCheckResult).delete()
    meta.Session.commit()


# -- Job state --

def get_saved_job() -> Optional[LinkCheckJob]:
    return meta.Session.query(LinkCheckJob).first()


def get_saved_job_id() -> Optional[str]:
    row = get_saved_job()
    return row.job_id if row else None


def save_new_job(job_id: str):
    """Start a fresh run with a new created_at."""
    session = meta.Session
    session.query(LinkCheckJob).delete()
    job = LinkCheckJob()
    job.job_id = job_id
    job.created_at = datetime.datetime.utcnow()
    session.add(job)
    session.commit()


def resume_job(job_id: str):
    """Resume a crashed run — keeps created_at so already-checked
    resources are skipped, updates job_id for the new RQ job."""
    row = meta.Session.query(LinkCheckJob).first()
    if row:
        row.job_id = job_id
        row.heartbeat_at = None
        meta.Session.commit()
    else:
        save_new_job(job_id)


def update_heartbeat():
    row = meta.Session.query(LinkCheckJob).first()
    if row:
        row.heartbeat_at = datetime.datetime.utcnow()
        meta.Session.commit()


def is_heartbeat_stale() -> bool:
    """True if the job hasn't sent a heartbeat within HEARTBEAT_TIMEOUT."""
    row = get_saved_job()
    if not row:
        return False
    ts = row.heartbeat_at or row.created_at
    return datetime.datetime.utcnow() - ts > HEARTBEAT_TIMEOUT


def clear_job():
    meta.Session.query(LinkCheckJob).delete()
    meta.Session.commit()

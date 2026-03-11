import datetime
import logging
import time

from rq import get_current_job
from sqlalchemy import or_

from ckan import model

from ckanext.link import config as link_config
from ckanext.link.model import (
    LinkCheckResult,
    get_saved_job,
    update_heartbeat,
    upsert_result,
)
from ckanext.link.safefetch import safe_check_url

log = logging.getLogger(__name__)


def check_all_links():
    """Background job: check all resource URLs for broken links.

    Supports resuming after a crash — only checks resources that haven't
    been checked since this run's created_at timestamp.
    """
    delay = link_config.batch_delay()
    job = get_current_job()

    saved = get_saved_job()
    run_started = saved.created_at if saved else datetime.datetime.utcnow()

    # Write initial heartbeat so staleness detection works immediately.
    update_heartbeat()

    # Query only resources not yet checked in this run.
    resources = (
        model.Session.query(
            model.Resource.id,
            model.Resource.url,
            model.Resource.package_id,
            model.Package.name,
        )
        .join(model.Package, model.Resource.package_id == model.Package.id)
        .outerjoin(
            LinkCheckResult,
            model.Resource.id == LinkCheckResult.resource_id,
        )
        .filter(model.Package.state == "active")
        .filter(model.Resource.state == "active")
        .filter(
            or_(
                LinkCheckResult.checked_at.is_(None),
                LinkCheckResult.checked_at < run_started,
            )
        )
        .all()
    )

    # Filter to HTTP(S) URLs only.
    resources = [
        r for r in resources
        if r.url and r.url.startswith(("http://", "https://"))
    ]

    total = len(resources)
    log.info("Link checker: %d resources to check", total)
    checked = 0
    broken = 0

    if job:
        job.meta["progress"] = {
            "total": total, "checked": 0, "broken": 0,
        }
        job.save_meta()

    for resource_id, url, package_id, package_name in resources:
        try:
            result = safe_check_url(url)
            upsert_result(
                resource_id=resource_id,
                package_id=package_id,
                url=url,
                status_code=result["status_code"],
                error=result["error"],
                is_broken=result["is_broken"],
                package_name=package_name,
            )

            if result["is_broken"]:
                broken += 1
        except Exception:
            log.exception(
                "Error processing resource %s (%s)", resource_id, url
            )
            broken += 1

        checked += 1
        update_heartbeat()

        if job:
            job.meta["progress"] = {
                "total": total, "checked": checked, "broken": broken,
            }
            job.save_meta()

        if delay > 0:
            time.sleep(delay)

    log.info(
        "Link checker: finished. Checked %d, broken %d.", checked, broken
    )

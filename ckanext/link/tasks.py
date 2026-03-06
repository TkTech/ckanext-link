import logging
import time

from rq import get_current_job

from ckan import model

from ckanext.link import config as link_config
from ckanext.link.model import upsert_result
from ckanext.link.safefetch import safe_check_url

log = logging.getLogger(__name__)


def check_all_links():
    """Background job: check all resource URLs for broken links."""
    delay = link_config.batch_delay()
    job = get_current_job()

    resources = (
        model.Session.query(
            model.Resource.id,
            model.Resource.url,
            model.Resource.package_id,
            model.Package.name,
        )
        .join(model.Package, model.Resource.package_id == model.Package.id)
        .filter(model.Package.state == "active")
        .filter(model.Resource.state == "active")
        .all()
    )

    # Filter to HTTP(S) URLs only.
    resources = [
        r for r in resources
        if r.url and r.url.startswith(("http://", "https://"))
    ]

    total = len(resources)
    log.info("Link checker: checking %d resources", total)
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

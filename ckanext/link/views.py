import logging

from flask import Blueprint, jsonify
from rq.exceptions import NoSuchJobError
from rq.job import Job as RqJob

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.jobs as jobs
import ckan.logic as logic
import ckan.plugins.toolkit as tk
from ckan.common import _, current_user

from ckanext.link import model as link_model
from ckanext.link.tasks import check_all_links

log = logging.getLogger(__name__)

link_checker = Blueprint(
    "link_checker", __name__, url_prefix="/ckan-admin/link-checker"
)


def _get_job_info():
    """Return (status, progress) for the current link check job.

    Returns ("stale", progress) when the worker appears to have died
    (heartbeat not updated within the timeout window).
    Returns (None, {}) if no job is tracked.
    """
    job_id = link_model.get_saved_job_id()
    if not job_id:
        return None, {}
    try:
        conn = jobs.get_queue().connection
        job = RqJob.fetch(job_id, connection=conn)
        status = job.get_status()
        progress = job.meta.get("progress", {})
        # Clean up finished/failed jobs.
        if status in ("finished", "failed", "stopped", "canceled"):
            link_model.clear_job()
            return status, progress
        # Detect dead worker via heartbeat.
        if status in ("queued", "started") and link_model.is_heartbeat_stale():
            return "stale", progress
        return status, progress
    except NoSuchJobError:
        # Job expired from Redis — check if heartbeat is also stale.
        if link_model.is_heartbeat_stale():
            return "stale", {}
        link_model.clear_job()
        return None, {}


@link_checker.before_request
def before_request():
    try:
        context = {"user": current_user.name, "auth_user_obj": current_user}
        logic.check_access("sysadmin", context)
    except logic.NotAuthorized:
        base.abort(403, _("Need to be system administrator to administer"))


@link_checker.route("", methods=["GET"])
def index():
    page = tk.request.args.get("page", 1, type=int)
    broken_only = tk.request.args.get("broken_only", "") == "1"

    summary = link_model.get_summary()
    total_count = link_model.count_results(broken_only=broken_only)
    results = link_model.get_results(
        page=page, per_page=20, broken_only=broken_only
    )

    page_obj = h.Page(
        collection=results,
        page=page,
        item_count=total_count,
        items_per_page=20,
        url=h.pager_url,
        presliced_list=True,
    )

    job_status, job_progress = _get_job_info()

    return tk.render(
        "admin/link_checker.html",
        extra_vars={
            "summary": summary,
            "page": page_obj,
            "broken_only": broken_only,
            "job_status": job_status,
            "job_progress": job_progress,
        },
    )


@link_checker.route("/progress", methods=["GET"])
def progress():
    job_status, job_progress = _get_job_info()
    return jsonify({
        "status": job_status,
        "progress": job_progress,
    })


@link_checker.route("", methods=["POST"])
def run_check():
    job_status, _progress = _get_job_info()
    if job_status in ("queued", "started"):
        h.flash_notice(_("A link check job is already running."))
        return h.redirect_to("link_checker.index")

    is_resume = job_status == "stale"

    job = jobs.enqueue(
        check_all_links,
        title="Link Checker: check all resource URLs",
        rq_kwargs={"timeout": 3600},
    )

    if is_resume:
        link_model.resume_job(job.id)
        h.flash_success(_("Resuming link check from where it left off."))
    else:
        link_model.clear_results()
        link_model.save_new_job(job.id)
        h.flash_success(_("Link check job has been queued."))

    return h.redirect_to("link_checker.index")

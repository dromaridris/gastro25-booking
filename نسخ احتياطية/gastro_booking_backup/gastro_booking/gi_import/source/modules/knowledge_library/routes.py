"""Knowledge Library administration routes — Sprint 5C."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import json

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.engines import permission_engine
from app.modules.knowledge_library import authoring_services
from app.modules.knowledge_library.forms import (
    ArchiveKnowledgeForm,
    KnowledgeLinkForm,
    KnowledgeObjectFilterForm,
    KnowledgeObjectForm,
)

bp = Blueprint("knowledge_library", __name__, url_prefix="/knowledge-library")


def _populate_filter_form(form: KnowledgeObjectFilterForm) -> None:
    form.object_type.choices = [("", "All types")] + authoring_services.object_type_catalogue()


@bp.route("/")
@login_required
@handle_service_errors
def index():
    permission_engine.require(current_user, "knowledge_library:edit")
    can_edit = True
    guideline_topics = authoring_services.list_guideline_topics_for_admin()
    return render_template(
        "knowledge_library/index.html",
        guideline_topics=guideline_topics,
        can_edit=can_edit,
    )


@bp.route("/objects", methods=["GET", "POST"])
@login_required
@handle_service_errors
def list_objects():
    form = KnowledgeObjectFilterForm()
    _populate_filter_form(form)
    if request.method == "GET" and request.args.get("object_type"):
        form.object_type.data = request.args.get("object_type")
    form.process(formdata=request.form if request.method == "POST" else None)
    object_type = form.object_type.data or None
    include_archived = bool(form.include_archived.data)
    records = authoring_services.list_knowledge_objects(
        current_user,
        object_type=object_type,
        include_archived=include_archived,
    )
    return render_template(
        "knowledge_library/list.html",
        records=records,
        filter_form=form,
        can_edit=permission_engine.check(current_user, "knowledge_library:edit"),
        can_suggest=permission_engine.check(current_user, "knowledge_library:suggest"),
    )


@bp.route("/objects/new", methods=["GET", "POST"])
@login_required
@handle_service_errors
def create_object():
    can_edit = permission_engine.check(current_user, "knowledge_library:edit")
    can_suggest = permission_engine.check(current_user, "knowledge_library:suggest")
    if not can_edit and not can_suggest:
        permission_engine.require(current_user, "knowledge_library:edit")

    form = KnowledgeObjectForm()
    if request.method == "GET":
        prefill = request.args.get("object_type")
        if prefill:
            form.object_type.data = prefill

    if form.validate_on_submit():
        try:
            record = authoring_services.create_knowledge_object(
                current_user,
                object_type=form.object_type.data,
                title=form.title.data,
                stable_id=form.stable_id.data,
                specialty_code=form.specialty_code.data,
                topic_key=form.topic_key.data,
                summary=form.summary.data,
                body=form.body.data,
                attributes=form.attributes_json.data,
                version_label=form.version_label.data or "1.0.0",
                as_suggestion=not can_edit and can_suggest,
            )
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("knowledge_library/form.html", form=form, mode="create")

        flash("Knowledge object saved as draft.", "success")
        return redirect(url_for("knowledge_library.view_object", record_id=record.id))

    return render_template("knowledge_library/form.html", form=form, mode="create")


@bp.route("/objects/<int:record_id>")
@login_required
@handle_service_errors
def view_object(record_id):
    record = authoring_services.get_knowledge_record(current_user, record_id)
    versions = authoring_services.list_versions(current_user, record.stable_id)
    links = authoring_services.list_links(current_user, record.stable_id)
    archive_form = ArchiveKnowledgeForm()
    link_form = KnowledgeLinkForm()
    return render_template(
        "knowledge_library/detail.html",
        record=record,
        versions=versions,
        links=links,
        archive_form=archive_form,
        link_form=link_form,
        can_edit=permission_engine.check(current_user, "knowledge_library:edit"),
    )


@bp.route("/objects/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_object(record_id):
    record = authoring_services.get_knowledge_record(current_user, record_id)
    form = KnowledgeObjectForm()

    if request.method == "GET":
        form.object_type.data = record.object_type
        form.title.data = record.title
        form.stable_id.data = record.stable_id
        form.specialty_code.data = record.specialty_code
        form.topic_key.data = record.topic_key
        form.version_label.data = record.version_label
        form.summary.data = record.summary
        form.body.data = record.body
        form.attributes_json.data = json.dumps(record.attributes, indent=2, ensure_ascii=False)

    if form.validate_on_submit():
        try:
            authoring_services.update_knowledge_object(
                current_user,
                record,
                title=form.title.data,
                specialty_code=form.specialty_code.data,
                topic_key=form.topic_key.data,
                summary=form.summary.data,
                body=form.body.data,
                attributes=form.attributes_json.data,
                version_label=form.version_label.data,
            )
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("knowledge_library/form.html", form=form, mode="edit", record=record)

        flash("Draft updated.", "success")
        return redirect(url_for("knowledge_library.view_object", record_id=record.id))

    return render_template("knowledge_library/form.html", form=form, mode="edit", record=record)


@bp.route("/objects/<int:record_id>/publish", methods=["POST"])
@login_required
@handle_service_errors
def publish_object(record_id):
    record = authoring_services.get_knowledge_record(current_user, record_id)
    try:
        authoring_services.publish_knowledge_object(current_user, record)
    except ValidationError as exc:
        flash(str(exc), "danger")
    else:
        flash("Knowledge published.", "success")
    return redirect(url_for("knowledge_library.view_object", record_id=record.id))


@bp.route("/objects/<int:record_id>/new-version", methods=["POST"])
@login_required
@handle_service_errors
def new_version(record_id):
    record = authoring_services.get_knowledge_record(current_user, record_id)
    try:
        new_record = authoring_services.create_new_version(current_user, record.stable_id)
    except ValidationError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("knowledge_library.view_object", record_id=record.id))
    flash(f"Version {new_record.version_sequence} draft created.", "success")
    return redirect(url_for("knowledge_library.edit_object", record_id=new_record.id))


@bp.route("/objects/<int:record_id>/archive", methods=["GET", "POST"])
@login_required
@handle_service_errors
def archive_object(record_id):
    record = authoring_services.get_knowledge_record(current_user, record_id)
    form = ArchiveKnowledgeForm()
    if form.validate_on_submit():
        try:
            authoring_services.archive_knowledge_object(current_user, record, form.reason.data)
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("knowledge_library/archive.html", form=form, record=record)
        flash("Knowledge archived.", "success")
        return redirect(url_for("knowledge_library.list_objects"))
    return render_template("knowledge_library/archive.html", form=form, record=record)


@bp.route("/objects/<int:record_id>/restore", methods=["POST"])
@login_required
@handle_service_errors
def restore_object(record_id):
    record = authoring_services.get_knowledge_record(current_user, record_id)
    try:
        authoring_services.restore_knowledge_object(current_user, record)
    except ValidationError as exc:
        flash(str(exc), "danger")
    else:
        flash("Knowledge restored.", "success")
    return redirect(url_for("knowledge_library.view_object", record_id=record.id))


@bp.route("/objects/<int:record_id>/links", methods=["POST"])
@login_required
@handle_service_errors
def add_link(record_id):
    record = authoring_services.get_knowledge_record(current_user, record_id)
    form = KnowledgeLinkForm()
    if form.validate_on_submit():
        try:
            authoring_services.upsert_link(
                current_user,
                from_stable_id=record.stable_id,
                to_stable_id=form.to_stable_id.data,
                link_type=form.link_type.data,
                version_sequence=record.version_sequence,
            )
        except ValidationError as exc:
            flash(str(exc), "danger")
        else:
            flash("Link added.", "success")
    return redirect(url_for("knowledge_library.view_object", record_id=record.id))

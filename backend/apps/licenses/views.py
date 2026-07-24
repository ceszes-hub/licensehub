import csv

from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.audit.services import record_event

from .forms import DocumentForm, LicenseForm, PartyContactFormSet, PartyForm
from .models import License, LicenseDocument, Party


@login_required
@permission_required("licenses.view_license", raise_exception=True)
def license_list(request):
    items = License.objects.select_related("manufacturer", "distributor", "owner")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    manufacturer = request.GET.get("manufacturer", "")
    organization = request.GET.get("organization", "").strip()
    if query:
        items = items.filter(
            Q(reference_code__icontains=query)
            | Q(name__icontains=query)
            | Q(manufacturer__name__icontains=query)
            | Q(distributor__name__icontains=query)
            | Q(organization__icontains=query)
            | Q(cost_center__icontains=query)
        )
    if status:
        items = items.filter(status=status)
    if manufacturer:
        items = items.filter(manufacturer_id=manufacturer)
    if organization:
        items = items.filter(organization=organization)
    all_items = License.objects.all()
    totals = all_items.aggregate(total_quantity=Sum("quantity"), total_value=Sum("cost"))
    status_counts = dict(all_items.values_list("status").annotate(total=Count("id")))
    page_obj = Paginator(items, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "licenses/list.html",
        {
            "licenses": page_obj,
            "page_obj": page_obj,
            "query": query,
            "selected_status": status,
            "selected_manufacturer": manufacturer,
            "selected_organization": organization,
            "statuses": License.Status.choices,
            "manufacturers": Party.objects.filter(kind=Party.Kind.MANUFACTURER, active=True),
            "organizations": all_items.exclude(organization="")
            .values_list("organization", flat=True)
            .distinct()
            .order_by("organization"),
            "total_licenses": all_items.count(),
            "total_quantity": totals["total_quantity"] or 0,
            "total_value": totals["total_value"] or 0,
            "active_count": status_counts.get(License.Status.ACTIVE, 0),
            "expiring_count": status_counts.get(License.Status.EXPIRING, 0),
            "expired_count": status_counts.get(License.Status.EXPIRED, 0),
        },
    )


def _save_uploaded_documents(request, license_obj, persist=True):
    document_type = request.POST.get("document_type", LicenseDocument.DocumentType.OTHER)
    allowed_types = {value for value, _label in LicenseDocument.DocumentType.choices}
    if document_type not in allowed_types:
        document_type = LicenseDocument.DocumentType.OTHER
    allowed_extensions = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".lic", ".zip")
    files = request.FILES.getlist("documents")
    for uploaded_file in files:
        if uploaded_file.size > 20 * 1024 * 1024:
            return f"A(z) {uploaded_file.name} fájl legfeljebb 20 MB lehet."
        if not uploaded_file.name.lower().endswith(allowed_extensions):
            return f"A(z) {uploaded_file.name} fájltípusa nem engedélyezett."
    if not persist:
        return None
    for uploaded_file in files:
        LicenseDocument.objects.create(
            license=license_obj,
            document_type=document_type,
            file=uploaded_file,
            original_name=uploaded_file.name,
            uploaded_by=request.user,
        )
    return None


@login_required
@permission_required("licenses.view_license", raise_exception=True)
def license_detail(request, pk):
    return render(
        request,
        "licenses/detail.html",
        {
            "license": get_object_or_404(
                License.objects.select_related(
                    "manufacturer", "distributor", "owner"
                ).prefetch_related("documents"),
                pk=pk,
            ),
            "document_form": DocumentForm(),
        },
    )


@login_required
@permission_required("licenses.add_license", raise_exception=True)
def license_create(request):
    form = LicenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(False)
        obj.created_by = request.user
        obj.updated_by = request.user
        error = _save_uploaded_documents(request, obj, persist=False)
        if error:
            form.add_error(None, error)
        else:
            obj.save()
            form.save_m2m()
            _save_uploaded_documents(request, obj)
            return redirect("license_detail", pk=obj.pk)
    return render(
        request,
        "licenses/form.html",
        {
            "form": form,
            "title": "Új licenc",
            "document_types": LicenseDocument.DocumentType.choices,
        },
    )


@login_required
@permission_required("licenses.change_license", raise_exception=True)
def license_edit(request, pk):
    obj = get_object_or_404(License.objects.prefetch_related("documents"), pk=pk)
    form = LicenseForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        error = _save_uploaded_documents(request, obj)
        if error:
            form.add_error(None, error)
        else:
            obj = form.save(False)
            obj.updated_by = request.user
            obj.save()
            form.save_m2m()
            return redirect("license_detail", pk=obj.pk)
    return render(
        request,
        "licenses/form.html",
        {
            "form": form,
            "license": obj,
            "title": "Licenc szerkesztése",
            "document_types": LicenseDocument.DocumentType.choices,
        },
    )


@login_required
@permission_required("licenses.add_licensedocument", raise_exception=True)
def document_upload(request, pk):
    license_obj = get_object_or_404(License, pk=pk)
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(False)
            doc.license = license_obj
            doc.original_name = doc.file.name
            doc.uploaded_by = request.user
            doc.save()
    return redirect("license_detail", pk=pk)


@login_required
@permission_required("licenses.delete_licensedocument", raise_exception=True)
def document_delete(request, pk, document_pk):
    document = get_object_or_404(LicenseDocument, pk=document_pk, license_id=pk)
    if request.method == "POST":
        name = document.original_name
        document.file.delete(save=False)
        document.delete()
        record_event(
            "LICENSE_DOCUMENT_DELETED",
            request=request,
            user=request.user,
            description=f"Dokumentum törölve: {name}",
            metadata={"license_id": pk, "document_name": name},
        )
    return redirect("license_detail", pk=pk)


@login_required
@permission_required("licenses.add_license", raise_exception=True)
def license_duplicate(request, pk):
    source = get_object_or_404(License, pk=pk)
    source.pk = None
    source.name = f"{source.name} (másolat)"
    source.created_by = request.user
    source.updated_by = request.user
    source.save()
    return redirect("license_edit", pk=source.pk)


@login_required
@permission_required("licenses.archive_license", raise_exception=True)
def license_archive(request, pk):
    obj = get_object_or_404(License, pk=pk)
    if request.method == "POST":
        obj.status = License.Status.ARCHIVED
        obj.updated_by = request.user
        obj.save(update_fields=["status", "updated_by", "updated_at"])
    return redirect("license_detail", pk=pk)


@login_required
@permission_required("licenses.export_license", raise_exception=True)
def license_export(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="licenses.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Licencazonosító",
            "Elnevezés",
            "Gyártó",
            "Disztribútor",
            "Szervezet",
            "Darabszám",
            "Felhasznált darabszám",
            "Státusz",
            "Lejárat",
            "Költség",
            "Pénznem",
        ]
    )
    for obj in License.objects.select_related("manufacturer", "distributor"):
        writer.writerow(
            [
                obj.reference_code or f"LH-{obj.pk:05d}",
                obj.name,
                obj.manufacturer or "",
                obj.distributor or "",
                obj.organization,
                obj.quantity,
                obj.used_quantity,
                obj.get_status_display(),
                obj.expires_at or "",
                obj.cost or "",
                obj.currency,
            ]
        )
    return response


def _party_kind(kind):
    return Party.Kind.MANUFACTURER if kind == "manufacturers" else Party.Kind.DISTRIBUTOR


@login_required
@permission_required("licenses.view_party", raise_exception=True)
def party_list(request, kind):
    party_kind = _party_kind(kind)
    title = "Gyártók" if party_kind == Party.Kind.MANUFACTURER else "Disztribútorok"
    return render(
        request,
        "licenses/parties.html",
        {
            "parties": Party.objects.filter(kind=party_kind).prefetch_related("contacts"),
            "kind": kind,
            "title": title,
        },
    )


def _party_form(request, kind, instance=None):
    party_kind = _party_kind(kind)
    form = PartyForm(request.POST or None, instance=instance)
    formset = PartyContactFormSet(request.POST or None, instance=instance, prefix="contacts")
    valid_contacts = formset is None or formset.is_valid()
    if request.method == "POST" and form.is_valid() and valid_contacts:
        obj = form.save(False)
        obj.kind = party_kind
        obj.save()
        if formset is not None:
            formset.instance = obj
            formset.save()
        return obj
    return form, formset


@login_required
@permission_required("licenses.add_party", raise_exception=True)
def party_create(request, kind):
    result = _party_form(request, kind)
    if isinstance(result, Party):
        return redirect("manufacturer_list" if kind == "manufacturers" else "distributor_list")
    form, formset = result
    noun = "gyártó" if kind == "manufacturers" else "disztribútor"
    template = (
        "licenses/distributor_form.html" if formset is not None else "licenses/party_form.html"
    )
    return render(
        request, template, {"form": form, "formset": formset, "title": f"Új {noun}", "party": None}
    )


@login_required
@permission_required("licenses.change_party", raise_exception=True)
def party_edit(request, kind, pk):
    party = get_object_or_404(Party, pk=pk, kind=_party_kind(kind))
    result = _party_form(request, kind, instance=party)
    if isinstance(result, Party):
        return redirect("party_edit", kind=kind, pk=party.pk)
    form, formset = result
    template = (
        "licenses/distributor_form.html" if formset is not None else "licenses/party_form.html"
    )
    related_licenses = (
        party.manufactured_licenses.all()
        if party.kind == Party.Kind.MANUFACTURER
        else party.distributed_licenses.all()
    )
    return render(
        request,
        template,
        {
            "form": form,
            "formset": formset,
            "title": f"{party.name} szerkesztése",
            "party": party,
            "related_licenses": related_licenses,
        },
    )


@login_required
@permission_required("licenses.view_license", raise_exception=True)
def reports(request):
    columns = {
        "reference": ("Licencazonosító", lambda obj: obj.reference_code),
        "name": ("Termék", lambda obj: obj.name),
        "type": ("Licenctípus", lambda obj: obj.get_license_type_display()),
        "manufacturer": ("Gyártó", lambda obj: str(obj.manufacturer or "")),
        "manufacturer_contacts": (
            "Gyártói kapcsolattartók",
            lambda obj: (
                "; ".join(
                    f"{c.name} | {c.phone} | {c.email}" for c in obj.manufacturer.contacts.all()
                )
                if obj.manufacturer
                else ""
            ),
        ),
        "distributor": ("Disztribútor", lambda obj: str(obj.distributor or "")),
        "distributor_contacts": (
            "Disztribútori kapcsolattartók",
            lambda obj: (
                "; ".join(
                    f"{c.name} | {c.phone} | {c.email}" for c in obj.distributor.contacts.all()
                )
                if obj.distributor
                else ""
            ),
        ),
        "organization": ("Szervezet", lambda obj: obj.organization),
        "status": ("Státusz", lambda obj: obj.get_status_display()),
        "quantity": ("Darabszám", lambda obj: obj.quantity),
        "used": ("Felhasznált", lambda obj: obj.used_quantity),
        "expires": ("Lejárat", lambda obj: obj.expires_at or ""),
        "cost": ("Költség", lambda obj: obj.cost or ""),
        "currency": ("Pénznem", lambda obj: obj.currency),
        "owner": ("Felelős", lambda obj: str(obj.owner or "")),
    }
    selected = [key for key in request.GET.getlist("columns") if key in columns]
    if not selected:
        selected = [
            "reference",
            "name",
            "manufacturer",
            "organization",
            "status",
            "quantity",
            "expires",
        ]
    items = License.objects.select_related("manufacturer", "distributor", "owner").prefetch_related(
        "manufacturer__contacts", "distributor__contacts"
    )
    status = request.GET.get("status", "")
    manufacturer = request.GET.get("manufacturer", "")
    distributor = request.GET.get("distributor", "")
    organization = request.GET.get("organization", "").strip()
    if status:
        items = items.filter(status=status)
    if manufacturer:
        items = items.filter(manufacturer_id=manufacturer)
    if distributor:
        items = items.filter(distributor_id=distributor)
    if organization:
        items = items.filter(organization__icontains=organization)
    rows = [[columns[key][1](obj) for key in selected] for obj in items[:500]]
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="license-report.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([columns[key][0] for key in selected])
        writer.writerows(rows)
        return response
    return render(
        request,
        "licenses/reports.html",
        {
            "available_columns": [(key, value[0]) for key, value in columns.items()],
            "selected_columns": selected,
            "headers": [columns[key][0] for key in selected],
            "rows": rows,
            "statuses": License.Status.choices,
            "selected_status": status,
            "manufacturers": Party.objects.filter(kind=Party.Kind.MANUFACTURER),
            "distributors": Party.objects.filter(kind=Party.Kind.DISTRIBUTOR),
            "selected_manufacturer": manufacturer,
            "selected_distributor": distributor,
            "selected_organization": organization,
        },
    )

import csv
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from .forms import DocumentForm, LicenseForm, PartyContactFormSet, PartyForm
from .models import License, LicenseDocument, Party


@login_required
@permission_required("licenses.view_license", raise_exception=True)
def license_list(request):
    items = License.objects.select_related("manufacturer", "distributor", "owner")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        items = items.filter(
            Q(name__icontains=q)
            | Q(manufacturer__name__icontains=q)
            | Q(distributor__name__icontains=q)
            | Q(cost_center__icontains=q)
        )
    if status:
        items = items.filter(status=status)
    return render(
        request,
        "licenses/list.html",
        {
            "licenses": items,
            "query": q,
            "selected_status": status,
            "statuses": License.Status.choices,
        },
    )


@login_required
@permission_required("licenses.view_license", raise_exception=True)
def license_detail(request, pk):
    return render(
        request,
        "licenses/detail.html",
        {
            "license": get_object_or_404(
                License.objects.select_related("manufacturer", "distributor", "owner"), pk=pk
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
        obj.save()
        form.save_m2m()
        return redirect("license_detail", pk=obj.pk)
    return render(request, "licenses/form.html", {"form": form, "title": "Új licenc"})


@login_required
@permission_required("licenses.change_license", raise_exception=True)
def license_edit(request, pk):
    obj = get_object_or_404(License, pk=pk)
    form = LicenseForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        obj = form.save(False)
        obj.updated_by = request.user
        obj.save()
        form.save_m2m()
        return redirect("license_detail", pk=obj.pk)
    return render(request, "licenses/form.html", {"form": form, "title": "Licenc szerkesztése"})


@login_required
@permission_required("licenses.add_licensedocument", raise_exception=True)
def document_upload(request, pk):
    license_obj = get_object_or_404(License, pk=pk)
    form = DocumentForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(False)
        doc.license = license_obj
        doc.original_name = doc.file.name
        doc.uploaded_by = request.user
        doc.save()
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
            "Elnevezés",
            "Gyártó",
            "Disztribútor",
            "Darabszám",
            "Státusz",
            "Lejárat",
            "Költség",
            "Pénznem",
        ]
    )
    for obj in License.objects.select_related("manufacturer", "distributor"):
        writer.writerow(
            [
                obj.name,
                obj.manufacturer or "",
                obj.distributor or "",
                obj.quantity,
                obj.get_status_display(),
                obj.expires_at or "",
                obj.cost or "",
                obj.currency,
            ]
        )
    return response


@login_required
@permission_required("licenses.view_party", raise_exception=True)
def party_list(request, kind):
    party_kind = Party.Kind.MANUFACTURER if kind == "manufacturers" else Party.Kind.DISTRIBUTOR
    title = "Gyártók" if party_kind == Party.Kind.MANUFACTURER else "Disztribútorok"
    return render(
        request,
        "licenses/parties.html",
        {"parties": Party.objects.filter(kind=party_kind), "kind": kind, "title": title},
    )


@login_required
@permission_required("licenses.add_party", raise_exception=True)
def party_create(request, kind):
    party_kind = Party.Kind.MANUFACTURER if kind == "manufacturers" else Party.Kind.DISTRIBUTOR
    form = PartyForm(request.POST or None)
    formset = (
        PartyContactFormSet(request.POST or None, prefix="contacts")
        if party_kind == Party.Kind.DISTRIBUTOR
        else None
    )
    valid_contacts = formset is None or formset.is_valid()
    if request.method == "POST" and form.is_valid() and valid_contacts:
        obj = form.save(False)
        obj.kind = party_kind
        obj.save()
        if formset is not None:
            formset.instance = obj
            formset.save()
        return redirect("manufacturer_list" if kind == "manufacturers" else "distributor_list")
    template = "licenses/distributor_form.html" if formset is not None else "licenses/form.html"
    return render(
        request,
        template,
        {"form": form, "formset": formset, "title": "Új törzsadat"},
    )


@login_required
@permission_required("licenses.view_licensedocument", raise_exception=True)
def document_list(request):
    return render(
        request,
        "licenses/documents.html",
        {
            "documents": LicenseDocument.objects.select_related("license", "uploaded_by").order_by(
                "-uploaded_at"
            )
        },
    )


@login_required
@permission_required("licenses.view_license", raise_exception=True)
def reports(request):
    by_manufacturer = (
        License.objects.values("manufacturer__name")
        .annotate(total=Sum("quantity"), cost=Sum("cost"))
        .order_by("-total")
    )
    by_owner = (
        License.objects.values("owner__username").annotate(total=Count("id")).order_by("-total")
    )
    return render(
        request, "licenses/reports.html", {"by_manufacturer": by_manufacturer, "by_owner": by_owner}
    )

import csv
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from .forms import DocumentForm, LicenseForm
from .models import License

@login_required
@permission_required("licenses.view_license", raise_exception=True)
def license_list(request):
    items=License.objects.select_related("manufacturer","distributor","owner")
    q=request.GET.get("q","").strip(); status=request.GET.get("status","")
    if q: items=items.filter(Q(name__icontains=q)|Q(manufacturer__name__icontains=q)|Q(distributor__name__icontains=q)|Q(cost_center__icontains=q))
    if status: items=items.filter(status=status)
    return render(request,"licenses/list.html",{"licenses":items,"query":q,"selected_status":status,"statuses":License.Status.choices})

@login_required
@permission_required("licenses.view_license", raise_exception=True)
def license_detail(request,pk): return render(request,"licenses/detail.html",{"license":get_object_or_404(License.objects.select_related("manufacturer","distributor","owner"),pk=pk),"document_form":DocumentForm()})

@login_required
@permission_required("licenses.add_license", raise_exception=True)
def license_create(request):
    form=LicenseForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        obj=form.save(False); obj.created_by=request.user; obj.updated_by=request.user; obj.save(); form.save_m2m(); return redirect("license_detail",pk=obj.pk)
    return render(request,"licenses/form.html",{"form":form,"title":"Új licenc"})

@login_required
@permission_required("licenses.change_license", raise_exception=True)
def license_edit(request,pk):
    obj=get_object_or_404(License,pk=pk); form=LicenseForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid(): obj=form.save(False); obj.updated_by=request.user; obj.save(); form.save_m2m(); return redirect("license_detail",pk=obj.pk)
    return render(request,"licenses/form.html",{"form":form,"title":"Licenc szerkesztése"})

@login_required
@permission_required("licenses.add_licensedocument", raise_exception=True)
def document_upload(request,pk):
    license_obj=get_object_or_404(License,pk=pk); form=DocumentForm(request.POST,request.FILES)
    if form.is_valid(): doc=form.save(False); doc.license=license_obj; doc.original_name=doc.file.name; doc.uploaded_by=request.user; doc.save()
    return redirect("license_detail",pk=pk)

@login_required
@permission_required("licenses.add_license", raise_exception=True)
def license_duplicate(request,pk):
    source=get_object_or_404(License,pk=pk); source.pk=None; source.name=f"{source.name} (másolat)"; source.created_by=request.user; source.updated_by=request.user; source.save(); return redirect("license_edit",pk=source.pk)

@login_required
@permission_required("licenses.archive_license", raise_exception=True)
def license_archive(request,pk):
    obj=get_object_or_404(License,pk=pk)
    if request.method=="POST": obj.status=License.Status.ARCHIVED; obj.updated_by=request.user; obj.save(update_fields=["status","updated_by","updated_at"])
    return redirect("license_detail",pk=pk)

@login_required
@permission_required("licenses.export_license", raise_exception=True)
def license_export(request):
    response=HttpResponse(content_type="text/csv; charset=utf-8"); response["Content-Disposition"]='attachment; filename="licenses.csv"'; response.write("\ufeff"); writer=csv.writer(response); writer.writerow(["Elnevezés","Gyártó","Disztribútor","Darabszám","Státusz","Lejárat","Költség","Pénznem"])
    for obj in License.objects.select_related("manufacturer","distributor"): writer.writerow([obj.name,obj.manufacturer or "",obj.distributor or "",obj.quantity,obj.get_status_display(),obj.expires_at or "",obj.cost or "",obj.currency])
    return response

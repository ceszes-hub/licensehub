from django.urls import path

from . import views

urlpatterns = [
    path("manufacturers/", views.party_list, {"kind": "manufacturers"}, name="manufacturer_list"),
    path(
        "manufacturers/new/",
        views.party_create,
        {"kind": "manufacturers"},
        name="manufacturer_create",
    ),
    path("distributors/", views.party_list, {"kind": "distributors"}, name="distributor_list"),
    path(
        "distributors/new/", views.party_create, {"kind": "distributors"}, name="distributor_create"
    ),
    path("<str:kind>/<int:pk>/edit/", views.party_edit, name="party_edit"),
    path("reports/", views.reports, name="reports"),
    path("", views.license_list, name="license_list"),
    path("new/", views.license_create, name="license_create"),
    path("export.csv", views.license_export, name="license_export"),
    path("<int:pk>/", views.license_detail, name="license_detail"),
    path("<int:pk>/edit/", views.license_edit, name="license_edit"),
    path("<int:pk>/documents/", views.document_upload, name="document_upload"),
    path(
        "<int:pk>/documents/<int:document_pk>/delete/",
        views.document_delete,
        name="document_delete",
    ),
    path("<int:pk>/duplicate/", views.license_duplicate, name="license_duplicate"),
    path("<int:pk>/archive/", views.license_archive, name="license_archive"),
]

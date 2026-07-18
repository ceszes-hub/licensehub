from django.urls import path
from . import views
urlpatterns=[path("",views.license_list,name="license_list"),path("new/",views.license_create,name="license_create"),path("export.csv",views.license_export,name="license_export"),path("<int:pk>/",views.license_detail,name="license_detail"),path("<int:pk>/edit/",views.license_edit,name="license_edit"),path("<int:pk>/documents/",views.document_upload,name="document_upload"),path("<int:pk>/duplicate/",views.license_duplicate,name="license_duplicate"),path("<int:pk>/archive/",views.license_archive,name="license_archive")]

from django.urls import include, path

urlpatterns = [path("", include("core.urls"))]
handler400 = "core.views.error400"
handler403 = "core.views.error403"
handler404 = "core.views.error404"
handler500 = "core.views.error500"

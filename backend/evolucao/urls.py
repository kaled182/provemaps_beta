from django.urls import path

from . import api

app_name = "evolucao"

urlpatterns = [
    path("itens/", api.ItemListCreateView.as_view(), name="itens"),
    path("itens/<int:pk>/", api.ItemDetailView.as_view(), name="item"),
    path("etiquetas/", api.EtiquetasView.as_view(), name="etiquetas"),
    path("anexos/", api.AnexoUploadView.as_view(), name="anexos"),
    path("anexos/<int:pk>/", api.AnexoDownloadView.as_view(), name="anexo"),
]

from django.contrib import admin

from .models import EvolucaoAnexo, EvolucaoContador, EvolucaoItem


@admin.register(EvolucaoItem)
class EvolucaoItemAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "tipo",
        "titulo",
        "estado",
        "prioridade",
        "origem",
        "autor",
        "criado_em",
    )
    list_filter = ("estado", "tipo", "origem", "prioridade")
    search_fields = ("codigo", "titulo", "descricao")
    readonly_fields = ("codigo", "fechado_por", "criado_em", "atualizado_em")


admin.site.register(EvolucaoAnexo)
admin.site.register(EvolucaoContador)

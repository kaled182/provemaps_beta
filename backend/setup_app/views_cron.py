"""Cron Job management API — DRF views with CSRF-exempt session auth."""

import json
import logging
from pathlib import Path

from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from .models_cron import CronJob

logger = logging.getLogger(__name__)

DATABASE_DIR = Path(getattr(settings, "DATABASE_DIR", "/app/database"))


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session auth sem CSRF — seguro para APIs internas com auth própria."""

    def enforce_csrf(self, request):
        return  # Skip CSRF enforcement


def _cron_auth(request) -> bool:
    u = request.user
    return bool(u and u.is_authenticated and u.is_active and (u.is_staff or u.is_superuser))


def _cron_to_dict(job: CronJob) -> dict:
    return {
        "id": job.id,
        "name": job.name,
        "description": job.description,
        "schedule": job.schedule,
        "command": job.command,
        "enabled": job.enabled,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


def _write_crontab_file(jobs) -> None:
    crontab_path = DATABASE_DIR / "provemaps.crontab"
    lines = [
        "# Provemaps — generated crontab (do not edit manually)",
        "",
        "SHELL=/bin/bash",
        "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin",
        "",
    ]
    for job in jobs:
        if job.enabled:
            lines.append(f"# {job.name}")
            if job.description:
                lines.append(f"# {job.description}")
            lines.append(f"{job.schedule} root {job.command}")
            lines.append("")
    crontab_path.write_text("\n".join(lines))


class CronJobsView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = []

    def get(self, request):
        if not _cron_auth(request):
            return Response({"error": "Acesso negado"}, status=403)
        jobs = CronJob.objects.all()
        return Response({"jobs": [_cron_to_dict(j) for j in jobs]})

    def post(self, request):
        if not _cron_auth(request):
            return Response({"error": "Acesso negado"}, status=403)
        data = request.data
        job = CronJob.objects.create(
            name=data.get("name", "").strip(),
            description=data.get("description", "").strip(),
            schedule=data.get("schedule", "").strip(),
            command=data.get("command", "").strip(),
            enabled=data.get("enabled", True),
        )
        _write_crontab_file(CronJob.objects.all())
        return Response({"success": True, "job": _cron_to_dict(job)}, status=201)


class CronJobDetailView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = []

    def _get_job(self, job_id):
        try:
            return CronJob.objects.get(id=job_id), None
        except CronJob.DoesNotExist:
            return None, Response({"error": "Não encontrado"}, status=404)

    def get(self, request, job_id):
        if not _cron_auth(request):
            return Response({"error": "Acesso negado"}, status=403)
        job, err = self._get_job(job_id)
        if err:
            return err
        return Response(_cron_to_dict(job))

    def put(self, request, job_id):
        if not _cron_auth(request):
            return Response({"error": "Acesso negado"}, status=403)
        job, err = self._get_job(job_id)
        if err:
            return err
        data = request.data
        job.name        = data.get("name", job.name).strip()
        job.description = data.get("description", job.description).strip()
        job.schedule    = data.get("schedule", job.schedule).strip()
        job.command     = data.get("command", job.command).strip()
        job.enabled     = data.get("enabled", job.enabled)
        job.save()
        _write_crontab_file(CronJob.objects.all())
        return Response({"success": True, "job": _cron_to_dict(job)})

    def delete(self, request, job_id):
        if not _cron_auth(request):
            return Response({"error": "Acesso negado"}, status=403)
        job, err = self._get_job(job_id)
        if err:
            return err
        job.delete()
        _write_crontab_file(CronJob.objects.all())
        return Response({"success": True})


class CronJobToggleView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = []

    def post(self, request, job_id):
        if not _cron_auth(request):
            return Response({"error": "Acesso negado"}, status=403)
        try:
            job = CronJob.objects.get(id=job_id)
        except CronJob.DoesNotExist:
            return Response({"error": "Não encontrado"}, status=404)
        job.enabled = not job.enabled
        job.save()
        _write_crontab_file(CronJob.objects.all())
        return Response({"success": True, "job": _cron_to_dict(job)})


class CronApplyView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = []

    def post(self, request):
        if not _cron_auth(request):
            return Response({"error": "Acesso negado"}, status=403)
        jobs = CronJob.objects.all()
        _write_crontab_file(jobs)
        enabled_count = jobs.filter(enabled=True).count()
        return Response({
            "success": True,
            "message": f"Arquivo crontab gerado com {enabled_count} job(s) ativo(s).",
            "path": str(DATABASE_DIR / "provemaps.crontab"),
        })

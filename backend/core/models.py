from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    avatar = models.ImageField(
        "Foto de Perfil",
        upload_to="avatars/",
        blank=True,
        null=True,
    )
    phone_number = models.CharField(
        "Celular/WhatsApp",
        max_length=20,
        blank=True,
        null=True,
    )
    telegram_chat_id = models.CharField(
        "Telegram ID",
        max_length=50,
        blank=True,
        null=True,
    )
    notify_via_email = models.BooleanField("Receber via Email", default=True)
    notify_via_whatsapp = models.BooleanField("Receber via WhatsApp", default=False)
    notify_via_telegram = models.BooleanField("Receber via Telegram", default=False)
    receive_critical_alerts = models.BooleanField("Alertas Criticos", default=True)
    receive_warning_alerts = models.BooleanField("Alertas de Aviso", default=False)
    department = models.CharField("Departamento", max_length=100, blank=True)
    departments = models.ManyToManyField(
        "Department",
        related_name="user_profiles",
        blank=True,
    )
    totp_secret = models.CharField("TOTP Secret", max_length=64, blank=True, null=True)
    totp_enabled = models.BooleanField("TOTP Ativo", default=False)

    def __str__(self) -> str:
        return f"Profile of {self.user.username}"


class Department(models.Model):
    name = models.CharField("Nome", max_length=120, unique=True)
    description = models.CharField("Descricao", max_length=255, blank=True)
    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    def __str__(self) -> str:
        return self.name


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()

from django.conf import settings
from django.db import models

from sourcing.models import ProductListing


class ContactExtraction(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        AGUARDANDO_CAPTCHA = 'aguardando_captcha', 'Aguardando resolução manual de captcha'
        EXTRAIDO = 'extraido', 'Extraído'
        FALHA = 'falha', 'Falha'

    product = models.ForeignKey(
        ProductListing, on_delete=models.CASCADE, related_name='contact_extractions'
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDENTE)
    raw_image = models.ImageField(upload_to='contacts/%Y/%m/', null=True, blank=True)
    phone_raw_text = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=64, null=True, blank=True)
    wechat = models.CharField(max_length=128, null=True, blank=True)
    # Último recurso quando o fornecedor não tem celular nem telefone
    # cadastrado — usado como contato alternativo. CharField (não URLField):
    # às vezes vem como texto puro do DOM sem "http://" (ex.: "www.foo.com"),
    # e é só exibido como texto no client, não usado como link — validação
    # estrita de URL só rejeitava dados válidos com 400.
    company_website = models.CharField(max_length=512, null=True, blank=True)
    extracted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.product.title} ({self.status})'

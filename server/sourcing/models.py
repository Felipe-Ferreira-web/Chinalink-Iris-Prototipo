from django.conf import settings
from django.db import models


class SourcingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        RUNNING = 'running', 'Em execução'
        DONE = 'done', 'Concluída'
        FAILED = 'failed', 'Falhou'

    query = models.CharField(max_length=255)
    limit = models.IntegerField(null=True, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.query} ({self.status})'


class Supplier(models.Model):
    class Status(models.TextChoices):
        NOVO = 'novo', 'Novo'
        CONTATO_EXTRAIDO = 'contato_extraido', 'Contato extraído'
        APROVADO = 'aprovado', 'Aprovado'
        REPROVADO = 'reprovado', 'Reprovado'

    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=32, default='alibaba')
    country_code = models.CharField(max_length=8, null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOVO)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Dedup best-effort: a origem (Apify) não expõe um id ou URL de perfil
        # estável para o fornecedor, só nome/país por item de produto.
        unique_together = ('platform', 'name', 'country_code')

    def __str__(self):
        return self.name


class ProductListing(models.Model):
    sourcing_request = models.ForeignKey(
        SourcingRequest, on_delete=models.CASCADE, related_name='products'
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name='products'
    )
    title = models.CharField(max_length=512)
    url = models.URLField(max_length=1024)
    price = models.CharField(max_length=64, null=True, blank=True)
    promotion_price = models.CharField(max_length=64, null=True, blank=True)
    discount = models.CharField(max_length=64, null=True, blank=True)
    moq = models.CharField(max_length=128, null=True, blank=True)
    main_image = models.URLField(max_length=1024, null=True, blank=True)
    review_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    review_count = models.IntegerField(null=True, blank=True)
    delivery_estimate = models.CharField(max_length=128, null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

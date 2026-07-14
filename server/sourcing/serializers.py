from rest_framework import serializers

from .models import ProductListing, SourcingRequest, Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'platform', 'country_code', 'status', 'created_at', 'updated_at']


class ProductListingSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer(read_only=True)
    contact_phone = serializers.SerializerMethodField()
    contact_website = serializers.SerializerMethodField()

    class Meta:
        model = ProductListing
        fields = [
            'id', 'sourcing_request', 'supplier', 'title', 'url', 'price',
            'promotion_price', 'discount', 'moq', 'main_image', 'review_score',
            'review_count', 'delivery_estimate', 'created_at', 'contact_phone',
            'contact_website',
        ]

    def _ultima_extracao(self, obj):
        # 'extraido' == contacts.models.ContactExtraction.Status.EXTRAIDO
        # (não importamos o model de contacts aqui pra evitar import
        # circular, já que contacts importa ProductListing daqui).
        return obj.contact_extractions.filter(status='extraido').order_by('-created_at').first()

    def get_contact_phone(self, obj):
        # extrairContato() (extensão) sempre prioriza Celular > Telefone,
        # então o número aqui já é o celular sempre que disponível.
        extracao = self._ultima_extracao(obj)
        return extracao.phone if extracao else None

    def get_contact_website(self, obj):
        # Só é preenchido quando o fornecedor não tinha celular nem telefone
        # (último recurso da extensão).
        extracao = self._ultima_extracao(obj)
        return extracao.company_website if extracao else None


class SourcingRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourcingRequest
        fields = ['id', 'query', 'limit', 'filters', 'requested_by', 'status', 'created_at', 'updated_at']
        read_only_fields = ['status', 'requested_by', 'created_at', 'updated_at']

from rest_framework import serializers

from .models import ContactExtraction


class ContactExtractionSerializer(serializers.ModelSerializer):
    # Imagem do número revelado (data URI base64, como vem do <img
    # class="value-image"> da página) — a extensão manda isso, não um arquivo.
    image_data = serializers.CharField(write_only=True, required=False)
    # Nem sempre o Alibaba renderiza o número como imagem; quando ele já vem
    # como texto visível no DOM, a extensão manda direto aqui (sem OCR).
    phone_text = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = ContactExtraction
        fields = [
            'id', 'product', 'status', 'image_data', 'phone_text', 'raw_image',
            'phone_raw_text', 'phone', 'wechat', 'company_website', 'error_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['raw_image', 'phone_raw_text', 'phone', 'error_message', 'created_at', 'updated_at']

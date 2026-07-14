from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny

from .models import ContactExtraction
from .serializers import ContactExtractionSerializer
from .services import extract_contact_from_image_data, extract_contact_from_text, mark_supplier_contato_extraido


class ContactExtractionViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin,
                                mixins.ListModelMixin, mixins.RetrieveModelMixin,
                                viewsets.GenericViewSet):
    queryset = ContactExtraction.objects.all()
    serializer_class = ContactExtractionSerializer
    # A extensão chama este endpoint sem sessão Django logada; autenticação
    # (ex: API key) fica para quando o fluxo real de extração for implementado.
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        self._save_and_process(serializer)

    def perform_update(self, serializer):
        self._save_and_process(serializer)

    def _save_and_process(self, serializer):
        image_data = serializer.validated_data.pop('image_data', None)
        phone_text = serializer.validated_data.pop('phone_text', None)
        instance = serializer.save()

        try:
            if image_data:
                extract_contact_from_image_data(instance, image_data)
            elif phone_text:
                extract_contact_from_text(instance, phone_text)
            elif instance.company_website:
                mark_supplier_contato_extraido(instance)
        except Exception as exc:
            instance.status = ContactExtraction.Status.FALHA
            instance.error_message = str(exc)
            instance.save()

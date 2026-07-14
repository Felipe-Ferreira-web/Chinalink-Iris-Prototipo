from django.contrib.auth import get_user_model
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import ProductListing, SourcingRequest, Supplier
from .serializers import ProductListingSerializer, SourcingRequestSerializer, SupplierSerializer
from .services import run_alibaba_search


class SourcingRequestViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                              mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = SourcingRequest.objects.all()
    serializer_class = SourcingRequestSerializer
    # Sem login implementado ainda no client; toda busca é atribuída a um
    # usuário de dev fixo até decidirmos o fluxo de autenticação real.
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        sourcing_request = serializer.instance
        data = serializer.data
        data['products'] = ProductListingSerializer(
            sourcing_request.products.all(), many=True
        ).data
        return Response(data, status=201)

    def perform_create(self, serializer):
        dev_user, _ = get_user_model().objects.get_or_create(username='dev')
        sourcing_request = serializer.save(
            requested_by=dev_user, status=SourcingRequest.Status.RUNNING
        )
        try:
            run_alibaba_search(sourcing_request)
            sourcing_request.status = SourcingRequest.Status.DONE
        except Exception as exc:
            sourcing_request.status = SourcingRequest.Status.FAILED
            sourcing_request.filters = {**sourcing_request.filters, 'error': str(exc)}
        sourcing_request.save()

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        sourcing_request = self.get_object()
        products = ProductListing.objects.filter(sourcing_request=sourcing_request)
        serializer = ProductListingSerializer(products, many=True)
        return Response(serializer.data)


class SupplierViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [AllowAny]


class ProductListingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    # A extensão usa isso pra saber o nome exato do fornecedor de um product_id
    # e localizar o link certo na página, em vez de adivinhar pelo DOM.
    queryset = ProductListing.objects.all()
    serializer_class = ProductListingSerializer
    permission_classes = [AllowAny]

from decimal import Decimal, InvalidOperation

from apify_client import ApifyClient
from django.conf import settings

from .models import ProductListing, SourcingRequest, Supplier

DEFAULT_LIMIT = 10
MAX_LIMIT = 50
MAX_ATTEMPTS = 3


def _parse_decimal(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def run_alibaba_search(sourcing_request: SourcingRequest) -> None:
    client = ApifyClient(settings.APIFY_TOKEN)

    run_input = {'search': sourcing_request.query}
    run_input['limit'] = max(1, min(sourcing_request.limit or DEFAULT_LIMIT, MAX_LIMIT))

    # O actor às vezes reporta sucesso mas devolve 0 itens (bloqueio silencioso
    # do Alibaba pra aquela requisição específica); tenta de novo antes de desistir.
    items = []
    for attempt in range(MAX_ATTEMPTS):
        run = client.actor(settings.APIFY_ALIBABA_ACTOR_ID).call(run_input=run_input)
        items = client.dataset(run.default_dataset_id).list_items().items
        if items:
            break
        if attempt < MAX_ATTEMPTS - 1:
            sourcing_request.filters = {
                **sourcing_request.filters,
                'retries': attempt + 1,
            }

    for item in items:
        supplier, _ = Supplier.objects.get_or_create(
            platform='alibaba',
            name=item.get('companyName') or '',
            country_code=item.get('countryCode'),
            defaults={'raw_data': item},
        )

        ProductListing.objects.create(
            sourcing_request=sourcing_request,
            supplier=supplier,
            title=item.get('title') or '',
            url=item.get('productUrl') or '',
            price=item.get('price'),
            promotion_price=item.get('promotionPrice'),
            discount=item.get('discount'),
            moq=item.get('moq'),
            main_image=item.get('mainImage'),
            review_score=_parse_decimal(item.get('reviewScore')),
            review_count=item.get('reviewCount'),
            delivery_estimate=item.get('deliveryEstimate'),
            raw_data=item,
        )

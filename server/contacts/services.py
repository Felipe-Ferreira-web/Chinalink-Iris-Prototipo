import base64
import re
from io import BytesIO

import pytesseract
from django.core.files.base import ContentFile
from PIL import Image

from sourcing.models import Supplier

from .models import ContactExtraction

OCR_CONFIG = '--psm 7 -c tessedit_char_whitelist=0123456789+()-. '


def mark_supplier_contato_extraido(contact_extraction: ContactExtraction) -> None:
    supplier = contact_extraction.product.supplier
    supplier.status = Supplier.Status.CONTATO_EXTRAIDO
    supplier.save(update_fields=['status', 'updated_at'])


def extract_contact_from_image_data(contact_extraction: ContactExtraction, data_uri: str) -> None:
    # A extensão envia o número como veio da página: <img class="value-image">
    # com src="data:image/png;base64,..." (o Alibaba renderiza o número como
    # imagem pra dificultar scraping). Decodificamos e rodamos OCR aqui.
    header, _, encoded = data_uri.partition(',')
    content = base64.b64decode(encoded)
    extension = 'png' if 'png' in header else 'jpg'

    image = Image.open(BytesIO(content))
    text = pytesseract.image_to_string(image, config=OCR_CONFIG)
    phone = re.sub(r'[^0-9+]', '', text)

    contact_extraction.raw_image.save(f'contact.{extension}', ContentFile(content), save=False)
    contact_extraction.phone_raw_text = text.strip()
    contact_extraction.phone = phone
    contact_extraction.status = ContactExtraction.Status.EXTRAIDO
    contact_extraction.save()

    mark_supplier_contato_extraido(contact_extraction)


def extract_contact_from_text(contact_extraction: ContactExtraction, text: str) -> None:
    # Quando o número já vem como texto visível no DOM (nem todo layout do
    # Alibaba usa o truque da imagem), a extensão manda o texto direto e a
    # gente pula o OCR.
    phone = re.sub(r'[^0-9+]', '', text)

    contact_extraction.phone_raw_text = text.strip()
    contact_extraction.phone = phone
    contact_extraction.status = ContactExtraction.Status.EXTRAIDO
    contact_extraction.save()

    mark_supplier_contato_extraido(contact_extraction)

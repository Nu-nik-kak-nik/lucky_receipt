from django.conf import settings


def promo_period(request):
    return {
        "PROMO_START_DATE": settings.PROMO_START_DATE,
        "PROMO_END_DATE": settings.PROMO_END_DATE,
        "PROMO_MIN_AMOUNT": settings.PROMO_MIN_AMOUNT,
    }

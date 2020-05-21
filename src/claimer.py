import datetime as dt
from itertools import chain
from math import ceil

from api import (
    DEFAULT_PAGINATION_SIZE,
    PACKT_API_FREE_LEARNING_CLAIM_URL,
    PACKT_API_FREE_LEARNING_OFFERS_URL,
    PACKT_API_PRODUCTS_URL,
    PACKT_API_USER_URL,
    PACKT_PRODUCT_SUMMARY_URL
)
from utils.logger import get_logger

logger = get_logger(__name__)


def get_all_books_data(api_client):
    """Fetch all user's ebooks data."""
    logger.info("Getting your books data...")
    try:
        response = api_client.get(PACKT_API_PRODUCTS_URL)
        pages_total = int(ceil(response.json().get('count') / DEFAULT_PAGINATION_SIZE))

        ids, my_books_data = (set(), [])
        for book in chain(*map(lambda page: get_single_page_books_data(api_client, page), range(pages_total))):
            if book['id'] not in ids:
                ids.add(book['id'])
                my_books_data.append(book)

        logger.info('Books data has been successfully fetched.')
        return my_books_data
    except (AttributeError, TypeError):
        logger.error('Couldn\'t fetch user\'s books data.')


def get_single_page_books_data(api_client, page):
    """Fetch ebooks data from single products API pagination page."""
    try:
        response = api_client.get(
            PACKT_API_PRODUCTS_URL,
            params={
                'sort': 'createdAt:DESC',
                'offset': DEFAULT_PAGINATION_SIZE * page,
                'limit': DEFAULT_PAGINATION_SIZE
            }
        )
        return [{'id': t['productId'], 'title': t['productName']} for t in response.json().get('data')]
    except Exception:
        logger.error('Couldn\'t fetch page {} of user\'s books data.'.format(page))


def claim_product(api_client, recaptcha_solution):
    """Grab Packt Free Learning ebook."""
    logger.info("Start grabbing ebook...")

    utc_today = dt.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    offer_response = api_client.get(
        PACKT_API_FREE_LEARNING_OFFERS_URL,
        params={
            'dateFrom': utc_today.isoformat(),
            'dateTo': (utc_today + dt.timedelta(days=1)).isoformat()
        }
    )
    # Handle case when there is no Free Learning offer
    offer_count = offer_response.json().get('count')
    if offer_count == 0:
        logger.info("There is no Free Learning offer right now")
        raise Exception("There is no Free Learning offer right now")

    [offer_data] = offer_response.json().get('data')
    offer_id = offer_data.get('id')
    product_id = offer_data.get('productId')

    user_response = api_client.get(PACKT_API_USER_URL)
    [user_data] = user_response.json().get('data')
    user_id = user_data.get('id')

    product_response = api_client.get(PACKT_PRODUCT_SUMMARY_URL.format(product_id=product_id))
    product_data = {'id': product_id, 'title': product_response.json()['title']}\
        if product_response.status_code == 200 else None

    if any(product_id == book['id'] for book in get_all_books_data(api_client)):
        logger.info('You have already claimed Packt Free Learning "{}" offer.'.format(product_data['title']))
        return product_data

    claim_response = api_client.put(
        PACKT_API_FREE_LEARNING_CLAIM_URL.format(user_id=user_id, offer_id=offer_id),
        json={'recaptcha': recaptcha_solution}
    )

    if claim_response.status_code == 200:
        logger.info('A new Packt Free Learning ebook "{}" has been grabbed!'.format(product_data['title']))
    elif claim_response.status_code == 409:
        logger.info('You have already claimed Packt Free Learning "{}" offer.'.format(product_data['title']))
    else:
        logger.error('Claiming Packt Free Learning book has failed.')

    return product_data

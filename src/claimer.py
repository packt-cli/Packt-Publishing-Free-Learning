import datetime as dt
from itertools import chain
from math import ceil
from re import split

from api import (
    DEFAULT_PAGINATION_SIZE,
    PACKT_API_FREE_LEARNING_CLAIM_URL,
    PACKT_API_FREE_LEARNING_OFFERS_URL,
    PACKT_API_PRODUCTS_URL,
    PACKT_API_USER_URL,
    PACKT_PRODUCT_SUMMARY_URL
)
from utils.anticaptcha import solve_recaptcha
from utils.logger import get_logger

logger = get_logger(__name__)


PACKT_FREE_LEARNING_URL = 'https://www.packtpub.com/packt/offers/free-learning/'
PACKT_RECAPTCHA_SITE_KEY = '6LeAHSgUAAAAAKsn5jo6RUSTLVxGNYyuvUcLMe0_'


def get_all_books_data(api_client):
    """Fetch all user's ebooks data."""
    logger.info("Getting your books data...")
    try:
        response = api_client.get(PACKT_API_PRODUCTS_URL)
        pages_total = int(ceil(response.json().get('count') / DEFAULT_PAGINATION_SIZE))
        my_books_data = list(chain(*map(
            lambda page: get_single_page_books_data(api_client, page),
            range(pages_total)
        )))
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


def ask_and_get_books_data(api_client):
    """Show the book list, ask for the books id and return the data of the chosen books"""
    books = get_all_books_data(api_client)
    books.reverse()
    i = 0
    for book in books:
        print(str(i) + '. ' + book['title'])
        i += 1

    book_ids = []
    while len(book_ids) == 0:
        selected_books = input('Enter the ids of the books to be downloaded separated by a comma, you can write 1-5 '
                               'to select all the ids from 1 to 5. Type \'exit\' to exit. '
                               'Ex: 1, 3, 7, 14-32, 54, 87\n>>>')
        if selected_books == 'exit':
            exit(0)
        elif ',' in selected_books:
            for book_id in split(',', selected_books):
                if '-' not in book_id:
                    try:
                        book_ids.append(int(book_id))
                    except ValueError:
                        logger.error('The parameter \'{}\' is not a number'.format(book_id))
                else:
                    if book_id.count('-') == 1:
                        range_par = split('-', book_id)
                        if len(range_par) == 2:
                            try:
                                range_from = int(range_par[0])
                                range_to = int(range_par[1])

                                for i in range(range_from, range_to + 1):
                                    if i not in book_ids:
                                        book_ids.append(i)
                            except ValueError:
                                logger.error('The range \'{}\' is incorrect'.format(book_id))
                        else:
                            logger.error('The range \'{}\' is incorrect'.format(book_id))
                    else:
                        logger.error('Parameter \'{}\' contains more tha one -'.format(book_id))
        elif '-' in selected_books:
            if selected_books.count('-') == 1:
                range_par = split('-', selected_books)
                if len(range_par) == 2:
                    try:
                        range_from = int(range_par[0])
                        range_to = int(range_par[1])

                        for i in range(range_from, range_to + 1):
                            if i not in book_ids:
                                book_ids.append(i)
                    except ValueError:
                        logger.error('The range \'{}\' is incorrect'.format(selected_books))
                else:
                    logger.error('The range \'{}\' is incorrect'.format(selected_books))
            else:
                logger.error('Parameter \'{}\' contains more tha one -'.format(selected_books))
        elif ' ' not in selected_books and ',' not in selected_books:
            try:
                book_ids = [int(selected_books)]
            except ValueError:
                logger.error('You must insert a number')
        else:
            logger.error('You must insert a number')

    books_data = []
    for book_id in book_ids:
        try:
            books_data.append(books[book_id])
        except IndexError:
            logger.error('ID {} does not exists'.format(book_id))
    return books_data


def claim_product(api_client, anticaptcha_key):
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

    logger.info('Started solving ReCAPTCHA on Packt Free Learning website...')
    recaptcha_solution = solve_recaptcha(anticaptcha_key, PACKT_FREE_LEARNING_URL, PACKT_RECAPTCHA_SITE_KEY)

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

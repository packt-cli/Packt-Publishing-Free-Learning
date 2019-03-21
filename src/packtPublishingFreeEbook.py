import click
import datetime as dt
from itertools import chain
import logging
from math import ceil
import os
import sys
import configparser

import requests
from requests.exceptions import ConnectionError
from slugify import slugify

from api import (
    PacktAPIClient,
    PACKT_API_PRODUCTS_URL,
    PACKT_PRODUCT_SUMMARY_URL,
    PACKT_API_PRODUCT_FILE_TYPES_URL,
    PACKT_API_PRODUCT_FILE_DOWNLOAD_URL,
    PACKT_API_FREE_LEARNING_OFFERS_URL,
    PACKT_API_USER_URL,
    PACKT_API_FREE_LEARNING_CLAIM_URL,
    DEFAULT_PAGINATION_SIZE
)
from utils.anticaptcha import Anticaptcha
from utils.logger import get_logger

logger = get_logger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)  # downgrading logging level for requests

DATE_FORMAT = "%Y/%m/%d"

SUCCESS_EMAIL_SUBJECT = "{} New free Packt ebook: \"{}\""
SUCCESS_EMAIL_BODY = "A new free Packt ebook \"{}\" was successfully grabbed. Enjoy!"
FAILURE_EMAIL_SUBJECT = "{} Grabbing a new free Packt ebook failed"
FAILURE_EMAIL_BODY = "Today's free Packt ebook grabbing has failed with exception: {}!\n\nCheck this out!"

PACKT_FREE_LEARNING_URL = 'https://www.packtpub.com/packt/offers/free-learning/'
PACKT_RECAPTCHA_SITE_KEY = '6LeAHSgUAAAAAKsn5jo6RUSTLVxGNYyuvUcLMe0_'


def slugify_book_title(title):
    """Return book title with spaces replaced by underscore and unicodes replaced by characters valid in filenames."""
    return slugify(title, separator='_', lowercase=False)


class PacktConnectionError(ConnectionError):
    """Error raised whenever fetching data from Packt page fails."""
    pass


class ConfigurationModel(object):
    """Contains all needed urls, passwords and packtpub account data stored in .cfg file"""

    def __init__(self, cfg_file_path):
        self.cfg_file_path = cfg_file_path
        self.cfg_folder_path = os.path.dirname(cfg_file_path)
        self.configuration = configparser.ConfigParser()
        if not self.configuration.read(self.cfg_file_path):
            raise configparser.Error('{} file not found'.format(self.cfg_file_path))
        self.anticaptcha_clientkey = self.configuration.get("ANTICAPTCHA_DATA", 'key')
        self.my_packt_email, self.my_packt_password = self._get_config_login_data()
        self.download_folder_path, self.download_formats = self._get_config_download_data()
        if not os.path.exists(self.download_folder_path):
            message = "Download folder path: '{}' doesn't exist".format(self.download_folder_path)
            logger.error(message)
            raise ValueError(message)

    def _get_config_login_data(self):
        """Gets user login credentials."""
        email = self.configuration.get("LOGIN_DATA", 'email')
        password = self.configuration.get("LOGIN_DATA", 'password')
        return email, password

    def _get_config_download_data(self):
        """Downloads ebook data from the user account."""
        download_path = self.configuration.get("DOWNLOAD_DATA", 'download_folder_path')
        download_formats = tuple(form.replace(' ', '') for form in
                                 self.configuration.get("DOWNLOAD_DATA", 'download_formats').split(','))
        return download_path, download_formats


class PacktPublishingFreeEbook(object):
    """Contains some methods to claim, download or send a free daily ebook"""

    download_formats = ('pdf', 'mobi', 'epub', 'video', 'code')

    def __init__(self, cfg):
        self.cfg = cfg
        self.book_data = None

    def get_all_books_data(self, api_client):
        """Fetch all user's ebooks data."""
        logger.info("Getting your books data...")
        try:
            response = api_client.get(PACKT_API_PRODUCTS_URL)
            pages_total = int(ceil(response.json().get('count') / DEFAULT_PAGINATION_SIZE))
            my_books_data = list(chain(*map(
                lambda page: self.get_single_page_books_data(api_client, page),
                range(pages_total)
            )))
            logger.info('Books data has been successfully fetched.')
            return my_books_data
        except (AttributeError, TypeError):
            logger.error('Couldn\'t fetch user\'s books data.')

    def get_single_page_books_data(self, api_client, page):
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

    def solve_packt_recapcha(self):
        """Solve Packt Free Learning website site ReCAPTCHA."""
        logger.info('Started solving ReCAPTCHA on Packt Free Learning website...')
        anticaptcha = Anticaptcha(self.cfg.anticaptcha_clientkey)
        return anticaptcha.solve_recaptcha(PACKT_FREE_LEARNING_URL, PACKT_RECAPTCHA_SITE_KEY)

    def grab_ebook(self, api_client):
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

        claim_response = api_client.put(
            PACKT_API_FREE_LEARNING_CLAIM_URL.format(user_id=user_id, offer_id=offer_id),
            json={'recaptcha': self.solve_packt_recapcha()}
        )

        product_response = api_client.get(PACKT_PRODUCT_SUMMARY_URL.format(product_id=product_id))
        self.book_data = {'id': product_id, 'title': product_response.json()['title']}\
            if product_response.status_code == 200 else None

        if claim_response.status_code == 200:
            logger.info('A new Packt Free Learning ebook "{}" has been grabbed!'.format(self.book_data['title']))
        elif claim_response.status_code == 409:
            logger.info('You have already claimed Packt Free Learning "{}" offer.'.format(self.book_data['title']))
        else:
            logger.error('Claiming Packt Free Learning book has failed.')

    def download_books(self, api_client, product_data=None, formats=None, into_folder=False):
        """Download selected products."""
        def get_product_download_urls(product_id):
            error_message = 'Couldn\'t fetch download URLs for product {}.'.format(product_id)
            try:
                response = api_client.get(PACKT_API_PRODUCT_FILE_TYPES_URL.format(product_id=product_id))
                if response.status_code == 200:
                    return {
                        format: PACKT_API_PRODUCT_FILE_DOWNLOAD_URL.format(product_id=product_id, file_type=format)
                        for format in response.json().get('data')[0].get('fileTypes')
                    }
                else:
                    logger.info(error_message)
                    return {}
            except Exception:
                raise PacktConnectionError(error_message)
        # download ebook
        my_books_data = [product_data] if product_data else self.get_all_books_data(api_client)
        formats = formats or self.cfg.download_formats or self.download_formats

        nr_of_books_downloaded = 0
        is_interactive = sys.stdout.isatty()
        for book in my_books_data:
            download_urls = get_product_download_urls(book['id'])
            for format, download_url in download_urls.items():
                if format in formats and not (format == 'code' and 'video' in download_urls and 'video' in formats):
                    file_extention = 'zip' if format in ('video', 'code') else format
                    file_name = slugify_book_title(book['title'])
                    logger.info('Title: "{}"'.format(book['title']))
                    if into_folder:
                        target_download_path = os.path.join(self.cfg.download_folder_path, file_name)
                        if not os.path.isdir(target_download_path):
                            os.mkdir(target_download_path)
                    else:
                        target_download_path = os.path.join(self.cfg.download_folder_path)
                    full_file_path = os.path.join(target_download_path, '{}.{}'.format(file_name, file_extention))
                    if os.path.isfile(full_file_path):
                        logger.info('"{}.{}" already exists under the given path.'.format(file_name, file_extention))
                    else:
                        if format == 'code':
                            logger.info('Downloading code for ebook: "{}"...'.format(book['title']))
                        elif format == 'video':
                            logger.info('Downloading "{}" video...'.format(book['title']))
                        else:
                            logger.info('Downloading ebook: "{}" in {} format...'.format(book['title'], format))
                        try:
                            file_url = api_client.get(download_url).json().get('data')
                            r = api_client.get(file_url, timeout=100, stream=True)
                            if r.status_code is 200:
                                with open(full_file_path, 'wb') as f:
                                    total_length = int(r.headers.get('content-length'))
                                    num_of_chunks = (total_length / 1024) + 1
                                    for num, chunk in enumerate(r.iter_content(chunk_size=1024)):
                                        if chunk:
                                            if is_interactive:
                                                PacktPublishingFreeEbook.update_download_progress_bar(
                                                    num / num_of_chunks
                                                )
                                            f.write(chunk)
                                            f.flush()
                                    if is_interactive:
                                        PacktPublishingFreeEbook.update_download_progress_bar(-1)  # add end of line
                                if format == 'code':
                                    logger.success('Code for ebook "{}" downloaded successfully!'.format(book['title']))
                                else:
                                    logger.success('Ebook "{}" in {} format downloaded successfully!'.format(
                                        book['title'],
                                        format
                                    ))
                                nr_of_books_downloaded += 1
                            else:
                                message = 'Couldn\'t download "{}" ebook in {} format.'.format(book['title'], format)
                                logger.error(message)
                                raise requests.exceptions.RequestException(message)
                        except Exception as e:
                            logger.error(e)
        logger.info("{} ebooks have been downloaded!".format(str(nr_of_books_downloaded)))

    @staticmethod
    def update_download_progress_bar(current_work_done):
        """Prints progress bar, current_work_done should be float value in range {0.0 - 1.0}, else prints '\n'"""
        if 0.0 <= current_work_done <= 1.0:
            print(
                "\r[PROGRESS] - [{0:50s}] {1:.1f}% ".format('#' * int(current_work_done * 50), current_work_done * 100),
                end="", )
        else:
            print("")


@click.command()
@click.option('-c', '--cfgpath', default=os.path.join(os.getcwd(), 'configFile.cfg'), help='Config file path.')
@click.option('-g', '--grab', is_flag=True, help='Grab Free Learning Packt ebook.')
@click.option('-gd', '--grabd', is_flag=True, help='Grab Free Learning Packt ebook and download it afterwards.')
@click.option('-da', '--dall', is_flag=True, help='Download all ebooks from your Packt account.')
@click.option('-sgd', '--sgd', is_flag=True, help='Grab Free Learning Packt ebook and download it to Google Drive.')
@click.option('-m', '--mail', is_flag=True, help='Grab Free Learning Packt ebook and send it by an email.')
@click.option('-sm', '--status_mail', is_flag=True, help='Send an email whether script execution was successful.')
@click.option('-f', '--folder', default=False, help='Download ebooks into separate directories.')
@click.option(
    '--noauth_local_webserver',
    is_flag=True,
    default=False,
    help='See Google Drive API Setup section in README.'
)
def packt_cli(cfgpath, grab, grabd, dall, sgd, mail, status_mail, folder, noauth_local_webserver):
    config_file_path = cfgpath
    into_folder = folder

    try:
        cfg = ConfigurationModel(config_file_path)
        ebook = PacktPublishingFreeEbook(cfg)
        api_client = PacktAPIClient(cfg.my_packt_email, cfg.my_packt_password)

        # Grab the newest book
        if grab or grabd or sgd or mail:
            ebook.grab_ebook(api_client)

            # Send email about successful book grab. Do it only when book
            # isn't going to be emailed as we don't want to send email twice.
            if status_mail and not mail:
                from utils.mail import MailBook
                mb = MailBook(config_file_path)
                mb.send_info(
                    subject=SUCCESS_EMAIL_SUBJECT.format(
                        dt.datetime.now().strftime(DATE_FORMAT),
                        ebook.book_data['title']
                    ),
                    body=SUCCESS_EMAIL_BODY.format(ebook.book_data['title'])
                )

        # Download book(s) into proper location.
        if grabd or dall or sgd or mail:
            if dall:
                ebook.download_books(api_client, into_folder=into_folder)
            elif grabd:
                ebook.download_books(api_client, ebook.book_data, into_folder=into_folder)
            else:  # sgd or mail
                # download it temporarily to cwd
                cfg.download_folder_path = os.getcwd()
                ebook.download_books(api_client, ebook.book_data, into_folder=False)

        # Send downloaded book(s) by mail or to Google Drive.
        if sgd or mail:
            paths = [
                os.path.join(cfg.download_folder_path, path)
                for path in os.listdir(cfg.download_folder_path)
                if os.path.isfile(path) and slugify_book_title(ebook.book_data['title']) in path
            ]
            if sgd:
                from utils.google_drive import GoogleDriveManager
                google_drive = GoogleDriveManager(config_file_path)
                google_drive.send_files(paths)
            else:
                from utils.mail import MailBook
                mb = MailBook(config_file_path)
                pdf_path = None
                mobi_path = None
                try:
                    pdf_path = [path for path in paths if path.endswith('.pdf')][-1]
                    mobi_path = [path for path in paths if path.endswith('.mobi')][-1]
                except IndexError:
                    pass
                if pdf_path:
                    mb.send_book(pdf_path)
                if mobi_path:
                    mb.send_kindle(mobi_path)
            for path in paths:
                os.remove(path)

        logger.success("Good, looks like all went well! :-)")
    except Exception as e:
        logger.error("Exception occurred {}".format(e))
        if status_mail:
            from utils.mail import MailBook
            mb = MailBook(config_file_path)
            mb.send_info(
                subject=FAILURE_EMAIL_SUBJECT.format(dt.datetime.now().strftime(DATE_FORMAT)),
                body=FAILURE_EMAIL_BODY.format(str(e))
            )
        sys.exit(2)

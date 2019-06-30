import os
import sys

import requests
from requests.exceptions import ConnectionError
from slugify import slugify

from api import (
    PACKT_API_PRODUCT_FILE_DOWNLOAD_URL,
    PACKT_API_PRODUCT_FILE_TYPES_URL
)
from utils.logger import get_logger


logger = get_logger(__name__)


class PacktConnectionError(ConnectionError):
    """Error raised whenever fetching data from Packt API fails."""
    pass


def slugify_product_name(title):
    """Return book title with spaces replaced by underscore and unicodes replaced by characters valid in filenames."""
    return slugify(title, separator='_', lowercase=False)


def get_product_download_urls(api_client, product_id):
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


def download_products(api_client, download_directory, formats, product_list, into_folder=False):
    """Download selected products."""
    nr_of_books_downloaded = 0
    is_interactive = sys.stdout.isatty()
    for book in product_list:
        download_urls = get_product_download_urls(api_client, book['id'])
        for format, download_url in download_urls.items():
            if format in formats and not (format == 'code' and 'video' in download_urls and 'video' in formats):
                file_extention = 'zip' if format in ('video', 'code') else format
                file_name = slugify_product_name(book['title'])
                logger.info('Title: "{}"'.format(book['title']))
                if into_folder:
                    target_download_path = os.path.join(download_directory, file_name)
                    if not os.path.isdir(target_download_path):
                        os.mkdir(target_download_path)
                else:
                    target_download_path = os.path.join(download_directory)
                full_file_path = os.path.join(target_download_path, '{}.{}'.format(file_name, file_extention))
                temp_file_path = os.path.join(target_download_path, 'download.tmp')
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
                            try:
                                with open(temp_file_path, 'wb') as f:
                                    total_length = int(r.headers.get('content-length'))
                                    num_of_chunks = (total_length / 1024) + 1
                                    for num, chunk in enumerate(r.iter_content(chunk_size=1024)):
                                        if chunk:
                                            if is_interactive:
                                                update_download_progress_bar(num / num_of_chunks)
                                            f.write(chunk)
                                            f.flush()
                                    if is_interactive:
                                        update_download_progress_bar(-1)  # add end of line
                                os.rename(temp_file_path, full_file_path)
                            finally:
                                if os.path.isfile(temp_file_path):
                                    os.remove(temp_file_path)

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


def update_download_progress_bar(current_work_done):
    """Prints progress bar, current_work_done should be float value in range {0.0 - 1.0}, else prints '\n'"""
    if 0.0 <= current_work_done <= 1.0:
        print(
            "\r[PROGRESS] - [{0:50s}] {1:.1f}% ".format('#' * int(current_work_done * 50), current_work_done * 100),
            end="", )
    else:
        print("")

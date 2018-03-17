import requests
import time
from urllib.parse import urljoin

from .logger import get_logger
logger = get_logger(__name__)

API_URL = 'https://api.anti-captcha.com'
CREATE_TASK_API_URL = urljoin(API_URL, 'createTask')
GET_TASK_API_URL = urljoin(API_URL, 'getTaskResult')


class AnticaptchaException(Exception):
    pass


class Anticaptcha(object):
    """
    anti-captcha.com client which helps to solve reCaptchas
    More info concerning the API: https://anti-captcha.com/apidoc/
    """
    timeout = 120  # Timeout in second - during busy periods, we may need to wait about 2 minutes to solve ReCAPTCHA.

    def __init__(self, api_key):
        self.api_key = api_key

    def __post_request(self, url, **kwargs):
        response = requests.post(url, **kwargs).json()
        if response.get('errorId'):
            raise AnticaptchaException("Error {0} occured: {1}".format(
                response.get('errorCode'),
                response.get('errorDescription')
            ))
        return response

    def __create_noproxy_task(self, website_url, website_key):
        content = {
            'clientKey': self.api_key,
            'task': {
                "type": "NoCaptchaTaskProxyless",
                "websiteURL": website_url,
                "websiteKey": website_key
            }
        }
        response = self.__post_request(CREATE_TASK_API_URL, json=content)
        return response.get('taskId')

    def __wait_for_task_result(self, task_id):
        start_time = time.time()
        content = {
            'clientKey': self.api_key,
            'taskId': task_id
        }
        while (time.time() - start_time) < self.timeout:
            response = self.__post_request(GET_TASK_API_URL, json=content)
            if response.get('status') == 'ready':
                return response
            time.sleep(1)
        raise AnticaptchaException('Timeout {} reached '.format(self.timeout))

    def solve_recaptcha(self, website_url, website_key):
        task_id = self.__create_noproxy_task(website_url, website_key)
        logger.info('Waiting for completion of the {} task...'.format(task_id))
        solution = self.__wait_for_task_result(task_id)['solution']['gRecaptchaResponse']
        logger.success('Solution found for {} task.'.format(task_id))
        return solution

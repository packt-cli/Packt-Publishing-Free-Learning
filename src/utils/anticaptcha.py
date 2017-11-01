import requests
import time

from .logger import get_logger
logger = get_logger(__name__)


class AnticaptchaException(Exception):
    pass

class TransientError(Exception):
    """Transient Error during anticaptcha, retry later"""
    pass


class Anticaptcha(object):
    """
    anti-captcha.com client which helps to solve reCaptchas
    More info concerning the API: https://anti-captcha.com/apidoc/
    """
    api_url = 'https://api.anti-captcha.com'
    create_task_url = api_url + '/createTask'
    get_task_result_url = api_url + '/getTaskResult'
    get_queue_stat_url = api_url + '/getQueueStats'
    timeout_time_sec = 60  # timeout
    # max duration for execution is 5 min or 300 seconds
    max_retry        = 30  # Number max of retry for transient errors
    sleep_time       = 10 # Number of seconds to wait before retrying

    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
    
    def __get_queue_stat(self):
        content = {
            'queueId': 1
        }
        response = self.__post_request(self.get_queue_stat_url, json=content)
        logger.info('ServerStats [{0}]'.format(response))


    def __post_request(self, url, **kwargs):
        response = self.session.post(url, **kwargs).json()
        if response.get('errorId'):
            raise AnticaptchaException("Error {0} occured: {1}".format(
                response.get('errorCode'),
                response.get('errorDescription')
            ))
        return response
    
    def __post_request_task(self, url, **kwargs):
        self.__get_queue_stat()
        response = self.session.post(url, **kwargs).json()
        if response.get('errorId'):
            error_code=response.get('errorCode')
            error_description=response.get('errorDescription')
            if ( not (error_code.find("ERROR_NO_SLOT_AVAILABLE") != -1  or  error_code.find("ERROR_INCORRECT_SESSION_DATA") != -1 ) ):
                raise AnticaptchaException("Error [{0}] occured: [{1}]".format(error_code,error_description))
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
        
        # Check if response is a transient error if yes try to submit it again.
        for x in range(0, self.max_retry):
            logger.info('Try to start anticaptcha session [{0}/{1}]'.format(x,self.max_retry))
            response = self.__post_request_task(self.create_task_url, json=content)
            if response.get('errorId'):
                error_code=response.get('errorCode')
                error_description=response.get('errorDescription')
                if ( not (error_code.find("ERROR_NO_SLOT_AVAILABLE") != -1  or  error_code.find("ERROR_INCORRECT_SESSION_DATA") != -1 ) ):
                    raise AnticaptchaException("Error [{0}] occured: [{1}]".format(error_code,error_description))
                else:
                    logger.warn('transient error[{0}] message [{1}]'.format(error_code,error_description))
                    logger.warn('Wait [{0}] seconds before retry'.format(self.sleep_time))
            else:
                return response.get('taskId')
            time.sleep(self.sleep_time)     
           
        return response.get('taskId')

    def __wait_for_task_result(self, task_id):
        start_time = time.time()
        content = {
            'clientKey': self.api_key,
            'taskId': task_id
        }
        while (time.time() - start_time) < self.timeout_time_sec:
            response = self.__post_request(self.get_task_result_url, json=content)
            if response.get('status') == 'ready':
                return response
            time.sleep(1)
        raise AnticaptchaException('Timeout {} reached '.format(self.timeout_time_sec))

    def solve_recaptcha(self, website_url, website_key):
        task_id = self.__create_noproxy_task(website_url, website_key)
        logger.info('TaskId created: {}'.format(task_id))
        logger.info('Waiting for completion of the task: {}...'.format(task_id))
        solution = self.__wait_for_task_result(task_id)['solution']['gRecaptchaResponse']
        logger.success('Solution found for task: {}'.format(task_id))
        return solution

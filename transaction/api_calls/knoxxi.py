import requests
import hashlib
import time
from transaction.utils import log_error
from kitiwa.settings import KNOXXI_TOP_UP_ENABLED, KNOXXI_USER_NAME,\
    KNOXXI_API_KEY, KNOXXI_BASE_URL, KNOXXI_NETWORK_CODES, proxies


def direct_top_up(mobile_number, amount, action='14', offset='0'):

    if not KNOXXI_TOP_UP_ENABLED:
        return

    timestamp = str(int(time.time() * 1000))

    network = KNOXXI_NETWORK_CODES[mobile_number[0:3]]
    mobile_number = '+233{}'.format(mobile_number[1::])

    to_encrypt = '{}{}{}{}{}{}'.format(
        KNOXXI_USER_NAME, network, KNOXXI_API_KEY, action,
        amount, mobile_number
    )

    checksum = hashlib.md5(to_encrypt).hexdigest()

    payload = {
        'action': action,
        'userName': KNOXXI_USER_NAME,
        'network': network,
        'receiverPhone': mobile_number,
        'amount': amount,
        'timeStamp': timestamp,
        'offset': offset,
        'checksum': checksum,
    }

    response = requests.get(
        KNOXXI_BASE_URL,
        params=payload,
        proxies=proxies
    )

    try:
        response_code = response.text[0:2]
        if response_code != '00':
            message = 'ERROR - Knoxxi: Failed to top up phone number {} '\
                      '(amount: {}). Response code: {}.'
            log_error(message.format(mobile_number, amount, response_code))
            return False

    except TypeError:
        message = 'ERROR - Knoxxi: Failed to top up phone number {} '\
                  '(amount: {}). No response code received.'
        log_error(message.format(mobile_number, amount))
        return False

    return True
import requests
import hashlib
import time
from kitiwa.settings import NOXXI_USER_NAME, NOXXI_API_KEY,\
    NOXXI_BASE_URL, NOXXI_NETWORK_CODES, proxies, NOXXI_TOP_UP_ENABLED


def direct_top_up(mobile_number, amount, action='14', offset='0'):

    if not NOXXI_TOP_UP_ENABLED:
        return

    timestamp = str(int(time.time() * 1000))

    network = NOXXI_NETWORK_CODES[mobile_number[0:3]]
    mobile_number = '+233{}'.format(mobile_number[1::])

    to_encrypt = '{}{}{}{}{}{}'.format(
        NOXXI_USER_NAME, network, NOXXI_API_KEY, action,
        amount, mobile_number
    )

    checksum = hashlib.md5(to_encrypt).hexdigest()

    payload = {
        'action': action,
        'userName': NOXXI_USER_NAME,
        'network': network,
        'receiverPhone': mobile_number,
        'amount': amount,
        'timeStamp': timestamp,
        'offset': offset,
        'checksum': checksum,
    }

    response = requests.get(
        NOXXI_BASE_URL,
        params=payload,
        proxies=proxies
    )

    try:
        response_code = response.text[0:2]
        if response_code != '00':
            pass
            # logging
    except TypeError:
        pass
        # logging

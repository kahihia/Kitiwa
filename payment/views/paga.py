from django.shortcuts import redirect
from django.db import transaction as dbtransaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status

from payment.models import PagaPayment
from payment.utils import PagaException

from transaction.models import Transaction

from kitiwa.api_calls import sendgrid_mail
from kitiwa.utils import log_error
from kitiwa.settings import ENV_SITE_MAPPING, ENV, SITE_USER, ENV_LOCAL
from kitiwa.settings import PAGA_MERCHANT_KEY, PAGA_PRIVATE_KEY


# TODO: make this a background task
@api_view(['POST'])
def backend_callback(request):

    try:
        invoice = request.DATA.get('invoice')
        transaction_id = request.DATA.get('transaction_id')
        transaction_reference = request.DATA.get('transaction_reference')

        notification_private_key = request.DATA.get('notification_private_key')
        merchant_key = request.DATA.get('merchant_key')

        amount = float(request.DATA.get('amount'))
        transaction_datetime = request.DATA.get('transaction_datetime')

        # find transaction
        transaction = Transaction.objects.get(transaction_uuid=invoice)
        if transaction.state != Transaction.INIT:
            message = 'ERROR - PAGA (backend): request refers to transaction {} in state {}. {}'
            message = message.format(transaction.id, transaction.state, request.DATA)
            raise PagaException

        # validate merchant key
        if merchant_key != PAGA_MERCHANT_KEY:
            message = 'ERROR - PAGA (backend): request with invalid merchant key ({}) for transaction {}. {}'
            message = message.format(merchant_key, transaction.id, request.DATA)
            raise PagaException

        # validate private key
        if notification_private_key != PAGA_PRIVATE_KEY:
            message = 'ERROR - PAGA (backend): request with invalid private key ({}) for transaction {}. {}'
            message = message.format(notification_private_key, transaction.id, request.DATA)
            raise PagaException

        # double check amount
        if amount != transaction.amount_ngn:
            message = 'ERROR - PAGA (backend): amount for transaction {} does not match database value (db: {}, paga: {}). {}'
            message = message.format(transaction.id, transaction.amount_ngn, amount, request.DATA)
            raise PagaException

        # create PagaPayment
        paga_payment = PagaPayment(
            transaction=transaction, paga_transaction_reference=transaction_reference,
            paga_transaction_id=transaction_id, paga_processed_at=transaction_datetime, status='SUCCESS')

        # update transaction and paga payment (all-or-nothing)
        with dbtransaction.atomic():
            transaction.set_paid()
            paga_payment.save()

        sendgrid_mail.notify_admins_paid()

        return Response({'detail': 'Success'})

    except PagaException as e:
        log_error(message)

    except Transaction.DoesNotExist as e:
        message = 'ERROR - PAGA (backend): no transaction found for uuid {}, {}. {}'
        log_error(message.format(invoice, e, request.DATA))

    except (KeyError, TypeError, ValueError) as e:
        message = 'ERROR - PAGA (backend): received invalid payment notification, {}, {}'
        log_error(message.format(e, request.DATA))

    return Response({'detail': 'Error'}, status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@require_http_methods(['POST'])
def user_callback(request):
    try:
        paga_status = request.POST.get('status')
        merchant_key = request.POST.get('key')
        transaction_id = request.POST.get('transaction_id')
        process_code = request.POST.get('process_code')
        invoice = request.POST.get('invoice')

        kitiwa_reference = request.GET.get('reference', 'error')

        # could be used for double checking the value
        # total = request.POST.get('total')

        # not needed for now
        # fee = request.POST.get('fee')
        # test = request.POST.get('test')
        # message = request.POST.get('message')
        # exchangeRate = request.POST.get('exchange_rate')
        # reference_number = request.POST.get('reference_number')
        # currency = request.POST.get('currency')
        # reference = request.POST.get('reference')
        # customer_account = request.POST.get('customer_account')

        if (paga_status is None or merchant_key is None or transaction_id is None
                or process_code is None or invoice is None):
            raise ValueError

        if merchant_key != PAGA_MERCHANT_KEY:
            raise PagaException
            # return redirect(http_prefix + ENV_SITE_MAPPING[ENV][SITE_USER] + '/#!/failed?error=merchantkey')

        http_prefix = 'https://'
        if ENV == ENV_LOCAL:
            http_prefix = 'http://'

        if paga_status == 'SUCCESS':
            return redirect(http_prefix + ENV_SITE_MAPPING[ENV][SITE_USER] + '/#!/thanks?reference=' + kitiwa_reference +
                            '&pagaTransactionId=' + transaction_id)
        else:
            # TODO: put this in messaging queue
            transaction = Transaction.objects.get(transaction_uuid=invoice, state=Transaction.INIT)
            paga_payment = PagaPayment(
                transaction=transaction, paga_transaction_reference=process_code,
                paga_transaction_id=transaction_id, status=paga_status)
            with dbtransaction.atomic():
                transaction.set_declined()
                paga_payment.save()

            return redirect(http_prefix + ENV_SITE_MAPPING[ENV][SITE_USER] + '/#!/failed?reference=' + kitiwa_reference +
                            '&status=' + paga_status)

    except (TypeError, ValueError) as e:
        message = 'ERROR - PAGA (user redirect): received invalid payment notification, {}, {}'
        log_error(message.format(e, request.POST))
    except Transaction.DoesNotExist as e:
        message = 'ERROR - PAGA (user redirect): no transaction in state INIT found for uuid {}, {}. {}'
        log_error(message.format(invoice, e, request.POST))
    except PagaException:
        message = 'ERROR - PAGA (user redirect): request with invalid merchant key ({}) for transaction {}. {}'
        log_error(message.format(merchant_key, transaction_id, request.POST))
 
    return Response({'detail': 'Error'}, status.HTTP_400_BAD_REQUEST)

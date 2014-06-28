from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from payment import views


urlpatterns = patterns(
    '',

    # payments
    url(r'^(?P<pk>[0-9]+)/$', views.RetrievePayment.as_view(), name='payment-detail'),

    # mpower
    url(r'^mpower/$', 'payment.views.mpower_opr_charge', name='mpower-charge'),

    # paga
    url(r'^paga/$', 'payment.views.paga_payment_notification', name='paga-notify'),
)

urlpatterns = format_suffix_patterns(urlpatterns)

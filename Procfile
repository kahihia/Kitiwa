web: python manage.py collectstatic --noinput;newrelic-admin run-program python manage.py run_gunicorn -b "0.0.0.0:$PORT" -w 3

heroku config -s | grep QUOTAGUARDSTATIC_URL >> .env
more .env
FROM python:3.8.5

WORKDIR /app/webapp/python/
ADD requirements.txt /tmp/

RUN apt-get update && \
    apt-get install -y mariadb-client &&  \
    rm -rf /var/lib/apt && \
    pip install -U pip && \
    pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt
# RUN pip install uwsgi

CMD ["python", "app.py"]
#CMD /home/isucon/local/python/bin/uwsgi -w app:app --master --processes 4 --pidfile /home/isucon/isuumo/webapp/python/server.pid --socket /tmp/uwsgi.sock --chmod-socket=666 --enable-threads

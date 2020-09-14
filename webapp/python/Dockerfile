FROM python:3.8.5

WORKDIR /app/webapp/python/
ADD requirements.txt /tmp

RUN pip3 install -U pip
RUN pip3 install -r /tmp/requirements.txt
#RUN pip3 install uwsgi

CMD python3 /app/webapp/python/app.py
#CMD /home/isucon/local/python/bin/uwsgi -w app:app --master --processes 4 --pidfile /home/isucon/isuumo/webapp/python/server.pid --socket /tmp/uwsgi.sock --chmod-socket=666 --enable-threads
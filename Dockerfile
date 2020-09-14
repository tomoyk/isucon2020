FROM ubuntu:18.04

WORKDIR /app
ADD app/requirements.txt /tmp
ADD mysql/* /etc/

RUN apt-get update && apt-get install -y \
	mysql-server \
	python3 \
	python3-pip \
	systemd \
	wget \
	htop

RUN wget https://nginx.org/keys/nginx_signing.key
RUN apt-key add nginx_signing.key
RUN echo "deb http://nginx.org/packages/ubuntu/ bionic nginx" >> /etc/apt/sources.list
RUN echo "deb-src http://nginx.org/packages/ubuntu/ bionic nginx" >> /etc/apt/sources.list

RUN apt-get update && apt-get install nginx

RUN pip3 install -r /tmp/requirements.txt


RUN usermod -d /var/lib/mysql mysql
RUN service mysql start && mysql -uroot -e "create user 'isucon'@'localhost' identified by 'isucon';"
RUN service mysql start && mysql -uroot -e "grant all privileges on *.* to 'isucon'@'%' identified by 'isucon' with grant option;"

RUN service nginx start

EXPOSE 80 3306

ENTRYPOINT service mysql start && service nginx start && /bin/bash

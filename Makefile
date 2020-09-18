NGX_LOG:=/var/log/nginx/access.log

kataru:
	sudo cat $(NGX_LOG) | kataribe -f ./kataribe.toml | tail -n 39 | tee /home/isucon/logs/kataribe/kataribe_log.`date "+%H-%M-%S"`
mysqltuner:
	perl MySQLTuner-perl/mysqltuner.pl --user isucon --pass='isucon' > /home/isucon/logs/mysqltuner/mysqltuner_log.`date "+%H-%M-%S"`

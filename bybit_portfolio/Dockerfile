ARG BUILD_FROM
FROM $BUILD_FROM

RUN pip3 install --no-cache-dir requests==2.32.3

COPY run.sh /
COPY app /app

RUN chmod a+x /run.sh

CMD ["/run.sh"]

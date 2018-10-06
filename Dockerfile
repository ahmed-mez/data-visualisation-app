FROM python:3.6.5

# update packages
RUN apt-get update -y

# set workdir
WORKDIR /visualisation-app

# pip install
COPY requirements.txt /visualisation-app
RUN pip install -r requirements.txt
RUN rm requirements.txt
RUN pip install uwsgi

# uwsgi conf
COPY uwsgi.ini /etc/uwsgi/apps-available/visualisation-app.ini

# data
COPY data /visualisation-app/data

# static
COPY static /visualisation-app/static

# static
COPY templates /visualisation-app/templates

# code
COPY app.py /visualisation-app
COPY config.py /visualisation-app

# logs folder
RUN mkdir logs

# entrypoint
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["start"]
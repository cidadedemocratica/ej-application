FROM python:3.7
ARG tag
ARG env
# Install debian dependencies
RUN apt-get update \
    && apt-get install -y \
    curl \
    gcc \
    git \
    ruby-sass \
    gnupg2 \
    libc6-dev \
    libdpkg-perl \
    make \
    gettext
# Move ej nginx conf to nginx volume
RUN touch /etc/apt/preferences.d/nodejs && \
    echo "Package: nodejs\nPin: origin deb.nodesource.com\nPin-Priority: 1001" > /etc/apt/preferences.d/nodejs
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash - \
    && apt install nodejs -y && npm install -g yarn webpack@4.6.0
COPY ./ /ej-server
WORKDIR ej-server
RUN cd lib && npm install
RUN pip install invoke markupsafe toolz libsass gunicorn
RUN pip install sidekick psycopg2 toml
RUN pip install -r etc/requirements-dev.txt
RUN inv i18n && inv i18n -c && inv build-assets && inv collect

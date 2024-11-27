FROM python:3.9.19-slim-bookworm
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
    gettext \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    g++ \
    locales
RUN sed -i 's/^# *\(pt_BR.UTF-8\)/\1/' /etc/locale.gen
RUN locale-gen
RUN touch /etc/apt/preferences.d/nodejs && \
    echo "Package: nodejs\nPin: origin deb.nodesource.com\nPin-Priority: 1001" > /etc/apt/preferences.d/nodejs
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - && apt install nodejs -y
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${PATH}:/root/.local/bin"
RUN poetry config virtualenvs.create false
COPY ./ /ej-application
WORKDIR ej-application
# Installs main and dev groups dependencies
RUN poetry install --with main,dev --no-root

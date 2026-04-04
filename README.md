[[_TOC_]]

<img width="128" src="https://gitlab.com/pencillabs/ej/ej-application/-/raw/develop/src/ej/static/ej/assets/img/logo/logo-dark.png?ref_type=heads" align="left" style="margin-right:15px"/>

**Pushing Together** is an open-source web platform to manage participative opinion research,
with built-in machine learning algorithm to generate opinion groups from participation data.
You can visit EJ at [https://www.ejplatform.org](https://www.ejplatform.org).
For detailed information on developing and using our system, please refer to the [documentation](https://www.ejplatform.org/docs/).
For contributions, issues or feature requests join us on [https://github.com/cidadedemocratica/ej-application](https://github.com/cidadedemocratica/ej-application).

# Getting started with Docker

**1. Clone the repository**

```sh
     git clone https://gitlab.com/pencillabs/ej/ej-application
     cd ej-application
```

**2. Install [docker compose plugin](https://docs.docker.com/compose/install/linux/#install-using-the-repository)**

**3. Create a virtual environment**

> **The current supported python version is 3.12.**

```shell
mkdir ../virtualenvs # if it does not exist
python -m venv ../virtualenvs/ej/
source ../virtualenvs/ej/bin/activate
poetry install
cp .env.sample .env
inv up
```


This will deploy EJ using **docker/docker-compose.yml** file.
Every code change will be synchronized with the `server` service. After `inv up`, you can access EJ on `http://localhost:8000` url.

> **From here, you can check our [guides](#documentation) to explore EJ participative features and more advanced development documentation.**

If you are creating a clean instance, you can populate the database with some fake data using the command `inv exec "inv db-fake"`.

Alternatively, if you wish to clean your database and repopulate it using the
script, you'll need to remove the `docker_backups` volume. After that, run `inv up` command and then
`inv exec "inv db-fake"`, as mentioned previously. To rebuild the server image, you can run `inv build --no-cache`.

## macOS

If you are using a Mac with Intel chip the above process may work for you, if not you can follow the same steps as below.

You will have to setup a virtual machine (Linux), preferably UTM for Apple silicon as VirtualBox for Apple silicon is still unstable and crashes every 15 min as of May 2024.
If you want to set up a virtual machine on Intel chip Mac, even VirtualBox is a good choice.
Follow [https://dev.to/ruanbekker/how-to-run-a-amd64-bit-linux-vm-on-a-mac-m1-51cp](https://dev.to/ruanbekker/how-to-run-a-amd64-bit-linux-vm-on-a-mac-m1-51cp), for VM setup. Then normally download all dependencies (git, python, pip, docker, code-editor) on virtual device.

1. Set up Docker [Docker Compose plugin](https://docs.docker.com/engine/install/debian/#installation-methods)
2. Install invoke and django environment

```sh
python -m venv ../virtualenvs/ej/
source ../virtualenvs/ej/bin/activate
poetry install
cp .env.sample .env
inv up
```

3. Build the server Docker image

```python
inv build --no-cache
```

4. Create the containers

```sh
inv up
```

# Celery

EJ uses [Celery](https://docs.celeryproject.org/) for asynchronous task processing, with RabbitMQ as the message broker.

## Clustering

The main use of Celery in EJ is for opinion clustering processing. When a conversation needs to update its opinion groups (clusters), this task is executed asynchronously to avoid blocking the application. The Docker `celery` service is responsible to run the Celery worker.

## Task Logs

To monitor Celery task logs:

```sh
inv celery-logs
```

## Available Tasks

| Task | Description |
| ---- | ----------- |
| `update_clusterization` | Updates clusters for a conversation |

# Available commands

Some useful commands to manage docker environment:

| Command           | Description                                      |
| ----------------- | ------------------------------------------------ |
| inv up     | Creates EJ containers and runs the application    |
| inv build   | Builds EJ server Docker image                    |
| inv logs    | Shows Django logs                                |
| inv celery  | Runs Celery worker                               |
| inv celery-logs | Shows Celery logs                             |
| inv stop    | Stops EJ containers                              |
| inv rm      | Removes EJ containers                            |
| inv attach  | Connects to Django container                     |
| inv exec    | Executes a shell command inside Django container |

Some useful commands to manage the application **(run this inside django container)**:

| Command          | Description                                                    |
| ---------------- | -------------------------------------------------------------- |
| inv i18n         | Extracts messages from Jinja templates for translation         |
| inv i18n -c      | Compile .po files                                              |
| inv sass         | Compile .sass files for all EJ apps.                           |
| inv sass --watch | Watch changes on code, and compile .sass files for all EJ apps |
| inv collect      | Moves compiled files (css, js) to Django static folder         |
| inv db           | Prepare database and run migrations                            |
| inv shell        | Executes Django shell with IPython                             |
| inv docs         | Compile .rst documentation to generate .html files            |
| inv celery  | Runs Celery worker                               |


# Tests

If you are making changes to EJ codebase, do not forget to run tests frequently.
EJ uses Pytest:

```sh/terminal
inv test
```

Beyond unit and integration tests, EJ also has e2e tests implemented with [Cypress](https://www.cypress.io/).
Check `src/ej/tests/e2e/README.md` for more information.

# API

EJ API autogenerated documentation and endpoints
will be available at [http://localhost:8000/api/v1/swagger/](http://localhost:8000/api/v1/swagger/).

# Guides

After configuring the local environment, the next step is reading our documentation. It can be generated with:

```sh
inv exec "inv docs"
```

and will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

from functools import reduce
from invoke import task

from .base import runner

__all__ = [
    "up",
    "build",
    "exec",
    "attach",
    "attach_db",
    "test",
    "stop",
    "rm",
    "logs",
    "celery_logs",
]

COMPOSE_BINARY = "docker compose"
COMPOSE_FILE = f"{COMPOSE_BINARY} -f docker/docker-compose.yml"


@task(
    help={
        "dry_run": "Exibe o comando sem executá-lo",
        "d": "Executa em background (detached)",
        "build": "Reconstroi as imagens antes de subir",
    }
)
def up(ctx, dry_run=False, d=False, build=False):
    """
    Executes EJ on url http://localhost:8000
    """
    do = runner(ctx, dry_run, pty=True)
    cmd = f"{COMPOSE_FILE} up"
    if d:
        cmd += " -d"
    if build:
        cmd += " --build"
    do(cmd)


@task(
    help={
        "dry_run": "Exibe o comando sem executá-lo",
        "no_cache": "Ignora o cache durante o build",
        "prod": "Build para ambiente de produção",
        "registry": "Endereço do registry para a imagem",
        "tag": "Tag aplicada à imagem",
    }
)
def build(ctx, dry_run=False, no_cache=False, prod=False, registry="", tag=""):
    """
    Build EJ web server image.
    By default, this command will install all EJ dependencies.
    """
    do = runner(ctx, dry_run, pty=True)
    image = f"{registry}/ej-server" if registry else "ej-server"
    tagged_image = f"{image}:{tag}" if tag else image
    argsList = ["-f docker/Dockerfile", f"-t {tagged_image}"]
    argsList.append("--no-cache") if no_cache else False
    args: str = reduce(lambda x, y: x + " " + y, argsList)
    do(f"docker build {args} .")


@task(
    help={
        "command": "Comando a ser executado dentro do container",
        "dry_run": "Exibe o comando sem executá-lo",
        "build": "Reconstroi o container antes de executar",
    }
)
def exec(ctx, command, dry_run=False, build=False):
    """
    Executes a command inside EJ web server container;
    """
    do = runner(ctx, dry_run, pty=True)
    do(
        f"{COMPOSE_FILE} exec server /bin/bash -c 'source /root/.bashrc && {command}'"
    )


@task(
    help={
        "dry_run": "Exibe o comando sem executá-lo",
        "build": "Reconstroi o container antes de executar",
        "path": "Caminho específico dos testes a executar",
    }
)
def test(ctx, dry_run=False, build=False, path=None):
    """
    Runs EJ tests;
    """
    do = runner(ctx, dry_run, pty=True)

    # Monta o comando inv test com o arquivo de teste especificado
    test_command = "inv test"
    if path:
        test_command += f" --path={path}"

    # Monta o comando docker exec com o comando de teste
    docker_command = f"{COMPOSE_FILE} exec server /bin/bash -c '{test_command}'"

    do(docker_command)


@task
def attach(ctx):
    """
    Connect to EJ web server container;
    """
    do = runner(ctx, dry_run=False, pty=True)
    do(f"{COMPOSE_FILE} exec server bash")


@task
def attach_db(ctx):
    """
    Connect to EJ database server container;
    """
    do = runner(ctx, dry_run=False, pty=True)
    do(f"{COMPOSE_FILE} exec db bash")


@task
def stop(ctx):
    """
    Stop EJ containers;
    """
    do = runner(ctx, dry_run=False, pty=True)
    do(f"{COMPOSE_FILE} stop")


@task
def rm(ctx):
    """
    Remove EJ containers;
    """
    do = runner(ctx, dry_run=False, pty=True)
    do(f"{COMPOSE_FILE} rm")


@task
def logs(ctx):
    """
    Follows EJ web server log;
    """
    do = runner(ctx, dry_run=False, pty=True)
    do(f"{COMPOSE_FILE} logs -f server")


@task
def celery_logs(ctx):
    """
    Follows Celery logs;
    """
    do = runner(ctx, dry_run=False, pty=True)
    do(f"{COMPOSE_FILE} logs -f celery")

import os

from invoke import task

from .base import su_docker, runner

__all__ = ["docker_up", "docker_build", "docker_exec", "docker_attach",
           "docker_test", "docker_compose_entrypoint", "docker_stop", "docker_logs"]


@task
def docker_up(ctx, dry_run=False):
    """
    Executes EJ on url http://localhost:8000
    """
    docker = su_docker("docker")
    do = runner(ctx, dry_run, pty=True)
    file = "docker/docker-compose.yml"
    compose = f"docker-compose -f {file}"
    do(f'{compose} up  -d')


@task
def docker_build(ctx, task, dry_run=False, build=False):
    """
     Build EJ web server image;
    """
    docker = su_docker("docker")
    do = runner(ctx, dry_run, pty=True)
    # file = prepare_dockerfile(cmd, file, deploy)
    file = "docker/docker-compose.yml"
    # compose = prepare_compose_cmd(file, task, rocket, docker)
    compose = f"docker-compose -f {file}"
    do(f'{compose} up  -d  --build')


@task
def docker_exec(ctx, command, dry_run=False, build=False):
    """
     Executes a command inside EJ web server container;
    """
    docker = su_docker("docker")
    do = runner(ctx, dry_run, pty=True)
    do(f'docker exec -it docker_server_1 {command}')


@task
def docker_test(ctx, dry_run=False, build=False):
    """
     Runs EJ tests;
    """
    docker = su_docker("docker")
    do = runner(ctx, dry_run, pty=True)
    do(f'docker exec -it docker_server_1 inv test')


@task
def docker_attach(ctx):
    """
     Connect to EJ web server container;
    """
    docker = su_docker("docker")
    do = runner(ctx, dry_run=False, pty=True)
    do(f'{docker} exec -it docker_server_1 bash')


@task
def docker_compose_entrypoint(ctx):
    """
     Entrypoint commands for docker-compose.yml;
    """
    docker = su_docker("docker")
    do = runner(ctx, dry_run=False, pty=True)
    do(f'inv db')
    do(f'inv db-assets')
    do(f'inv i18n --compile')
    do(f'inv i18n')
    do(f'inv run')


@task
def docker_stop(ctx):
    """
     Stop EJ containers;
    """
    docker = su_docker("docker-compose")
    do = runner(ctx, dry_run=False, pty=True)
    do(f'{docker} -f docker/docker-compose.yml stop')


@task
def docker_logs(ctx):
    """
     Follows EJ web server log;
    """
    docker = su_docker("docker")
    do = runner(ctx, dry_run=False, pty=True)
    do(f'{docker} logs -f docker_server_1')

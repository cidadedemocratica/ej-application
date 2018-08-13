import os
import pathlib
import sys

from invoke import task

python = sys.executable
sys.path.append('src')


#
# Call python manage.py in a more robust way
#
def manage(ctx, cmd, env=None, **kwargs):
    kwargs = {k.replace('_', '-'): v for k, v in kwargs.items() if v is not False}
    opts = ' '.join(f'--{k} {"" if v is True else v}' for k, v in kwargs.items())
    cmd = f'{python} manage.py {cmd} {opts}'
    env = {**os.environ, **(env or {})}
    path = env.get("PYTHONPATH", ":".join(sys.path))
    env.setdefault('PYTHONPATH', f'src:{path}')
    ctx.run(cmd, pty=True, env=env)


#
# Build assets
#
@task
def sass(ctx, watch=False, theme='default', trace=False, dry_run=False, rocket=True):
    """
    Run Sass compiler
    """
    if theme and '/' in theme:
        theme = theme.rstrip('/')
        root = f'{theme}/scss/'
        theme = os.path.basename(theme)
    else:
        root = 'lib/scss/' if theme == 'default' else f'lib/themes/{theme}/scss/'

    os.environ['EJ_THEME'] = theme or 'default'
    go = runner(ctx, dry_run, pty=True)
    cmd = f'sass {root}/main.scss:lib/build/css/main.css'
    cmd += f' {root}/rocket.scss:lib/build/css/rocket.css' if rocket else ''
    cmd += ' --watch' if watch else ''
    cmd += ' --trace' if trace else ''
    go('rm -rf .sass-cache lib/build/css/main.css lib/build/css/rocket.css')
    go(cmd)


@task
def js(ctx):
    """
    Build js assets
    """
    print('Nothing to do now ;)')


#
# Django tasks
#
@task
def run(ctx, no_toolbar=False):
    """
    Run development server
    """
    env = {}
    if no_toolbar:
        env['DISABLE_DJANGO_DEBUG_TOOLBAR'] = 'true'
    else:
        manage(ctx, 'runserver 0.0.0.0:8000', env=env)


@task
def gunicorn(ctx, debug=None, environment='production', port=8000, workers=4):
    """
    Run application using gunicorn for production deploys.

    It assumes that static media is served by a reverse proxy.
    """

    from gunicorn.app.wsgiapp import run as run_gunicorn

    env = {
        'DISABLE_DJANGO_DEBUG_TOOLBAR': str(not debug),
        'PYTHONPATH': 'src',
        'DJANGO_ENVIRONMENT': environment,
    }
    if debug is not None:
        env['DJANGO_DEBUG'] = str(debug).lower()
    os.environ.update(env)

    args = [
        'ej.wsgi', '-w', str(workers), '-b', f'0.0.0.0:{port}',
        '--error-logfile=-',
        '--access-logfile=-',
        '--log-level', 'info',
    ]
    sys.argv = ['gunicorn', *args]
    run_gunicorn()


@task
def clean_migrations(ctx):
    """
    Remove all automatically created migrations.
    """
    import re
    auto_migration = re.compile(r'\d{4}_auto_\w+.py')

    remove_files = []
    for app in os.listdir('src'):
        migrations_path = f'src/{app}/migrations/'
        if os.path.exists(migrations_path):
            migrations = os.listdir(migrations_path)
            if '__pycache__' in migrations:
                migrations.remove('__pycache__')
            if sorted(migrations) == ['__init__.py', '0001_initial.py']:
                remove_files.append(f'{migrations_path}/0001_initial.py')
            else:
                remove_files.extend([
                    f'{migrations_path}/{f}' for f in migrations
                    if auto_migration.fullmatch(f)
                ])

    print('Listing auto migrations')
    for file in remove_files:
        print(f'* {file}')
    if input('Remove those files? (y/N)').lower() == 'n':
        for file in remove_files:
            os.remove(file)


#
# DB management
#
@task
def db(ctx, migrate_only=False):
    """
    Perform migrations
    """
    if not migrate_only:
        manage(ctx, 'makemigrations')
    manage(ctx, 'migrate')


@task
def db_reset(ctx):
    """
    Reset data in database and optionally fill with fake data
    """
    ctx.run('rm -f local/db/db.sqlite3')
    manage(ctx, 'migrate')


@task
def db_fake(ctx, users=True, conversations=True, admin=True, safe=False):
    """
    Adds fake data to the database
    """
    msg_error = 'Release build. No fake data will be created!'

    if safe:
        if os.environ.get("FAKE_DB") == 'true':
            print('Creating fake data...')
        else:
            return print(msg_error)
    if users:
        manage(ctx, 'createfakeusers', admin=admin)
    if conversations:
        manage(ctx, 'createfakeconversations')


@task
def db_assets(ctx, path=None, force=False):
    """
    Install assets from a local folder in the database.
    """

    resources = pathlib.Path('lib/resources')
    pages = resources / 'pages'
    fragments = resources / 'fragments'
    data = resources / 'data'

    if path is not None:
        path = pathlib.Path(path)
        if (path / 'pages').exists():
            pages = path / 'pages'
        if (path / 'fragments').exists():
            pages = path / 'fragments'
        if (path / 'data').exists():
            pages = path / 'data'

    icons = data / 'social-icons.json'
    manage(ctx, 'loadpages', path=pages, force=force)
    manage(ctx, 'loadfragments', path=fragments, force=force)
    manage(ctx, 'loadsocialmediaicons', path=icons, force=force)


#
# Docker
#
@task
def docker(ctx, task, cmd=None, port=8000, clean_perms=False, prod=False,
           compose_file=None, dry_run=False, tag='latest', namespace='ej'):
    """
    Runs EJ platform using a docker container.

    Use inv docker-run <cmd>, where cmd is one of single, start, up, run,
    deploy.
    """
    docker = su_docker('docker')
    do = runner(ctx, dry_run, pty=True)
    if compose_file is None and prod or task == 'production':
        compose_file = 'docker/docker-compose.production.yml'
    elif compose_file is None:
        compose_file = 'docker/docker-compose.yml'
    compose = f'{docker}-compose -f {compose_file}'

    if task == 'single':
        do(f'{docker} run'
           f'  -v `pwd`:/app'
           f'  -p {port}:8000'
           f'  -u django'
           f'  -it ej-dev:{tag} {cmd or "bash"}')
    elif task == 'start':
        do(f'{compose} up -d')
        do(f'{compose} run -p {port}:8000 web {cmd or "bash"}')
        do(f'{compose} stop')
    elif task == 'up':
        do(f'{compose} up')
    elif task == 'run':
        do(f'{compose} run -p {port}:8000 web {cmd or "bash"}')
    elif task == 'production':
        do(f'{compose} up')
    else:
        raise SystemExit(f'invalid choice for env: {task}\n'
                         f'valid options: single, start, up, run, deploy')
    if clean_perms:
        do(f'sudo chown `whoami`:`whoami` * -R')


@task
def docker_build(ctx, tag='latest', theme='default:ejplatform', dry_run=False,
                 web=False, dev=False):
    """
    Rebuild all docker images for the project.
    """
    do = runner(ctx, dry_run, pty=True)
    cmd = su_docker(f'docker build . -f docker/Dockerfile')
    if dev is False and web is False:
        web = dev = True
    if dev:
        do(f'{cmd}-dev -t ej-dev:{tag} '
           f'  --build-arg UID={os.getuid()}'
           f'  --build-arg GID={os.getgid()}')
    if web:
        for item in theme.split(','):
            theme, org = item.split(':') if ':' in item else (item, item)
            do(f'{cmd} -t {org}/web:{tag} --build-arg THEME={theme}')


@task
def docker_push(ctx, tag='latest', theme='default:ejplatform', dry_run=False):
    """
    Push docker images for the web container.
    """
    cmd = su_docker(f'docker push')
    do = runner(ctx, dry_run, pty=True)

    for item in theme.split(','):
        theme, org = item.split(':') if ':' in item else (item, item)
        do(f'{cmd} {org}/web:{tag}')


#
# Translations
#
@task
def i18n(ctx, compile=False, edit=False, lang='pt_BR', keep_pot=False):
    """
    Extract messages for translation.
    """
    if edit:
        ctx.run(f'poedit locale/{lang}/LC_MESSAGES/django.po')
    elif compile:
        ctx.run(f'{python} etc/scripts/compilemessages.py')
    else:
        print('Collecting messages')
        manage(ctx, 'makemessages', all=True, keep_pot=True)

        print('Extract Jinja translations')
        ctx.run('pybabel extract -F etc/babel.cfg -o locale/jinja2.pot .')

        print('Join Django + Jinja translation files')
        ctx.run('msgcat locale/django.pot locale/jinja2.pot --use-first -o locale/join.pot', pty=True)
        ctx.run(r'''sed -i '/"Language: \\n"/d' locale/join.pot''', pty=True)

        print(f'Update locale {lang} with Jinja2 messages')
        ctx.run(f'msgmerge locale/{lang}/LC_MESSAGES/django.po locale/join.pot -U')

        if not keep_pot:
            print('Cleaning up')
            ctx.run('rm locale/*.pot')


#
# Good practices and productivity
#
@task
def lint(ctx):
    """
    Execute linters
    """
    ctx.run('flake8 src/', pty=True)


@task
def clean(ctx):
    """
    Clean pyc files and build assets.
    """
    join = os.path.join
    rm_files = []
    rm_dirs = []
    for base, subdirs, files in os.walk('.'):
        if '__pycache__' in subdirs:
            rm_dirs.append(join(base, '__pycache__'))
        elif os.path.basename(base) == '__pycache__':
            rm_files.extend(join(base, f) for f in files)

    print('Removing compiled bytecode files')
    for path in rm_files:
        os.unlink(path)
    for path in rm_dirs:
        os.rmdir(path)


@task
def install_hooks(ctx):
    """
    Install git hooks in repository.
    """
    print('Installing flake8 pre-commit hook')
    ctx.run('flake8 --install-hook=git')


@task
def update_deps(ctx, all=False, vendor=None):
    """
    Update volatile dependencies
    """
    suffix = f' --vendor {vendor}' if vendor else ''
    ctx.run(f'{python} etc/scripts/install-deps.py' + suffix)
    if all:
        ctx.run(f'{python} -m pip install -r etc/requirements/local.txt')
        ctx.run(f'{python} -m pip install -r etc/requirements/develop.txt')
    else:
        print('By default we only update the volatile dependencies. Run '
              '"inv update-deps --all" in order to update everything.')


@task
def configure(ctx, silent=False):
    """
    Install dependencies and configure a test server.
    """
    if silent:
        ask = (lambda x: print(x + 'yes') or True)
    else:
        ask = (lambda x: input(x + ' (y/n) ').lower() == 'y')

    print('\nLoading dependencies (inv update-deps)')
    update_deps(ctx, all=True)

    print('\nCreating database and running migrations (inv db)')
    db(ctx)

    if ask('\nLoad assets to database?'):
        print('Running inv db-assets')
        db_assets(ctx)

    if ask('\nLoad fake data to database?'):
        print('Running inv db-fake')
        db_fake(ctx)


#
# Useful docker entry points
#
@task
def bash(ctx):
    """
    Starts a bash shell.
    """
    print('\nStarting bash console')
    os.execve('/bin/bash', ['bash'], os.environ)


@task
def shell(ctx):
    """
    Starts a Django shell
    """
    manage(ctx, 'shell')


@task
def test(ctx):
    """
    Run all unittests.
    """
    ctx.run('pytest')


@task(name='manage')
def manage_task(ctx, command, noinput=False, args=''):
    """
    Run a Django manage.py command
    """
    kwargs = {}
    if noinput:
        kwargs['noinput'] = noinput
    manage(ctx, f'{command} {args}', **kwargs)


#
# Deploy tasks
#
@task
def docker_deploy(ctx, task, environment='production', command=None, dry_run=False):
    """
    Start a deploy build for the platform.
    """
    os.environ.update(environment=environment, task=task)
    compose_file = 'local/deploy/docker-compose.yml'
    env = docker_deploy_variables('local/deploy/config.py')
    compose = su_docker(f'docker-compose -f {compose_file}')
    do = runner(ctx, dry_run, pty=True, env=env)
    tag = env.get('TAG', 'latest')
    org = env.get('ORGANIZATION', 'ejplatform')

    if task == 'build':
        do(f'{compose} build')
    elif task == 'up':
        do(f'{compose} up')
    elif task == 'run':
        do(f'{compose} run web {command or "bash"}')
    elif task == 'publish':
        docker = su_docker('docker')
        do(f'{docker} pull {org}/web:{tag}')
    elif task == 'notify':
        listeners = env.get('LISTENERS')
        if listeners is None:
            print("Don't know hot to notify the infrastructure!")
            print('(hmm, mail the sysadmin?)')
        for listener in listeners.split(','):
            do(f'sh local/deploy/notify.{listener}.sh')
    else:
        raise SystemExit(f'invalid command: {task}\n'
                         f'Possible commands: build, up, run, publish, notify')


#
# Utilities
#
def su_docker(cmd):
    if os.getuid() == 0:
        return cmd
    else:
        return f'sudo {cmd}'


def runner(ctx, dry_run, **extra):
    def do(cmd, **kwargs):
        if dry_run:
            print(cmd)
        else:
            kwargs = dict(extra, **kwargs)
            return ctx.run(cmd, **kwargs)

    return do


def docker_deploy_variables(path):
    ns = {}
    seq = (list, tuple)
    to_str = (lambda x: ','.join(map(str, x)) if isinstance(x, seq) else str(x))
    with open(path) as fd:
        src = fd.read()
        exec(src, ns)
    return {k: to_str(v) for k, v in ns.items() if k.isupper()}

import os

from invoke import task

__all__ = ["clean", "install_hooks", "test", "lint"]


@task
def clean(_ctx):
    """
    Clean pyc files and build assets.
    """
    join = os.path.join
    rm_files = []
    rm_dirs = []
    for base, subdirs, files in os.walk("."):
        if "__pycache__" in subdirs:
            rm_dirs.append(join(base, "__pycache__"))
        elif os.path.basename(base) == "__pycache__":
            rm_files.extend(join(base, f) for f in files)

    print("Removing compiled bytecode files")
    for path in rm_files:
        os.unlink(path)
    for path in rm_dirs:
        os.rmdir(path)


@task
def install_hooks(ctx):
    """
    Install git hooks in repository.
    """
    print("Installing flake8 pre-commit hook")
    ctx.run("flake8 --install-hook=git")


@task
def lint(ctx, python=True, js=True):
    """
    Run all linters.
    """
    if python:
        ctx.run("flake8 src/")
    if js:
        print("NOT IMPLEMENTED")


@task(help={"verbose": "Detailed error messages", "lf": "Run only the last failed tests"})
def test(ctx, verbose=False, lf=False, cov=False):
    """
    Run all unittests.
    """
    opts = ""
    if verbose:
        opts += " -vv"
    if lf:
        opts += " --lf"
    if cov:
        opts += " --cov"
    ctx.run(
        f"pytest {opts}",
        env={
            "EJ_THEME": "default",
            "EJ_BASE_URL": "localhost",
            "USE_I18N": "false",
            "USE_L10N": "false",
            "USE_TZ": "false",
            "DB_HOST": "db",
            "COUNTRY": "",
        },
    )

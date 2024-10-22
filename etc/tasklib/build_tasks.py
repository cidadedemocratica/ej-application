import os

from invoke import task
import environ

try:
    from colorama import Fore, Style

    def reset_output_color():
        return Style.RESET_ALL

    def print_green(msg: str):
        print(Fore.GREEN + msg + reset_output_color())

    def print_yellow(msg: str):
        print(Fore.YELLOW + msg + reset_output_color())

    def print_red(msg: str):
        print(Fore.RED + msg + reset_output_color())

except Exception:

    def reset_output_color() -> None:
        return None

    def print_green(msg: str):
        print(msg)

    def print_yellow(msg: str):
        print(msg)

    def print_red(msg: str):
        print(msg)


from .base import directory, exec_watch, manage, python

__all__ = ["build_assets", "docs", "i18n", "js", "sass"]

env = environ.Env(
    EJ_THEME=(str, "ej"),
)


MINIFY_BINARY = f"{directory}/src/ej/static/ej/node_modules/.bin/minify"


@task
def build_assets(ctx):
    """
    Builds all required assets to make EJ ready for deployment.
    """
    from toml import load

    # Build Javascript
    # Parcel already minifies and 'minify' doesn't seem to be helping much.
    print_green("Building javascript assets")
    js(ctx, minify=False)

    # Build CSS
    config = load(open(directory / "pyproject.toml"))
    for theme in config["tool"]["ej"]["conf"]["themes"]:
        print_green(f"\nBuilding theme: {theme!r}")
        sass(ctx, minify=True)


@task
def docs(ctx, watch=False, orm=False):
    """
    Builds Sphinx documentation.
    """
    if orm:
        for app in [
            "ej_users",
            "ej_profiles",
            "ej_conversations",
            "ej_boards",
            "ej_clusters",
            "ej_dataviz",
            "ej_tools",
        ]:
            print_green(f"Making ORM graph for {app}")
            manage(
                ctx, "graph_models", app, env={}, output=f"docs/dev-docs/orm/{app}.svg"
            )
    else:
        print_yellow("call inv docs --orm to update ORM graphs")

    if watch:
        ctx.run("sphinx-autobuild --port 8080 -b html docs/ build/docs/", pty=True)

    ctx.run("sphinx-build docs/ build/docs/", pty=True)


@task(
    help={
        "compile": "Compile .po files",
        "edit": "Open poedit to edit translations",
        "lang": "Language",
        "keep-pot": "If true, do not clean up temporary .pot files (debug)",
    }
)
def i18n(ctx, compile=False, edit=False, lang="pt_BR", keep_pot=False):
    """
    Extract messages for translation.
    """
    if edit:
        ctx.run(f"poedit locale/{lang}/LC_MESSAGES/django.po")
    elif compile:
        ctx.run(f"{python} etc/scripts/compilemessages.py")
    else:
        print_green("Collecting messages")
        manage(ctx, "makemessages", keep_pot=True, locale=lang)

        print_green("Extract Jinja translations")
        ctx.run("pybabel extract -F etc/babel.cfg -o locale/jinja2.pot .")

        print_green("Join Django + Jinja translation files")
        ctx.run(
            "msgcat locale/django.pot locale/jinja2.pot --use-first -o locale/join.pot",
            pty=True,
        )
        ctx.run(r"""sed -i '/"Language: \\n"/d' locale/join.pot""", pty=True)

        print_green(f"Update locale {lang} with Jinja2 messages")
        ctx.run(f"msgmerge locale/{lang}/LC_MESSAGES/django.po locale/join.pot -U")

        if not keep_pot:
            print_yellow("Cleaning up")
            ctx.run("rm locale/*.pot")


@task
def js(ctx, theme=env("EJ_THEME"), watch=False, minify=False, app_name=None):
    """
    Compile typescript assets
    """
    if not app_name:
        app_name = theme
    print_green(f"compiling {app_name} typescript assets")
    build_cmd = "npm run watch" if watch else "npm run build"
    cwd = os.getcwd()
    app_root = f"{directory}/src/{app_name}"
    app_static_root = f"{app_root}/static/{app_name}"
    try:
        ctx.run(f"rm -rf {app_static_root}/js")
        os.chdir(f"{app_static_root}/ts")
        ctx.run(build_cmd)
        if minify:
            base = f"{app_static_root}/js"
            for path in os.listdir(str(base)):
                if path.endswith(".js") and not path.endswith(".min.js"):
                    path = f"{base}/{path}"
                    print_green(f"Minifying {path}")
                    ctx.run(f"{MINIFY_BINARY} {path} > {path[:-3]}.min.js")
    finally:
        os.chdir(cwd)


@task
def sass(ctx, watch=False, background=False, minify=False, app_name=None):
    """
    Compile EJ apps sass assets.
    """
    import sass
    import os
    from threading import Thread

    def get_django_apps() -> [str]:
        """
        returns a list of strings. Each string is the name of an EJ app.
        """
        from glob import glob

        apps_absolute_path = glob(f"{str(directory)}/src/ej*", recursive=True)
        return list(map(lambda app: app.split("/")[-1], apps_absolute_path))

    def run(app_name: str):
        """Run the sass compile on app_name static directory.

        Parameters:
        app_name (str): some EJ app, like ej or ej_conversations.
        """
        print_green(f"compiling {app_name} sass assets!")
        for file in (app_name, "main", "hicontrast"):
            app_root = f"{directory}/src/{app_name}"
            app_static_root = f"{app_root}/static/{app_name}"
            scss_root_path = f"{app_static_root}/scss"
            css_root_path = f"{app_static_root}/css"
            ctx.run(f"mkdir -p {css_root_path}")
            css_path = f"{css_root_path}/{file}.css"
            css_min_path = f"{css_root_path}/{file}.min.css"
            map_path = f"{css_root_path}/{file}.css.map"
            scss_file_to_compile = f"{scss_root_path}/{file}.scss"
            if os.path.exists(scss_file_to_compile):
                css, sourcemap = sass.compile(
                    filename=str(f"{scss_root_path}/{file}.scss"),
                    source_map_filename=str(map_path),
                    source_map_root=str(css_root_path),
                    source_map_contents=True,
                    source_map_embed=True,
                )
                with open(css_path, "w") as fd:
                    fd.write(css)
                    if minify:
                        ctx.run(f"{MINIFY_BINARY} {css_path} > {css_min_path}")
                with open(map_path, "w") as fd:
                    fd.write(sourcemap)

    if app_name:
        try:
            exec_watch(app_name, run, name="sass", watch=watch, background=background)
        except Exception as exc:
            print_red(f"ERROR EXECUTING SASS COMPILATION: {exc}")
    else:
        for app_name in get_django_apps():
            app_root = f"{directory}/src/{app_name}"
            app_static_root = f"{app_root}/static/{app_name}/scss"
            if os.path.isdir(app_static_root):

                def go(app_name, run, name, watch, background):
                    return exec_watch(
                        app_name, run, name=name, watch=watch, background=background
                    )

                thread = Thread(None, go, args=(app_name, run, "sass", watch, background))
                thread.start()

    print_green("\nCompilation finished!")

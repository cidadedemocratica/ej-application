import os

from invoke import task

from .base import directory, HELP_MESSAGES, set_theme, exec_watch, manage, python

__all__ = ["build_assets", "docs", "i18n", "js", "sass"]


@task
def build_assets(ctx):
    """
    Builds all required assets to make EJ ready for deployment.
    """
    from toml import load

    config = load(open(directory / "pyproject.toml"))

    # Build CSS
    for theme in config["tool"]["ej"]["conf"]["themes"]:
        print(f"\nBuilding theme: {theme!r}")

        sass(ctx, theme, suffix=f"-{theme}", minify=True)

    # Build Javascript
    # Parcel already minifies and 'minify' doesn't seem to be helping much.
    print("Building javascript assets")
    js(ctx, minify=False)


@task
def docs(ctx, orm=False):
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
            "ej_gamification",
            "ej_dataviz",
            "ej_rocketchat",
        ]:
            print(f"Making ORM graph for {app}")
            env = {"EJ_ROCKETCHAT_INTEGRATION": "true"} if app == "ej_rocketchat" else {}
            manage(ctx, "graph_models", app, env=env, output=f"docs/dev-docs/orm/{app}.svg")
    else:
        print("call inv docs --orm to update ORM graphs")

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
        print("Collecting messages")
        manage(ctx, "makemessages", keep_pot=True, locale=lang)

        print("Extract Jinja translations")
        ctx.run("pybabel extract -F etc/babel.cfg -o locale/jinja2.pot .")

        print("Join Django + Jinja translation files")
        ctx.run("msgcat locale/django.pot locale/jinja2.pot --use-first -o locale/join.pot", pty=True)
        ctx.run(r"""sed -i '/"Language: \\n"/d' locale/join.pot""", pty=True)

        print(f"Update locale {lang} with Jinja2 messages")
        ctx.run(f"msgmerge locale/{lang}/LC_MESSAGES/django.po locale/join.pot -U")

        if not keep_pot:
            print("Cleaning up")
            ctx.run("rm locale/*.pot")


@task
def js(ctx, watch=False, minify=False):
    """
    Build js assets
    """
    build_cmd = "npm run watch" if watch else "npm run build"
    cwd = os.getcwd()
    try:
        path = directory / "lib"
        os.chdir(path)
        ctx.run("mkdir -p build/js/")
        ctx.run("rm build/js/main.js* -f")
        ctx.run(build_cmd)
        if minify:
            minify = directory / "lib/node_modules/.bin/minify"
            base = directory / "lib/build/js/"
            for path in os.listdir(str(base)):
                if path.endswith(".js") and not path.endswith(".min.js"):
                    path = str(base / path)
                    print(f"Minifying {path}")
                    ctx.run(f"{minify} {path} > {path[:-3]}.min.js")
    finally:
        os.chdir(cwd)


@task(help={**HELP_MESSAGES, "suffix": "Append suffix to resulting file names."})
def sass(ctx, theme=None, watch=False, background=False, suffix="", minify=False):
    """
    Run Sass compiler
    """

    theme, root = set_theme(theme)
    os.environ["EJ_THEME"] = theme or "default"
    ctx.run(f'mkdir -p {directory / "lib/build/css"}')
    root = directory / f"{root}scss"
    minify = directory / "lib/node_modules/.bin/minify"

    def go():
        import sass

        root_url = f'file://{directory / "lib/build/css/"}'
        for file in ("main", "rocket", "hicontrast"):
            try:
                css_path = directory / f"lib/build/css/{file}{suffix}.css"
                css_min_path = directory / f"lib/build/css/{file}{suffix}.min.css"
                map_path = directory / f"lib/build/css/{file}{suffix}.css.map"
                css, sourcemap = sass.compile(
                    filename=str(root / f"{file}.scss"),
                    source_map_filename=str(map_path),
                    source_map_root=str(root_url),
                    source_map_contents=True,
                    source_map_embed=True,
                )
                with open(css_path, "w") as fd:
                    fd.write(css)
                    if minify:
                        ctx.run(f"{minify} {css_path} > {css_min_path}")
                with open(map_path, "w") as fd:
                    fd.write(sourcemap)

            except Exception as exc:
                print(f"ERROR EXECUTING SASS COMPILATION: {exc}")

    exec_watch(root, go, name="sass", watch=watch, background=background)
    print("Compilation finished!")

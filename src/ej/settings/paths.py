import os
import pathlib
import environ

from boogie.configurations import PathsConf as Base

env = environ.Env(
    EJ_THEME=(str, "ej"),
)


class PathsConf(Base):
    BASE_DIR = REPO_DIR = pathlib.Path(__file__).parent.parent.parent.parent
    ROOT_DIR = SRC_DIR = APPS_DIR = REPO_DIR / "src"
    PROJECT_DIR = ROOT_DIR / "ej"

    # Local paths
    LOCAL_DIR = REPO_DIR / "local"
    STATIC_ROOT = LOCAL_DIR / "static"
    DB_DIR = LOCAL_DIR / "db"
    MEDIA_ROOT = LOCAL_DIR / "media"
    FRAGMENTS_DIR = LOCAL_DIR / "fragments"
    PAGES_DIR = LOCAL_DIR / "pages"
    LOG_DIR = LOCAL_DIR / "logs"
    LOG_FILE_PATH = LOG_DIR / "logfile.log"
    ROOT_TEMPLATE_DIR = PROJECT_DIR / "templates"

    # Frontend paths
    EJ_THEME_PATH, THEMES_DIR = [ROOT_DIR / env("EJ_THEME")] * 2

    def finalize(self, settings):
        """
        Create missing paths.
        """
        for path in [
            self.LOCAL_DIR,
            self.DB_DIR,
            self.MEDIA_ROOT,
            self.STATIC_ROOT,
            self.LOG_DIR,
        ]:
            if not os.path.exists(path):
                mkdir_recursive(path)

        return super().finalize(settings)

    def get_staticfiles_dirs(self, repo_dir):
        from glob import glob

        # get static dir for all EJ apps.
        apps_absolute_path = glob(
            f"{str(self.BASE_DIR)}/src/ej*", recursive=True
        )
        dirs = list(
            map(
                lambda app: f"{app}/static/{app.split('/')[-1]}",
                apps_absolute_path,
            )
        )
        valid_dirs = [dir for dir in dirs if os.path.exists(dir)]
        return [f'{str(repo_dir) + "/src/ej/static/ej/assets"}', *valid_dirs]

    def get_django_templates_dirs(self):
        dirs = [self.ROOT_TEMPLATE_DIR / "django"]
        if self.EJ_THEME:
            dirs.insert(0, self.EJ_THEME_PATH / "templates" / "django")
        return dirs

    def get_jinja_templates_dirs(self):
        dirs = [self.ROOT_TEMPLATE_DIR / "jinja2"]
        if self.EJ_THEME:
            dirs.insert(0, self.EJ_THEME_PATH / "templates" / "jinja2")
        return dirs

    def get_ej_theme_path(self):
        if os.path.sep in self.EJ_THEME:
            return self.EJ_THEME
        else:
            return self.THEMES_DIR / self.EJ_THEME


def mkdir_recursive(path):
    # TODO: implement recursive dir creation.
    print(f"making required directory: {path}")
    os.mkdir(path)

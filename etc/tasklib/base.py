import os
import sys
from pathlib import Path
import environ

python = sys.executable
directory = Path(os.path.dirname(__file__)).parent.parent
sys.path.append("src")
HELP_MESSAGES = {
    "theme": "Set theme (e.g. cpa or default)",
    "watch": "Re-run when any file changes",
    "minify": "Minify resulting assets",
    "background": "Runs on background",
}

env = environ.Env(
    EJ_THEME=(str, "ej"),
)


#
# Utility functions
#
def manage(ctx, cmd, *args, env=None, **kwargs):
    kwargs = {k.replace("_", "-"): v for k, v in kwargs.items() if v is not False}
    opts = " ".join(f'--{k} {"" if v is True else v}' for k, v in kwargs.items())
    opts = " ".join((*args, opts))
    cmd = f"{python} manage.py {cmd} {opts}"
    env = {**os.environ, **(env or {})}
    path = env.get("PYTHONPATH", ":".join(sys.path))
    env.setdefault("PYTHONPATH", f"src:{path}")
    os.chdir(str(directory))
    ctx.run(cmd, pty=True, env=env)


def runner(ctx, dry_run, **extra):
    def do(cmd, **kwargs):
        if dry_run:
            print(cmd)
        else:
            kwargs = dict(extra, **kwargs)
            return ctx.run(cmd, **kwargs)

    return do


def set_theme(theme):
    theme = env("EJ_THEME") if not theme else theme
    return theme, f"{directory}/src/{theme}/static/{theme}"


def watch_path(app_name, func, poll_time=0.5, name=None, skip_first=False):
    """
    Watch path and execute the given function everytime a file changes.
    """
    import time
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler,
        FileCreatedEvent,
        FileDeletedEvent,
        FileModifiedEvent,
        FileMovedEvent,
    )

    file_event = (FileCreatedEvent, FileDeletedEvent, FileModifiedEvent, FileMovedEvent)
    last = time.time()

    def dispatch(ev):
        nonlocal last

        if (
            ev.src_path.endswith("__")
            or ev.src_path.startswith("__")
            or ev.src_path.startswith("~")
            or ev.src_path.startswith(".")
        ):
            return

        if isinstance(ev, file_event):
            last = start = time.time()
            time.sleep(poll_time)
            if last == start:
                print(f"File modified: {ev.src_path}")
                func(app_name)

    app_root = f"{directory}/src/{app_name}"
    app_static_root = f"{app_root}/static/{app_name}"
    path = f"{app_static_root}/scss"
    observer = Observer()
    handler = FileSystemEventHandler()
    handler.dispatch = dispatch
    observer.schedule(handler, path, recursive=True)
    observer.start()
    name = name or func.__name__
    print(f"Running {name} in watch mode.")
    if not skip_first:
        func(app_name)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def exec_watch(app_name, func, name, watch=False, background=False, poll_time=0.5):
    if watch and background:

        def go(app_name):
            return watch_path(app_name, func, name=name, poll_time=poll_time)

        return exec_watch(app_name, go, name, background=True)
    elif watch:
        return watch_path(app_name, func, name=name, poll_time=poll_time)
    elif background:
        from threading import Thread

        def go():
            print(".", end="", flush=True)
            try:
                func(app_name)
            except KeyboardInterrupt:
                pass

        thread = Thread(target=go, daemon=True)
        thread.start()
    else:
        func(app_name)

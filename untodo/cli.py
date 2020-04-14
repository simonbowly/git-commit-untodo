import json
import operator
import os
import pathlib
import subprocess
import tempfile
import textwrap
import webbrowser

import appdirs
import click
import prompt_toolkit

from .git import (
    get_todo_created_issues,
    get_todos_pending_removal,
    get_configured_remotes,
)


def config_dir():
    p = pathlib.Path(appdirs.user_config_dir()).joinpath("untodo")
    os.makedirs(p, exist_ok=True)
    return p


def update_github_token(token):
    with config_dir().joinpath("token").open("w") as outfile:
        outfile.write(token)


def get_github_token():
    try:
        with config_dir().joinpath("token").open() as infile:
            return infile.read().strip()
    except FileNotFoundError:
        raise LookupError(
            "Untodo is not configured yet. Run `git commit-untodo --configure`."
        )


def set_issue_source_repo(repo_dir, remote):
    repo_dir = str(pathlib.Path(repo_dir).resolve())
    remotes_file = config_dir().joinpath("remotes.json")
    if remotes_file.exists():
        with remotes_file.open() as infile:
            remotes = json.load(infile)
    else:
        remotes = {}
    remotes[repo_dir] = remote
    with remotes_file.open("w") as outfile:
        json.dump(remotes, outfile)


def get_issue_source_repo(repo_dir):
    repo_dir = str(pathlib.Path(repo_dir).resolve())
    remotes_file = config_dir().joinpath("remotes.json")
    if remotes_file.exists():
        with remotes_file.open() as infile:
            remote = json.load(infile).get(repo_dir)
    else:
        remote = None
    if remote is None:
        raise LookupError(
            "Untodo is not configured for this repository. Run `git commit-untodo --configure`."
        )
    return remote


def cli_update_token():
    click.echo(
        textwrap.dedent(
            """
            Taking you to GitHub to get an app token. Generate a new token
            with repo access in order to retrieve issues.
            """
        )
    )
    webbrowser.open("https://github.com/settings/tokens")
    token = prompt_toolkit.prompt("Enter generated token: ")
    update_github_token(token)


def cli_configure():
    try:
        get_github_token()
    except LookupError:
        cli_update_token()
    options = {i + 1: rmt for i, rmt in enumerate(get_configured_remotes(repo_dir="."))}
    click.echo("Choose the GitHub remote to retrieve issues from:")
    for i, rmt, in sorted(options.items()):
        click.echo(f"    {i} - {rmt['name']} = {rmt['user']}/{rmt['repo']}")
    choice = prompt_toolkit.prompt("Choice [1]? ")
    choice = 1 if not choice else choice
    remote = options[int(choice)]
    remote = f"{remote['user']}/{remote['repo']}"
    set_issue_source_repo(repo_dir=".", remote=remote)
    click.echo(f"Issues will be retrieved from github:{remote}")


@click.command()
@click.option("--update-token/--no-update-token", default=False)
@click.option("--configure/--no-configure", default=False)
def cli(update_token, configure):
    """Prepare a commit message including 'closes' tags for issues that should
    be closed as a result of todo removals."""
    if update_token:
        cli_update_token()
        return
    if configure:
        cli_configure()
        return
    try:
        github_token = get_github_token()
        issue_source_repo = get_issue_source_repo(repo_dir=".")
    except LookupError as e:
        click.echo(str(e))
        return 1
    open_todo_issues = {
        issue["title"]: issue
        for issue in get_todo_created_issues(github_token, issue_source_repo)
    }
    draft_message = ""
    for pending in get_todos_pending_removal(repo_dir="."):
        issue = open_todo_issues.get(pending)
        if issue is not None:
            draft_message += textwrap.dedent(
                f"""
                Closes #{issue['number']} TODO - {pending}
                """
            )
    with tempfile.TemporaryDirectory() as tempdir:
        template = pathlib.Path(tempdir).joinpath("draft-msg")
        with template.open("w") as outfile:
            outfile.write(draft_message)
        subprocess.run(["git", "commit", "--template", template])

import json
import os
import pathlib
import textwrap
import webbrowser

import appdirs
import click
import prompt_toolkit

from .git import get_todo_created_issues, get_todos_pending_removal


def config_dir():
    p = pathlib.Path(appdirs.user_config_dir()).joinpath("untodo")
    os.makedirs(p, exist_ok=True)
    return p


def update_github_token(token):
    with config_dir().joinpath("token").open("w") as outfile:
        outfile.write(token)


def get_github_token():
    with config_dir().joinpath("token").open() as infile:
        return infile.read().strip()


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
            "Untodo is not configured for this repository. Run `untodo configure`"
        )
    return remote


@click.group()
def cli():
    pass


@cli.command()
@click.option("--update-token/--no-update-token", default=False)
def configure(update_token):
    if update_token:
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
    try:
        remote = get_issue_source_repo(repo_dir=".")
    except LookupError:
        remote = None
    new_remote = prompt_toolkit.prompt(
        f"Set github user/repo to search for issues [{remote}]: "
    )
    if new_remote:
        set_issue_source_repo(repo_dir=".", remote=new_remote)


@cli.command()
@click.argument("outfile", type=click.File("w"))
def commit(outfile):
    """Prepare a commit message including 'closes' tags for issues that should
    be closed as a result of todo removals."""
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
    for pending in get_todos_pending_removal(repo_dir="."):
        issue = open_todo_issues.get(pending)
        if issue is not None:
            outfile.write(
                textwrap.dedent(
                    f"""
                    Closes #{issue['number']} - {pending}
                    """
                )
            )
import json
import logging
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

logger = logging.getLogger(__name__)


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
        raise LookupError("Not configured yet. Run `git commit-untodo --configure`.")


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
            "Not configured for this repository yet. Run `git commit-untodo --configure`."
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
@click.option("--debug/--no-debug", default=False)
def cli(update_token, configure, debug):
    """Prepare a commit message including 'closes' tags for issues that should
    be closed as a result of todo removals."""
    if debug:
        l = logging.getLogger("git_commit_untodo")
        l.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        l.addHandler(ch)
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
    for issue_title in open_todo_issues:
        logger.debug(f"Check against issue -> '{issue_title}'")
    for pending in get_todos_pending_removal(repo_dir="."):
        logger.info(f"Pending removal -> '{pending}'")
        issue = open_todo_issues.get(pending)
        if issue is None:
            logger.warning("No match found for this todo")
            draft_message += textwrap.dedent(
                f"""
                # Couldn't find a match for this todo line:
                #     '{pending}'
                """
            )
        else:
            logger.info(f"Matched issue #{issue['number']}")
            draft_message += textwrap.dedent(
                f"""
                Closes #{issue['number']} TODO - {pending}
                """
            )
    if debug:
        click.echo("===== Begin Commit Draft =====")
        click.echo(draft_message)
        click.echo("====== End Commit Draft ======")
    else:
        with tempfile.TemporaryDirectory() as tempdir:
            template = pathlib.Path(tempdir).joinpath("draft-msg")
            with template.open("w") as outfile:
                outfile.write(draft_message)
            subprocess.run(["git", "commit", "--template", template])

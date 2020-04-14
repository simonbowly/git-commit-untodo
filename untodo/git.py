import logging
import re
import subprocess

import github

logger = logging.getLogger(__name__)


todo_body_commit = re.compile("based on a `todo` comment in ([0-9\w]+)")
todo_addition = re.compile("\+.*(@todo|TODO)(.*)")
todo_removal = re.compile("\-.*(@todo|TODO)(.*)")


def get_todo_created_issues(github_token, issue_source_repo):
    """Get currently open issues created by the todo bot on the given
    remote."""
    user_name, mid, repo_name = issue_source_repo.partition("/")
    assert mid
    repo = github.Github(github_token).get_user(user_name).get_repo(repo_name)
    return [
        {
            "title": issue.title,
            "number": issue.number,
            "commit": todo_body_commit.search(issue.body).group(1),
        }
        for issue in repo.get_issues(state="open")
        if todo_body_commit.search(issue.body)
    ]


def get_todos_added_in_commit(repo_dir, commit):
    """Get the todo-detectable lines that were added in the given commit."""
    try:
        return [
            todo_addition.match(line).group(2).strip()
            for line in subprocess.check_output(["git", "show", commit], cwd=repo_dir)
            .decode()
            .split("\n")
            if todo_addition.match(line)
        ]
    except subprocess.CalledProcessError:
        logger.warning(f"Can't find commit {commit} locally")


def get_todos_pending_removal(repo_dir):
    """Get the todo-detectable lines to be removed when staged changes are
    committed."""
    return [
        todo_removal.match(line).group(2).strip()
        for line in subprocess.check_output(["git", "diff", "--staged"], cwd=repo_dir)
        .decode()
        .split("\n")
        if todo_removal.match(line)
    ]

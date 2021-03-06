# Git Commit-UnTodo

Adds a git subcommand `commit-untodo` which automatically detects `todo` issues you are about to close and references them in a commit message template.

It's not very sophisticated in the way it matches removed lines with issues, currently just runs an exact text match.
Post an issue if it doesn't pick up something it should - the best way to post would be to reference the commit you made in your (public) git repo and the issues that it didn't (but should have) closed.

## Installation

I haven't put this on PyPi yet, but it's installable from GitHub.

    pip install git+https://github.com/simonbowly/git-commit-untodo.git

Once installed you'll have a `git commit-untodo` subcommand which essentially just runs `git commit` but drafts a message for you to edit.

## Workflow

Using a repository with a Github remote that uses todo (https://todo.jasonet.co/) to open issues automatically.

1. Stage some changes (`git add`) which delete `@todo` comments linked to open issues.
2. Run `git commit-untodo`, which will add `closes` references to your commit message template and start the commit process.
3. Edit/finalise the commit message. Relevant bot-generated issues will be closed once your changes are pushed!

## Troubleshooting

If this worked successfully, you'll get your usual text editor opened to run a commit message:

    Closes #23 TODO - something to do

    # Please enter the commit message for your changes. Lines starting
    # ...

If a todo removal was found but was not matched to an issue, you'll see this commented out message in the commit file instead, which indicates no issues will actually be closed if you run this commit.

    # Couldn't find a match for this todo line:
    #     'something to do'

    # Please enter the commit message for your changes. Lines starting
    # ...

If no todo removals were identified, you'll just get your normal (empty) commit message.

The CLI uses `git commit --template` to work; so if you make no changes or delete all uncommented lines in the commit body, the commit will be aborted as normal.
You can then use the debug mode (`git commit-untodo --debug`) that prints all logging and writes the commit message to terminal instead of starting a commit.
This should help diagnosing whether it's an issue identifying the todo removal or matching it with a github issue.

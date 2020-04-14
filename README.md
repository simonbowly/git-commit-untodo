# Git Commit-UnTodo

Adds a git subcommand `commit-untodo` which automatically detects `todo` issues you are about to close and references them in a commit message template.

Workflow:
1. Push some changes including `@todo` comments (so the todo bot opens issues)
2. `git add` some changes that delete `@todo` comments
3. Run `git commit-untodo`, which adds `closes` references to your commit message template
4. Bot issues will be closed once your changes are pushed!

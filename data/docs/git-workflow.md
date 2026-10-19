# Git Workflow

## Branching

Create a short lived branch for each change, for example feature/login-form. Keep the main branch always deployable. Delete the branch after it is merged.

## Commits

A good commit changes one thing and has a message that says why. Use the imperative mood, such as Fix timeout in retry loop. Small commits are easier to review, revert and bisect.

## Pull Requests

A pull request proposes merging a branch. Keep it small, describe what changed and how you tested it, and ask for review before merging. Automated checks such as tests and linters should pass first.

## Merge or Rebase

Merge keeps the full history and adds a merge commit. Rebase replays your commits on top of the target branch and gives a straight history. Never rebase commits that other people already pulled.

## Undoing Mistakes

Use git revert to undo a published commit with a new commit. Use git reset only on local work that is not pushed. Use git reflog to find commits that seem lost.

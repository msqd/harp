---
allowed-tools: Bash(git:*)
description: Prepare good commit message.
---

Prepare a good, descriptive commit message. All informations in commit message must help
the user that will read the message understand the change, and why it was made.

Read what is actually staged in git index, and if available, use github cli to read related
issues and current open pull request.

Use Conventional Commits, a lightweight convention on top of commit messages. It provides
an easy set of rules for creating an explicit commit history; which makes it easier to
write automated tools on top of. This convention dovetails with SemVer, by describing the
features, fixes, and breaking changes made in commit messages.

Do not be too verbose. Don't say the tests pass, this is obvious. Avoid all obvious stuff.

Make sure unreleased changelog file is updated, if needed (it is only needed if there is a
user facing change, do not add entries for typos, documentation (unless massive update),
minor code changes (like small refactorings without impact...).

Do not push the changes.

You're authorized to commit exactly once, and you will need to wait for the user to ask
again explicitely before you can do any other commit.

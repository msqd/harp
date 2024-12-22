Templates
=========

Pull Request Review Checklist
::::::::::::::::::::::::::::::

* [ ] **Title**: The pull request title should contain a category (feature, fix, change, ...) and an understandable
  description of the change.
* [ ] **Description**: The pull request description should contain details about the change and the motivation behind
  it. This does not need to be a novel, but it should be clear enough for someone who is not familiar with the issue to
  understand what, why, and how the change was made. The motivation can be as simple as linking to the related issue(s).
* [ ] **Tests**: Does the PR contain tests? Backend, frontend? This is important to ensure that the change was made with
  conscience both about the existing code and the new one. It demonstrates how the new code work, and make sure that it
  will continue to work the same way in the future. The amount of effort put into testing should be proportional to the
  complexity of the change.
* [ ] **Documentation**: Does the PR contain documentation for the added/changed/removed feature? Even if it's not full
  new pages with long descriptive texts, it is important to at least find the existing related documenation pages and
  update them with the new information.
* [ ] **Changelog**: Does the PR contain an «unreleased» changelog entry?

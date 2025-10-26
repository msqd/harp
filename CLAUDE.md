# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Project Overview

HARP is an open-source API Runtime Proxy toolkit built with Python to improve reliability,
performance, security, and observability of APIs. It runs in your infrastructure, close to
your applications.

## Core Philosophy

**TEST-DRIVEN DEVELOPMENT IS NON-NEGOTIABLE.** Every single line of production code must be
written in response to a failing test. No exceptions. This is not a suggestion or a
preference - it is the fundamental practice that enables all other principles in this
document.

Follow Test-Driven Development (TDD) with a strong emphasis on behavior-driven testing and
functional programming principles. All work should be done in small, incremental changes
that maintain a working state throughout development.

## Quick Reference

**Key Principles:**

- Simplicity: Clear, simple code is easier to maintain and scale. Avoid convoluted logic.
- Consistency: Use consistent naming and structuring. Code should be readable and
  predictable.
- Clarity Over Cleverness: Optimize for readability. Smart, complex solutions should not
  come at the cost of clarity.
- Use real schemas/types in tests, never redefine them.
- Write tests first (TDD), then implement once tested.
- Keep functions small and focused on a single responsibility
- Prefer flat, readable code over clever abstractions

## Technology Stack

- **Backend**: Python 3.13 (required `>=3.13,<3.14`)
- **Frontend**: React 18 with TypeScript, built with Vite
- **Package Management**:
    - Backend: UV (migrating from Poetry)
    - Frontend: pnpm (ALWAYS use pnpm, never npm)
- **Database Support**: SQLite (dev), PostgreSQL, MySQL
- **Testing**: pytest (backend), Vitest/Playwright (frontend)

## Development Workflow

We keep a changelog in `docs/changelogs/unreleased.rst`. When making changes, new features,
bug fixes, or refactors, update this file with a brief description of the change (one
liners). Use the "Keep a changelog" format (https://keepachangelog.com/en/1.1.0/).

### TDD Process - THE FUNDAMENTAL PRACTICE

**CRITICAL**: TDD is not optional. Every feature, every bug fix, every change
MUST follow this process:

Follow Red-Green-Refactor strictly:

1. **Red**: Write a failing test for the desired behavior. NO PRODUCTION CODE
   until you have a failing test.
2. **Green**: Write the MINIMUM code to make the test pass. Resist the urge to
   write more than needed.
3. **Refactor**: Assess the code for improvement opportunities. If refactoring
   would add value, clean up the code while keeping tests green. If the code is
   already clean and expressive, move on.

**Common TDD Violations to Avoid:**

- Writing production code without a failing test first
- Writing multiple tests before making the first one pass
- Writing more production code than needed to pass the current test
- Skipping the refactor assessment step when code could be improved
- Adding functionality "while you're there" without a test driving it

### Refactoring - The Critical Third Step

Evaluating refactoring opportunities is not optional - it's the third step in
the TDD cycle. After achieving a green state and committing your work, you MUST
assess whether the code can be improved. However, only refactor if there's
clear value - if the code is already clean and expresses intent well, move on
to the next test.

#### What is Refactoring?

Refactoring means changing the internal structure of code without changing its
external behavior. The public API remains unchanged, all tests continue to
pass, but the code becomes cleaner, more maintainable, or more efficient.
Remember: only refactor when it genuinely improves the code - not all code
needs refactoring.

#### When to Refactor

- **Always assess after green**: Once tests pass, before moving to the next
  test, evaluate if refactoring would add value
- **When you see duplication**: But understand what duplication really means
  (see DRY below)
- **When names could be clearer**: Variable names, function names, or type
  names that don't clearly express intent
- **When structure could be simpler**: Complex conditional logic, deeply nested
  code, or long functions
- **When patterns emerge**: After implementing several similar features, useful
  abstractions may become apparent

**Remember**: Not all code needs refactoring. If the code is already clean,
expressive, and well-structured, commit and move on. Refactoring should improve
the code - don't change things just for the sake of change.

#### Refactoring Guidelines

##### 1. Commit Before Refactoring

Always commit your working code before starting any refactoring. This gives a
safe point to return to.

##### 2. Look for Useful Abstractions Based on Semantic Meaning

Create abstractions only when code shares the same semantic meaning and
purpose. Don't abstract based on structural similarity alone - **duplicate code
is far cheaper than the wrong abstraction**.

**Questions to ask before abstracting:**

- Do these code blocks represent the same concept or different concepts that
  happen to look similar?
- If the business rules for one change, should the others change too?
- Would a developer reading this abstraction understand why these things are
  grouped together?
- Am I abstracting based on what the code IS (structure) or what it MEANS
  (semantics)?

**Remember**: It's much easier to create an abstraction later when the semantic
relationship becomes clear than to undo a bad abstraction that couples
unrelated concepts.

##### 3. Understanding DRY - It's About Knowledge, Not Code

DRY (Don't Repeat Yourself) is about not duplicating **knowledge** in the
system, not about eliminating all code that looks similar.

##### 4. Maintain External APIs During Refactoring

Refactoring must never break existing consumers of your code:

##### 5. Verify and Commit After Refactoring

**CRITICAL**: After every refactoring:

1. Run all tests - they must pass without modification
2. Run static analysis (linting, type checking) - must pass
3. Commit the refactoring separately from feature changes

#### Refactoring Checklist

Before considering refactoring complete, verify:

- [ ] The refactoring actually improves the code (if not, don't refactor)
- [ ] All tests still pass without modification
- [ ] All static analysis tools pass (linting, type checking)
- [ ] No new public APIs were added (only internal ones)
- [ ] Code is more readable than before
- [ ] Any duplication removed was duplication of knowledge, not just code
- [ ] No speculative abstractions were created
- [ ] The refactoring is committed separately from feature changes

### Commit Guidelines

- Each commit should represent a complete, working change
- Use conventional commits format:
  ```
  feat: add payment validation
  fix: correct date formatting in payment processor
  refactor: extract payment validation logic
  test: add edge cases for payment validation
  ```
- Include test changes with feature changes in the same commit

### Pull Request Standards

- Every PR must have all tests passing
- All linting and quality checks must pass
- Work in small increments that maintain a working state
- PRs should be focused on a single feature or fix
- Include description of the behavior change, not implementation details

You can use github CLI to create / edit / comment on pull requests.

## Essential Development Commands

### Running Tests

Uses pytest with testcontainers for database tests.

```bash
# Run specific backend test
uv run pytest tests/features/test_http_proxy.py::TestAsgiProxyWithoutEndpoints::test_asgi_proxy_get_no_endpoint
```

### Database Migrations

Based on alembic, wrapped with custom logic.

```bash
# Run migrations
harp-proxy db:migrate up head

# Create new migration
harp-proxy db:create-migration "description"

# Reset database
harp-proxy db:reset
```

### Frontend Development

```bash
cd harp_apps/dashboard/frontend

# Run tests
pnpm test:unit
pnpm test:browser

# Update snapshots
pnpm test:unit:update
pnpm test:ui:update

# Component development
pnpm ui:serve
```

## Architecture

### Directory Structure

- `/harp/` - Core framework (ASGI kernel, controllers, models, services)
- `/harp_apps/` - Plugin applications:
    - `dashboard/` - Web UI with React frontend
    - `proxy/` - Core proxy functionality
    - `http_client/` - HTTP client with caching
    - `storage/` - Database backends
    - `rules/` - Rules engine
- `/tests/` - Test suites
- `/docs/` - Sphinx documentation

### Key Patterns

- **Plugin Architecture**: Each app in `harp_apps/` is independent
- **Dependency Injection**: Using `rodi` for IoC container
- **Async First**: All database operations and HTTP handling are async
- **Event System**: Event-driven architecture for extensibility

## Development Guidelines

1. **Testing**: Write unit tests for all new functionality. Use existing test patterns in
   the codebase.

2. **Code Style**: The project uses Ruff. Always run `make format` before committing.

3. **Frontend Development**:
    - Always use pnpm, never npm
    - Frontend code is in `harp_apps/dashboard/frontend/`
    - Build artifacts go to `harp_apps/dashboard/web/`

4. **Database Testing**:
    - Tests use testcontainers to spawn Docker containers
    - Use `StorageTestFixtureMixin` for storage tests
    - Use `@parametrize_with_database_urls` to test against multiple databases

5. **Commits**: Use conventional commit format.

## Important Notes

- Development servers (Python, Vite, Storybook) are always running in the background. Never
  start them manually
- The project is currently on the `migrate_to_uv` branch, migrating from Poetry to UV
- When implementing new features, check existing patterns in similar components first
- Avoid code duplication - factor out common logic after writing tests

## Release Process

For release managers: see the complete release documentation in `docs/contribute/release/python.rst`.

**Quick reference:**
- Update changelog: `docs/contribute/release/changelog.rst`
- Python package releases: `docs/contribute/release/python.rst`
- Pre-release tasks: `docs/contribute/release/chores.rst`

## Summary

The key is to write clean, testable, functional code that evolves through
small, safe increments. Every change should be driven by a test that describes
the desired behavior, and the implementation should be the simplest thing that
makes that test pass. When in doubt, favor simplicity and readability over
cleverness.

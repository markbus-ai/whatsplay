# Contributing to WhatsPlay

Thank you for your interest in contributing to WhatsPlay! We welcome contributions from the community to help improve this library.

## How to Contribute

1.  **Fork the Repository:** Create a fork of the [WhatsPlay repository](https://github.com/markbus-ai/whatsplay) on GitHub.
2.  **Clone the Fork:** Clone your forked repository to your local machine.
3.  **Create a Branch:** Create a new branch for your feature or bug fix.
    ```bash
    git checkout -b feature/my-new-feature
    ```
4.  **Make Changes:** Implement your changes. Please ensure your code follows the existing style and conventions.
5.  **Test Your Changes:** Run existing tests and add new ones if applicable.
6.  **Commit and Push:** Commit your changes (using [Conventional Commits](https://www.conventionalcommits.org/), e.g. `fix: ...`, `feat: ...`) and push them to your fork.
    ```bash
    git commit -m "feat: add a new feature"
    git push origin feature/my-new-feature
    ```
7.  **Create a Pull Request:** Open a Pull Request (PR) on the main repository. Describe your changes clearly.

## Development Setup

To set up your development environment:

1.  **Install the package in editable mode, plus test and docs tooling:**
    ```bash
    pip install -e . pytest pytest-asyncio
    pip install -r requirements-docs.txt
    ```
2.  **Install the Playwright browser:**
    ```bash
    python -m playwright install chromium
    ```
3.  **Run the tests:**
    ```bash
    pytest tests/ -v
    ```
4.  **Preview the docs locally:**
    ```bash
    mkdocs serve
    ```
    The site is deployed to GitHub Pages automatically on every push to `main`.

## Reporting Bugs

If you find a bug, please open an issue on GitHub. Include:
*   A clear description of the bug.
*   Steps to reproduce it.
*   Expected vs. actual behavior.
*   Your operating system and Python version.
*   Logs or screenshots if possible.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

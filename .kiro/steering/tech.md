# Technology Stack

## Core Technologies

- **Python 3.12+**: Primary programming language
- **PyQt6**: GUI framework for cross-platform desktop application
- **uv**: Modern Python package manager and build tool

## Development Dependencies

- **pytest**: Unit testing framework
- **ruff**: Fast Python linter and formatter
- **pre-commit**: Git hooks for code quality
- **pyinstaller**: Application packaging for distribution
- **tox-uv**: Testing across Python environments
- **radon**: Code complexity analysis
- **xenon**: Cyclomatic complexity monitoring

## Build System

- **uv_build**: Build backend for packaging
- **PyInstaller**: Creates standalone executables
- **Makefile**: Task automation and common commands

## Common Commands

### Development Setup

```bash
make install          # Install dependencies and pre-commit hooks
make upgrade          # Upgrade all dependencies
```

### Code Quality

```bash
make check            # Run all code quality checks
```

### Testing

```bash
make test             # Run all unit tests
make test-single TEST=test_file.py  # Run specific test file
```

### Running Application

```bash
make run              # Run the application in development
```

### Utilities

```bash
make clean            # Clean build artifacts
make context          # Build context file for LLM tools
make help             # Show all available commands
```

## Project Structure Conventions

- Use `uv` for all Python package management
- Follow ruff formatting and linting rules
- Maintain test coverage with pytest
- Use pre-commit hooks for code quality
- Package with PyInstaller for distribution

## General Rules:

- Use `repomap` command to get an overview of a file or files in a directory.
  Eg. `repomap main.py` or `repomap src/`
- MUST Add extensive logging to help with debugging as this is a GUI application

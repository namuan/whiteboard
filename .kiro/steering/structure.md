# Project Structure

## Directory Organization

```
whiteboard/
├── .kiro/                    # Kiro IDE configuration and specs
├── src/whiteboard/           # Main application source code
│   ├── __init__.py          # Application entry point
│   ├── main_window.py       # Main GUI window implementation
│   └── utils/               # Utility modules
│       ├── exceptions.py    # Custom exception classes
│       └── logging_config.py # Logging setup and configuration
├── tests/                   # Unit tests (mirrors src structure)
├── assets/                  # Application assets (icons, images)
├── pyproject.toml          # Project configuration and dependencies
├── main.spec               # PyInstaller build specification
├── Makefile                # Development task automation
└── uv.lock                 # Dependency lock file
```

## Code Organization Patterns

### Module Structure

- **Main application**: `src/whiteboard/__init__.py` - Entry point with main() function
- **GUI components**: `src/whiteboard/main_window.py` - PyQt6 window classes
- **Utilities**: `src/whiteboard/utils/` - Shared functionality and helpers
- **Tests**: `tests/` - Unit tests mirroring source structure

### Naming Conventions

- **Files**: snake_case (e.g., `main_window.py`, `logging_config.py`)
- **Classes**: PascalCase (e.g., `MainWindow`, `WhiteboardError`)
- **Functions/Methods**: snake_case (e.g., `setup_logging`, `toggle_fullscreen`)
- **Constants**: UPPER_SNAKE_CASE
- **Private methods**: Leading underscore (e.g., `_setup_window`)

### Import Organization

- Standard library imports first
- Third-party imports (PyQt6) second
- Local imports last
- Use relative imports within package (e.g., `from .utils.exceptions import`)

### Documentation Standards

- Module-level docstrings for all Python files
- Class and method docstrings following Google/NumPy style
- Type hints for function parameters and return values
- Inline comments for complex logic

### Error Handling

- Custom exceptions in `utils/exceptions.py`
- Base `WhiteboardError` class for all application errors
- Specific error types: `FileOperationError`, `RenderingError`, etc.
- Proper logging of errors using configured logger

### Testing Structure

- Test files mirror source structure in `tests/` directory
- Test classes named `Test{ClassName}`
- Test methods named `test_{functionality}`
- Use pytest fixtures for common setup
- Maintain high test coverage

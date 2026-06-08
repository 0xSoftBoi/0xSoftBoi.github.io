```markdown
# 0xSoftBoi.github.io Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the `0xSoftBoi.github.io` repository. The codebase is written in Python and does not use a specific framework. It emphasizes clear file organization, consistent import/export styles, and a simple approach to testing. This guide will help you contribute code that fits seamlessly with the existing project structure.

## Coding Conventions

### File Naming
- Use **kebab-case** for all file names.
  - Example: `my-module.py`, `data-processor.py`

### Import Style
- Use **relative imports** within the project.
  - Example:
    ```python
    from .utils import helper_function
    ```

### Export Style
- Use **named exports** (explicitly listing functions/classes in `__all__`).
  - Example:
    ```python
    __all__ = ['my_function', 'MyClass']
    ```

### Commit Messages
- Freeform style, no strict prefix required.
- Average commit message length: ~63 characters.
  - Example: `fix bug in data processing pipeline`

## Workflows

### Adding a New Module
**Trigger:** When you need to introduce new functionality.
**Command:** `/add-module`

1. Create a new Python file using kebab-case naming (e.g., `new-feature.py`).
2. Implement your functions/classes.
3. Use relative imports to reference other modules.
4. Add your exports to the `__all__` list.
5. Write a corresponding test file (see Testing Patterns).

### Updating Imports
**Trigger:** When reorganizing or refactoring modules.
**Command:** `/update-imports`

1. Change import statements to use relative paths.
    ```python
    from .other-module import SomeClass
    ```
2. Ensure all references are updated throughout the codebase.

### Writing Tests
**Trigger:** When adding or modifying code.
**Command:** `/write-test`

1. Create a test file named with the pattern `*.test.*` (e.g., `my-module.test.py`).
2. Write test functions for each public function/class.
3. Use simple assertions (framework is unknown; follow existing patterns).

## Testing Patterns

- Test files are named using the pattern: `*.test.*`
  - Example: `data-processor.test.py`
- The testing framework is not specified; use basic Python assertions or mimic existing tests.
- Place test files alongside the modules they test or in a dedicated test directory if one exists.

  Example test:
  ```python
  def test_my_function():
      result = my_function(2, 3)
      assert result == 5
  ```

## Commands
| Command         | Purpose                                      |
|-----------------|----------------------------------------------|
| /add-module     | Add a new module following conventions       |
| /update-imports | Refactor imports to use relative paths       |
| /write-test     | Create a test file for a module              |
```

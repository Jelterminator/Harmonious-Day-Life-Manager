# Best Practices Implementation Guide

## Summary of Improvements

### 1. **Configuration Management** ✅
- **Created**: `config_manager.py`
- **Benefits**: 
  - Single source of truth for all configuration
  - Environment variable support
  - Easy to modify without touching code
  - Validation on startup

### 2. **Logging** ✅
- **Created**: `logger.py`
- **Benefits**:
  - Structured logging with levels
  - File and console output
  - Easy debugging and monitoring
  - Better error tracking

### 3. **Type Hints & Documentation** ✅
- **Improved**: `task_processor.py`
- **Benefits**:
  - Better IDE autocomplete
  - Catches type errors early
  - Self-documenting code
  - Easier maintenance

### 4. **Service Layer** ✅
- **Created**: `services.py`
- **Benefits**:
  - Separation of concerns
  - Easier testing
  - Better error handling per service
  - Reusable components

### 5. **Testing** ✅
- **Created**: `tests/test_task_processor.py`
- **Benefits**:
  - Confidence in refactoring
  - Catches regressions
  - Documents expected behavior
  - Easier onboarding

---

## Additional Improvements Needed

### 6. **Error Handling**

#### Current Issues:
```python
# Bad: Silent failures
try:
    result = api_call()
except:
    pass

# Bad: Catching too broad
except Exception as e:
    print(f"Error: {e}")
```

#### Best Practice:
```python
# Good: Specific exceptions with proper handling
from logger import setup_logger
logger = setup_logger(__name__)

try:
    result = api_call()
except APIError as e:
    logger.error(f"API call failed: {e}", exc_info=True)
    raise
except ValueError as e:
    logger.warning(f"Invalid input: {e}")
    return default_value
```

### 7. **Dependency Injection**

#### Current Issue:
```python
# Bad: Hard-coded dependencies
class Orchestrator:
    def __init__(self):
        self.services = get_google_services()
```

#### Best Practice:
```python
# Good: Inject dependencies
class Orchestrator:
    def __init__(
        self, 
        calendar_service: GoogleCalendarService,
        tasks_service: GoogleTasksService,
        sheets_service: GoogleSheetsService
    ):
        self.calendar = calendar_service
        self.tasks = tasks_service
        self.sheets = sheets_service
```

**Benefits**: Easier testing, better modularity, clearer dependencies

### 8. **Constants & Magic Numbers**

#### Current Issues:
```python
# Bad: Magic numbers scattered everywhere
if hours_per_day_needed > 4:
    tier = 'T1'
elif hours_per_day_needed > 2:
    tier = 'T2'
```

#### Best Practice:
```python
# Good: Named constants with explanation
class PriorityThresholds:
    """Priority tier thresholds in hours per day."""
    CRITICAL = 4.0  # T1: Requires immediate attention
    HIGH = 2.0      # T2: Needs daily focus
    MEDIUM = 1.0    # T3: Regular attention
    LOW = 0.5       # T4: Can be scheduled flexibly
```

### 9. **File Structure**

#### Recommended Structure:
```
harmonious_day/
├── src/
│   ├── __init__.py
│   ├── config_manager.py
│   ├── logger.py
│   ├── auth.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── calendar.py
│   │   ├── tasks.py
│   │   └── sheets.py
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── task_processor.py
│   │   └── habit_processor.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── prompt_builder.py
│   └── orchestrator.py
├── tests/
│   ├── __init__.py
│   ├── test_task_processor.py
│   ├── test_habit_processor.py
│   └── test_services.py
├── config.json
├── system_prompt.txt
├── .env.example
├── requirements.txt
├── setup.py
├── plan.py
└── README.md
```

### 10. **Data Classes for Data Transfer**

#### Current Issue:
```python
# Bad: Dictionaries everywhere
def process_task(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'title': task.get('title'),
        'effort': parse_effort(task),
        # ... more fields
    }
```

#### Best Practice:
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Task:
    """Represents a task with all metadata."""
    id: str
    title: str
    effort_hours: float
    priority: str
    deadline: Optional[datetime] = None
    is_subtask: bool = False
    parent_title: Optional[str] = None
    
    def is_urgent(self) -> bool:
        """Check if task is urgent (T1 or T2)."""
        return self.priority in ['T1', 'T2']
```

**Benefits**: Type safety, IDE autocomplete, clearer code, immutability options

### 11. **Input Validation**

#### Add validation decorators:
```python
from functools import wraps
from typing import Callable

def validate_date_range(func: Callable) -> Callable:
    """Validate that dates are within reasonable range."""
    @wraps(func)
    def wrapper(date_str: str, *args, **kwargs):
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            if date.year < 2020 or date.year > 2030:
                raise ValueError(f"Date out of range: {date_str}")
            return func(date_str, *args, **kwargs)
        except ValueError as e:
            logger.error(f"Invalid date: {e}")
            raise
    return wrapper
```

### 12. **Environment-Specific Configuration**

#### Create `.env.example`:
```bash
# Groq API Configuration
GROQ_API_KEY=your_key_here

# Google Sheets Configuration
SHEET_ID=your_sheet_id_here

# Application Settings
TIMEZONE=Europe/Amsterdam
LOG_LEVEL=INFO
MAX_OUTPUT_TASKS=24

# Feature Flags
ENABLE_CALENDAR_CLEANUP=true
ENABLE_DEBUG_OUTPUT=false
```

### 13. **Documentation Standards**

#### Use Google-style docstrings:
```python
def process_tasks(
    raw_tasks: List[Dict[str, Any]],
    max_tasks: int = 24
) -> List[Task]:
    """
    Process raw tasks into prioritized, schedulable format.
    
    This function takes raw task data from Google Tasks API and:
    1. Groups parent tasks with subtasks
    2. Calculates urgency based on effort and deadlines
    3. Expands projects into individual subtasks
    4. Limits output to most urgent tasks
    
    Args:
        raw_tasks: List of raw task dictionaries from Google Tasks API.
            Each dict should contain 'id', 'title', 'due', and optional 'parent'.
        max_tasks: Maximum number of tasks to return. Defaults to 24.
    
    Returns:
        List of Task objects sorted by priority and urgency.
        Limited to max_tasks entries.
    
    Raises:
        ValueError: If raw_tasks contains invalid data structure.
        KeyError: If required task fields are missing.
    
    Example:
        >>> raw_tasks = [
        ...     {'id': '1', 'title': 'Task (2h)', 'due': '2025-12-31'}
        ... ]
        >>> processed = process_tasks(raw_tasks, max_tasks=10)
        >>> len(processed) <= 10
        True
    """
    pass
```

### 14. **CI/CD Integration**

#### Create `.github/workflows/tests.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov mypy black
    
    - name: Run type checking
      run: mypy src/
    
    - name: Run linting
      run: black --check src/
    
    - name: Run tests
      run: pytest tests/ --cov=src/
```

---

## Migration Plan

### Phase 1: Foundation (Week 1)
1. ✅ Add `config_manager.py`
2. ✅ Add `logger.py`
3. Update all modules to use new config and logger
4. Add `.gitignore` entry for `logs/`

### Phase 2: Refactoring (Week 2)
1. ✅ Create `services.py` with service layer
2. Refactor `main.py` to use services
3. Add dataclasses for common data structures
4. Update error handling across all modules

### Phase 3: Testing (Week 3)
1. ✅ Set up `tests/` directory
2. Write unit tests for critical modules
3. Add integration tests
4. Set up CI/CD pipeline

### Phase 4: Documentation (Week 4)
1. Add comprehensive docstrings
2. Create API documentation
3. Update README with new structure
4. Add inline code comments where needed

---

## Quick Wins (Implement Today)

1. **Replace all `print()` with `logger` calls**
   ```python
   # Find: print(
   # Replace with: logger.info(
   ```

2. **Add type hints to function signatures**
   ```python
   # Before
   def process_task(task):
   
   # After
   def process_task(task: Dict[str, Any]) -> Task:
   ```

3. **Use constants instead of magic strings**
   ```python
   # Before
   if priority == 'T1':
   
   # After
   if priority == PriorityTier.CRITICAL:
   ```

4. **Add try-except blocks with specific exceptions**
   ```python
   # Before
   result = api_call()
   
   # After
   try:
       result = api_call()
   except APIError as e:
       logger.error(f"API failed: {e}")
       raise
   ```

---

## Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Real Python: Logging](https://realpython.com/python-logging/)
- [Effective Python](https://effectivepython.com/)
- [Clean Code in Python](https://www.oreilly.com/library/view/clean-code-in/9781800560215/)

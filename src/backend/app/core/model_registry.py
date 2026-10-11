"""Discovery and import of SQLModel table modules.

Importing every ``models.py`` registers its tables on ``SQLModel.metadata``
so they are known before tables are created or migrations are generated.
"""

import importlib
from pathlib import Path

from src.backend.app.core.logging import get_logger

logger = get_logger()

EXCLUDED_DIRS = frozenset({".venv", "__pycache__", ".pytest_cache"})


def discover_models() -> list[str]:
    """Find every ``models.py`` module under the app package.

    Returns:
        list[str]: Dotted import paths of the discovered modules, e.g.
        ``"src.backend.app.auth.models"``, sorted alphabetically.
    """
    models_modules: list[str] = []
    root_path = Path(__file__).parent.parent

    logger.debug(f"Searching for models in the root path: {root_path}")
    for models_file in sorted(root_path.rglob("models.py")):
        rel_path = models_file.relative_to(root_path)
        if EXCLUDED_DIRS.intersection(rel_path.parts):
            continue

        full_module_path = ".".join(
            ("src", "backend", "app", *rel_path.with_suffix("").parts)
        )
        logger.debug(f"Discovered models file in: {full_module_path}")
        models_modules.append(full_module_path)

    return models_modules


def load_models() -> None:
    """Import every discovered models module.

    Import errors are logged and skipped so one broken module does not stop
    the others from loading.
    """
    modules = discover_models()
    for module_path in modules:
        try:
            importlib.import_module(module_path)
            logger.debug(f"Imported module {module_path}")
        except ImportError as exc:
            logger.error(f"Failed to import module {module_path}: {exc}")

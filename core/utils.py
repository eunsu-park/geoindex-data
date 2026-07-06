"""Config loading utilities."""
import yaml
import os
import re
from pathlib import Path


def load_config(path: str | Path) -> dict:
    """Load a YAML config file with environment variable substitution.

    Supports ${VAR} and ${VAR:default} syntax.
    """
    with open(path) as f:
        config = yaml.safe_load(f)

    def substitute(obj):
        if isinstance(obj, str):
            for match in re.findall(r'\$\{(\w+)(?::([^}]*))?\}', obj):
                var, default = match
                value = os.environ.get(var, default)
                obj = obj.replace(f'${{{var}:{default}}}' if default else f'${{{var}}}', value)
            return obj
        elif isinstance(obj, dict):
            return {k: substitute(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [substitute(i) for i in obj]
        return obj
    
    return substitute(config)
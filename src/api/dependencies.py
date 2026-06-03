from typing import Any, Dict

_app_state: Dict[str, Any] = {}


def get_app_state() -> Dict[str, Any]:
    return _app_state


def set_app_state(state: Dict[str, Any]) -> None:
    _app_state.clear()
    _app_state.update(state)

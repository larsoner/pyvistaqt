"""PyVista package for 3D plotting and mesh analysis."""
from ._version import __version__
import os
assert os.getenv('QT_API', '').lower() != 'pyqt5', os.getenv('QT_API')
print(os.getenv('QT_API'))

try:
    from qtpy import QtCore  # noqa
except Exception as exc:  # pragma: no cover # pylint: disable=broad-except
    _exc_msg = exc

    # pylint: disable=too-few-public-methods
    class _QtBindingError:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(f"No Qt binding was found, got: {_exc_msg}")

    # pylint: disable=too-few-public-methods
    class BackgroundPlotter(_QtBindingError):
        """Handle Qt binding error for BackgroundPlotter."""

    # pylint: disable=too-few-public-methods
    class MainWindow(_QtBindingError):
        """Handle Qt binding error for MainWindow."""

    # pylint: disable=too-few-public-methods
    class MultiPlotter(_QtBindingError):
        """Handle Qt binding error for MultiPlotter."""

    # pylint: disable=too-few-public-methods
    class QtInteractor(_QtBindingError):
        """Handle Qt binding error for QtInteractor."""

else:
    print(os.getenv('QT_API'))
    print(QtCore.__version__)
    assert os.getenv('QT_API', '').lower() != 'pyqt5', os.getenv('QT_API')
    from .plotting import BackgroundPlotter, MainWindow, MultiPlotter, QtInteractor
assert os.getenv('QT_API', '').lower() != 'pyqt5', os.getenv('QT_API')


__all__ = [
    "__version__",
    "BackgroundPlotter",
    "MainWindow",
    "MultiPlotter",
    "QtInteractor",
]

import gc
import os
import pytest
import pyvista
from pyvista.plotting import system_supports_plotting


NO_PLOTTING = not system_supports_plotting()
GC_TEST = os.getenv('GC_TEST', '').lower() == 'true'


def pytest_collection_finish(session):
    from py.io import TerminalWriter
    writer = TerminalWriter()
    writer.line(
        f'{"Excluding" if NO_PLOTTING else "Including"} plotting tests '
        f'(NO_PLOTTING={NO_PLOTTING})')
    writer.line(
        f'{"Including" if GC_TEST else "Excluding"} garbage collection tests '
        f'(GC_TEST={GC_TEST})')


# Adapted from PyVista
def _is_vtk(obj):
    try:
        return obj.__class__.__name__.startswith('vtk')
    except Exception:  # old Python sometimes no __class__.__name__
        return False


@pytest.fixture(autouse=True)
def check_gc(request):
    """Ensure that all VTK objects are garbage-collected by Python."""
    if 'test_ipython' in request.node.name:  # XXX this keeps a ref
        yield
        return
    # We need https://github.com/pyvista/pyvista/pull/958 to actually run
    # this test. Eventually we should use LooseVersion, but as of 2020/10/22
    # 0.26.1 is the latest PyPi version and on master the version is weirdly
    # 0.26.0 (as opposed to 0.26.2.dev0 or 0.27.dev0) so we can't. So for now
    # let's use an env var (GC_TEST) instead of:
    # if LooseVersion(pyvista.__version__) < LooseVersion('0.26.2'):
    if os.getenv('GC_TEST', '').lower() != 'true':
        yield
        return
    before = set(id(o) for o in gc.get_objects() if _is_vtk(o))
    yield
    pyvista.close_all()
    gc.collect()
    after = [o for o in gc.get_objects() if _is_vtk(o) and id(o) not in before]
    after = sorted(o.__class__.__name__ for o in after)
    assert len(after) == 0, 'Not all objects GCed:\n' + '\n'.join(after)


@pytest.fixture()
def plotting():
    """Require plotting."""
    if NO_PLOTTING:
        pytest.skip(NO_PLOTTING, reason="Requires system to support plotting")
    yield
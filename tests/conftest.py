from __future__ import annotations  # noqa: D100

import gc
import inspect

from packaging.version import Version
import pytest
import pyvista
from pyvista import _vtk
from pyvista.plotting import system_supports_plotting

NO_PLOTTING = not system_supports_plotting()

# The allow_bad_gc(_pyside) markers below are only needed on PyVista versions
# that predate the upstream GC fixes (Renderer.close() properly detaching
# props/render passes/orbit threads). Once installed PyVista is new enough,
# the markers are registered but ignored so the strict GC check always runs.
PYVISTA_GC_FIXED = Version(pyvista.__version__) >= Version("0.49.dev0")


def pytest_configure(config) -> None:
    """Configure pytest options."""
    # Fixtures
    for fixture in ("check_gc",):
        config.addinivalue_line("usefixtures", fixture)
    # Markers
    for marker in (
        "allow_bad_gc",
        "allow_bad_gc_pyside",
        "skip_check_gc",
        "expect_check_gc_fail",
        "slow",
    ):
        config.addinivalue_line("markers", marker)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):  # noqa: ANN201, ARG001
    """
    Stash each phase's report on the item, so ``check_gc`` can see a test's own outcome.

    PyVista gets this for free from the ``pytest-pyvista`` plugin, which
    pyvistaqt does not depend on, so it is reimplemented here directly.
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# Adapted from PyVista
def _is_vtk(obj):  # noqa: ANN202
    try:
        return isinstance(obj, _vtk.vtkObjectBase) and obj.__class__.__name__.startswith("vtk")
    except ReferenceError:
        return False


@pytest.fixture(scope="session", autouse=True)
def _warm_up_trame():  # noqa: ANN202
    """
    Trigger trame_vtk's process-global vtkWebApplication cache once, up front.

    ``trame_vtk`` caches a ``Helper`` (owning a ``vtkWebApplication`` and several
    ``vtkWeb*`` protocol handlers) per trame server name for the life of the
    process -- see ``trame_vtk.modules.vtk.HELPERS_PER_SERVER``. That cache is
    intentional and outside pyvista/pyvistaqt's control, so triggering it here,
    before any test's ``check_gc`` "before" snapshot is taken, keeps those
    long-lived singletons out of the leak check for tests that exercise the
    trame export path.
    """
    if NO_PLOTTING:
        return
    try:
        plotter = pyvista.Plotter(off_screen=True)
        plotter.add_mesh(pyvista.Sphere())
        plotter.trame.export_vtksz(filename=None)
        plotter.close()
    except Exception:  # noqa: BLE001, S110
        pass


@pytest.fixture(autouse=True)
def check_gc(request):  # noqa: ANN201, C901, PLR0912
    """Ensure that all VTK objects are garbage-collected by Python."""
    if request.node.get_closest_marker("skip_check_gc"):
        yield
        return
    if not PYVISTA_GC_FIXED:
        try:
            from qtpy import API_NAME  # noqa: PLC0415
        except Exception:  # noqa: BLE001
            API_NAME = ""  # noqa: N806
        marks = {mark.name for mark in request.node.iter_markers()}
        if "allow_bad_gc" in marks:
            yield
            return
        if "allow_bad_gc_pyside" in marks and API_NAME.lower().startswith("pyside"):
            yield
            return
    gc.collect()
    before = {id(o) for o in gc.get_objects() if _is_vtk(o)}
    yield
    pyvista.close_all()

    # Skip the leak check if the test itself failed: a real failure can easily
    # leave things half-initialized in ways that are expected, and a "Not all
    # objects GCed" failure on top of that just obscures the actual error.
    if getattr(request.node, "rep_call", None) is not None and request.node.rep_call.failed:
        return

    gc.collect()
    after = [o for o in gc.get_objects() if _is_vtk(o) and id(o) not in before]
    msg = "Not all objects GCed:\n"
    for obj in after:
        cn = obj.__class__.__name__
        cf = inspect.currentframe()
        referrers = [v for v in gc.get_referrers(obj) if v is not after and v is not cf]
        del cf
        for ri, referrer in enumerate(referrers):
            if isinstance(referrer, dict):
                for k, v in referrer.items():
                    if k is obj:
                        referrers[ri] = "dict: d key"
                        del k, v
                        break
                    elif v is obj:
                        referrers[ri] = f"dict: d[{k!r}]"
                        # raise RuntimeError(referrers[ri])  # noqa: ERA001
                        del k, v
                        break
                    del k, v
                else:
                    referrers[ri] = f"dict: len={len(referrer)}"
            else:
                referrers[ri] = repr(referrer)
            del ri, referrer
        msg += f"{cn} at {hex(id(obj))}: {referrers}\n"
        del cn, referrers

    if request.node.get_closest_marker("expect_check_gc_fail"):
        assert after
        return

    assert len(after) == 0, msg


@pytest.fixture
def plotting() -> None:
    """Require plotting."""
    if NO_PLOTTING:
        pytest.skip(NO_PLOTTING, reason="Requires system to support plotting")

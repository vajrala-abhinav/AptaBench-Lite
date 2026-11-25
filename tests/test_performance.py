from concurrent.futures import ThreadPoolExecutor
import pytest
from aptabench_lite.performance import Capture, measured, timed


def test_timing_capture_counts_only_and_preserves_behavior():
    @timed('normalization')
    def work(value):return value+1
    @timed('failure')
    def fail():raise ValueError('expected')
    capture=Capture()
    with capture.activate():
        assert work(3)==4
        with pytest.raises(ValueError):fail()
        with measured('view'):assert work(4)==5
    assert set(capture.stages)=={'normalization','failure','view'}
    assert capture.stages['normalization']['calls']==2
    assert all(set(row)=={'calls','seconds'} and row['seconds']>=0 for row in capture.stages.values())
    assert work(1)==2 and capture.stages['normalization']['calls']==2


def test_capture_is_context_local_and_nestable():
    outer,inner=Capture(),Capture()
    with outer.activate():
        with measured('outer'):pass
        with inner.activate():
            with measured('inner'):pass
        with measured('outer'):pass
        def background():
            with measured('background'):pass
        with ThreadPoolExecutor() as executor:executor.submit(background).result()
    assert set(outer.stages)=={'outer'} and outer.stages['outer']['calls']==2
    assert set(inner.stages)=={'inner'}

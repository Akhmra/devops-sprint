"""Тесты инструмента devcheck."""
from tools.devcheck import cpu_cores, disk_used_pct, is_over, mem_used_pct, pct


def test_pct_format_and_precision():
    result = pct(1500, 3900)
    assert isinstance(result, str)
    value = float(result)
    assert abs(value - 38.5) < 0.1


def test_is_over():
    assert is_over(38.5, 90) is False
    assert is_over(95.0, 90) is True
    # Порог достигнут — уже сигнал (контракт: >=)
    assert is_over(90.0, 90) is True
    assert is_over(89.99, 90) is False


def test_metrics_in_range():
    assert cpu_cores() >= 1
    assert 0 <= mem_used_pct() <= 100
    assert 0 <= disk_used_pct("/") <= 100

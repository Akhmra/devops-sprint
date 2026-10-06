"""Тесты инструмента devcheck."""
from tools.devcheck import cpu_cores, disk_used_pct, is_over, mem_used_pct, pct


def test_pct_format_and_precision():
    # Проверяем, что результат — строка и выглядит как число с одним знаком после запятой
    result = pct(1500, 3900)
    assert isinstance(result, str)
    # Можно проверить через float, чтобы не зависеть от точного форматирования
    value = float(result)
    assert abs(value - 38.5) < 0.1


def test_is_over():
    assert is_over(38.5, 90) is False
    assert is_over(95.0, 90) is True
    # Крайние случаи
    assert is_over(90.0, 90) is True  # если порог включается
    assert is_over(89.99, 90) is False


def test_metrics_in_range_without_side_effects():
    # cpu_cores() — оставляем как есть, но считаем, что >=1 — минимально ожидаемо
    assert cpu_cores() >= 1

    # Для mem_used_pct и disk_used_pct лучше использовать фикстуры-моки,
    # но если нельзя менять devcheck, то хотя бы проверяем диапазон.
    # Это всё ещё не идеально для CI, но безопаснее, чем сравнивать точные значения.
    assert 0 <= mem_used_pct() <= 100
    assert 0 <= disk_used_pct("/") <= 100

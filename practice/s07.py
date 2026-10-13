import re
from typing import Union

# Порядок единиц важен: от меньшей к большей для парсинга,
# и от большей к меньшей для красивого форматирования.
_UNITS = ['Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei']
_BASE = 1024

# Скомпилированное регулярное выражение для производительности и валидации.
# Разрешает: опциональный пробел, число (целое или float), опциональный пробел, суффикс.
_SIZE_RE = re.compile(
    r'^\s*([0-9]*\.?[0-9]+)\s*([KMGTPE]?i)?\s*$',
    re.IGNORECASE
)

def parse_size(size_str: str) -> int:
    """
    Преобразует строку с бинарным суффиксом (например, '10Gi') в количество байт.
    
    Аргументы:
        size_str: Строка вида "10Gi", "1.5Mi", "1024" или " 2 Ti ".
        
    Возвращает:
        Количество байт (int).
        
    Исключения:
        ValueError: если строка имеет неверный формат.
    """
    if not isinstance(size_str, str):
        raise ValueError("Input must be a string")
        
    match = _SIZE_RE.match(size_str)
    if not match:
        raise ValueError(f"Invalid size format: '{size_str}'")

    number_str, unit_str = match.groups()
    number = float(number_str)
    
    # Если суффикс не указан, считаем, что это байты.
    if not unit_str:
        return int(number)
        
    unit_str = unit_str.capitalize() # Приводим к стандартному виду (Ki, Mi и т.д.)
    
    if unit_str not in _UNITS:
        raise ValueError(f"Unknown unit: '{unit_str}'")
        
    power = _UNITS.index(unit_str) + 1
    return int(number * (_BASE ** power))


def fmt_size(num_bytes: Union[int, float], precision: int = 1) -> str:
    """
    Форматирует количество байт в человекочитаемую строку с бинарным суффиксом.
    
    Аргументы:
        num_bytes: Количество байт.
        precision: Количество знаков после запятой (по умолчанию 1).
        
    Возвращает:
        Строку вида '10Gi', '1.5Mi', '512Ki' или '42B'.
    """
    if not isinstance(num_bytes, (int, float)):
        raise ValueError("num_bytes must be a number")
    if num_bytes < 0:
        raise ValueError("num_bytes cannot be negative")
        
    # Байты без суффикса
    if num_bytes < _BASE:
        return f"{int(num_bytes)}B"

    # Ищем самую крупную единицу, значение в которой >= 1
    for i in range(len(_UNITS) - 1, -1, -1):
        unit_size = _BASE ** (i + 1)
        if num_bytes >= unit_size:
            value = num_bytes / unit_size
            
            # Форматируем число: убираем лишние нули после запятой (1.0 -> 1)
            if precision == 0:
                value_str = f"{int(round(value))}"
            else:
                fmt = f"{{:.{precision}f}}".format(value)
                value_str = fmt.rstrip('0').rstrip('.')
                
            return f"{value_str}{_UNITS[i]}"
            
    # Фоллбэк (теоретически не должен достигаться из-за проверки num_bytes < _BASE)
    return f"{int(num_bytes)}B"


# --- Проверка ожидаемого результата ---
if __name__ == '__main__':
    # Прямой тест из ТЗ
    bytes_val = parse_size('10Gi')
    size_str = fmt_size(10737418240)
    
    print(f"parse_size('10Gi') -> {bytes_val}")
    print(f"fmt_size(10737418240) -> '{size_str}'")
    
    # Дополнительные тесты для демонстрации возможностей
    test_cases = [
        '1024',      # байты без суффикса
        '1Ki', 
        '1.5Mi', 
        '2 Ti',      # пробелы и регистр
        '0.5Gi',
        '100Ei'
    ]
    
    print("\nДополнительные тесты:")
    for case in test_cases:
        try:
            b = parse_size(case)
            back = fmt_size(b)
            print(f"'{case}' -> {b} байт -> '{back}'")
        except ValueError as e:
            print(f"Ошибка в '{case}': {e}")

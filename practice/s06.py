def parse_env(text: str) -> dict[str, str]:
    """
    Парсит текст в формате .env и возвращает словарь KEY=VALUE.
    
    Игнорирует:
    - пустые строки;
    - строки, состоящие только из пробелов;
    - комментарии (строки, начинающиеся с # после удаления пробелов).
    
    Если в строке нет символа '=', она пропускается.
    Если ключ пустой (строка начинается с '='), она пропускается.
    """
    result = {}
    
    for line in text.splitlines():
        # 1. Убираем пробелы и переносы по краям
        stripped_line = line.strip()
        
        # 2. Игнорируем пустые строки и комментарии
        if not stripped_line or stripped_line.startswith('#'):
            continue
            
        # 3. Ищем первый символ '='. Если его нет — пропускаем строку
        if '=' not in stripped_line:
            continue
            
        # 4. Разделяем строго на две части: ключ и значение
        key, value = stripped_line.split("=", 1)
        
        # 5. Убираем случайные пробелы вокруг ключа и значения
        key = key.strip()
        value = value.strip()
        
        # 6. Защита от некорректных строк вида '=value'
        if not key:
            continue
            
        result[key] = value
        
    return result

# Пример использования и проверки:
test_input = 'A=1\n# ком\nB=2\n   \nC=  значение с пробелами  \n# еще комментарий\nD='
expected_output = {'A': '1', 'B': '2', 'C': 'значение с пробелами'}

actual_output = parse_env(test_input)

print(f"Результат: {actual_output}")
print(f"Соответствует ожиданиям: {actual_output == expected_output}")

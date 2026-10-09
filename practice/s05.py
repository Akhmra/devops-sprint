def manifest_kind(text):
    kind = None
    name = None
    for line in text.splitlines():        # режем текст на отдельные строки
        s = line.strip()                  # убираем отступы и пробелы по краям
        if s.startswith("kind:"):         # строка начинается с "kind:"
            kind = s.split(":", 1)[1].strip()    # берём часть после двоеточия
        elif s.startswith("name:"):
            name = s.split(":", 1)[1].strip()
    return kind, name                     # возвращаем кортеж из двух значений


print(manifest_kind('kind: Deployment\n  name: app'))

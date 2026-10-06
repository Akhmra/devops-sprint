import re


def image_tag(version, name="app"):
    return f"{name}:{version}"


def is_semver(s):
    return bool(re.fullmatch(r"\d+\.\d+\.\d+", s))


print(image_tag("1.2.3"))
print(is_semver("1.2"))
print(is_semver("1.2.3"))

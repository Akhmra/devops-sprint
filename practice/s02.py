from collections import Counter


def top_messages(lines, n=3):
    return Counter(lines).most_common(n)


print(top_messages(['a', 'b', 'a']))

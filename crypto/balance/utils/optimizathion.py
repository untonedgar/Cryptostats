import time
from functools import wraps


def timer(func):
    """Декоратор для измерения времени выполнения функции"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()  # Используйте perf_counter для точности
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed = end_time - start_time

        print(f"⏱️  {func.__name__} выполнилась за {elapsed:.4f} секунд")
        return result

    return wrapper
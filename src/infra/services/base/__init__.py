"""
Для реализации своего клиента, нужна наследоваться от ``SrvBaseConfig`` (можно не расширять атрибутами),
после чего наследоваться от ``SrvBaseClient`` и передать в конструктор новый конфиг.

``SrvBaseClient`` уже реализует аутентификацию в экосистеме DIOS (пока legacy вариант).
"""

from .client import SrvBaseClient
from .config import SrvBaseConfig

__all__ = ["SrvBaseClient", "SrvBaseConfig"]

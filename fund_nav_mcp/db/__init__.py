from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List


class RdbmsDBManager(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """建立连接池"""

    @abstractmethod
    async def disconnect(self) -> None:
        """关闭所有连接"""

    @abstractmethod
    async def execute(self, statement: Any, params: Optional[Dict] = None) -> Any:
        """执行写操作（INSERT/UPDATE/DELETE）"""

    @abstractmethod
    async def fetch_one(self, statement: Any, params: Optional[Dict] = None) -> Optional[Dict]:
        """查询单行（返回字典）"""

    @abstractmethod
    async def fetch_all(self, statement: Any, params: Optional[Dict] = None) -> List[Dict]:
        """查询多行（返回字典列表）"""

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""


class TimeseriesDBManager(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """建立连接池"""

    @abstractmethod
    async def disconnect(self) -> None:
        """关闭所有连接"""

    @abstractmethod
    async def write(self, data: Any) -> None:
        """写入时序数据，data 格式由子类决定"""
        pass

    @abstractmethod
    async def query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """执行时序查询，返回字典列表"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""

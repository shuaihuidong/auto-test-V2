"""
存储抽象层 - 支持 Local 和 MinIO 两种存储后端

用于 Playwright Trace 文件的持久化存储。
通过 settings.STORAGE_BACKEND.TYPE 配置切换。
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """存储后端抽象基类"""

    @abstractmethod
    def save(self, filename: str, content: bytes) -> str:
        """
        保存文件，返回可访问的路径或 URL

        Args:
            filename: 文件名 (如 task_1_20260422_120000.zip)
            content: 文件内容 (bytes)

        Returns:
            文件的可访问路径 (如 /media/traces/filename 或 http://minio:9000/bucket/filename)
        """
        pass

    @abstractmethod
    def get_path(self, filename: str) -> str:
        """获取文件的访问路径"""
        pass


class LocalStorage(StorageBackend):
    """本地文件系统存储 - 保存到 /media/traces/"""

    def __init__(self):
        self.traces_dir = os.path.join(settings.MEDIA_ROOT, 'traces')
        os.makedirs(self.traces_dir, exist_ok=True)

    def save(self, filename: str, content: bytes) -> str:
        file_path = os.path.join(self.traces_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
        logger.info(f"Trace 已保存到本地: {filename}")
        return f"/media/traces/{filename}"

    def get_path(self, filename: str) -> str:
        return f"/media/traces/{filename}"


class MinIOStorage(StorageBackend):
    """MinIO (S3 兼容) 对象存储"""

    def __init__(self):
        self._client = None
        self._bucket = settings.STORAGE_BACKEND['MINIO_BUCKET']
        self._endpoint = settings.STORAGE_BACKEND['MINIO_ENDPOINT']
        self._secure = settings.STORAGE_BACKEND['MINIO_SECURE']

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError:
                raise ImportError(
                    "使用 MinIO 存储需要安装 boto3: pip install boto3"
                )

            access_key = settings.STORAGE_BACKEND['MINIO_ACCESS_KEY']
            secret_key = settings.STORAGE_BACKEND['MINIO_SECRET_KEY']

            # 解析 endpoint，分离协议和主机
            endpoint = self._endpoint
            if not endpoint.startswith('http'):
                protocol = 'https' if self._secure else 'http'
                endpoint = f"{protocol}://{endpoint}"

            self._client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1',
            )

            # 确保 bucket 存在
            self._ensure_bucket()

        return self._client

    def _ensure_bucket(self):
        """确保存储桶存在"""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception:
            try:
                self._client.create_bucket(Bucket=self._bucket)
                logger.info(f"MinIO bucket '{self._bucket}' 已创建")
            except Exception as e:
                logger.warning(f"创建 MinIO bucket 失败 (可能已存在): {e}")

    def save(self, filename: str, content: bytes) -> str:
        client = self._get_client()

        # 上传到 MinIO
        client.put_object(
            Bucket=self._bucket,
            Key=f"traces/{filename}",
            Body=content,
            ContentType='application/zip',
        )

        # 构建访问 URL
        protocol = 'https' if self._secure else 'http'
        url = f"{protocol}://{self._endpoint}/{self._bucket}/traces/{filename}"
        logger.info(f"Trace 已上传到 MinIO: {filename}")
        return url

    def get_path(self, filename: str) -> str:
        protocol = 'https' if self._secure else 'http'
        return f"{protocol}://{self._endpoint}/{self._bucket}/traces/{filename}"


def get_storage_backend() -> StorageBackend:
    """
    获取配置的存储后端实例

    Returns:
        StorageBackend 实例 (LocalStorage 或 MinIOStorage)
    """
    storage_type = settings.STORAGE_BACKEND.get('TYPE', 'local').lower()

    if storage_type == 'minio':
        return MinIOStorage()
    return LocalStorage()

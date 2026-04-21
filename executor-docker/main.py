"""
Docker 执行器入口
启动流程：加载配置 → 注册 → 连 MQ → 消费任务
"""

import asyncio
import signal
import sys
from loguru import logger

from config import load_config
from task_manager import AsyncTaskManager


async def main():
    """主入口"""
    # 配置 loguru
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | {message}",
        level="INFO",
    )
    logger.add(
        "/app/logs/executor.log",
        rotation="10 MB",
        retention="3 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
        level="DEBUG",
    )

    # 加载配置
    config = load_config()
    logger.info(f"执行机启动: {config.executor_name} (UUID: {config.executor_uuid})")
    logger.info(f"后端: {config.backend_url}")
    logger.info(f"RabbitMQ: {config.rabbitmq_host}:{config.rabbitmq_port}")
    logger.info(f"并发数: {config.max_concurrent}, Trace: {config.trace_enabled}")

    # 创建任务管理器
    manager = AsyncTaskManager(config)

    # 优雅退出
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("收到退出信号，正在优雅关闭...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    # 连接平台
    if not await manager.connect():
        logger.error("连接平台失败，退出")
        sys.exit(1)

    # 等待退出信号
    logger.info("执行机运行中，等待任务...")
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass

    # 清理
    await manager.disconnect()
    logger.info("执行机已关闭")


if __name__ == "__main__":
    asyncio.run(main())

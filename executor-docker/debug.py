"""
本地调试 CLI 工具
直连后端拉取脚本，使用 Playwright headed + Inspector 逐行调试

用法:
    python debug.py --script 123 --headed --slow-mo 500
    python debug.py --script 123 --browser firefox
"""

import argparse
import asyncio
import json
import sys
from loguru import logger

from config import load_config, ExecutorConfig
from executor import PlaywrightScriptExecutor

import httpx
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


async def fetch_script(config: ExecutorConfig, script_id: int) -> dict:
    """从后端拉取脚本数据"""
    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        resp = await client.get(
            f"{config.backend_url}/api/scripts/{script_id}/",
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f"拉取脚本失败: HTTP {resp.status_code} - {resp.text}")


async def run_debug(
    backend_url: str,
    script_id: int,
    headed: bool,
    slow_mo: int,
    browser: str,
):
    """本地调试主流程"""
    # 构建调试配置
    config = ExecutorConfig(
        backend_url=backend_url,
        headless=not headed,
        slow_mo=slow_mo,
        trace_enabled=True,
        default_browser=browser,
    )

    # 拉取脚本
    logger.info(f"从后端拉取脚本 #{script_id} ...")
    script_data = await fetch_script(config, script_id)
    logger.info(f"脚本名称: {script_data.get('name')}")
    logger.info(f"步骤数: {len(script_data.get('steps', []))}")

    # 创建执行器
    executor = PlaywrightScriptExecutor(config)

    def on_step(index, result):
        status = "PASS" if result["success"] else "FAIL"
        logger.info(f"  [{status}] 步骤 {index + 1}: {result.get('name', '')} - {result.get('message', '')}")

    try:
        # 启动浏览器
        logger.info(f"启动浏览器: {browser} (headed={headed}, slow_mo={slow_mo}ms)")
        if not await executor.start(browser):
            logger.error("浏览器启动失败")
            return

        if headed:
            logger.info("已启动 Playwright Inspector，可单步调试")
            logger.info("按 F8 暂停/继续，按 F10 单步跳过")

        # 执行脚本
        variables = script_data.get("variables", {})
        result = await executor.execute_script(script_data, variables, on_step_complete=on_step)

        # 输出结果
        logger.info("=" * 50)
        if result["success"]:
            logger.info(f"脚本执行成功，耗时 {result.get('duration', 0)}s")
        else:
            logger.error(f"脚本执行失败: {result.get('message')}")

        for step in result.get("steps", []):
            icon = "+" if step.get("success") else "x"
            logger.info(f"  [{icon}] 步骤 {step.get('step_index', 0) + 1}: {step.get('name', '')} ({step.get('duration', 0)}ms)")

        logger.info("=" * 50)

    finally:
        await executor.stop()


def main():
    parser = argparse.ArgumentParser(description="自动化测试平台 - 本地调试工具")
    parser.add_argument("--script", type=int, required=True, help="脚本 ID")
    parser.add_argument("--headed", action="store_true", default=True, help="有头模式（默认开启）")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--slow-mo", type=int, default=500, help="每步延迟（毫秒，默认500）")
    parser.add_argument("--browser", default="chromium", choices=["chromium", "firefox"], help="浏览器类型")
    parser.add_argument("--backend", default="http://localhost:8000", help="后端地址")

    args = parser.parse_args()

    headed = not args.headless

    logger.info("本地调试模式启动")
    asyncio.run(run_debug(
        backend_url=args.backend,
        script_id=args.script,
        headed=headed,
        slow_mo=args.slow_mo,
        browser=args.browser,
    ))


if __name__ == "__main__":
    main()

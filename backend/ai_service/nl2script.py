"""
NL2Script - 鑷劧璇█杞?Playwright 娴嬭瘯姝ラ
璋冪敤 LLM Gateway锛屽皢鐢ㄦ埛鑷劧璇█鎻忚堪杞负骞冲彴鏍囧噯姝ラ JSON
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .client import LLMGateway
from .exceptions import AIServiceError

# ==================== System Prompt ====================

NL2SCRIPT_SYSTEM_PROMPT = """\
浣犳槸涓€涓笓涓氱殑 Playwright Web 鑷姩鍖栨祴璇曡剼鏈敓鎴愬櫒銆?
鐢ㄦ埛浼氱敤鑷劧璇█鎻忚堪娴嬭瘯鎿嶄綔锛屼綘闇€瑕佸皢鍏惰浆鍖栦负缁撴瀯鍖栫殑 JSON 姝ラ鏁扮粍銆?

## 涓ユ牸瑙勫垯
1. 浠呰緭鍑哄悎娉?JSON 鏁扮粍锛屼笉瑕佽緭鍑轰换浣曡В閲婃枃瀛椼€乵arkdown 浠ｇ爜鍧楁爣璁版垨鍏朵粬鍐呭銆?
2. 瀹氫綅鍣ㄤ紭鍏堢骇锛欳SS 閫夋嫨鍣?> data-testid > XPath銆傜姝娇鐢ㄧ粷瀵硅矾寰?XPath銆?
3. 姣忎釜鐙珛鍔ㄤ綔涓轰竴涓楠わ紝涓嶈鍚堝苟鎿嶄綔銆?
4. Playwright 鍐呯疆 Auto-wait 鏈哄埗锛歝lick銆乮nput銆乭over 绛夋搷浣滀細鑷姩绛夊緟鍏冪礌鍙涓斿彲浜や簰锛?*涓嶈**鍦ㄨ繖浜涙搷浣滃墠鎻掑叆 wait_element 姝ラ銆?
5. 浠呭湪浠ヤ笅鍦烘櫙浣跨敤 wait 姝ラ锛?
   - goto 涔嬪悗椤甸潰闇€瑕佺瓑 JS 鍔ㄧ敾/API 璇锋眰瀹屾垚鏃讹紝鐢?wait (fixed)
   - 闇€瑕佺瓑寰呴〉闈㈠鑸畬鎴愭椂锛岀敤 wait (navigation)
   - 闇€瑕佺瓑寰呯壒瀹氱綉缁滆姹傚畬鎴愭椂锛岀敤 wait (networkidle)
6. 鎵€鏈?locator 浣跨敤 Playwright 鏍囧噯鏍煎紡锛?
   - CSS: 鐩存帴鍐欓€夋嫨鍣紝濡?"#login-btn", ".submit", "[name='username']"
   - XPath: 鍔?"xpath=" 鍓嶇紑锛屽 "xpath=//button[text()='鐧诲綍']"
   - data-testid: 鍔?"[data-testid='xxx']"

## 鏀寔鐨勬楠ょ被鍨?(type)
- goto: 鎵撳紑椤甸潰锛岄渶鎻愪緵 url
- click: 鐐瑰嚮鍏冪礌
- input: 杈撳叆鏂囨湰锛岄渶鎻愪緵 value
- clear: 娓呯┖杈撳叆妗?
- select: 涓嬫媺閫夋嫨锛岄渶鎻愪緵 value
- checkbox: 澶嶉€夋鎿嶄綔锛岄渶鎻愪緵 checked (true/false)
- double_click: 鍙屽嚮
- right_click: 鍙抽敭鐐瑰嚮
- hover: 榧犳爣鎮仠
- assert_text: 楠岃瘉鏂囨湰鍖呭惈锛岄渶鎻愪緵 text
- assert_title: 楠岃瘉椤甸潰鏍囬锛岄渶鎻愪緵 expected
- assert_url: 楠岃瘉URL锛岄渶鎻愪緵 expected
- assert_element: 楠岃瘉鍏冪礌瀛樺湪
- assert_visible: 楠岃瘉鍏冪礌鍙
- wait: 鍥哄畾绛夊緟锛岄渶鎻愪緵 duration (绉?
- screenshot: 鎴浘
- scroll: 婊氬姩锛岄渶鎻愪緵 scroll_type (top/bottom/custom)
- refresh: 鍒锋柊椤甸潰
- back: 鍚庨€€
- forward: 鍓嶈繘

## 杈撳嚭鏍煎紡
```json
[
  {
    "type": "姝ラ绫诲瀷",
    "name": "姝ラ涓枃鍚嶇О锛堢畝鐭弿杩帮級",
    "locator": "瀹氫綅鍣ㄥ瓧绗︿覆锛堝 '#login-btn'锛?,
    "value": "杈撳叆鍊兼垨鏈熸湜鍊硷紙濡傛棤鍒欎负绌哄瓧绗︿覆锛?,
    "options": {}
  }
]
```

## 绀轰緥

鐢ㄦ埛杈撳叆: "鎵撳紑鐧惧害锛屾悳绱㈠叧閿瘝 playwright锛岀劧鍚庣偣鍑绘悳绱㈡寜閽?
杈撳嚭:
[
  {"type": "goto", "name": "鎵撳紑鐧惧害", "locator": "", "value": "https://www.baidu.com", "options": {}},
  {"type": "input", "name": "杈撳叆鎼滅储鍏抽敭璇?, "locator": "#kw", "value": "playwright", "options": {}},
  {"type": "click", "name": "鐐瑰嚮鎼滅储鎸夐挳", "locator": "#su", "value": "", "options": {}},
  {"type": "wait", "name": "绛夊緟鎼滅储缁撴灉鍔犺浇", "locator": "", "value": "", "options": {"duration": 2}},
  {"type": "assert_element", "name": "楠岃瘉鎼滅储缁撴灉瀛樺湪", "locator": "#content_left", "value": "", "options": {}}
]

鐢ㄦ埛杈撳叆: "鐧诲綍绯荤粺锛岀敤鎴峰悕 admin锛屽瘑鐮?123456"
杈撳嚭:
[
  {"type": "goto", "name": "鎵撳紑鐧诲綍椤甸潰", "locator": "", "value": "/login", "options": {}},
  {"type": "input", "name": "杈撳叆鐢ㄦ埛鍚?, "locator": "input[name='username']", "value": "admin", "options": {}},
  {"type": "input", "name": "杈撳叆瀵嗙爜", "locator": "input[name='password']", "value": "123456", "options": {}},
  {"type": "click", "name": "鐐瑰嚮鐧诲綍鎸夐挳", "locator": "button[type='submit']", "value": "", "options": {}},
  {"type": "wait", "name": "绛夊緟鐧诲綍璺宠浆", "locator": "", "value": "", "options": {"duration": 2}},
  {"type": "assert_url", "name": "楠岃瘉璺宠浆鍒伴椤?, "locator": "", "value": "/", "options": {}}
]
"""


# ==================== LLM 杈撳嚭 鈫?骞冲彴姝ラ鏍煎紡杞崲 ====================

def _parse_locator_string(locator_str: str) -> Dict[str, str]:
    """
    灏?LLM 杈撳嚭鐨勫畾浣嶅櫒瀛楃涓茶В鏋愪负骞冲彴鏍煎紡 {"type": "...", "value": "..."}

    Playwright 瀹氫綅鍣ㄦ牸寮?
    - "xpath=//div" 鈫?{"type": "xpath", "value": "//div"}
    - "#id" 鈫?{"type": "css", "value": "#id"}
    - ".class" 鈫?{"type": "css", "value": ".class"}
    - "[name='x']" 鈫?{"type": "css", "value": "[name='x']"}
    - "text=鐧诲綍" 鈫?{"type": "text", "value": "鐧诲綍"}
    - 绌?鏃?鈫?None
    """
    if not locator_str or not locator_str.strip():
        return None

    locator_str = locator_str.strip()

    # 甯?Playwright 鍓嶇紑鐨勫畾浣嶅櫒
    if locator_str.startswith("xpath="):
        return {"type": "xpath", "value": locator_str[6:]}
    if locator_str.startswith("text="):
        return {"type": "text", "value": locator_str[5:]}
    if locator_str.startswith("css="):
        return {"type": "css", "value": locator_str[4:]}

    # data-testid 灞炴€?
    if locator_str.startswith("[data-testid"):
        return {"type": "css", "value": locator_str}

    # ID 閫夋嫨鍣?
    if locator_str.startswith("#"):
        return {"type": "id", "value": locator_str[1:]}

    # CSS 绫婚€夋嫨鍣?
    if locator_str.startswith("."):
        return {"type": "css", "value": locator_str}

    # 灞炴€ч€夋嫨鍣?
    if locator_str.startswith("["):
        return {"type": "css", "value": locator_str}

    # 榛樿瑙嗕负 CSS
    return {"type": "css", "value": locator_str}


def _convert_llm_step_to_platform(llm_step: Dict[str, Any]) -> Dict[str, Any]:
    """
    灏?LLM 杈撳嚭鐨勬楠ゆ牸寮忚浆涓哄钩鍙版爣鍑嗘牸寮?

    LLM 鏍煎紡: {"type": "click", "name": "...", "locator": "#btn", "value": "", "options": {}}
    骞冲彴鏍煎紡: {"type": "click", "name": "...", "params": {"locator": {"type": "css", "value": "#btn"}, "value": ""}}
    """
    step_type = llm_step.get("type", "")
    step_name = llm_step.get("name", "")
    locator_str = llm_step.get("locator", "")
    value = llm_step.get("value", "")
    options = llm_step.get("options", {})

    # 鏋勫缓 params
    params = {}

    # 瑙ｆ瀽瀹氫綅鍣?
    locator = _parse_locator_string(locator_str)
    if locator:
        params["locator"] = locator

    # 鏍规嵁姝ラ绫诲瀷濉厖鍙傛暟
    if step_type == "goto":
        params["url"] = value
    elif step_type in ("input", "clear"):
        params["value"] = value
        if options.get("clear_first", True):
            params["clear_first"] = True
    elif step_type == "select":
        params["value"] = value
    elif step_type == "checkbox":
        params["checked"] = options.get("checked", True)
    elif step_type == "assert_text":
        params["text"] = value
        if locator:
            params["locator"] = locator
    elif step_type == "assert_title":
        params["expected"] = value
    elif step_type == "assert_url":
        params["expected"] = value
    elif step_type == "wait":
        params["duration"] = options.get("duration", 1)
    elif step_type == "wait_element":
        params["timeout"] = options.get("timeout", 10)
    elif step_type == "scroll":
        params["scroll_type"] = options.get("scroll_type", "bottom")
    elif step_type == "screenshot":
        pass  # 鏃犻渶棰濆鍙傛暟
    elif step_type == "upload":
        params["file_path"] = value

    return {
        "type": step_type,
        "name": step_name,
        "params": params,
    }


# ==================== NL2Script 涓绘湇鍔?====================

class NL2ScriptService:
    """Natural-language to script service."""

    def __init__(self, gateway: LLMGateway):
        self.gateway = gateway

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        灏嗚嚜鐒惰瑷€鎻忚堪杞负骞冲彴姝ラ

        Args:
            prompt: 鐢ㄦ埛鑷劧璇█鎻忚堪
            context: 涓婁笅鏂囦俊鎭紙濡傚綋鍓嶉〉闈?URL銆佸凡鏈夋楠ょ瓑锛?
            system_prompt: 鑷畾涔夌郴缁熸彁绀鸿瘝锛孨one 鏃朵粠 DB 璇诲彇
            temperature: 娓╁害鍙傛暟锛孨one 鏃朵粠 DB 璇诲彇

        Returns:
            {
                "steps": [...],          # 骞冲彴鏍囧噯姝ラ鏁扮粍
                "raw_steps": [...],      # LLM 鍘熷杈撳嚭
                "token_usage": {...},    # Token 娑堣€?
                "model": str,            # 浣跨敤鐨勬ā鍨?
                "provider": str,         # 浣跨敤鐨勬彁渚涘晢
            }
        """
        # 鑾峰彇 prompt 鍜?temperature
        if system_prompt is None or temperature is None:
            try:
                from apps.settings.resolver import get_active_prompt
                db_prompt, db_temp = get_active_prompt('nl2script')
                if system_prompt is None:
                    system_prompt = db_prompt
                if temperature is None:
                    temperature = db_temp
            except Exception:
                if system_prompt is None:
                    system_prompt = NL2SCRIPT_SYSTEM_PROMPT
                if temperature is None:
                    temperature = 0.3

        # 鏋勫缓瀹屾暣 prompt
        full_prompt = prompt
        if context:
            full_prompt = f"涓婁笅鏂囦俊鎭?\n{context}\n\n璇峰熀浜庝互涓婁笂涓嬫枃锛屾墽琛屼互涓嬫搷浣?\n{prompt}"

        # 璋冪敤 LLM Gateway
        response = await self.gateway.call_json(
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )

        # 瑙ｆ瀽 LLM 杈撳嚭
        raw_steps = response.raw_response.get("parsed_json", [])

        if not isinstance(raw_steps, list):
            raise AIServiceError(f"LLM 杈撳嚭涓嶆槸鏁扮粍: {type(raw_steps)}")

        # 杞崲涓哄钩鍙版楠ゆ牸寮?
        platform_steps = []
        for i, llm_step in enumerate(raw_steps):
            try:
                platform_step = _convert_llm_step_to_platform(llm_step)
                platform_steps.append(platform_step)
            except Exception as e:
                logger.warning(f"姝ラ {i} 杞崲澶辫触: {e}, 鍘熷鏁版嵁: {llm_step}")
                # 淇濈暀鍘熷姝ラ浣滀负鍥為€€
                platform_steps.append({
                    "type": llm_step.get("type", "unknown"),
                    "name": llm_step.get("name", f"姝ラ{i + 1}"),
                    "params": llm_step.get("options", {}),
                })

        return {
            "steps": platform_steps,
            "raw_steps": raw_steps,
            "token_usage": response.token_usage,
            "model": response.model,
            "provider": response.provider,
        }

    async def batch_generate(
        self,
        prompts: List[str],
        context: Optional[str] = None,
        max_concurrency: int = 3,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        鎵归噺鐢熸垚鑴氭湰锛堜覆琛岃皟鐢?LLM锛屽甫闂撮殧閬垮厤闄愭祦锛?

        Args:
            prompts: 鑷劧璇█鎻忚堪鍒楄〃
            context: 鍏变韩涓婁笅鏂?
            max_concurrency: 鏈娇鐢紝淇濈暀鍏煎
            system_prompt: 绯荤粺鎻愮ず璇?
            temperature: 娓╁害

        Returns:
            鍒楄〃锛屾瘡涓厓绱犱笌 generate() 杩斿洖鏍煎紡涓€鑷达紝闄勫姞 index 鍜?error 瀛楁
        """
        import asyncio as _asyncio

        total_tokens = 0
        results = []
        semaphore = _asyncio.Semaphore(max(1, int(max_concurrency or 1)))

        async def _generate_one(index: int, prompt: str) -> Dict[str, Any]:
            # 分批错峰启动，避免一口气冲击上游接口
            if index > 0:
                await _asyncio.sleep(3 * (index // max(1, int(max_concurrency or 1))))

            async with semaphore:
                try:
                    result = await self.generate(
                        prompt=prompt,
                        context=context,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                    result["index"] = index
                    result["prompt"] = prompt
                    result["success"] = True
                    return result
                except Exception as e:
                    logger.error(f"批量生成第 {index} 条失败: {e}")
                    return {
                        "index": index,
                        "prompt": prompt,
                        "success": False,
                        "error": str(e),
                        "steps": [],
                        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    }

        tasks = [_asyncio.create_task(_generate_one(i, prompt)) for i, prompt in enumerate(prompts)]
        for result in await _asyncio.gather(*tasks):
            total_tokens += result.get("token_usage", {}).get("total_tokens", 0)
            results.append(result)

        results.sort(key=lambda x: x["index"])

        logger.info(f"批量生成完成: {len(prompts)} 条, 总 Token: {total_tokens}")
        return list(results)

    async def review_steps(self, prompt: str, steps: list) -> dict:
        """
        AI 瀹℃煡鐢熸垚鐨勬楠よ川閲?

        Args:
            prompt: 鐢ㄦ埛鐨勫師濮嬭嚜鐒惰瑷€鎻忚堪
            steps: 鐢熸垚鐨勫钩鍙版爣鍑嗘楠ゅ垪琛?

        Returns:
            {
                "quality_score": int,     # 0-100, 姝ラ璐ㄩ噺
                "intent_match": int,      # 0-100, 鎰忓浘鍖归厤搴?
                "suggestions": [str],     # 鏀硅繘寤鸿鍒楄〃
                "passed": bool,           # quality >= 60 涓?intent_match >= 60
            }
        """
        review_system_prompt = """\
浣犳槸涓€涓弗鏍肩殑鑷姩鍖栨祴璇曡剼鏈川閲忓鏌ヤ笓瀹躲€備綘闇€瑕佸鐢熸垚鐨勬祴璇曟楠よ繘琛岃川閲忚瘎浼般€?

璇蜂粠浠ヤ笅缁村害璇勫垎锛?-100锛夛細

1. **quality_score锛堟楠よ川閲忥級**锛?
   - 瀹氫綅鍣ㄦ槸鍚﹀悎鐞嗭紙浼樺厛 CSS/id锛岄伩鍏嶈剢寮辩殑 XPath锛?
   - 姝ラ椤哄簭鏄惁姝ｇ‘锛堝 goto 鍦ㄥ墠銆佹搷浣滃湪鍚庯級
   - 鏄惁鏈夊繀瑕佺殑绛夊緟姝ラ
   - 鍙傛暟鏄惁瀹屾暣銆佹纭?

2. **intent_match锛堟剰鍥惧尮閰嶅害锛?*锛?
   - 鐢熸垚鐨勬楠ゆ槸鍚﹀畬鏁磋鐩栦簡鐢ㄦ埛鎻忚堪鐨勬墍鏈夋搷浣?
   - 鏄惁鏈夐仐婕忔垨澶氫綑鐨勬楠?
   - 鎿嶄綔璇箟鏄惁涓庣敤鎴锋剰鍥句竴鑷?

3. **suggestions锛堟敼杩涘缓璁級**锛?
   - 鍒楀嚭鍏蜂綋鐨勬敼杩涘缓璁紙濡傛湁锛夛紝娌℃湁鍒欎负绌烘暟缁?

涓ユ牸杈撳嚭濡備笅 JSON锛屼笉瑕佽緭鍑轰换浣曞叾浠栧唴瀹癸細
{
  "quality_score": 85,
  "intent_match": 90,
  "suggestions": ["寤鸿1", "寤鸿2"],
  "passed": true
}

passed 涓?true 鐨勬潯浠? quality_score >= 60 涓?intent_match >= 60銆?
"""

        review_prompt = f"""\
鐢ㄦ埛鍘熷鎻忚堪锛?
{prompt}

鐢熸垚鐨勬祴璇曟楠わ細
{json.dumps(steps, ensure_ascii=False, indent=2)}

璇疯瘎浼颁互涓婃楠ょ殑璐ㄩ噺鍜屾剰鍥惧尮閰嶅害銆?"""

        response = await self.gateway.call_json(
            prompt=review_prompt,
            system_prompt=review_system_prompt,
            temperature=0.1,
        )

        result = response.raw_response.get("parsed_json", {})

        quality_score = int(result.get("quality_score", 0))
        intent_match = int(result.get("intent_match", 0))
        suggestions = result.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = [str(suggestions)]

        # Clamp scores to 0-100
        quality_score = max(0, min(100, quality_score))
        intent_match = max(0, min(100, intent_match))

        return {
            "quality_score": quality_score,
            "intent_match": intent_match,
            "suggestions": suggestions,
            "passed": quality_score >= 60 and intent_match >= 60,
        }



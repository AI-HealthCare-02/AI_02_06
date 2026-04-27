"""OpenAI ``tools`` 파라미터에 그대로 넣을 수 있는 함수 선언.

Router LLM 은 두 함수만 인지한다:
- ``search_hospitals_by_location`` — 사용자 GPS 좌표가 필요한 위치 검색.
- ``search_hospitals_by_keyword`` — 지명/지역명/랜드마크 등 자유 키워드 검색.

병렬 호출 정책:
    호출 측에서 ``parallel_tool_calls=True`` + ``tool_choice="auto"`` 로
    호출하면 LLM 이 두 함수를 한 응답에 묶어 호출할 수 있다. message_service
    는 모든 결과를 ``asyncio.gather`` 로 모아 2nd LLM 호출에 전달한다.

description 은 한국어:
    LLM 의 의도 분류 정확도를 위해 사용자가 보낼 한국어 표현과 가까운
    용어로 작성한다 (예: "주변 약국", "근처 병원", "강남역 약국").
"""

from typing import Any

HOSPITAL_LOCATION_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_hospitals_by_location",
        "description": (
            "사용자 GPS 좌표 주변에서 약국 또는 병원을 검색한다. "
            "사용자가 '내 주변', '근처', '가까운' 같은 표현으로 위치 기반 추천을 "
            "요청할 때 사용한다. 좌표는 백엔드가 별도로 수집하므로 인자에는 포함하지 "
            "않는다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["약국", "병원"],
                    "description": "검색 대상 카테고리. 약국 또는 병원.",
                },
                "radius_m": {
                    "type": "integer",
                    "description": "검색 반경 (m). 기본 1000m.",
                    "default": 1000,
                },
            },
            "required": ["category"],
        },
    },
}

HOSPITAL_KEYWORD_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_hospitals_by_keyword",
        "description": (
            "지명, 지역명, 랜드마크 등 자유 키워드로 약국/병원을 검색한다. "
            "사용자가 '강남역 약국', '역삼동 병원', '서울대병원' 처럼 "
            "특정 위치 키워드를 명시했을 때 사용한다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색 키워드. 예: '강남역 약국', '서울대병원'",
                },
            },
            "required": ["query"],
        },
    },
}

TOOL_SCHEMAS: list[dict[str, Any]] = [HOSPITAL_LOCATION_TOOL, HOSPITAL_KEYWORD_TOOL]

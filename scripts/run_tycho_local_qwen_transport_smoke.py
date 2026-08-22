#!/usr/bin/env python3
"""Run the single frozen local OpenAI-compatible Tycho transport call."""

from __future__ import annotations

import io
import json
import os
from collections.abc import Mapping


EXPECTED = {
    "LLM_BACKEND": "openai",
    "LLM_BASE_URL": "http://127.0.0.1:1234/v1",
    "LLM_MODEL": "qwen3.6-27b-oia",
    "LLM_API_KEY": "EMPTY",
}
FORBIDDEN_CREDENTIALS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "ARC_API_KEY",
)


def validate_environment(environ: Mapping[str, str]) -> dict[str, str]:
    for name, expected in EXPECTED.items():
        if environ.get(name) != expected:
            raise ValueError(f"frozen local transport setting changed: {name}")
    present = [name for name in FORBIDDEN_CREDENTIALS if environ.get(name)]
    if present:
        raise ValueError(f"credential entered local transport process: {present}")
    return dict(EXPECTED)


def main() -> int:
    validate_environment(os.environ)

    from PIL import Image, ImageDraw

    from tycho.serving.llm_client import LLMConfig, chat_tools

    image = Image.new("RGB", (256, 256), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((64, 64, 191, 191), fill=(30, 90, 220))
    image_output = io.BytesIO()
    image.save(image_output, format="PNG")
    tool = {
        "name": "report_transport_ok",
        "description": "Report that text, image, and tool calling were received.",
        "schema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["ok"]}},
            "required": ["status"],
        },
    }
    config = LLMConfig.from_env()
    reply = chat_tools(
        [{
            "role": "user",
            "content": [
                {
                    "text": (
                        "Inspect the attached blue-square test image, then call "
                        "report_transport_ok."
                    )
                },
                {"image_png": image_output.getvalue()},
            ],
        }],
        [tool],
        config,
        system="This is a transport test. Call the provided tool exactly once.",
        max_tokens=256,
        timeout=180,
        effort="off",
        call_type="local_provider_smoke",
    )
    calls = reply.get("tool_calls") or []
    expected_calls = [
        call
        for call in calls
        if call.get("name") == "report_transport_ok"
        and call.get("input", {}).get("status") == "ok"
    ]
    if len(calls) != 1 or len(expected_calls) != 1:
        raise ValueError("local transport did not return exactly the frozen tool call")
    usage = reply.get("usage") or {}
    result = {
        "backend": config.backend,
        "base_url": config.base_url,
        "input_tokens": usage.get("in"),
        "model": config.model,
        "output_tokens": usage.get("out"),
        "status": "local_qwen_tycho_transport_pass",
        "tool_call": {
            "name": expected_calls[0]["name"],
            "input": expected_calls[0]["input"],
        },
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

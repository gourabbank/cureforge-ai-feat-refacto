import os
from pathlib import Path
import threading
from time import perf_counter
from uuid import uuid4
from litellm.integrations.custom_logger import CustomLogger


CACHE_DIR = "/app/.cache/litellm"
LOG_FILE = Path(CACHE_DIR) / "litellm.log"
LOG_LOCK = threading.Lock()


def _log(message: str):
    with LOG_LOCK:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")


class LiteLLMProxy(CustomLogger):
    """Custom LiteLLM Proxy Handler for CureForge AI."""

    def __init__(self):
        super().__init__(turn_off_message_logging=True)
        self._success_count = 0
        self._failure_count = 0
        self._success_lock = threading.Lock()
        self._request_timer_lock = threading.Lock()
        self._request_timers: dict[str, float] = {}

        os.makedirs(CACHE_DIR, exist_ok=True)
        LOG_FILE.touch(exist_ok=True)
        _log("==== CureForge Custom Gateway Logic Initialized! ====")

    @staticmethod
    def _extract_tool_names(request_data: dict) -> list[str]:
        tools = request_data.get("tools") or []
        names: list[str] = []
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            function_obj = tool.get("function")
            if isinstance(function_obj, dict):
                name = function_obj.get("name")
                if isinstance(name, str) and name:
                    names.append(name)
        return names

    @staticmethod
    def _extract_metadata_from_kwargs(kwargs: dict) -> dict:
        litellm_params = kwargs.get("litellm_params") or {}
        for metadata_key in ("litellm_metadata", "metadata"):
            metadata = litellm_params.get(metadata_key)
            if isinstance(metadata, dict):
                return metadata
        return {}

    @staticmethod
    def _extract_received_headers(kwargs):
        metadata = LiteLLMProxy._extract_metadata_from_kwargs(kwargs)
        headers = metadata.get("headers")
        if isinstance(headers, dict):
            return headers

        proxy_server_request = kwargs.get("proxy_server_request")
        if isinstance(proxy_server_request, dict):
            headers = proxy_server_request.get("headers")
            if isinstance(headers, dict):
                return headers

        return {}

    @staticmethod
    def _extract_agent_id(kwargs: dict, fallback: str = "unknown-agent") -> str:
        headers = LiteLLMProxy._extract_received_headers(kwargs)
        for key in ("x-agent-id", "X-Agent-ID"):
            value = headers.get(key)
            if isinstance(value, str) and value:
                return value
        return fallback

    @staticmethod
    def _extract_tool_call_count(response_obj) -> int:
        choices = getattr(response_obj, "choices", None)
        if not choices:
            return 0

        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        if message is None and isinstance(first_choice, dict):
            message = first_choice.get("message")

        if isinstance(message, dict):
            tool_calls = message.get("tool_calls") or []
            return len(tool_calls)

        tool_calls = getattr(message, "tool_calls", None) or []
        return len(tool_calls)

    @staticmethod
    def _extract_finish_reason(response_obj) -> str:
        choices = getattr(response_obj, "choices", None)
        if not choices:
            return "unknown"

        first_choice = choices[0]
        if isinstance(first_choice, dict):
            return str(first_choice.get("finish_reason", "unknown"))
        return str(getattr(first_choice, "finish_reason", "unknown"))

    @staticmethod
    def _approx_tokens(text: str) -> int:
        """
        Very fast approximation:
        - ~4 chars per token is a common heuristic for LLM text
        - avoids tokenizer overhead entirely
        """
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _extract_token_usage(self, kwargs: dict, response_obj):
        """
        Priority:
        1. Provider usage (accurate)
        2. Approximation (fast fallback)
        """
        try:
            usage = getattr(response_obj, "usage", None)

            if usage:
                if isinstance(usage, dict):
                    prompt_tokens = usage.get("prompt_tokens")
                    completion_tokens = usage.get("completion_tokens")
                else:
                    prompt_tokens = getattr(usage, "prompt_tokens", None)
                    completion_tokens = getattr(usage, "completion_tokens", None)

                if isinstance(prompt_tokens, int) and isinstance(
                    completion_tokens, int
                ):
                    return prompt_tokens, completion_tokens

            # fallback approximation
            messages = kwargs.get("messages") or []
            input_text = ""

            for m in messages:
                if isinstance(m, dict):
                    input_text += str(m.get("content", "")) + " "

            input_tokens = self._approx_tokens(input_text)

            output_text = ""
            choices = getattr(response_obj, "choices", None)
            if choices:
                first = choices[0]
                msg = getattr(first, "message", None)

                if isinstance(msg, dict):
                    output_text = msg.get("content", "") or ""
                else:
                    output_text = getattr(msg, "content", "") or ""

            output_tokens = self._approx_tokens(output_text)

            return input_tokens, output_tokens

        except Exception:
            return 0, 0

    async def async_pre_call_hook(
        self, user_api_key_dict, cache, data: dict, call_type
    ):
        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            data["metadata"] = metadata

        request_id = metadata.get("cureforge_request_id")
        if not isinstance(request_id, str) or not request_id:
            request_id = uuid4().hex[:12]
            metadata["cureforge_request_id"] = request_id

        tool_names = self._extract_tool_names(data)
        forced_tool_choice = False
        if tool_names and not data.get("tool_choice"):
            data["tool_choice"] = "required"
            forced_tool_choice = True

        with self._request_timer_lock:
            self._request_timers[request_id] = perf_counter()

        headers = metadata.get("headers") if isinstance(metadata, dict) else {}
        agent_id = "unknown-agent"
        if isinstance(headers, dict):
            agent_id = (
                headers.get("x-agent-id") or headers.get("X-Agent-ID") or agent_id
            )

        model_name = data.get("model", "unknown-model")
        tool_list = ",".join(tool_names) if tool_names else "none"
        # _log(
        #     f"[{agent_id}] pre_call id={request_id} type={call_type} model={model_name} "
        #     f"tools={tool_list} tool_choice={data.get('tool_choice', 'unset')} "
        #     f"forced_tool_choice={forced_tool_choice}"
        # )

        return data

    def _get_elapsed_ms(self, request_id: str | None) -> str:
        if not request_id:
            return "unknown"

        with self._request_timer_lock:
            start = self._request_timers.pop(request_id, None)
        if start is None:
            return "unknown"
        return f"{(perf_counter() - start) * 1000:.2f}"

    def _print_success(self, kwargs):
        with self._success_lock:
            self._success_count += 1
            current_count = self._success_count

        agent_id = self._extract_agent_id(kwargs)
        metadata = self._extract_metadata_from_kwargs(kwargs)
        request_id = (
            metadata.get("cureforge_request_id") if isinstance(metadata, dict) else None
        )
        model_name = kwargs.get("model", "unknown-model")
        elapsed_ms = self._get_elapsed_ms(request_id)

        _log(
            f"[{agent_id}] LiteLLM success | count={current_count} id={request_id or 'unknown'} "
            f"model={model_name} elapsed_ms={elapsed_ms}"
        )

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._print_success(kwargs)

        agent_id = self._extract_agent_id(kwargs)
        tool_call_count = self._extract_tool_call_count(response_obj)
        finish_reason = self._extract_finish_reason(response_obj)

        input_tokens, output_tokens = self._extract_token_usage(kwargs, response_obj)

        _log(
            f"[{agent_id}] completion_summary finish_reason={finish_reason} "
            f"provider_tool_calls={tool_call_count} "
            f"input_tokens={input_tokens} output_tokens={output_tokens}"
        )

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self.log_success_event(kwargs, response_obj, start_time, end_time)

    def _print_failure(self, kwargs, response_obj):
        with self._success_lock:
            self._failure_count += 1
            current_failures = self._failure_count

        agent_id = self._extract_agent_id(kwargs)
        metadata = self._extract_metadata_from_kwargs(kwargs)
        request_id = (
            metadata.get("cureforge_request_id") if isinstance(metadata, dict) else None
        )
        model_name = kwargs.get("model", "unknown-model")
        elapsed_ms = self._get_elapsed_ms(request_id)
        error_text = (
            str(response_obj)[:300] if response_obj is not None else "unknown-error"
        )

        _log(
            f"[{agent_id}] LiteLLM failure | count={current_failures} id={request_id or 'unknown'} "
            f"model={model_name} elapsed_ms={elapsed_ms} error={error_text}"
        )

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        self._print_failure(kwargs, response_obj)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        self._print_failure(kwargs, response_obj)


proxy_handler = LiteLLMProxy()

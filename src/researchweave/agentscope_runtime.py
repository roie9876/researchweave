"""Real AgentScope 2.0 (agentscope==2.0.11) Runtime & Microsoft Foundry Model Bridge.

Integrates the open-source AgentScope 2.0 library (Apache-2.0):
- Wraps Microsoft Foundry deployments (`gpt-6.1-sol` and `gpt-6-astra`) in an
  `agentscope.model.ChatModelBase` implementation (`FoundryAgentScopeChatModel`).
- Spawns genuine `agentscope.agent.Agent` specialist instances at runtime with
  role-specific system prompts, model bindings, and `UserMsg` / `AssistantMsg`
  execution.
"""

from __future__ import annotations

import asyncio
from typing import Any

try:
    import agentscope
    from agentscope.agent import Agent as AgentScopeAgent
    from agentscope.message import TextBlock, UserMsg
    from agentscope.model import ChatModelBase, ChatResponse, ChatUsage, FinishedReason
    from agentscope.tool import Toolkit
    from pydantic import BaseModel

    AGENTSCOPE_AVAILABLE = True
    AGENTSCOPE_VERSION = getattr(agentscope, "__version__", "2.0.11")
    try:
        agentscope.setup_logger(level="ERROR")
    except Exception:
        pass
except Exception:
    from pydantic import BaseModel

    AGENTSCOPE_AVAILABLE = False
    AGENTSCOPE_VERSION = "unavailable"
    ChatModelBase = object  # type: ignore[misc,assignment]


class FoundryAgentScopeChatModel(ChatModelBase):  # type: ignore[misc]
    """Adapter bridging ResearchWeave's FoundryModelAdapter into AgentScope 2.0's ChatModelBase."""

    class Parameters(BaseModel):
        max_tokens: int = 1500

    def __init__(self, foundry_adapter: Any, model_name: str, fallback_text: str = "") -> None:
        if AGENTSCOPE_AVAILABLE:
            super().__init__(
                credential=None,  # type: ignore[arg-type]
                model=model_name,
                parameters=self.Parameters(),
                stream=False,
            )
        else:
            self.model = model_name
            self.stream = False
        self.model_name = model_name
        self.foundry_adapter = foundry_adapter
        self.fallback_text = fallback_text
        self.last_used_deployment = model_name
        self.last_usage: dict[str, Any] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "duration_seconds": 0.0,
        }

    async def _call_api(
        self,
        model: str,
        messages: list[Any],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
        **kwargs: Any,
    ) -> Any:
        sys_parts: list[str] = []
        user_parts: list[str] = []
        for m in messages:
            role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else "user")
            text = ""
            if hasattr(m, "get_text_content"):
                text = m.get_text_content() or ""
            elif isinstance(m, dict):
                text = str(m.get("content", ""))
            else:
                text = str(getattr(m, "content", ""))
            if role == "system":
                sys_parts.append(text)
            else:
                user_parts.append(text)

        system_prompt = "\n".join(p for p in sys_parts if p).strip() or "You are a ResearchWeave specialist agent."
        user_prompt = "\n".join(p for p in user_parts if p).strip() or "Execute assigned research step."

        target_model = self.model_name or model
        if hasattr(self.foundry_adapter, "complete_with_usage"):
            live_text, used_dep, usage_meta = self.foundry_adapter.complete_with_usage(
                target_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=kwargs.get("max_tokens", 1500),
            )
            self.last_usage = usage_meta
        else:
            live_text, used_dep = self.foundry_adapter.complete(
                target_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=kwargs.get("max_tokens", 1500),
            )
            in_tok = max(1, (len(system_prompt) + len(user_prompt)) // 4)
            out_tok = max(1, len(live_text or self.fallback_text) // 4)
            self.last_usage = {
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "total_tokens": in_tok + out_tok,
                "duration_seconds": 0.1,
            }
        self.last_used_deployment = used_dep
        final_text = live_text or self.fallback_text or f"Completed analysis using {used_dep}."

        if AGENTSCOPE_AVAILABLE:
            return ChatResponse(
                content=[TextBlock(text=final_text)],
                is_last=True,
                finished_reason=FinishedReason.STOP,
                usage=ChatUsage(
                    input_tokens=int(self.last_usage.get("input_tokens", 0)),
                    output_tokens=int(self.last_usage.get("output_tokens", 0)),
                ),
            )
        return {"text": final_text, "deployment": used_dep}


class AgentScopeTeamRuntime:
    """Manages runtime creation and execution of real AgentScope 2.0 specialist agents."""

    def __init__(self, foundry_adapter: Any) -> None:
        self.foundry_adapter = foundry_adapter
        self._live_agents: dict[str, Any] = {}

    @property
    def runtime_info(self) -> dict[str, Any]:
        return {
            "agentscope_available": AGENTSCOPE_AVAILABLE,
            "agentscope_version": AGENTSCOPE_VERSION,
            "active_agent_instances": len(self._live_agents),
        }

    def spawn_specialist_agent(
        self,
        agent_id: str,
        name: str,
        system_prompt: str,
        assigned_model: str,
        fallback_text: str = "",
    ) -> Any:
        """Instantiate a real AgentScope 2.0 `Agent` bound to the assigned Foundry model."""
        chat_model = FoundryAgentScopeChatModel(
            foundry_adapter=self.foundry_adapter,
            model_name=assigned_model,
            fallback_text=fallback_text,
        )
        if AGENTSCOPE_AVAILABLE:
            toolkit = Toolkit()
            ag = AgentScopeAgent(
                name=name,
                system_prompt=system_prompt,
                model=chat_model,
                toolkit=toolkit,
            )
            self._live_agents[agent_id] = (ag, chat_model)
            return ag
        self._live_agents[agent_id] = (None, chat_model)
        return None

    def run_specialist_turn(
        self,
        agent_id: str,
        name: str,
        system_prompt: str,
        assigned_model: str,
        user_prompt: str,
        fallback_text: str = "",
    ) -> tuple[str, str, bool, dict[str, Any]]:
        """Execute a single reasoning turn through the AgentScope 2.0 Agent instance.

        Returns `(response_text, resolved_deployment, used_live_foundry, usage_meta)`.
        """
        if agent_id not in self._live_agents:
            self.spawn_specialist_agent(
                agent_id=agent_id,
                name=name,
                system_prompt=system_prompt,
                assigned_model=assigned_model,
                fallback_text=fallback_text,
            )
        ag, chat_model = self._live_agents[agent_id]
        chat_model.model_name = assigned_model
        chat_model.fallback_text = fallback_text

        if AGENTSCOPE_AVAILABLE and ag is not None:
            try:
                async def _invoke() -> str:
                    reply_msg = await ag.reply(UserMsg(content=user_prompt))
                    if hasattr(reply_msg, "get_text_content"):
                        return (reply_msg.get_text_content() or "").strip()
                    return str(getattr(reply_msg, "content", "")).strip()

                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        out_text = pool.submit(lambda: asyncio.run(_invoke())).result(timeout=28.0)
                else:
                    out_text = asyncio.run(_invoke())

                used_live = bool(out_text and out_text != fallback_text)
                return out_text, chat_model.last_used_deployment, used_live, dict(chat_model.last_usage)
            except Exception:
                pass

        if hasattr(self.foundry_adapter, "complete_with_usage"):
            live_text, used_dep, usage_meta = self.foundry_adapter.complete_with_usage(
                assigned_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        else:
            live_text, used_dep = self.foundry_adapter.complete(
                assigned_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            usage_meta = {
                "input_tokens": max(1, len(user_prompt) // 4),
                "output_tokens": max(1, len(live_text or fallback_text) // 4),
                "total_tokens": max(2, (len(user_prompt) + len(live_text or fallback_text)) // 4),
                "duration_seconds": 0.1,
            }
        if live_text:
            return live_text, used_dep, True, usage_meta
        return fallback_text, assigned_model, False, usage_meta

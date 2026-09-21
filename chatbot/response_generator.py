"""
chatbot/response_generator.py
--------------------------------
PHASE 3 IMPLEMENTATION.

Orchestrates a single chat turn:

    screen_input() -> [crisis/block short-circuit] -> analyze_mood()
        -> OpenRouter call -> screen_output() -> [block override] -> result

This is the ONLY place these pieces are wired together — UI code
(components/chatbot_launcher.py, pages/companion.py) calls only
generate_response(), never the individual chatbot/backend modules
directly, so the safety ordering can't be accidentally bypassed by a
future UI change.

No conversation persistence happens here (or anywhere in Phase 3) — see
PHASE3_PRE_IMPLEMENTATION_AUDIT.md §6. `chat_history` is whatever the
caller already has in st.session_state; nothing is written to Supabase.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from backend.auth import AuthUser
from backend.logging_config import get_logger
from backend.openrouter_client import (
    chat_completion, chat_completion_with_tools, OpenRouterError, OpenRouterNotConfiguredError,
)
from chatbot import safety
from chatbot import tools
from chatbot.mood_analyzer import analyze_mood, DEFAULT_RESULT as DEFAULT_MOOD, MOOD_SUGGESTIONS, VALID_MOODS
from chatbot.system_prompt import get_system_prompt, get_navigator_prompt

logger = get_logger(__name__)

MAX_HISTORY_TURNS = 12  # trim like LearnMate's client did — bounds prompt size/cost


@dataclass(frozen=True)
class AgentConfig:
    """PHASE 2 (Agentic AI upgrade — shared orchestration).

    One entry per orchestrated agent. Adding a new agent — e.g. a
    future Insight Agent — means adding one new AgentConfig entry to
    AGENT_REGISTRY below. Nothing else in this module's pipeline
    (safety screening, mood analysis, the OpenRouter call, output
    screening, suggestion mapping) needs to change to support a new
    agent, since all of that is already agent-agnostic — this phase
    only formalizes prompt-selection, which was previously an inline
    if/else in _build_messages().

    This phase intentionally stops here: no tool calling, no per-agent
    tool allowlist, and no Insight Agent implementation are introduced.
    Those remain future, separately-approved phases (see the
    PHASE1_AUDIT / roadmap: this is roadmap step 2 of 9)."""
    name: str
    get_prompt: Callable[[str], str]  # (language) -> full system prompt text


AGENT_REGISTRY: dict[str, AgentConfig] = {
    "companion": AgentConfig(name="companion", get_prompt=get_system_prompt),
    "navigator": AgentConfig(name="navigator", get_prompt=get_navigator_prompt),
    # FUTURE EXTENSION POINT — NOT IMPLEMENTED IN THIS PHASE:
    #   "insight": AgentConfig(name="insight", get_prompt=get_insight_prompt),
    # chatbot/system_prompt.py has no get_insight_prompt() yet, and this
    # phase does not add one. Listed here only so the shape of a future
    # addition is unambiguous when that phase is separately approved.
}

DEFAULT_AGENT = "companion"


# ---------------------------------------------------------------------------
# PHASE 4 (Agentic AI upgrade — Companion tool-calling).
#
# chatbot/tools.py (Phase 3, unmodified) supplies TOOL_REGISTRY and
# call_tool() — the controlled, allowlisted tool layer. Everything below
# is the orchestration ON TOP of that layer: which agents may use tools
# at all, which of the six tools each agent may use, and the JSON-schema
# descriptions OpenRouter needs to actually offer them to the model.
# None of this changes chatbot/tools.py's own behavior or guarantees.
# ---------------------------------------------------------------------------

MAX_TOOL_ITERATIONS = 3

TOOL_CALLING_ENABLED: dict[str, bool] = {
    "companion": True,
    "navigator": True,  # Navigator's allowlist below is defined for future use only — inactive this phase.
}

AGENT_TOOL_ALLOWLIST: dict[str, frozenset[str]] = {
    "companion": frozenset(tools.TOOL_REGISTRY.keys()) - {"open_page"},
    "navigator": frozenset({"recommend_relaxation_activity", "recommend_resource", "find_human_support", "open_page"}),
}

TOOL_SCHEMAS: dict[str, dict] = {
    "get_user_checkins": {
        "type": "function",
        "function": {
            "name": "get_user_checkins",
            "description": (
                "Get the student's recent non-clinical mood check-ins (mood, sentiment, "
                "stress/energy/sleep levels, timestamps) to inform a supportive, "
                "context-aware reply. Never includes free-text notes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many recent check-ins to return. Default 20, maximum 50.",
                    },
                },
                "required": [],
            },
        },
    },
    "get_recent_conversation_summary": {
        "type": "function",
        "function": {
            "name": "get_recent_conversation_summary",
            "description": (
                "Get metadata only (title, message count, last-updated time) about the "
                "student's single most recent conversation with Sahay. Never returns any "
                "message content."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    "get_wellness_progress": {
        "type": "function",
        "function": {
            "name": "get_wellness_progress",
            "description": (
                "Get the student's recently completed wellness activities (which activity, "
                "when completed) from the Relaxation Center."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many recent completions to return. Default 50, maximum 100.",
                    },
                },
                "required": [],
            },
        },
    },
    "recommend_relaxation_activity": {
        "type": "function",
        "function": {
            "name": "recommend_relaxation_activity",
            "description": (
                "Recommend ONE existing relaxation activity that matches a mood. Only ever "
                "returns a real activity already available in the Relaxation Center — never "
                "invents one."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mood": {
                        "type": "string",
                        "enum": ["Angry", "Anxious", "Calm", "Happy", "Lonely",
                                 "Neutral", "Overwhelmed", "Sad", "Stressed"],
                        "description": "The student's current mood, if known.",
                    },
                },
                "required": [],
            },
        },
    },
    "recommend_resource": {
        "type": "function",
        "function": {
            "name": "recommend_resource",
            "description": (
                "Recommend ONE existing support-resource category matching a topic (e.g. "
                "'exam stress', 'sleep', 'loneliness', 'procrastination'). Only ever returns "
                "a real category already available on the Resources page — never invents one."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "A short topic or keyword to match against existing resource categories.",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    "find_human_support": {
        "type": "function",
        "function": {
            "name": "find_human_support",
            "description": (
                "Get information about existing human-support options (trusted people, "
                "campus resources, verified crisis resources) and the Human Help page. Does "
                "NOT replace the app's own deterministic crisis handling."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    "open_page": {
        "type": "function",
        "function": {
            "name": "open_page",
            "description": (
                "Suggest ONE existing page in Sahay AI the student could open next. This only "
                "prepares a suggestion — it does NOT navigate anywhere by itself. The student "
                "will see a button and must explicitly click it before any page actually changes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_key": {
                        "type": "string",
                        "enum": ["overview", "companion", "mood_checkin", "wellness_dashboard",
                                  "relaxation", "mood_history", "conversations", "resources",
                                  "government_services", "human_help", "reports", "profile",
                                  "privacy", "settings"],
                        "description": "The internal key of the page to suggest opening.",
                    },
                },
                "required": ["page_key"],
            },
        },
    },
}

_TOOL_LOOP_FALLBACK_TEXT = (
    "Sorry — I wasn't able to pull that information together just now. "
    "Let's keep talking, and I can try again in a moment."
)


def _run_tool_loop(messages: list[dict], agent: str, user: AuthUser | None) -> tuple[str, dict | None]:
    """Runs up to MAX_TOOL_ITERATIONS rounds of tool-calling for `agent`
    (only ever invoked when TOOL_CALLING_ENABLED[agent] is True — see
    generate_response()). Works on a local copy of `messages`, never the
    caller's list. Returns the final text reply only — the tool
    machinery itself never reaches generate_response()'s caller.

    Every tool call is checked against AGENT_TOOL_ALLOWLIST[agent] BEFORE
    chatbot.tools.call_tool() is ever invoked — a disallowed/unknown name
    never reaches call_tool() at all; it gets a synthetic
    {"error": "tool_not_allowed"} result instead. `user` is resolved by
    the caller from the existing session (see pages/companion.py) and
    passed straight through to call_tool(user=user, ...) — never taken
    from the model's own arguments, which have no user/user_id field to
    even attempt (see TOOL_SCHEMAS above).

    Raises the same OpenRouterNotConfiguredError/OpenRouterError as
    chat_completion_with_tools() itself — generate_response()'s existing
    except blocks (unchanged) already handle those.

    PHASE 5 (Option B — Navigator page-navigation suggestions): also
    returns `action` — {"type": "open_page", "page_key": ..., "label":
    ...} or None. Populated ONLY when chatbot.tools.call_tool() returns
    a successful, non-None result for the "open_page" tool during this
    loop — never fabricated here, never derived from the model's own
    text. Purely descriptive data: nothing in this function (or
    anywhere in chatbot/) writes st.session_state or calls st.rerun() —
    that decision belongs entirely to the UI layer, triggered only by
    an explicit student click (see components/chatbot_launcher.py). If
    open_page() succeeds more than once in one turn, the most recent
    result wins.
    """
    working_messages = list(messages)
    allowlist = AGENT_TOOL_ALLOWLIST.get(agent, frozenset())
    schemas = [TOOL_SCHEMAS[name] for name in allowlist if name in TOOL_SCHEMAS]
    pending_action: dict | None = None

    for _round in range(MAX_TOOL_ITERATIONS):
        result = chat_completion_with_tools(working_messages, tools=schemas)
        tool_calls = result.get("tool_calls") or []

        if not tool_calls:
            content = result.get("content")
            if isinstance(content, str) and content.strip():
                return content, pending_action
            break  # no tool call AND no usable content — fall through to the fallback below

        working_messages.append({"role": "assistant", "tool_calls": tool_calls})

        for call in tool_calls:
            call_id = call.get("id", "")
            fn = call.get("function") or {}
            name = fn.get("name")
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else {}
                if not isinstance(args, dict):
                    args = {}
            except (json.JSONDecodeError, TypeError):
                args = {}

            if name in allowlist:
                tool_result = tools.call_tool(name, user=user, **args)
            else:
                logger.warning(
                    "Tool call to disallowed/unknown tool %r for agent %r — call_tool() never invoked",
                    name, agent,
                )
                tool_result = {"ok": False, "tool": name, "data": None, "error": "tool_not_allowed"}

            if name == "open_page" and tool_result.get("ok") and tool_result.get("data"):
                data = tool_result["data"]
                pending_action = {"type": "open_page", "page_key": data.get("page_key"), "label": data.get("label")}

            working_messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(tool_result),
            })

    logger.info("Tool loop reached MAX_TOOL_ITERATIONS (%d) without a final reply", MAX_TOOL_ITERATIONS)
    return _TOOL_LOOP_FALLBACK_TEXT, pending_action


def generate_response(
    message: str,
    chat_history: list[dict] | None = None,
    language: str = "English",
    user_id: str | None = None,
    agent: str = "companion",
    user: AuthUser | None = None,
) -> dict:
    """Returns {"reply": str, "mood": dict, "safety_action": str, "suggestion": dict | None}.

    "suggestion", added in Phase 5, is {"activity_key": str | None, "text": str}
    or None — a pure-data hint from chatbot.mood_analyzer.MOOD_SUGGESTIONS,
    attached ONLY on a normal successful turn (never on crisis/blocked/error/
    not-configured turns, and never when the mapped mood has no suggestion
    text — e.g. Happy/Calm/Neutral). This is a UI-layer hint, not part of
    the model's own reply — chatbot/system_prompt.py is unaware of it, per
    the approved Phase 5 decision. Whether/how often to actually render it
    (avoiding repetition, allowing dismissal) is entirely a UI-layer
    decision — see components/chatbot_launcher.py / pages/companion.py.

    NEVER raises — every failure mode (misconfiguration, network error,
    malformed model output, a safety block) resolves to a friendly reply
    string, so UI code can always just display result["reply"].

    NOT LIVE-TESTED in this environment — see PHASE3_IMPLEMENTATION_REPORT.md.

    PHASE 7: `user_id`, if provided (authenticated callers only — Demo
    Mode never passes one, matching Demo Mode's existing "never touches
    Supabase" rule), causes a crisis/block outcome to be best-effort
    logged to safety_events via backend.safety_log — never blocks or
    alters the reply itself, and never logs message content (see
    backend/safety_log.py's function signature — it has no parameter
    for it).

    PHASE 1 (Agentic AI upgrade — role separation via prompts only):
    `agent` — "companion" (default) or "navigator" — selects which
    system prompt is used (chatbot/system_prompt.get_system_prompt for
    Companion, vs. get_navigator_prompt for the floating Navigator
    widget). This is the ONLY thing that changes based on `agent` —
    safety screening (input and output), mood analysis, the OpenRouter
    call itself, retry/error handling, and suggestion mapping are all
    identical for both agents, unchanged from before this parameter
    existed. An unrecognized value falls back to "companion" with a
    logged warning — this function still NEVER raises. No tool calling,
    no navigation actions, and no persistence changes are introduced by
    this parameter; that is out of scope for this phase.

    PHASE 2 (Agentic AI upgrade — shared orchestration): `agent`
    validation and prompt selection are now driven by AGENT_REGISTRY /
    AgentConfig below, instead of a flat set + inline if/else — same
    external behavior (documented above), formalized into an
    extensible registry so a future agent (e.g. Insight) can be added
    with one new registry entry rather than editing this function's
    logic. generate_companion_response() and generate_navigator_response()
    are new, additive, named wrappers around this function for that
    same purpose — no existing caller is required to use them, and
    generate_response() itself is unchanged for anyone who doesn't.
    
    PHASE 4 (Agentic AI upgrade — Companion tool-calling): `user` —
    the full backend.auth.AuthUser object, or None — is used ONLY to
    resolve which authenticated user's data chatbot.tools.call_tool()
    may read, and ONLY when TOOL_CALLING_ENABLED[agent] is True
    (Companion this phase; Navigator's tool-calling stays disabled
    regardless of what's passed here). `user` is never derived from
    the model's own output — it must come from the caller's own
    server-side session resolution (see pages/companion.py), exactly
    as `user_id` already does for safety-event logging. Passing `user`
    has NO effect on Navigator turns, and has no effect at all unless
    tool-calling is enabled for the given agent. Demo Mode (user=None)
    is unaffected: every chatbot.tools function already returns a
    neutral, empty result for user=None without touching Supabase —
    see chatbot/tools.py's Phase 3 guarantees, unchanged by this phase.

    PHASE 5 (Option B — Navigator page-navigation suggestions): the
    return dict gains one new key, "action" — either
    {"type": "open_page", "page_key": ..., "label": ...} or None.
    Populated ONLY for the Navigator agent, ONLY when its open_page
    tool successfully resolved a real, allowlisted page (see
    chatbot/tools.py: open_page(), AGENT_TOOL_ALLOWLIST above — open_page
    is explicitly excluded from Companion's allowlist). This function
    never writes st.session_state and never calls st.rerun() — "action"
    is purely descriptive data for the UI layer to render as a
    student-confirmed button (see components/chatbot_launcher.py). A
    blocked output (step 4 below) always discards any pending action.
    The existing "reply"/"mood"/"safety_action"/"suggestion" keys and
    their meanings are completely unchanged by this addition.
    """
    chat_history = chat_history or []

    if agent not in AGENT_REGISTRY:
        logger.warning("generate_response: unrecognized agent %r, defaulting to %r", agent, DEFAULT_AGENT)
        agent = DEFAULT_AGENT

    # ---- 1. Deterministic input screening — runs BEFORE any model call ----
    input_screen = safety.screen_input(message)
    if input_screen["action"] == "crisis":
        logger.info("Crisis pattern matched on input — short-circuiting to deterministic response")
        _log_safety_event_if_authenticated(user_id, input_screen["category"], "crisis")
        return {
            "reply": safety.crisis_response_text(),
            "mood": dict(DEFAULT_MOOD),
            "safety_action": "crisis",
            "suggestion": None,
            "action": None,
        }
    if input_screen["action"] == "block":
        logger.info("Blocked pattern matched on input (category=%s) — short-circuiting", input_screen["category"])
        _log_safety_event_if_authenticated(user_id, input_screen["category"], "block")
        return {
            "reply": safety.blocked_response_text(input_screen["category"]),
            "mood": dict(DEFAULT_MOOD),
            "safety_action": "block",
            "suggestion": None,
            "action": None,
        }

    # ---- 2. Non-clinical mood/sentiment/risk classification ----
    mood = analyze_mood(message, chat_history)

    # ---- 3. Model call ----
    action = None
    try:
        messages = _build_messages(message, chat_history, language, agent)
        if TOOL_CALLING_ENABLED.get(agent, False):
            reply, action = _run_tool_loop(messages, agent, user)
        else:
            reply = chat_completion(messages)
    except OpenRouterNotConfiguredError:
        logger.info("OpenRouter not configured — returning a friendly not-available message")
        return {
            "reply": (
                "Sahay's AI conversation engine isn't connected yet in this environment. "
                "Once it is, I'll be able to respond here."
            ),
            "mood": mood,
            "safety_action": "not_configured",
            "suggestion": None,
            "action": None,
        }
    except OpenRouterError as exc:
        logger.warning("OpenRouter call failed: %s", type(exc).__name__)
        return {
            "reply": str(exc),  # OpenRouterError messages are already user-safe (see openrouter_client.py)
            "mood": mood,
            "safety_action": "error",
            "suggestion": None,
            "action": None,
        }

    # ---- 4. Deterministic output screening — runs BEFORE showing the reply ----
    output_screen = safety.screen_output(reply)
    if output_screen["action"] == "block":
        logger.warning("Model output blocked by output screening (category=%s)", output_screen["category"])
        reply = safety.safe_fallback_text()
        # PHASE 5 (Option B): a blocked reply never carries a navigation
        # suggestion along with it — action is deliberately discarded here,
        # regardless of what the tool loop produced.
        return {"reply": reply, "mood": mood, "safety_action": output_screen["action"], "suggestion": None, "action": None}

    # ---- 5. Personalized wellness suggestion — data only, UI decides rendering ----
    suggestion = None
    mapped = MOOD_SUGGESTIONS.get(mood.get("mood"))
    if mapped and mapped.get("text"):
        suggestion = {"activity_key": mapped.get("activity_key"), "text": mapped["text"]}

    return {"reply": reply, "mood": mood, "safety_action": output_screen["action"], "suggestion": suggestion, "action": action}


def _log_safety_event_if_authenticated(user_id: str | None, category: str | None, action: str) -> None:
    """Only logs for authenticated callers (user_id present) — Demo Mode
    never passes a user_id, so this is a no-op there, consistent with
    Demo Mode never touching Supabase in any form. Import is local to
    avoid a module-level dependency on the service-role client for a
    module (response_generator) that's otherwise entirely
    Supabase-independent."""
    if not user_id or not category:
        return
    from backend.safety_log import log_safety_event
    log_safety_event(user_id, category, action)


def _build_messages(message: str, chat_history: list[dict], language: str, agent: str = DEFAULT_AGENT) -> list[dict]:
    trimmed = chat_history[-MAX_HISTORY_TURNS:]
    system_prompt = AGENT_REGISTRY[agent].get_prompt(language)
    messages = [{"role": "system", "content": system_prompt}]
    for turn in trimmed:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


def generate_companion_response(
    message: str,
    chat_history: list[dict] | None = None,
    language: str = "English",
    user_id: str | None = None,
) -> dict:
    """PHASE 2: named orchestration entry point for the Companion agent —
    a thin, purely additive wrapper around generate_response(...,
    agent="companion"). No existing caller uses this yet; it exists so
    future call sites (and a future Insight Agent's own equivalent
    wrapper) have a clearly-named, non-stringly-typed entry point
    instead of remembering the 'agent' string. generate_response()
    itself, and every existing call to it, is completely unaffected."""
    return generate_response(message, chat_history=chat_history, language=language, user_id=user_id, agent="companion")


def generate_navigator_response(
    message: str,
    chat_history: list[dict] | None = None,
    language: str = "English",
    user_id: str | None = None,
) -> dict:
    """PHASE 2: named orchestration entry point for the Navigator agent —
    a thin, purely additive wrapper around generate_response(...,
    agent="navigator"). Same rationale as generate_companion_response()
    above. Not called by any existing code in this phase."""
    return generate_response(message, chat_history=chat_history, language=language, user_id=user_id, agent="navigator")

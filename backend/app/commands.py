"""Command presets sent to the orchestrator (labels are i18n keys on the client)."""

from dataclasses import dataclass
from typing import Literal

Category = Literal["edit", "analyze", "create"]
ActionType = Literal["inline_edit", "chat_only", "new_document"]


@dataclass(frozen=True)
class CommandPreset:
    id: str
    i18n_key: str
    category: Category
    action_type: ActionType


COMMAND_PRESETS: list[CommandPreset] = [
    CommandPreset("improve", "commands.improve", "edit", "inline_edit"),
    CommandPreset("rephrase", "commands.rephrase", "edit", "inline_edit"),
    CommandPreset("shorten", "commands.shorten", "edit", "inline_edit"),
    CommandPreset("expand", "commands.expand", "edit", "inline_edit"),
    CommandPreset("simplify", "commands.simplify", "edit", "inline_edit"),
    CommandPreset("fix_grammar", "commands.fixGrammar", "edit", "inline_edit"),
    CommandPreset("change_tone", "commands.changeTone", "edit", "inline_edit"),
    CommandPreset("professional", "commands.professional", "edit", "inline_edit"),
    CommandPreset("friendly", "commands.friendly", "edit", "inline_edit"),
    CommandPreset("natural", "commands.natural", "edit", "inline_edit"),
    CommandPreset("academic", "commands.academic", "edit", "inline_edit"),
    CommandPreset("persuasive", "commands.persuasive", "edit", "inline_edit"),
    CommandPreset("translate", "commands.translate", "edit", "inline_edit"),
    CommandPreset("summarize", "commands.summarize", "analyze", "chat_only"),
    CommandPreset("main_ideas", "commands.mainIdeas", "analyze", "chat_only"),
    CommandPreset("keywords", "commands.keywords", "analyze", "chat_only"),
    CommandPreset("structure", "commands.structure", "analyze", "chat_only"),
    CommandPreset("find_repetitions", "commands.findRepetitions", "analyze", "chat_only"),
    CommandPreset("analyze_text", "commands.analyzeText", "analyze", "chat_only"),
    CommandPreset("create_summary", "commands.createSummary", "create", "new_document"),
    CommandPreset("create_notes", "commands.createNotes", "create", "new_document"),
    CommandPreset("create_outline", "commands.createOutline", "create", "new_document"),
    CommandPreset("create_faq", "commands.createFaq", "create", "new_document"),
    CommandPreset("create_document", "commands.createDocument", "create", "new_document"),
    CommandPreset("custom", "commands.custom", "edit", "inline_edit"),
]

PRESET_INSTRUCTIONS: dict[str, str] = {
    "fix_grammar": "Fix grammar, spelling, and punctuation. Preserve meaning and tone unless errors require minor wording changes.",
    "improve": "Improve clarity, flow, and word choice without changing the core message.",
    "shorten": "Shorten the text while keeping all important facts and intent.",
    "expand": "Expand with useful detail and smoother transitions; do not invent new facts.",
    "simplify": "Use simpler words and shorter sentences; keep the same meaning.",
    "professional": "Make the text more professional and polished for a business audience.",
    "friendly": "Make the tone warmer and more friendly while staying appropriate.",
    "natural": "Make the text sound more natural and conversational.",
    "academic": "Adjust toward formal academic style suitable for essays or papers.",
    "translate": "Translate to the target language specified in extra instructions, or English if unspecified.",
    "rephrase": "Rephrase for fresh wording while preserving meaning.",
    "change_tone": "Adjust tone according to extra user instructions.",
    "persuasive": "Make the text more convincing and compelling without adding false claims.",
    "summarize": "Write a concise summary of the document. Return analysis text only.",
    "main_ideas": "Extract the main ideas as a short bullet list. Return analysis text only.",
    "keywords": "List key terms and phrases. Return analysis text only.",
    "structure": "Describe the document structure (sections, flow). Return analysis text only.",
    "find_repetitions": "Find repeated ideas or wording and list them. Return analysis text only.",
    "analyze_text": "Analyze clarity, tone, audience fit, and weaknesses. Return analysis text only.",
    "create_summary": "Create a standalone summary document from the source text.",
    "create_notes": "Create study/work notes from the source text.",
    "create_outline": "Create a structured outline of the source text.",
    "create_faq": "Create an FAQ document based on the source text.",
    "create_document": "Create a new document based on the user's instruction and source text.",
    "custom": "Follow the user's custom instructions exactly.",
}

COMMAND_BY_ID = {c.id: c for c in COMMAND_PRESETS}

"""Rules for incorporating the current user message into recommendation context."""

import re


_APPLICATION_PROCEDURE = re.compile(
    r"\b(?:how (?:do|can|should|to) (?:i |we )?(?:fill|fill out|complete|submit|start)|"
    r"help (?:me )?(?:fill|fill out|complete|submit)|application (?:form|portal|login|"
    r"deadline|fee|fees|requirement|requirements|submission)|upload (?:a |my )?transcript)\b|"
    r"(?:怎么|如何)(?:填写|填|提交|完成)(?:UC|大学)?申请|申请(?:表|系统|截止日期|费用|材料)(?:怎么|如何)",
    re.IGNORECASE,
)
_ESSAY_SCOPE = re.compile(
    r"\b(?:PIQs?|personal insight questions?|essay prompts?|application essays?|"
    r"common app essays?|writing prompts?)\b|个人洞察|文书|题目推荐|推荐.*题",
    re.IGNORECASE,
)


USER_MESSAGE_POLICY = """

# USER MESSAGE RELEVANCE

First inspect the supplied USER MESSAGE. If it is casual conversation, unclear,
or unrelated to the selected essay-recommendation tool, do not perform the
recommendation task and do not discuss the student profile. Reply briefly and
politely that you did not understand the request and explain that this tool is
for recommending application essay prompts. Keep that reply to at most two short
sentences. Do not generate recommendations, summarize the profile, ask the user to
confirm starting an analysis, or repeat the tool description. If the message is
relevant, proceed with the recommendation task normally.

# USER-PROVIDED EXPERIENCE

Treat explicit first-person facts in the USER MESSAGE as information the student
has provided for this current answer. Do not claim that an experience is absent
or did not happen merely because it is not present in the retrieved STUDENT
EVIDENCE. Clearly distinguish the two sources: say "you mentioned" for facts from
the current message and "your documented profile says" only for retrieved facts.
Do not assign an Experience number or invented title to information supplied only
in the current message.

A brief user mention establishes only that the experience was mentioned. It does
not establish what the student did in response, whether they sought help, how the
experience ended, what coping strategies they used, or what growth, empathy, or
resilience resulted. Never borrow actions or outcomes from a different documented
experience and present them as the response to the user-mentioned experience.
Describe the evidence as incomplete until the student voluntarily supplies the
relevant non-sensitive actions and reflection. Do not label such a minimally
described experience "Evidence Strength: High" or "No major evidence gap."

If the user asks whether a sensitive experience such as depression, bullying,
grief, illness, trauma, or family conflict could be an essay topic, answer the
question directly and sensitively. Explain that suitability depends on reflection,
agency, growth, values, and what the student is comfortable disclosing—not on how
dramatic the hardship is. Do not diagnose the student, pressure them to disclose
private details, or reject the topic solely because it is absent from the stored
profile. Ask only for non-sensitive details needed to assess prompt fit. For this
kind of suitability question, the direct answer takes priority over the requested
recommendation count: do not manufacture a full ranked recommendation list unless
the user asks for one.
"""


def response_language(configured_language: str, message: str) -> str:
    """Use the current message language when it is clear in either direction."""
    chinese_count = len(re.findall(r"[\u3400-\u9fff]", message))
    latin_count = len(re.findall(r"[A-Za-z]", message))
    if chinese_count >= 2:
        return "zh"
    if chinese_count == 0 and latin_count >= 4:
        return "en"
    return configured_language


def requests_application_procedure(message: str) -> bool:
    """Identify application-form/process requests outside essay recommendation scope."""
    return bool(_APPLICATION_PROCEDURE.search(message)) and not bool(_ESSAY_SCOPE.search(message))

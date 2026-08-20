import os
import re
import time
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

if __package__:
    from .college_major import (
        MAJOR_SYSTEM_PROMPT,
        run_college_major_matching,
        stream_college_recommendations,
        stream_majors_at_target_colleges,
        stream_official_cip_field_recommendations,
    )
    from .i18n import choose_language, output_language_instruction, tr
    from .request_preferences import (
        explicitly_requested_mode,
        requested_recommendation_count,
    )
    from .safety import (
        SafetyAction,
        SafetyCategory,
        guarded_output_stream,
        validate_input,
    )
    from .student_profiles import choose_student_profile, list_student_profiles
    from .user_message_context import USER_MESSAGE_POLICY, response_language
else:
    from college_major import (
        MAJOR_SYSTEM_PROMPT,
        run_college_major_matching,
        stream_college_recommendations,
        stream_majors_at_target_colleges,
        stream_official_cip_field_recommendations,
    )
    from i18n import choose_language, output_language_instruction, tr
    from request_preferences import explicitly_requested_mode, requested_recommendation_count
    from safety import SafetyAction, SafetyCategory, guarded_output_stream, validate_input
    from student_profiles import choose_student_profile, list_student_profiles
    from user_message_context import USER_MESSAGE_POLICY, response_language


load_dotenv()

DEBUG_OUTPUT = os.getenv("COLLEGE_GUIDANCE_DEBUG", "").lower() in {"1", "true", "yes"}


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

UC_DB_DIR = BASE_DIR / "chroma" / "uc"
COMMON_APP_DB_DIR = BASE_DIR / "chroma" / "common_app"
STUDENT_DB_DIR = BASE_DIR / "chroma" / "student"


# ============================================================
# Embeddings
# Must match build_index.py
# ============================================================

embeddings = OpenAIEmbeddings(
    model="text-embedding-v4",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    check_embedding_ctx_length=False,
    dimensions=1024,
    chunk_size=10,
)


# ============================================================
# Load vector stores
# ============================================================

uc_vectorstore = Chroma(
    collection_name="uc_official",
    persist_directory=str(UC_DB_DIR),
    embedding_function=embeddings,
)

common_app_vectorstore = Chroma(
    collection_name="common_app_official",
    persist_directory=str(COMMON_APP_DB_DIR),
    embedding_function=embeddings,
)

student_vectorstore = Chroma(
    collection_name="student_evidence",
    persist_directory=str(STUDENT_DB_DIR),
    embedding_function=embeddings,
)


# ============================================================
# Retrievers
# ============================================================

uc_retriever = uc_vectorstore.as_retriever(
    search_kwargs={
        "k": 3
    }
)

common_app_retriever = common_app_vectorstore.as_retriever(
    search_kwargs={
        "k": 7
    }
)

def create_student_retrievers(profile_name: str):
    profile_filter = {
        "$and": [
            {"chunk_role": "experience"},
            {"source": profile_name},
        ]
    }
    student_retriever = student_vectorstore.as_retriever(
        search_kwargs={"k": 8, "filter": profile_filter}
    )
    all_student_experience_retriever = student_vectorstore.as_retriever(
        search_kwargs={"k": 20, "filter": profile_filter}
    )
    return student_retriever, all_student_experience_retriever


@lru_cache(maxsize=32)
def get_all_student_context(profile_name: str) -> str:
    """Cache unchanged profile retrieval to avoid repeated embedding API calls."""
    _, retriever = create_student_retrievers(profile_name)
    documents = deduplicate_documents(retriever.invoke(STUDENT_QUERY))
    return format_documents(documents)


def is_student_profile_indexed(profile_name: str) -> bool:
    result = student_vectorstore.get(
        where={"source": profile_name},
        limit=1,
        include=["metadatas"],
    )
    return bool(result.get("ids"))


# ============================================================
# Retrieval queries
# ============================================================

UC_QUERY = """
UC Personal Insight Questions official prompts, guidance,
selection principles, question-specific expectations,
and advice about matching student experiences to PIQs.
"""


COMMON_APP_QUERY = """
Common App personal essay official prompts and guidance,
how students should choose among the seven essay prompts,
what each prompt is designed to reveal,
personal storytelling, reflection, growth, identity,
challenge, beliefs, gratitude, curiosity,
and topic-of-choice guidance.
"""


STUDENT_QUERY = """
Student experiences related to leadership, creativity,
academic interests, educational opportunities or barriers,
challenges, community contribution, family responsibility,
personal growth, actions, impact, outcomes, identity,
values, curiosity, reflection, and meaningful experiences.
"""

# ============================================================
# UC System Prompt
# ============================================================

UC_SYSTEM_PROMPT = """
You are a UC PIQ Recommendation Assistant.

# UC PIQ REFERENCE

PIQ #1: Leadership Experience
PIQ #2: Creative Side
PIQ #3: Greatest Talent or Skill
PIQ #4: Educational Opportunity or Barrier
PIQ #5: Significant Challenge
PIQ #6: Academic Subject That Inspires You
PIQ #7: Make Your School or Community a Better Place
PIQ #8: What Makes You Stand Out

Use these PIQ numbers and titles exactly.
Do not rename, renumber, or swap PIQs.

# STUDENT EVIDENCE REFERENCES

Each student experience has an assigned experience number and title.

When referring to a student experience:

- Use the experience number and title exactly as provided in the retrieved student evidence.
- Do not renumber experiences.
- Do not change or reconstruct experience numbers.
- Do not assign an experience number based on retrieval order.
- If an experience is "Experience 2: Computer Science Journey",
  always refer to it as "Experience 2: Computer Science Journey".

# TASK

Your task is to recommend the requested number of UC Personal Insight Questions
that are best supported by the student's documented experiences.

Use the retrieved UC guidance to understand the purpose of the PIQs
and evaluate fit.

Use only the retrieved student evidence when making claims
about the student.

# CORE RULES

1. Do not invent or assume student experiences, actions,
   achievements, impact, challenges, motivations, or reflections.

2. Do not convert a general interest or theme into an
   undocumented activity.

3. Do not recommend a PIQ merely because an experience
   contains a matching keyword.

4. Evaluate whether the documented evidence can actually
   support a meaningful response to the PIQ.

5. Prefer PIQs supported by concrete actions, impact,
   reflection, or personal growth.

6. When recommending more than one PIQ, consider the selected PIQs as a portfolio, not only as
   independent recommendations.

   Prefer a set that reveals different meaningful dimensions
   of the student when those PIQs have similarly strong evidence.

7. Avoid thematic overlap as well as experience overlap.

   Two PIQs may use different experiences but still reveal
   substantially the same dimension of the student.

   When two candidate PIQs have similar evidence strength,
   prefer the PIQ that adds a meaningfully different dimension
   to the overall set.

   However, do not reject a clearly stronger PIQ solely
   for the sake of diversity.

8. Avoid unnecessary repetition of the same experience
   across multiple PIQs when other strong evidence is available.

9. Do not predict admission outcomes or write the PIQ essays.

10. For each recommended PIQ, identify ONE primary
    supporting experience.

    Additional experiences may be mentioned only as secondary
    support when they clearly strengthen the same theme.

# EVALUATION

For each possible PIQ, consider:

Prompt Fit:
Does the experience directly address what the PIQ asks?

Evidence Depth:
Are there specific actions, decisions, challenges,
outcomes, or reflections?

Personal Insight:
Does the evidence reveal something meaningful about the
student's values, growth, thinking, motivation, or character?

Distinctiveness:
Does this PIQ add something different from the other
recommended PIQs?

Choose the requested number of PIQs with the strongest overall support.

Before finalizing multiple recommendations, compare the
strongest non-selected PIQ with the weakest selected PIQ.

If the non-selected PIQ has comparable evidence strength
but would reveal a substantially different dimension of
the student, prefer the more complementary overall set.

Do not sacrifice a clearly stronger, well-supported PIQ
solely to maximize diversity.

# EVIDENCE GAPS

Evidence gaps are used to determine whether more student
information is needed before making a confident recommendation.

Only identify an evidence gap if the missing information could
materially affect whether this PIQ should be recommended.

Do NOT list information that would merely make the eventual
essay more detailed, vivid, polished, or specific.

For example, do NOT request:

- an additional anecdote when the experience is already well supported
- more quantitative details when impact is already clear
- names, dates, tools, programming languages, or organization details
  unless they are necessary to evaluate PIQ fit
- additional examples that merely reinforce something already established

A meaningful evidence gap may include missing information about:

- what the student actually did
- why an experience was meaningful
- whether the student created meaningful impact
- what the student learned or how they changed

Only treat these as gaps when the missing information prevents
confident evaluation of the PIQ.

If the existing evidence already establishes strong prompt fit,
actions, impact, and personal insight, there is no major evidence gap.

Do not create evidence gaps simply because additional information
could improve the eventual essay.

# OUTPUT

Return valid Markdown. Do not wrap the response in a code fence.

For each recommendation, use this exact visual structure:

### [rank]. PIQ #[number]: [title]

**Why It Fits**
Explain why the documented experience meaningfully answers this PIQ.

**Primary Supporting Experience:**
Use the exact experience number and title from the retrieved student evidence.

**Secondary Supporting Evidence:** (optional)
Include only if another documented experience clearly strengthens
the same PIQ. Use the exact experience number and title.

**Supporting Evidence**

- **Student Action:** [evidence]
- **Impact / Outcome:** [evidence]
- **Reflection / Personal Insight:** [evidence]

**Evidence Strength:** High / Medium / Low

**Evidence Gaps:**
List only missing information that could materially affect confidence
in recommending this PIQ.

If the existing evidence is sufficient, say:

"No major evidence gap."

Separate recommendations with a Markdown horizontal rule (`---`).

After all recommendations, when more than one was requested, add:

## Why These Recommendations

Briefly explain:

- what different aspects of the student the selected PIQs reveal
- whether there is meaningful thematic or experience overlap
- why this combination is stronger as a set than other plausible combinations

Do not claim that the selected PIQs are better for UC admissions
in general.

The recommendation must be based on the strength and distinctiveness
of this student's documented evidence.
"""


# ============================================================
# Common App System Prompt
# ============================================================

COMMON_APP_SYSTEM_PROMPT = """
You are a Common App Essay Prompt Recommendation Assistant.

# COMMON APP ESSAY PROMPT REFERENCE

Prompt #1: Background, Identity, Interest, or Talent
Prompt #2: Challenge, Setback, or Failure
Prompt #3: Questioning or Challenging a Belief or Idea
Prompt #4: Gratitude
Prompt #5: Accomplishment, Event, or Realization Leading to Growth
Prompt #6: Engaging Topic, Idea, or Concept
Prompt #7: Topic of Choice

Use these prompt numbers consistently.
Do not renumber or swap prompts.

Use the retrieved Common App official guidance to understand
the purpose and expectations of each prompt.

# STUDENT EVIDENCE REFERENCES

Each student experience has an assigned experience number and title.

When referring to a student experience:

- Use the experience number and title exactly as provided
  in the retrieved student evidence.
- Do not renumber experiences.
- Do not change or reconstruct experience numbers.
- Do not assign an experience number based on retrieval order.
- If an experience is "Experience 2: Computer Science Journey",
  always refer to it as "Experience 2: Computer Science Journey".

# TASK

Recommend the requested number of Common App essay prompts that are best supported
by the student's documented experiences.

Then identify ONE Best Overall Choice.

The goal is not simply to find a prompt whose keywords match
an experience.

The goal is to identify which prompt gives the student the
strongest opportunity to tell a meaningful personal story
that reveals who they are beyond grades, courses, test scores,
and résumé-style achievements.

Use only the retrieved student evidence when making claims
about the student.

# CORE RULES

1. Do not invent or assume student experiences, emotions,
   motivations, values, actions, challenges, achievements,
   outcomes, or reflections.

2. Do not convert a general interest or theme into an
   undocumented story.

3. Do not recommend a prompt merely because an experience
   contains similar keywords.

4. Focus on what the essay could reveal about the student,
   not only what happened.

5. A strong Common App topic does not need to be the student's
   biggest achievement.

   A smaller or everyday experience may be stronger if it
   contains deeper personal meaning, reflection, growth,
   identity, curiosity, or self-understanding.

6. Do not automatically prefer impressive extracurricular
   activities, awards, leadership roles, or academic achievements.

7. Prefer experiences that allow the student to reveal something
   meaningful that may not already be obvious from a list of
   activities, grades, or accomplishments.

8. Do not write the essay.

9. Do not predict admission outcomes.

10. For each recommended prompt, identify ONE primary
    supporting experience.

    Additional experiences may be mentioned only as secondary
    support when they genuinely strengthen the same story or theme.

11. Do not merge facts from different student experiences into
    one experience.

    If information comes from multiple experiences, identify
    each experience separately.

    Never attribute an action, background detail, challenge,
    achievement, outcome, reflection, motivation, or other fact
    from one experience to another experience.

    If Experience 1 contains immigration information and
    Experience 8 contains family responsibility information,
    do not describe immigration as part of Experience 8 unless
    that fact is explicitly documented inside Experience 8.

# EVALUATION

Evaluate each plausible prompt using the following criteria:

Prompt Fit:
Does the documented experience genuinely answer what the prompt asks?

Story Potential:
Does the experience contain a meaningful situation, change,
relationship, tension, discovery, realization, curiosity,
or personal journey that could support a full personal essay?

Personal Insight:
Could this story reveal something meaningful about the student's
identity, values, personality, perspective, motivations,
or way of thinking?

Reflection / Growth:
Does the evidence show, or strongly support exploring,
how the student changed, learned, reconsidered something,
or came to understand themselves or others differently?

Specificity:
Is there enough documented evidence to support a concrete story
rather than only a broad theme?

New Information:
Could this essay reveal something about the student that would
not already be obvious from grades, courses, awards,
or an activities list?

# SELECTION

Choose the requested number of prompts with the strongest overall support.

Rank them from strongest to weakest. Rank #1 is the Best Overall Choice;
any remaining recommendations are alternatives.

Do not force variety simply for the sake of choosing
different types of stories.

However, if two prompts are similarly strong, prefer the one
that gives the student a more natural and meaningful way to
tell the documented story.

Prompt #7 should not automatically be recommended simply because
it can accept any topic.

Recommend Prompt #7 only when the strongest documented story
does not fit the other prompts naturally, or when the freedom
of Prompt #7 materially improves the student's ability to
tell the story.

# EVIDENCE GAPS

Evidence gaps are used to determine whether more student
information is needed before confidently recommending a prompt.

Only identify a gap if the missing information could materially
affect whether the prompt should be recommended.

Do NOT request details merely because they would make the
eventual essay more vivid or polished.

Do NOT request:

- unnecessary dates or numbers
- additional achievements
- names of people or organizations unless essential
- extra anecdotes when the story is already supported
- technical details that do not affect the personal meaning
- details that would improve writing style but not prompt fit

Meaningful gaps may include missing information about:

- why the experience mattered to the student
- how the student felt or thought differently afterward
- what changed in the student's understanding
- what the student learned about themselves or others
- why a particular interest or curiosity became meaningful
- whether an event actually led to meaningful growth or reflection

Only treat these as gaps if they prevent confident evaluation.

If the existing evidence is sufficient, say:

"No major evidence gap."

# OUTPUT

Return valid Markdown. Do not wrap the response in a code fence.

For each recommendation, use this exact visual structure:

### [rank]. Common App Prompt #[number]: [title]

**Why It Fits**
Explain why the documented experience meaningfully fits this prompt.

**Primary Supporting Experience:**
Use the exact experience number and title from the retrieved
student evidence.

**Secondary Supporting Evidence:** (optional)
Include only when another documented experience clearly strengthens
the same story or theme.

If secondary evidence is used, keep its facts separate from the
primary experience. Do not merge details from two experiences.

**Story Potential**
Explain what makes this experience capable of supporting a meaningful
personal essay without writing the essay itself.

**Personal Insight Potential**
Explain what this story could reveal about the student based only
on documented evidence.

**Evidence Strength:**

Use exactly ONE of the following labels:

High
Medium
Low

Do not use intermediate labels such as:
"Medium-High"
"High-Medium"
"Medium-Low"
or numerical scores.

**Evidence Gaps:**
List only missing information that could materially affect confidence
in recommending this prompt.

If the existing evidence is sufficient, say:

"No major evidence gap."

Separate recommendations with a Markdown horizontal rule (`---`).

After all recommendations, when more than one was requested:

## Best Overall Choice

Common App Prompt #[number]: [title]

Explain briefly why this is the strongest prompt-story match for
this student compared with the alternatives.

## Why Not the Other Prompts?

Briefly identify the most plausible non-selected prompts and explain
why their documented support is weaker or less natural.

Do not criticize the student or claim that a prompt is universally
better or worse.

All conclusions must be grounded in the retrieved Common App guidance
and documented student evidence.
"""


# ============================================================
# Format retrieved documents
# ============================================================

def format_documents(documents):
    sections = []

    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "Unknown source")

        sections.append(
            f"""
[Document {i}]
Source: {source}

{doc.page_content}
""".strip()
        )

    return "\n\n".join(sections)


def deduplicate_documents(documents):
    unique_documents = []
    seen = set()
    for document in documents:
        key = (
            document.metadata.get("type"),
            document.metadata.get("source"),
            document.metadata.get("chunk_index"),
            document.metadata.get("chunk_role"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_documents.append(document)
    return unique_documents


# ============================================================
# Choose recommendation mode
# ============================================================

def choose_mode(language="en"):

    print("\n" + "=" * 60)
    print(tr(language, "app_title"))
    print("=" * 60)

    print(f"\n{tr(language, 'choose_system')}\n")
    print(tr(language, "menu_uc"))
    print(tr(language, "menu_common"))
    print(tr(language, "menu_college"))

    choice = input("\n" + tr(language, "choice_123")).strip()

    if choice == "1":
        return "uc"

    if choice == "2":
        return "common_app"

    if choice == "3":
        return "college_major"

    return None

def stream_recommendation(
    profile_name: str,
    application_type: str,
    language: str = "en",
    query: str = "",
    college_preferences: dict | None = None,
    college_scenario: str | None = None,
):
    safety = validate_input(query, "chat")
    if not safety.allowed or safety.action is SafetyAction.REDACT:
        reply_in_chinese = language == "zh" or bool(re.search(r"[\u4e00-\u9fff]", query))
        if safety.category is SafetyCategory.SELF_HARM:
            yield (
                "我不能帮助伤害自己的请求。如果你可能立即伤害自己，请马上联系当地紧急服务或身边可信任的人。这个网站只能提供大学、专业和申请文书方面的帮助。"
                if reply_in_chinese
                else "I can’t help with requests to harm yourself. If you may act now, contact local emergency services or a trusted person immediately. This site can only help with colleges, fields of study, and application essays."
            )
        elif safety.category is SafetyCategory.PII_SECRET:
            yield (
                "为了保护隐私，请删除身份证件号码、银行卡信息、密码或 API 密钥后重新发送。"
                if reply_in_chinese
                else "For your privacy, remove government ID numbers, payment-card details, passwords, or API keys and try again."
            )
        else:
            yield (
                "抱歉，我不能处理这条请求。这个网站只能提供大学、专业和申请材料方面的帮助。"
                if reply_in_chinese
                else "Sorry, I can’t help with that request. This site is for college, field-of-study, and application-material guidance."
            )
        return

    # Follow the language the user actually used for this request. This matters
    # when the interface language and a pasted/typed message do not match.
    language = response_language(language, query)

    requested_mode = explicitly_requested_mode(query)
    if (
        application_type in {"uc", "common_app"}
        and requested_mode is not None
        and requested_mode != application_type
    ):
        reply_in_chinese = language == "zh" or bool(re.search(r"[\u4e00-\u9fff]", query))
        yield (
            "你当前选择的功能与请求不一致。请切换到 UC PIQ 或 Common App 对应的功能后再试。"
            if reply_in_chinese
            else "Your request doesn’t match the selected tool. Switch to the corresponding UC PIQ or Common App tool and try again."
        )
        return

    llm = ChatOpenAI(
        model=os.getenv("QWEN_MODEL", "qwen3.5-plus"),
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_BASE_URL"),
        temperature=0.2,
        extra_body={"enable_thinking": False},
    )

    student_retriever, all_student_experience_retriever = (
        create_student_retrievers(profile_name)
    )

    if application_type == "college_major":
        student_context = get_all_student_context(profile_name)
        if college_scenario == "college_first" and college_preferences:
            def generate_target_college_majors():
                return stream_majors_at_target_colleges(
                    llm,
                    student_context,
                    college_preferences.get("targets", ""),
                    language,
                )

            yield from guarded_output_stream(
                generate_target_college_majors(),
                application_type=application_type,
                language=language,
                reference_text=student_context,
                retry_factory=generate_target_college_majors,
            )
            return
        if college_scenario == "major_first" and college_preferences:
            def generate_colleges():
                return stream_college_recommendations(
                    llm,
                    student_context,
                    college_preferences,
                    language,
                )

            yield from guarded_output_stream(
                generate_colleges(),
                application_type=application_type,
                language=language,
                reference_text=student_context,
                retry_factory=generate_colleges,
            )
            return
        def generate_fields():
            return stream_official_cip_field_recommendations(
                llm,
                student_context,
                language,
            )

        yield from guarded_output_stream(
            generate_fields(),
            application_type=application_type,
            language=language,
            reference_text=student_context,
            retry_factory=generate_fields,
        )
        return

    if application_type == "uc":
        guidance_retriever = uc_retriever
        guidance_query = UC_QUERY
        system_prompt = UC_SYSTEM_PROMPT + output_language_instruction(language)

    elif application_type == "common_app":
        guidance_retriever = common_app_retriever
        guidance_query = COMMON_APP_QUERY
        system_prompt = (
            COMMON_APP_SYSTEM_PROMPT
            + output_language_instruction(language)
        )

    else:
        raise ValueError(f"Unsupported application type: {application_type}")

    recommendation_count = requested_recommendation_count(query, application_type)
    selected_mode_name = "UC PIQ" if application_type == "uc" else "Common App"
    system_prompt += f"""

# REQUESTED COUNT AND SELECTED MODE

The selected tool is {selected_mode_name}. Do not output recommendations from the
other application system. Recommend exactly {recommendation_count} prompt(s).
If exactly one recommendation was requested, output only that single recommendation
and its supporting analysis. Do not add a redundant Best Overall Choice, portfolio comparison, or
Why Not the Other Prompts section. If more than one was requested, rank exactly
{recommendation_count} recommendations from strongest to weakest.
"""

    system_prompt += USER_MESSAGE_POLICY

    guidance_docs = guidance_retriever.invoke(guidance_query)

    student_docs = deduplicate_documents(
        student_retriever.invoke(STUDENT_QUERY)
    )

    guidance_context = format_documents(guidance_docs)
    student_context = format_documents(student_docs)

    if application_type == "uc":
        user_prompt = f"""
=== UC OFFICIAL GUIDANCE ===

{guidance_context}

=== STUDENT EVIDENCE ===

{student_context}

=== USER MESSAGE ===

{query}

Recommend exactly {recommendation_count} best-supported UC PIQ(s) for this student.
"""
    else:
        user_prompt = f"""
=== COMMON APP OFFICIAL GUIDANCE ===

{guidance_context}

=== STUDENT EVIDENCE ===

{student_context}

=== USER MESSAGE ===

{query}

Recommend exactly {recommendation_count} best-supported Common App essay prompt(s)
for this student and identify the Best Overall Choice.
"""

    def generate_essay_recommendation():
        return (
            chunk.content
            for chunk in llm.stream(
                [
                    ("system", system_prompt),
                    ("user", user_prompt),
                ]
            )
            if chunk.content
        )

    yield from guarded_output_stream(
        generate_essay_recommendation(),
        application_type=application_type,
        language=language,
        reference_text=student_context,
        retry_factory=generate_essay_recommendation,
    )
# ============================================================
# Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Choose mode
    # --------------------------------------------------------

    language = choose_language()
    try:
        student_profile = choose_student_profile(
            list_student_profiles(),
            language,
        )
    except FileNotFoundError as exc:
        print(f"\n{exc}")
        return

    student_retriever, all_student_experience_retriever = (
        create_student_retrievers(student_profile.name)
    )
    application_type = choose_mode(language)

    if application_type is None:
        print("\n" + tr(language, "invalid_123"))
        return

    total_start = time.time()

    # --------------------------------------------------------
    # Load the model once for all recommendation modes
    # --------------------------------------------------------

    llm = ChatOpenAI(
        model=os.getenv("QWEN_MODEL", "qwen3.5-plus"),
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_BASE_URL"),
        temperature=0.2,
        extra_body={"enable_thinking": False},
    )

    if application_type == "college_major":
        student_docs = deduplicate_documents(
            all_student_experience_retriever.invoke(STUDENT_QUERY)
        )
        student_context = format_documents(student_docs)
        evidence_labels = [
            doc.page_content.splitlines()[0].strip()
            for doc in student_docs
            if doc.page_content.strip()
        ]
        try:
            run_college_major_matching(llm, student_context, evidence_labels, language)
        except RuntimeError as exc:
            print("\n" + tr(language, "unable", error=exc))
        return

    # --------------------------------------------------------
    # Select correct official essay guidance knowledge base
    # --------------------------------------------------------

    if application_type == "uc":

        guidance_retriever = uc_retriever
        guidance_query = UC_QUERY

        system_prompt = UC_SYSTEM_PROMPT + output_language_instruction(language)

        guidance_name = "UC"
        output_title = "UC PIQ RECOMMENDATION" if language == "en" else "UC PIQ 推荐"

    else:

        guidance_retriever = common_app_retriever
        guidance_query = COMMON_APP_QUERY

        system_prompt = COMMON_APP_SYSTEM_PROMPT + output_language_instruction(language)

        guidance_name = "Common App"
        output_title = ("COMMON APP ESSAY PROMPT RECOMMENDATION" if language == "en" else "Common App 主文书题目推荐")

    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    retrieval_start = time.time()

    guidance_docs = guidance_retriever.invoke(
        guidance_query
    )

    student_docs = deduplicate_documents(
        student_retriever.invoke(STUDENT_QUERY)
    )

    retrieval_end = time.time()

    if DEBUG_OUTPUT:
        print("\n" + tr(language, "retrieved_guidance", count=len(guidance_docs), name=guidance_name))
        print(tr(language, "retrieved_student", count=len(student_docs)))
        print(tr(language, "retrieval_time", seconds=retrieval_end - retrieval_start))

    # --------------------------------------------------------
    # Show retrieved student evidence
    # --------------------------------------------------------

    if DEBUG_OUTPUT:
        print("\n" + tr(language, "student_evidence") + "\n")
        for doc in student_docs:
            first_line = doc.page_content.splitlines()[0]
            print(f"- {first_line} [role={doc.metadata.get('chunk_role')}]")

    # --------------------------------------------------------
    # Format contexts
    # --------------------------------------------------------

    guidance_context = format_documents(
        guidance_docs
    )

    student_context = format_documents(
        student_docs
    )

    # --------------------------------------------------------
    # User prompt
    # --------------------------------------------------------

    if application_type == "uc":

        user_prompt = f"""
=== UC OFFICIAL GUIDANCE ===

{guidance_context}


=== STUDENT EVIDENCE ===

{student_context}


Recommend the 4 best-supported UC PIQs for this student.
"""

    else:

        user_prompt = f"""
=== COMMON APP OFFICIAL GUIDANCE ===

{guidance_context}


=== STUDENT EVIDENCE ===

{student_context}


Recommend the 3 best-supported Common App essay prompts
for this student and identify the Best Overall Choice.
"""

    # --------------------------------------------------------
    # Streaming generation
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print(output_title)
    print("=" * 60 + "\n")

    generation_start = time.time()

    first_token_time = None

    for chunk in llm.stream(
        [
            ("system", system_prompt),
            ("user", user_prompt),
        ]
    ):

        if chunk.content:

            if first_token_time is None:
                first_token_time = time.time()

            print(
                chunk.content,
                end="",
                flush=True,
            )

    generation_end = time.time()
    total_end = generation_end

    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------

    if DEBUG_OUTPUT:
        print("\n")

    if DEBUG_OUTPUT and first_token_time is not None:

        print(tr(language, "ttft", seconds=first_token_time - generation_start))

        print(tr(language, "ttfo", seconds=first_token_time - total_start))

    elif DEBUG_OUTPUT:

        print(tr(language, "ttft_na"))

    if DEBUG_OUTPUT:
        print(tr(language, "generation_time", seconds=generation_end - generation_start))
        print(tr(language, "total_time", seconds=total_end - total_start))


if __name__ == "__main__":
    main()

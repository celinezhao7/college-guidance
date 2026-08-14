import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from college_major import run_college_major_matching
from i18n import choose_language, output_language_instruction, tr


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

student_retriever = student_vectorstore.as_retriever(
    search_kwargs={
        "k": 8,
        "filter": {
            "chunk_role": "experience"
        }
    }
)

all_student_experience_retriever = student_vectorstore.as_retriever(
    search_kwargs={
        "k": 20,
        "filter": {
            "chunk_role": "experience"
        }
    }
)


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

Your task is to recommend the 4 UC Personal Insight Questions
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

6. Consider the four PIQs as a portfolio, not only as four
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

Choose the 4 PIQs with the strongest overall support.

Before finalizing the four recommendations, compare the
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

For each recommendation:

PIQ #[number]: [title]

Why It Fits:
Explain why the documented experience meaningfully answers this PIQ.

Primary Supporting Experience:
Use the exact experience number and title from the retrieved student evidence.

Secondary Supporting Evidence (optional):
Include only if another documented experience clearly strengthens
the same PIQ. Use the exact experience number and title.

Supporting Evidence:
- Student Action:
- Impact / Outcome:
- Reflection / Personal Insight:

Evidence Strength:
High / Medium / Low

Evidence Gaps:
List only missing information that could materially affect confidence
in recommending this PIQ.

If the existing evidence is sufficient, say:

"No major evidence gap."

After all four recommendations:

Why These Four:

Briefly explain:

- what different aspects of the student these four PIQs reveal
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

Recommend the 3 Common App essay prompts that are best supported
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

Choose the 3 prompts with the strongest overall support.

Rank them:

1. Best Overall Choice
2. Strong Alternative
3. Additional Alternative

Do not force variety simply for the sake of choosing
three different types of stories.

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

For each of the 3 recommendations:

Rank #[number]

Common App Prompt #[number]: [title]

Why It Fits:
Explain why the documented experience meaningfully fits this prompt.

Primary Supporting Experience:
Use the exact experience number and title from the retrieved
student evidence.

Secondary Supporting Evidence (optional):
Include only when another documented experience clearly strengthens
the same story or theme.

If secondary evidence is used, keep its facts separate from the
primary experience. Do not merge details from two experiences.

Story Potential:
Explain what makes this experience capable of supporting a meaningful
personal essay without writing the essay itself.

Personal Insight Potential:
Explain what this story could reveal about the student based only
on documented evidence.

Evidence Strength:

Use exactly ONE of the following labels:

High
Medium
Low

Do not use intermediate labels such as:
"Medium-High"
"High-Medium"
"Medium-Low"
or numerical scores.

Evidence Gaps:
List only missing information that could materially affect confidence
in recommending this prompt.

If the existing evidence is sufficient, say:

"No major evidence gap."

After all three recommendations:

# Best Overall Choice

Common App Prompt #[number]: [title]

Explain briefly why this is the strongest prompt-story match for
this student compared with the alternatives.

# Why Not the Other Prompts?

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


# ============================================================
# Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Choose mode
    # --------------------------------------------------------

    language = choose_language()
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
        output_title = ("COMMON APP ESSAY PROMPT RECOMMENDATION" if language == "en" else "COMMON APP 主文书题目推荐")

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

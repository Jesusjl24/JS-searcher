"""
Claude-powered media bias analysis.
Classifies sources and generates overall diet diagnostics.
"""

import json
import logging
from anthropic import Anthropic
from config import CLAUDE_CONFIG, get_anthropic_api_key

logger = logging.getLogger(__name__)


def _get_client() -> Anthropic:
    key = get_anthropic_api_key()
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=key)


# ---------------------------------------------------------------------------
# Source classification
# ---------------------------------------------------------------------------

SOURCE_PROMPT = """You are a media bias analyst. Analyze the following list of social media accounts,
YouTube channels, subreddits, news outlets, or websites that a person follows online.

For EACH source, return a JSON object with exactly these fields:
- "source": the source name as given
- "platform": "twitter" | "youtube" | "reddit" | "website" | "podcast" | "other"
- "type": "news_outlet" | "commentary" | "entertainment" | "education" | "satire" | "person" | "community" | "other"
- "political_leaning_score": float from -10 (far left) to +10 (far right), 0 = non-political or truly centrist
- "political_label": "Far Left" | "Left" | "Center-Left" | "Center" | "Center-Right" | "Right" | "Far Right" | "Non-Political"
- "content_categories": array of 1-3 strings from this list: ["News & Politics", "Technology", "Science & Education", "Entertainment", "Sports", "Business & Finance", "Health & Wellness", "Arts & Culture", "Gaming", "Opinion & Commentary", "Satire", "Lifestyle"]
- "reliability": "high" | "medium" | "low" | "unknown"
- "known_for": 3-5 word summary of what this source is known for
- "description": one sentence about this source's content and stance

Return a JSON array — one object per source, in the same order as the input.
If you don't recognise a source, use your best judgment from the name and context.

Sources to analyse:
{sources_block}"""


def classify_sources(sources: list[dict]) -> list[dict]:
    """
    Send sources to Claude Haiku for per-source bias classification.
    Returns the original sources with 'analysis' key added to each.
    """
    client = _get_client()
    model = CLAUDE_CONFIG["source_analysis_model"]
    batch_size = CLAUDE_CONFIG["max_sources_per_batch"]

    results = []
    for i in range(0, len(sources), batch_size):
        batch = sources[i : i + batch_size]
        sources_block = "\n".join(
            f"{j+1}. {s.get('display', s['name'])} [platform: {s.get('platform','unknown')}]"
            for j, s in enumerate(batch)
        )
        prompt = SOURCE_PROMPT.format(sources_block=sources_block)

        try:
            resp = client.messages.create(
                model=model,
                max_tokens=CLAUDE_CONFIG["max_tokens_source"],
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            analyses = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in source classification: {e}\nRaw: {raw[:500]}")
            analyses = [_fallback_analysis(s) for s in batch]
        except Exception as e:
            logger.error(f"Claude API error during source classification: {e}")
            analyses = [_fallback_analysis(s) for s in batch]

        for src, analysis in zip(batch, analyses):
            enriched = src.copy()
            enriched["analysis"] = analysis
            results.append(enriched)

    return results


def _fallback_analysis(source: dict) -> dict:
    return {
        "source": source["name"],
        "platform": source.get("platform", "unknown"),
        "type": "other",
        "political_leaning_score": 0,
        "political_label": "Center",
        "content_categories": ["News & Politics"],
        "reliability": "unknown",
        "known_for": "unknown source",
        "description": "Could not analyze this source.",
    }


# ---------------------------------------------------------------------------
# Overall diet analysis
# ---------------------------------------------------------------------------

DIET_PROMPT = """You are a media diet analyst. Based on the following per-source analyses of a user's
internet following, generate a comprehensive media diet diagnostic report.

Source analyses (JSON):
{analyses_json}

Return a single JSON object with exactly these fields:
- "overall_bias_score": float -10 to +10 (weighted average across sources)
- "overall_bias_label": string label for their overall diet lean
- "echo_chamber_score": integer 0-100 (higher = more of an echo chamber)
- "diversity_grade": "A" | "B" | "C" | "D" | "F"
- "political_distribution": object with keys "Far Left", "Left", "Center-Left", "Center", "Center-Right", "Right", "Far Right", "Non-Political" and integer counts
- "content_distribution": object mapping content category strings to integer source counts
- "reliability_distribution": object with keys "high", "medium", "low", "unknown" and counts
- "dominant_topics": array of 5 strings — the main topics this user is exposed to
- "blind_spots": array of 4 strings — important perspectives or topics they are NOT getting
- "what_you_see_more_of": array of 3 strings — what their feed over-indexes on
- "key_insights": array of 3 strings — notable observations about this specific diet
- "recommendations": array of 5 objects each with "source" (specific name) and "reason" (one sentence why) to balance their diet
- "summary": 2-3 sentence narrative summary of their media diet

Be specific and data-driven. Reference actual sources from the analysis where relevant."""


def analyze_diet(classified_sources: list[dict]) -> dict:
    """
    Send all classified sources to Claude Sonnet for an overall diet diagnosis.
    Returns the diet analysis dict.
    """
    client = _get_client()
    model = CLAUDE_CONFIG["diet_analysis_model"]

    analyses = [s["analysis"] for s in classified_sources]
    prompt = DIET_PROMPT.format(analyses_json=json.dumps(analyses, indent=2))

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=CLAUDE_CONFIG["max_tokens_diet"],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in diet analysis: {e}\nRaw: {raw[:500]}")
        return _fallback_diet(classified_sources)
    except Exception as e:
        logger.error(f"Claude API error during diet analysis: {e}")
        return _fallback_diet(classified_sources)


def _fallback_diet(classified_sources: list[dict]) -> dict:
    return {
        "overall_bias_score": 0,
        "overall_bias_label": "Unable to determine",
        "echo_chamber_score": 50,
        "diversity_grade": "C",
        "political_distribution": {},
        "content_distribution": {},
        "reliability_distribution": {},
        "dominant_topics": [],
        "blind_spots": ["Analysis failed — please check your API key and try again."],
        "what_you_see_more_of": [],
        "key_insights": ["Analysis incomplete due to an API error."],
        "recommendations": [],
        "summary": "Analysis could not be completed. Please verify your ANTHROPIC_API_KEY.",
    }


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

DEMO_CLASSIFIED = [
    {"name": "@CNN", "platform": "twitter", "display": "@CNN", "analysis": {"source": "@CNN", "platform": "twitter", "type": "news_outlet", "political_leaning_score": -2.5, "political_label": "Center-Left", "content_categories": ["News & Politics"], "reliability": "high", "known_for": "Breaking US news", "description": "Major US cable news network with a center-left editorial leaning."}},
    {"name": "@FoxNews", "platform": "twitter", "display": "@FoxNews", "analysis": {"source": "@FoxNews", "platform": "twitter", "type": "news_outlet", "political_leaning_score": 4.5, "political_label": "Right", "content_categories": ["News & Politics", "Opinion & Commentary"], "reliability": "medium", "known_for": "Conservative US news", "description": "US cable news network with a right-leaning editorial stance."}},
    {"name": "r/worldnews", "platform": "reddit", "display": "r/worldnews", "analysis": {"source": "r/worldnews", "platform": "reddit", "type": "community", "political_leaning_score": -1.5, "political_label": "Center-Left", "content_categories": ["News & Politics"], "reliability": "medium", "known_for": "Global news discussion", "description": "Large Reddit community for international news with a slight center-left lean."}},
    {"name": "r/technology", "platform": "reddit", "display": "r/technology", "analysis": {"source": "r/technology", "platform": "reddit", "type": "community", "political_leaning_score": -1.0, "political_label": "Center-Left", "content_categories": ["Technology"], "reliability": "medium", "known_for": "Tech news and debate", "description": "Reddit community for technology news, with progressive-leaning discussions."}},
    {"name": "@NYTimes", "platform": "twitter", "display": "@NYTimes", "analysis": {"source": "@NYTimes", "platform": "twitter", "type": "news_outlet", "political_leaning_score": -2.0, "political_label": "Center-Left", "content_categories": ["News & Politics", "Arts & Culture"], "reliability": "high", "known_for": "Journalism of record", "description": "Prestigious US newspaper with center-left editorial positions."}},
    {"name": "@elonmusk", "platform": "twitter", "display": "@elonmusk", "analysis": {"source": "@elonmusk", "platform": "twitter", "type": "person", "political_leaning_score": 3.0, "political_label": "Center-Right", "content_categories": ["Technology", "Opinion & Commentary"], "reliability": "medium", "known_for": "Tech billionaire commentary", "description": "CEO of Tesla/SpaceX/X with increasingly right-leaning public commentary."}},
    {"name": "Veritasium", "platform": "youtube", "display": "Veritasium", "analysis": {"source": "Veritasium", "platform": "youtube", "type": "education", "political_leaning_score": 0.0, "political_label": "Non-Political", "content_categories": ["Science & Education"], "reliability": "high", "known_for": "Science explainer videos", "description": "Popular YouTube channel covering physics, science, and engineering with no political bias."}},
    {"name": "r/Conservative", "platform": "reddit", "display": "r/Conservative", "analysis": {"source": "r/Conservative", "platform": "reddit", "type": "community", "political_leaning_score": 6.5, "political_label": "Right", "content_categories": ["News & Politics", "Opinion & Commentary"], "reliability": "low", "known_for": "US right-wing politics", "description": "Reddit community for conservative political discussion, often partisan."}},
    {"name": "@TheGuardian", "platform": "twitter", "display": "@TheGuardian", "analysis": {"source": "@TheGuardian", "platform": "twitter", "type": "news_outlet", "political_leaning_score": -3.0, "political_label": "Left", "content_categories": ["News & Politics", "Arts & Culture"], "reliability": "high", "known_for": "Progressive UK journalism", "description": "Major UK newspaper with a left-of-center editorial stance."}},
    {"name": "r/nba", "platform": "reddit", "display": "r/nba", "analysis": {"source": "r/nba", "platform": "reddit", "type": "community", "political_leaning_score": 0.0, "political_label": "Non-Political", "content_categories": ["Sports"], "reliability": "high", "known_for": "Basketball discussion", "description": "Reddit's largest NBA community focused on basketball news and discussion."}},
]

DEMO_DIET = {
    "overall_bias_score": -0.9,
    "overall_bias_label": "Slightly Left-Leaning",
    "echo_chamber_score": 42,
    "diversity_grade": "B",
    "political_distribution": {"Far Left": 0, "Left": 2, "Center-Left": 3, "Center": 1, "Center-Right": 2, "Right": 2, "Far Right": 0, "Non-Political": 2},
    "content_distribution": {"News & Politics": 7, "Technology": 3, "Science & Education": 1, "Sports": 1, "Opinion & Commentary": 3, "Arts & Culture": 2},
    "reliability_distribution": {"high": 5, "medium": 3, "low": 1, "unknown": 1},
    "dominant_topics": ["US Politics", "Tech Industry", "International News", "Social Media", "Sports"],
    "blind_spots": [
        "Very little local or community-level news",
        "No dedicated business or financial news sources",
        "Science and health coverage is limited to one channel",
        "Far-right and far-left perspectives are both underrepresented for full context",
    ],
    "what_you_see_more_of": [
        "Center-left framing of political events",
        "Twitter/X-centric news cycle and hot takes",
        "US-centric world view with limited global south perspectives",
    ],
    "key_insights": [
        "Your feed has more balance than most — you follow both CNN and Fox News.",
        "Reddit subs skew slightly left; the inclusion of r/Conservative adds balance.",
        "Non-political content (Veritasium, r/nba) makes up 20% of your sources — healthy.",
    ],
    "recommendations": [
        {"source": "Reuters (@Reuters)", "reason": "Wire service with the highest neutrality rating — great counterbalance to opinion-heavy sources."},
        {"source": "r/finance", "reason": "Your feed lacks business and financial perspectives that affect everyday decisions."},
        {"source": "@AP (Associated Press)", "reason": "Fact-focused reporting with minimal editorial slant to ground your news consumption."},
        {"source": "DW News (YouTube)", "reason": "German public broadcaster provides a non-US, non-UK perspective on world events."},
        {"source": "r/science", "reason": "Peer-reviewed science discussion to complement Veritasium's popular science approach."},
    ],
    "summary": (
        "Your media diet leans slightly left-of-center with reasonable diversity across the political spectrum. "
        "You follow high-reliability sources like the NYT and Guardian balanced by right-leaning Fox News, giving you broader coverage than most. "
        "Key gaps include local news, financial media, and non-Western perspectives."
    ),
}

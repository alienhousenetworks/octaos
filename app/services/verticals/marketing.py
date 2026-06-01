from sqlalchemy.orm import Session
from app.models.verticals import ContentPost
from app.services.llm_gateway import LLMGateway
import re as _re

_MARKDOWN_STRIP = _re.compile(
    r'^(#{1,4}\s|Visual Suggestion|Image Suggestion|Caption:|Hook:|Content:|CTA:|'
    r'Call-to-Action:|Option [A-Z]:|---|\*\*\*)',
    _re.IGNORECASE
)

def _clean_post_content(text: str) -> str:
    """Strip markdown headers, copywriter labels, and bold/italic markers."""
    lines = []
    for line in text.split("\n"):
        if _MARKDOWN_STRIP.match(line.strip()):
            continue
        line = _re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', line)
        lines.append(line)
    result = "\n".join(lines).strip()
    return _re.sub(r'\n{3,}', '\n\n', result)

class MarketingService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def generate_post(self, topic: str, platform: str = "linkedin"):
        if platform == "instagram":
            system_prompt = (
                "You are a professional Instagram content creator. "
                "Output ONLY the exact post text — copy-paste ready. "
                "Format: hook sentence, 3-5 punchy body lines with emojis, CTA, blank line, 15-25 hashtags. "
                "NO markdown, NO section labels, NO 'Visual Suggestion' lines."
            )
        elif platform == "facebook":
            system_prompt = (
                "You are a professional Facebook content creator. "
                "Output ONLY the exact post text — copy-paste ready. "
                "Format: 2-3 hook sentences, 2-3 value sentences, CTA, 5-10 hashtags. "
                "NO markdown, NO section labels."
            )
        elif platform == "linkedin":
            system_prompt = (
                "You are a professional LinkedIn content creator. "
                "Output ONLY the exact post text — copy-paste ready. "
                "Format: bold opening (no emoji), 4-6 short insight lines, professional CTA, 3-5 hashtags. "
                "NO markdown headers, NO section labels."
            )
        else:
            system_prompt = (
                f"You are a social media expert for {platform}. "
                "Write ONLY the exact post text — no markdown, no section labels. Copy-paste ready."
            )

        prompt = (
            f"Write a high-engagement {platform} post about: {topic}.\n"
            "Follow the output format in your instructions exactly. "
            "Output only the post text, nothing else."
        )

        content = await self.llm.complete(prompt, system_prompt=system_prompt)
        content = _clean_post_content(content)

        post = ContentPost(
            tenant_id=self.tenant_id,
            platform=platform,
            content=content,
            status="draft"
        )
        self.db.add(post)
        self.db.commit()
        return post

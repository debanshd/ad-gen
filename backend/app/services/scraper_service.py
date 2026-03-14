import httpx
from bs4 import BeautifulSoup
import logging
from app.ai.gemini import GeminiService
from app.models.brand import BrandDNA

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self, gemini: GeminiService):
        self.gemini = gemini

    async def scrape_brand_dna(self, url: str) -> BrandDNA:
        """Fetch URL, extract text, and use Gemini to get BrandDNA."""
        if not url:
            return BrandDNA(
                tone_of_voice="professional and neutral",
                target_demographic="general audience",
                core_messaging="high-quality products and services"
            )

        try:
            logger.info(f"Scraping Brand DNA from: {url}")
            headers = {"User-Agent": "GenflowAdStudio/2.0"}
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0, headers=headers) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

            soup = BeautifulSoup(html, "html.parser")
            # Remove scripts and styles
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()

            text = soup.get_text(separator=" ", strip=True)
            # Limit text to reasonable length for Gemini
            text = " ".join(text.split())[:10000]

            dna_dict = await self.gemini.extract_brand_dna(text)
            logger.info(f"Successfully extracted Brand DNA for {url}")
            return BrandDNA(**dna_dict)
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            # Return a safe default if scraping fails
            return BrandDNA(
                tone_of_voice="professional and neutral",
                target_demographic="general audience",
                core_messaging="high-quality products and services"
            )

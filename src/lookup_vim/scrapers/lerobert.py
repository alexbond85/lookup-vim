"""Le Robert dictionary scraper implementation

This module handles three types of dictionary lookups:

1. Simple word (e.g., "chat", "manger"):
   - Direct fetch from /definition/word
   - Page contains definitions, examples, combinations
   - Returns WordResult immediately

2. Conjugated form with inflection page (e.g., "mangeais"):
   - Fetch /definition/mangeais -> inflection page (no definitions, has conj-link)
   - Follow conj-link to /conjugaison/manger -> conjugation page
   - Extract def-link from conjugation page
   - Fetch /definition/manger -> definition page
   - Returns WordResult for base verb "manger"

3. Conjugation page directly (e.g., direct lookup redirects to /conjugaison/word):
   - URL contains '/conjugaison/'
   - Returns ConjugationResult with conjugation info
"""

import logging
import re

import requests
from bs4 import BeautifulSoup, Tag

from lookup_vim.constants import BASE_URL, DEFAULT_TIMEOUT
from lookup_vim.models import ConjugationResult, Definition, WordResult

logger = logging.getLogger(__name__)


class LeRobertFetcher:
    """Handles HTTP requests for Le Robert dictionary"""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        logger.debug(f"Initialized LeRobertFetcher with timeout={timeout}s")

    def fetch_html(self, url: str) -> tuple[BeautifulSoup, str]:
        """Fetch HTML from URL and parse with BeautifulSoup"""
        try:
            response = requests.get(
                url, timeout=self.timeout, allow_redirects=True
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError("Word not found in dictionary") from None
            raise
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch: {e}") from e

        soup = BeautifulSoup(response.content, "lxml")
        return soup, response.url


def _clean_text(text: str) -> str:
    """Clean extracted text by removing artifacts"""
    if not text:
        return text

    text = re.sub(
        r"Votre navigateur ne prend pas en charge l\'audio\.?", "", text
    )
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


class DefinitionParser:
    """Parses definition pages from Le Robert dictionary"""

    def parse(
        self,
        soup: BeautifulSoup,
        url: str,
        word: str,
        original_word: str | None = None,
    ) -> WordResult:
        """Parse definition page and return WordResult"""
        definitions = self._extract_definitions(soup)
        examples = self._extract_examples(soup)
        combinations = self._extract_combinations(soup)

        return WordResult(
            word=word,
            url=url,
            original_word=original_word or word,
            definitions=definitions,
            usage_examples=examples,
            word_combinations=combinations,
        )

    def _extract_definitions(self, soup: BeautifulSoup) -> list[Definition]:
        """Extract word definitions from page"""
        definitions: list[Definition] = []

        def_section = soup.find("section", class_="def")
        if not def_section or not isinstance(def_section, Tag):
            return definitions

        def_blocks = def_section.find_all("div", class_="b", recursive=False)

        for block in def_blocks:
            category = self._extract_category(block)
            def_items = self._find_definition_items(block)

            for item in def_items:
                dfn_elem = item.find("span", class_="d_dfn")
                if not dfn_elem:
                    continue

                definition_text = _clean_text(
                    dfn_elem.get_text(separator=" ", strip=True)
                )
                examples = self._extract_definition_examples(item)

                definitions.append(
                    Definition(
                        category=category,
                        definition=definition_text,
                        examples=examples,
                    )
                )

        return definitions

    def _extract_category(self, block) -> str:
        """Extract word category from definition block"""
        category_elem = block.find("span", class_="d_cat")
        return (
            _clean_text(category_elem.get_text(separator=" ", strip=True))
            if category_elem
            else ""
        )

    def _find_definition_items(self, block: Tag) -> list[Tag]:
        """Find definition items in block"""
        def_items = block.find_all("div", class_="d_dvn")
        if not def_items:
            def_items = block.find_all("div", class_="d_ptma")
        return list(def_items)

    def _extract_definition_examples(self, item: Tag) -> list[str]:
        """Extract examples from a definition item"""
        examples = []
        xpl_elems = item.find_all("span", class_="d_xpl")

        for xpl in xpl_elems:
            for unwanted in xpl.find_all(
                ["span"], class_=["d_gls", "d_sound_cont", "d_mtb", "d_lca"]
            ):
                unwanted.decompose()

            example_text = _clean_text(xpl.get_text(separator=" ", strip=True))
            if (
                example_text
                and len(example_text) > 5
                and not example_text.startswith("locution")
            ):
                examples.append(example_text)

        return examples

    def _extract_examples(self, soup: BeautifulSoup) -> list[str]:
        """Extract usage examples from page"""
        examples: list[str] = []

        ex_section = soup.find("section", class_="ex", id="exemples")
        if not ex_section or not isinstance(ex_section, Tag):
            return examples

        example_divs = ex_section.find_all("div", class_="ex_example")

        for div in example_divs:
            author_elem = div.find("a", class_="ex_author")
            if author_elem:
                author_elem.decompose()

            text = _clean_text(div.get_text(separator=" ", strip=True))
            if text and len(text) > 10:
                examples.append(text)

        return examples[:20]

    def _extract_combinations(self, soup: BeautifulSoup) -> list[str]:
        """Extract word combinations from page"""
        combinations: list[str] = []

        collo_section = soup.find("section", class_="collo", id="collos")
        if not collo_section or not isinstance(collo_section, Tag):
            return combinations

        combo_links = collo_section.find_all("div", class_="collolink")

        for link_div in combo_links:
            link = link_div.find("a")
            if not link:
                continue

            text = _clean_text(link.get_text(separator=" ", strip=True))
            if text and len(text) > 3:
                combinations.append(text)

        return combinations[:30]


class ConjugationParser:
    """Parses conjugation pages from Le Robert dictionary"""

    def parse(
        self, soup: BeautifulSoup, url: str, original_word: str
    ) -> ConjugationResult:
        """Parse conjugation page and return ConjugationResult"""
        base_form = self.extract_base_verb(soup) or original_word
        definition_url = self.extract_definition_url(soup)
        conjugations = self._extract_present_conjugations(soup)
        message = f"The word '{original_word}' is a conjugated form of '{base_form}'. Full conjugation table available at the URL."

        return ConjugationResult(
            original_word=original_word,
            redirected_to=base_form,
            url=url,
            definition_url=definition_url,
            conjugations_sample=conjugations,
            message=message,
        )

    def has_conjugation_link(self, soup: BeautifulSoup) -> bool:
        """Check if page has conjugation redirect link"""
        return soup.find("div", class_="conj-link") is not None

    def extract_base_verb(self, soup: BeautifulSoup) -> str:
        """Extract base verb from conjugation page"""
        lemme_elem = soup.find("span", class_="conj_lemme")
        if lemme_elem:
            return _clean_text(lemme_elem.get_text(strip=True))
        return ""

    def extract_conjugation_url(self, soup: BeautifulSoup) -> str:
        """Extract conjugation URL from page"""
        conj_link_div = soup.find("div", class_="conj-link")
        if not conj_link_div or not isinstance(conj_link_div, Tag):
            return ""

        conj_link = conj_link_div.find("a", href=True)
        if not conj_link or not isinstance(conj_link, Tag):
            return ""

        url = conj_link.get("href")
        if isinstance(url, str) and url.startswith("/"):
            return f"https://dictionnaire.lerobert.com{url}"
        return str(url) if url else ""

    def extract_definition_url(self, soup: BeautifulSoup) -> str:
        """Extract definition URL from conjugation page"""
        def_link_elem = soup.find("div", class_="def-link")
        if not def_link_elem or not isinstance(def_link_elem, Tag):
            return ""

        link = def_link_elem.find("a", href=True)
        if not link or not isinstance(link, Tag):
            return ""

        url = link.get("href")
        if isinstance(url, str) and url.startswith("/"):
            return f"https://dictionnaire.lerobert.com{url}"
        return str(url) if url else ""

    def _extract_present_conjugations(
        self, soup: BeautifulSoup
    ) -> dict[str, list[str]]:
        """Extract present tense conjugations sample"""
        conjugations: dict[str, list[str]] = {}
        present_section = soup.find("h4", string="présent")

        if not present_section:
            return conjugations

        parent = present_section.find_parent("div", class_="b")
        if not parent:
            return conjugations

        forms = []
        for p in parent.find_all("p"):
            form_text = _clean_text(p.get_text(strip=True))
            if form_text:
                forms.append(form_text)

        if forms:
            conjugations["présent"] = forms

        return conjugations


class LeRobertParser:
    """Main parser dispatcher for Le Robert dictionary pages"""

    def __init__(self):
        self.definition_parser = DefinitionParser()
        self.conjugation_parser = ConjugationParser()

    def parse(
        self,
        soup: BeautifulSoup,
        url: str,
        word: str,
        original_word: str | None = None,
    ) -> WordResult | ConjugationResult:
        """Parse dictionary page and return appropriate result"""
        if self._is_conjugation_page(url):
            return self.conjugation_parser.parse(
                soup, url, original_word or word
            )
        return self.definition_parser.parse(soup, url, word, original_word)

    def _is_conjugation_page(self, url: str) -> bool:
        """Check if URL is a conjugation page"""
        return "/conjugaison/" in url

    def has_conjugation_link(self, soup: BeautifulSoup) -> bool:
        """Check if page has conjugation redirect link"""
        return self.conjugation_parser.has_conjugation_link(soup)

    def extract_base_verb(self, soup: BeautifulSoup) -> str:
        """Extract base verb from conjugation page"""
        return self.conjugation_parser.extract_base_verb(soup)

    def extract_conjugation_url(self, soup: BeautifulSoup) -> str:
        """Extract conjugation URL from page"""
        return self.conjugation_parser.extract_conjugation_url(soup)

    def extract_definition_url(self, soup: BeautifulSoup) -> str:
        """Extract definition URL from conjugation page"""
        return self.conjugation_parser.extract_definition_url(soup)


class LeRobertScraper:
    """Main scraper interface for Le Robert dictionary (implements Scraper protocol)

    Orchestrates fetching and parsing to handle three cases:
    - Simple words: direct definition page
    - Conjugated forms: follows redirect chain through conjugation page to definition
    - Conjugation pages: returns conjugation information
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.fetcher = LeRobertFetcher(timeout)
        self.parser = LeRobertParser()
        logger.debug(f"Initialized LeRobertScraper with timeout={timeout}s")

    def fetch(self, word: str) -> WordResult | ConjugationResult:
        """
        Fetch dictionary definition for a word.

        Automatically follows redirects for conjugated forms (e.g., "mangeais" -> "manger").

        Args:
            word: The word to look up

        Returns:
            WordResult or ConjugationResult: Word definition with original_word preserved

        Raises:
            ValueError: If word not found (HTTP 404)
            requests.RequestException: For network errors
        """
        logger.debug(f"Fetching definition for: {word}")
        original_word = word
        url = f"{BASE_URL}/{word}"
        soup, final_url = self.fetcher.fetch_html(url)
        logger.debug(f"Fetched URL: {final_url}")

        # Check if we need to follow conjugation redirect (inflection page case)
        if self.parser.has_conjugation_link(soup):
            soup, final_url, base_verb = self._follow_conjugation_redirect(
                soup, word
            )
            return self.parser.parse(soup, final_url, base_verb, original_word)

        return self.parser.parse(soup, final_url, word)

    def fetch_conjugation(self, word: str) -> ConjugationResult:
        """
        Fetch conjugation information for a word.

        Args:
            word: The word to get conjugations for

        Returns:
            ConjugationResult: Conjugation table and information

        Raises:
            ValueError: If word not found (HTTP 404)
            requests.RequestException: For network errors
        """
        logger.debug(f"Fetching conjugation for: {word}")

        # First get the base form if it's a conjugated word
        definition_result = self.fetch(word)
        if isinstance(definition_result, ConjugationResult):
            # Already on conjugation page
            return definition_result
        base_verb = definition_result.word

        # Fetch the conjugation page
        conj_url = f"https://dictionnaire.lerobert.com/conjugaison/{base_verb}"
        soup, final_url = self.fetcher.fetch_html(conj_url)

        return self.parser.conjugation_parser.parse(soup, final_url, word)

    def _follow_conjugation_redirect(
        self, soup: BeautifulSoup, original_word: str
    ) -> tuple[BeautifulSoup, str, str]:
        """Follow conjugation link to get base verb definition"""
        conj_url = self.parser.extract_conjugation_url(soup)
        if not conj_url:
            return soup, "", original_word

        conj_soup, _ = self.fetcher.fetch_html(conj_url)

        def_url = self.parser.extract_definition_url(conj_soup)
        if not def_url:
            return soup, "", original_word

        def_soup, final_url = self.fetcher.fetch_html(def_url)
        base_verb = self.parser.extract_base_verb(conj_soup) or original_word

        return def_soup, final_url, base_verb


if __name__ == "__main__":
    scraper = LeRobertScraper()

    print("=" * 60)
    print("COMMAND: Definition")
    print("=" * 60)

    # Example 1: Simple word
    print("\n1. Looking up 'manger':")
    try:
        result = scraper.fetch("manger")
        if isinstance(result, WordResult):
            print(f"   Word: {result.word}")
            print(f"   Original search: {result.original_word}")
            print(f"   Definitions: {len(result.definitions)}")
            print(f"   First: {result.definitions[0].definition[:80]}...")
    except (ValueError, requests.RequestException) as e:
        print(f"   Error: {e}")

    # Example 2: Conjugated form (auto-redirects to base verb)
    print("\n2. Looking up 'mangeais' (conjugated form):")
    try:
        result = scraper.fetch("mangeais")
        if isinstance(result, WordResult):
            print(f"   Word: {result.word}")
            print(f"   Original search: {result.original_word}")
            print(f"   Definitions: {len(result.definitions)}")
            print("   -> Automatically resolved to base verb!")
    except (ValueError, requests.RequestException) as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 60)
    print("COMMAND: Conjugation")
    print("=" * 60)

    # Example 3: Get conjugation table
    print("\n3. Getting conjugations for 'mangeais':")
    try:
        conj_result = scraper.fetch_conjugation("mangeais")
        print(f"   Original word: {conj_result.original_word}")
        print(f"   Base form: {conj_result.redirected_to}")
        print(f"   Message: {conj_result.message}")
        print(
            f"   Présent conjugations: {conj_result.conjugations_sample.get('présent', [])[:3]}..."
        )
        print(f"   Full table at: {conj_result.url}")
    except (ValueError, requests.RequestException) as e:
        print(f"   Error: {e}")

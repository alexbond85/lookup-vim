from robert_dict.scrapers.lerobert import LeRobertScraper


class DictionaryService:
    """Service for looking up word definitions and conjugations"""

    def __init__(self, scraper: LeRobertScraper):
        self.scraper = scraper

    def lookup_word(self, word: str) -> str:
        result = self.scraper.fetch(word)
        return result

    def lookup_conjugation(self, word: str) -> str:
        result = self.scraper.fetch_conjugation(word)
        return result

from robert_dict.scrapers.base import Scraper
from robert_dict.printers.base import Printer


class DictionaryService:

    def __init__(self, scraper: Scraper, printer: Printer):
        self.scraper = scraper
        self.printer = printer
    
    def lookup(self, word: str) -> str:
        result = self.scraper.fetch(word)
        return self.printer.print(result)


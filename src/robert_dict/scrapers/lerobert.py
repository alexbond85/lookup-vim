"""Le Robert dictionary scraper implementation"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Union, List, Dict, Any

from robert_dict.models import WordResult, Definition, ConjugationResult


BASE_URL = "https://dictionnaire.lerobert.com/definition"


class LeRobertScraper:
    """Scraper for Le Robert online dictionary"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def fetch(self, word: str) -> Union[WordResult, ConjugationResult]:
        """
        Fetch dictionary information for a word.
        
        Args:
            word: The word to look up
            
        Returns:
            WordResult or ConjugationResult
            
        Raises:
            ValueError: If word not found
            requests.RequestException: For network errors
        """
        url = f"{BASE_URL}/{word}"
        soup, final_url = self._fetch_html(url)
        
        # Detect page type and handle accordingly
        if self._is_conjugation_page(final_url):
            return self._handle_conjugation_page(soup, final_url, word)
        
        # Check if conjugated form with redirect needed
        if self._has_conjugation_link(soup):
            soup, final_url, word = self._follow_conjugation_redirect(soup, word)
        
        # Extract standard definition data
        definitions = self._extract_definitions(soup)
        examples = self._extract_examples(soup)
        combinations = self._extract_combinations(soup)
        
        return WordResult(
            word=word,
            url=final_url,
            original_word=word,
            definitions=definitions,
            usage_examples=examples,
            word_combinations=combinations
        )
    
    def _fetch_html(self, url: str) -> tuple[BeautifulSoup, str]:
        """Fetch HTML from URL and parse with BeautifulSoup"""
        try:
            response = requests.get(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Word not found in dictionary")
            raise
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch: {e}")
        
        soup = BeautifulSoup(response.content, 'lxml')
        return soup, response.url
    
    def _is_conjugation_page(self, url: str) -> bool:
        """Check if URL is a conjugation page"""
        return '/conjugaison/' in url
    
    def _has_conjugation_link(self, soup: BeautifulSoup) -> bool:
        """Check if page has conjugation redirect link"""
        return soup.find('div', class_='conj-link') is not None
    
    def _follow_conjugation_redirect(
        self, 
        soup: BeautifulSoup, 
        original_word: str
    ) -> tuple[BeautifulSoup, str, str]:
        """Follow conjugation link to get base verb definition"""
        conj_link_div = soup.find('div', class_='conj-link')
        conj_link = conj_link_div.find('a', href=True)
        
        if not conj_link:
            return soup, "", original_word
        
        # Get conjugation URL
        conj_url = conj_link.get('href')
        if conj_url.startswith('/'):
            conj_url = f"https://dictionnaire.lerobert.com{conj_url}"
        
        # Fetch conjugation page
        conj_soup, _ = self._fetch_html(conj_url)
        
        # Find definition link
        def_link_elem = conj_soup.find('div', class_='def-link')
        if not def_link_elem:
            return soup, "", original_word
        
        link = def_link_elem.find('a', href=True)
        if not link:
            return soup, "", original_word
        
        # Get definition URL
        def_url = link.get('href')
        if def_url.startswith('/'):
            def_url = f"https://dictionnaire.lerobert.com{def_url}"
        
        # Fetch definition page
        def_soup, final_url = self._fetch_html(def_url)
        
        # Extract base verb
        lemme_elem = conj_soup.find('span', class_='conj_lemme')
        base_verb = self._clean_text(lemme_elem.get_text(strip=True)) if lemme_elem else original_word
        
        return def_soup, final_url, base_verb
    
    def _handle_conjugation_page(
        self, 
        soup: BeautifulSoup, 
        url: str, 
        original_word: str
    ) -> ConjugationResult:
        """Handle conjugation page redirect"""
        # Extract base form
        lemme_elem = soup.find('span', class_='conj_lemme')
        base_form = self._clean_text(lemme_elem.get_text(strip=True)) if lemme_elem else original_word
        
        # Find definition link
        definition_url = None
        def_link_elem = soup.find('div', class_='def-link')
        if def_link_elem:
            link = def_link_elem.find('a')
            if link and link.get('href'):
                definition_url = f"https://dictionnaire.lerobert.com{link.get('href')}"
        
        # Extract present tense conjugations
        conjugations = self._extract_present_conjugations(soup)
        
        message = f"The word '{original_word}' is a conjugated form of '{base_form}'. Full conjugation table available at the URL."
        
        return ConjugationResult(
            original_word=original_word,
            redirected_to=base_form,
            url=url,
            definition_url=definition_url,
            conjugations_sample=conjugations,
            message=message
        )
    
    def _extract_present_conjugations(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract present tense conjugations sample"""
        conjugations = {}
        present_section = soup.find('h4', string='présent')
        
        if not present_section:
            return conjugations
        
        parent = present_section.find_parent('div', class_='b')
        if not parent:
            return conjugations
        
        forms = []
        for p in parent.find_all('p'):
            form_text = self._clean_text(p.get_text(strip=True))
            if form_text:
                forms.append(form_text)
        
        if forms:
            conjugations['présent'] = forms
        
        return conjugations
    
    def _extract_definitions(self, soup: BeautifulSoup) -> List[Definition]:
        """Extract definitions with fallback to v1"""
        try:
            return self._extract_definitions_v1(soup)
        except Exception:
            # Placeholder for future v2 fallback
            return []
    
    def _extract_definitions_v1(self, soup: BeautifulSoup) -> List[Definition]:
        """Extract word definitions from page (version 1)"""
        definitions = []
        
        def_section = soup.find('section', class_='def')
        if not def_section:
            return definitions
        
        def_blocks = def_section.find_all('div', class_='b', recursive=False)
        
        for block in def_blocks:
            category = self._extract_category(block)
            def_items = self._find_definition_items(block)
            
            for item in def_items:
                dfn_elem = item.find('span', class_='d_dfn')
                if not dfn_elem:
                    continue
                
                definition_text = self._clean_text(dfn_elem.get_text(separator=' ', strip=True))
                examples = self._extract_definition_examples(item)
                
                definitions.append(Definition(
                    category=category,
                    definition=definition_text,
                    examples=examples
                ))
        
        return definitions
    
    def _extract_category(self, block) -> str:
        """Extract word category from definition block"""
        category_elem = block.find('span', class_='d_cat')
        return self._clean_text(category_elem.get_text(separator=' ', strip=True)) if category_elem else ""
    
    def _find_definition_items(self, block) -> List:
        """Find definition items in block"""
        def_items = block.find_all('div', class_='d_dvn')
        if not def_items:
            def_items = block.find_all('div', class_='d_ptma')
        return def_items
    
    def _extract_definition_examples(self, item) -> List[str]:
        """Extract examples from a definition item"""
        examples = []
        xpl_elems = item.find_all('span', class_='d_xpl')
        
        for xpl in xpl_elems:
            # Remove unwanted nested elements
            for unwanted in xpl.find_all(['span'], class_=['d_gls', 'd_sound_cont', 'd_mtb', 'd_lca']):
                unwanted.decompose()
            
            example_text = self._clean_text(xpl.get_text(separator=' ', strip=True))
            if self._is_valid_example(example_text):
                examples.append(example_text)
        
        return examples
    
    def _is_valid_example(self, text: str) -> bool:
        """Check if example text is valid"""
        return text and len(text) > 5 and not text.startswith('locution')
    
    def _extract_examples(self, soup: BeautifulSoup) -> List[str]:
        """Extract usage examples with fallback"""
        try:
            return self._extract_examples_v1(soup)
        except Exception:
            return []
    
    def _extract_examples_v1(self, soup: BeautifulSoup) -> List[str]:
        """Extract usage examples from page (version 1)"""
        examples = []
        
        ex_section = soup.find('section', class_='ex', id='exemples')
        if not ex_section:
            return examples
        
        example_divs = ex_section.find_all('div', class_='ex_example')
        
        for div in example_divs:
            # Remove author attribution
            author_elem = div.find('a', class_='ex_author')
            if author_elem:
                author_elem.decompose()
            
            text = self._clean_text(div.get_text(separator=' ', strip=True))
            if text and len(text) > 10:
                examples.append(text)
        
        return examples[:20]
    
    def _extract_combinations(self, soup: BeautifulSoup) -> List[str]:
        """Extract word combinations with fallback"""
        try:
            return self._extract_combinations_v1(soup)
        except Exception:
            return []
    
    def _extract_combinations_v1(self, soup: BeautifulSoup) -> List[str]:
        """Extract word combinations (version 1)"""
        combinations = []
        
        collo_section = soup.find('section', class_='collo', id='collos')
        if not collo_section:
            return combinations
        
        combo_links = collo_section.find_all('div', class_='collolink')
        
        for link_div in combo_links:
            link = link_div.find('a')
            if not link:
                continue
            
            text = self._clean_text(link.get_text(separator=' ', strip=True))
            if text and len(text) > 3:
                combinations.append(text)
        
        return combinations[:30]
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing artifacts"""
        if not text:
            return text
        
        # Remove audio player artifacts
        text = re.sub(r'Votre navigateur ne prend pas en charge l\'audio\.?', '', text)
        
        # Remove invisible Unicode characters
        text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text


"""Web scraping functions for Le Robert dictionary"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any


BASE_URL = "https://dictionnaire.lerobert.com/definition"


def _clean_text(text: str) -> str:
    """Clean extracted text by removing artifacts and normalizing whitespace"""
    if not text:
        return text
    
    # Remove audio player artifacts
    text = re.sub(r'Votre navigateur ne prend pas en charge l\'audio\.?', '', text)
    
    # Remove invisible Unicode characters (zero-width spaces, etc.)
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]', '', text)
    
    # Normalize whitespace (replace multiple spaces with single space)
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def fetch_definition(word: str) -> Dict[str, Any]:
    """
    Fetch the definition of a word from Le Robert dictionary.
    
    Args:
        word: The French word to look up
        
    Returns:
        A dictionary containing the word's definitions, examples, and other information
        
    Raises:
        ValueError: If the word is not found (404)
        requests.RequestException: If there's a network error
    """
    url = f"{BASE_URL}/{word}"
    
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        response.raise_for_status()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Word '{word}' not found in dictionary")
        raise
    except requests.RequestException as e:
        raise requests.RequestException(f"Failed to fetch definition: {e}")
    
    soup = BeautifulSoup(response.content, 'lxml')
    
    # Check if we were redirected to a conjugation page
    if '/conjugaison/' in response.url:
        return _handle_conjugation_redirect(word, response.url, soup)
    
    # Check if this is a conjugated form with a link to conjugation page
    original_word = None
    final_url = response.url
    conj_link_div = soup.find('div', class_='conj-link')
    if conj_link_div:
        # This is a conjugated form, we need to fetch the definition of the base verb
        original_word = word
        
        # Find the conjugation link to extract the base verb
        conj_link = conj_link_div.find('a', href=True)
        if conj_link:
            conj_url = conj_link.get('href')
            if conj_url.startswith('/'):
                conj_url = f"https://dictionnaire.lerobert.com{conj_url}"
            
            # Fetch the conjugation page to get the definition URL
            conj_response = requests.get(conj_url, timeout=10)
            conj_soup = BeautifulSoup(conj_response.content, 'lxml')
            
            # Find the definition link on the conjugation page
            def_link_elem = conj_soup.find('div', class_='def-link')
            if def_link_elem:
                link = def_link_elem.find('a', href=True)
                if link:
                    def_url = link.get('href')
                    if def_url.startswith('/'):
                        def_url = f"https://dictionnaire.lerobert.com{def_url}"
                    
                    # Fetch the actual definition page
                    def_response = requests.get(def_url, timeout=10)
                    soup = BeautifulSoup(def_response.content, 'lxml')
                    final_url = def_response.url
                    
                    # Extract the base verb from the conjugation page
                    lemme_elem = conj_soup.find('span', class_='conj_lemme')
                    base_verb = _clean_text(lemme_elem.get_text(strip=True)) if lemme_elem else word
                    word = base_verb
    
    # Standard definition extraction
    definitions = _extract_definitions(soup)
    examples = _extract_examples(soup)
    combinations = _extract_combinations(soup)
    
    result = {
        "original_word": original_word if original_word else word,
        "word": word,
        "url": final_url,
        "definitions": definitions,
        "usage_examples": examples,
        "word_combinations": combinations,
    }
    
    return result


def _handle_conjugation_redirect(original_word: str, final_url: str, soup: BeautifulSoup) -> Dict[str, Any]:
    """Handle when a word redirects to a conjugation page"""
    # Extract the base verb form
    lemme_elem = soup.find('span', class_='conj_lemme')
    base_form = _clean_text(lemme_elem.get_text(strip=True)) if lemme_elem else original_word
    
    # Find the definition link
    def_link_elem = soup.find('div', class_='def-link')
    definition_url = None
    if def_link_elem:
        link = def_link_elem.find('a')
        if link and link.get('href'):
            definition_url = f"https://dictionnaire.lerobert.com{link.get('href')}"
    
    # Extract a sample of conjugations (just present tense for simplicity)
    conjugations = {}
    present_section = soup.find('h4', string='présent')
    if present_section:
        parent = present_section.find_parent('div', class_='b')
        if parent:
            forms = []
            for p in parent.find_all('p'):
                form_text = _clean_text(p.get_text(strip=True))
                if form_text:
                    forms.append(form_text)
            if forms:
                conjugations['présent'] = forms
    
    result = {
        "type": "conjugation",
        "original_word": original_word,
        "redirected_to": base_form,
        "url": final_url,
        "definition_url": definition_url,
        "conjugations_sample": conjugations,
        "message": f"The word '{original_word}' is a conjugated form of '{base_form}'. Full conjugation table available at the URL."
    }
    
    return result


def _extract_definitions(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract word definitions from the page"""
    definitions = []
    
    # Find the main definitions section
    def_section = soup.find('section', class_='def')
    if not def_section:
        return definitions
    
    # Find all definition blocks (b class contains the structured definitions)
    def_blocks = def_section.find_all('div', class_='b', recursive=False)
    
    for block in def_blocks:
        # Get the word category (adverbe, nom masculin, etc.)
        category_elem = block.find('span', class_='d_cat')
        category = _clean_text(category_elem.get_text(separator=' ', strip=True)) if category_elem else ""
        
        # Find all definition items (d_dvn class)
        def_items = block.find_all('div', class_='d_dvn')
        
        for item in def_items:
            # Extract the main definition text (d_dfn class)
            dfn_elem = item.find('span', class_='d_dfn')
            if dfn_elem:
                definition_text = _clean_text(dfn_elem.get_text(separator=' ', strip=True))
                
                # Extract examples from this definition item (only direct d_xpl, not nested)
                examples = []
                xpl_elems = item.find_all('span', class_='d_xpl')
                for xpl in xpl_elems:
                    # Remove nested elements that are not examples (like glosses, audio, etc.)
                    for unwanted in xpl.find_all(['span'], class_=['d_gls', 'd_sound_cont', 'd_mtb', 'd_lca']):
                        unwanted.decompose()
                    
                    example_text = _clean_text(xpl.get_text(separator=' ', strip=True))
                    # Filter out examples that are too short or seem like metadata
                    if example_text and len(example_text) > 5 and not example_text.startswith('locution'):
                        examples.append(example_text)
                
                definitions.append({
                    "category": category,
                    "definition": definition_text,
                    "examples": examples
                })
    
    return definitions


def _extract_examples(soup: BeautifulSoup) -> List[str]:
    """Extract usage examples from the 'exemples' section"""
    examples = []
    
    # Find the examples section
    ex_section = soup.find('section', class_='ex', id='exemples')
    if not ex_section:
        return examples
    
    # Find all example divs
    example_divs = ex_section.find_all('div', class_='ex_example')
    
    for div in example_divs:
        # Remove author attribution before extracting text
        author_elem = div.find('a', class_='ex_author')
        if author_elem:
            author_elem.decompose()
        
        # Get the example text
        text = _clean_text(div.get_text(separator=' ', strip=True))
        
        if text and len(text) > 10:
            examples.append(text)
    
    return examples[:20]  # Limit to 20 examples


def _extract_combinations(soup: BeautifulSoup) -> List[str]:
    """Extract word combinations (mots qui s'emploient fréquemment avec)"""
    combinations = []
    
    # Find the combinations section
    collo_section = soup.find('section', class_='collo', id='collos')
    if not collo_section:
        return combinations
    
    # Find all combination links
    combo_links = collo_section.find_all('div', class_='collolink')
    
    for link_div in combo_links:
        link = link_div.find('a')
        if link:
            text = _clean_text(link.get_text(separator=' ', strip=True))
            if text and len(text) > 3:
                combinations.append(text)
    
    return combinations[:30]  # Limit to 30 combinations


# Placeholder functions for future extensions
def fetch_synonyms(word: str) -> Dict[str, Any]:
    """
    Fetch synonyms for a word (to be implemented).
    
    Args:
        word: The French word to look up
        
    Returns:
        A dictionary containing synonyms
    """
    # Future implementation
    url = f"{BASE_URL}/{word}"
    # Will parse the synonymes section
    raise NotImplementedError("Synonym fetching not yet implemented")


def fetch_conjugations(word: str) -> Dict[str, Any]:
    """
    Fetch conjugations for a verb (to be implemented).
    
    Args:
        word: The French verb to conjugate
        
    Returns:
        A dictionary containing conjugation tables
    """
    # Future implementation
    url = f"{BASE_URL}/{word}"
    # Will parse the conjugaison section
    raise NotImplementedError("Conjugation fetching not yet implemented")


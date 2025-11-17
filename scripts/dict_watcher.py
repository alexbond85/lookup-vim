#!/usr/bin/env python3
"""One-shot dictionary lookup with intelligent routing between Robert and ChatGPT."""

import os
import sys
import json
from pathlib import Path

# Colors
class C:
    BOLD, DIM = '\033[1m', '\033[2m'
    BLUE, GREEN, YELLOW, CYAN, MAGENTA, RED = '\033[1;34m', '\033[1;32m', '\033[1;33m', '\033[1;36m', '\033[1;35m', '\033[1;31m'
    RESET = '\033[0m'

class Printer:
    @staticmethod
    def header():
        print(f"{C.GREEN}╔{'═' * 78}╗{C.RESET}")
        print(f"{C.GREEN}║{C.RESET}  {C.CYAN}{C.BOLD}📖  Dictionnaire Le Robert & ChatGPT{C.RESET}                                   {C.GREEN}║{C.RESET}")
        print(f"{C.GREEN}╚{'═' * 78}╝{C.RESET}\n")
    
    @staticmethod
    def context(phrase=None, paragraph=None):
        text = phrase or paragraph
        if text:
            print(f"{C.DIM}Context: {C.RESET}{text[:76]}{'...' if len(text) > 76 else ''}\n")
    
    @staticmethod
    def robert(word, result):
        print(f"{C.YELLOW}{'═' * 40}\n{word.upper().center(40)}\n{'═' * 40}{C.RESET}\n")
        for line in result.split('\n'):
            if line.startswith('[') and line.endswith(']'):
                print(f"{C.MAGENTA}{C.BOLD}{line}{C.RESET}")
            elif line.strip() and line.lstrip()[0:1].isdigit() and '. ' in line:
                print(f"{C.CYAN}{line}{C.RESET}")
            elif '→' in line:
                print(f"{C.DIM}{line}{C.RESET}")
            elif line.isupper() and len(line) < 80 and line.strip():
                print(f"{C.YELLOW}{C.BOLD}{line}{C.RESET}")
            elif all(c in '─═' for c in line.strip()):
                print(f"{C.GREEN}{line}{C.RESET}")
            else:
                print(line)
    
    @staticmethod
    def chatgpt(query, translation, explanations):
        print(f"{C.CYAN}{C.BOLD}🔍 {query}{C.RESET}\n")
        print(f"{C.GREEN}{C.BOLD}📝 {translation}{C.RESET}\n")
        if explanations.strip():
            print(f"{C.YELLOW}{C.BOLD}💡 Explications:{C.RESET}")
            for line in explanations.split('\n'):
                if line.strip():
                    print(f"  {line}")
    
    @staticmethod
    def error(msg):
        print(f"{C.RED}⚠ {msg}{C.RESET}")

def is_single_word(text):
    return ' ' not in text.strip()

def lookup():
    word_file = Path(os.environ.get('TMPDIR', '/tmp')) / 'robert-dict-word.json'
    
    if not word_file.exists():
        Printer.error("No word file found")
        return 1
    
    try:
        data = json.loads(word_file.read_text())
        selection = data.get('selection', '').strip()
        phrase = data.get('phrase', '').strip() or None
        paragraph = data.get('paragraph', '').strip() or None
    except:
        Printer.error("Failed to parse JSON")
        return 1
    
    if not selection:
        Printer.error("Empty selection")
        return 1
    
    os.system('clear')
    Printer.header()
    Printer.context(phrase, paragraph)
    
    try:
        from robert_dict.service import DictionaryService
        from robert_dict.scrapers.lerobert import LeRobertScraper
        from robert_dict.printers.text import TextPrinter
        from robert_dict.chatgpt_service import ChatGPTTranslationService
        
        if is_single_word(selection):
            try:
                result = DictionaryService(LeRobertScraper(), TextPrinter()).lookup(selection)
                if result and len(result) > 100:
                    Printer.robert(selection, result)
                    return 0
            except:
                pass
            
            print(f"{C.YELLOW}⚠ Not in Le Robert, using ChatGPT...{C.RESET}\n")
            result = ChatGPTTranslationService().translate(selection, phrase or paragraph)
            Printer.chatgpt(result.query, result.translation, result.explanations)
        else:
            result = ChatGPTTranslationService().translate(selection, phrase or paragraph)
            Printer.chatgpt(result.query, result.translation, result.explanations)
        
        return 0
    
    except Exception as e:
        Printer.error(f"Error: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(lookup())

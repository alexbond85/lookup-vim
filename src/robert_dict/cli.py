"""Command-line interface for Robert Dictionary scraper"""

import sys
import argparse

from robert_dict.scrapers.lerobert import LeRobertScraper
from robert_dict.printers.text import TextPrinter
from robert_dict.printers.json import JsonPrinter
from robert_dict.service import DictionaryService


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Fetch French word definitions from Le Robert dictionary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  robert-dict bien
  robert-dict maison --format json
  robert-dict "bien que"
        """
    )
    
    parser.add_argument(
        'word',
        help='The French word to look up'
    )
    
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    parser.add_argument(
        '--indent',
        type=int,
        default=2,
        help='JSON indentation level (default: 2, only applies to --format json)'
    )
    
    args = parser.parse_args()
    
    # Dependency injection: create scraper, printer, and service
    scraper = LeRobertScraper()
    
    if args.format == 'json':
        printer = JsonPrinter(indent=args.indent)
    else:
        printer = TextPrinter()
    
    service = DictionaryService(scraper=scraper, printer=printer)
    
    # Perform lookup
    try:
        result = service.lookup(args.word)
        print(result)
        sys.exit(0)
        
    except ValueError as e:
        # Word not found
        if args.format == 'json':
            import json
            error = {
                "error": "Word not found",
                "message": str(e),
                "word": args.word
            }
            print(json.dumps(error, ensure_ascii=False, indent=args.indent), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        # Other errors (network, parsing, etc.)
        if args.format == 'json':
            import json
            error = {
                "error": "Failed to fetch definition",
                "message": str(e),
                "word": args.word
            }
            print(json.dumps(error, ensure_ascii=False, indent=args.indent), file=sys.stderr)
        else:
            print(f"Error: Failed to fetch definition - {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

"""Command-line interface for Robert Dictionary scraper"""

import sys
import json
import logging
import argparse

from robert_dict.scrapers.lerobert import LeRobertScraper
from robert_dict.printers.text import TextPrinter
from robert_dict.printers.json import JsonPrinter
from robert_dict.service import DictionaryService
from robert_dict.constants import ExitCode, DEFAULT_JSON_INDENT


# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        default=DEFAULT_JSON_INDENT,
        help=f'JSON indentation level (default: {DEFAULT_JSON_INDENT}, only applies to --format json)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger('robert_dict').setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Dependency injection: create scraper, printer, and service
    logger.debug(f"Looking up word: {args.word}")
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
        logger.debug(f"Successfully looked up word: {args.word}")
        sys.exit(ExitCode.SUCCESS)
        
    except ValueError as e:
        # Word not found
        logger.warning(f"Word not found: {args.word} - {e}")
        if args.format == 'json':
            error = {
                "error": "Word not found",
                "message": str(e),
                "word": args.word
            }
            print(json.dumps(error, ensure_ascii=False, indent=args.indent), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(ExitCode.WORD_NOT_FOUND)
        
    except Exception as e:
        # Other errors (network, parsing, etc.)
        logger.error(f"Failed to fetch definition for '{args.word}': {e}", exc_info=args.verbose)
        if args.format == 'json':
            error = {
                "error": "Failed to fetch definition",
                "message": str(e),
                "word": args.word
            }
            print(json.dumps(error, ensure_ascii=False, indent=args.indent), file=sys.stderr)
        else:
            print(f"Error: Failed to fetch definition - {e}", file=sys.stderr)
        sys.exit(ExitCode.GENERAL_ERROR)


if __name__ == "__main__":
    main()

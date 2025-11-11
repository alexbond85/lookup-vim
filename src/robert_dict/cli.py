"""Command-line interface for Robert Dictionary scraper"""

import sys
import json
import argparse
from typing import NoReturn

from robert_dict.scraper import fetch_definition


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Fetch French word definitions from Le Robert dictionary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  robert-dict bien
  robert-dict maison
  robert-dict "bien que"
        """
    )
    
    parser.add_argument(
        'word',
        help='The French word to look up'
    )
    
    parser.add_argument(
        '--indent',
        type=int,
        default=2,
        help='JSON indentation level (default: 2)'
    )
    
    args = parser.parse_args()
    
    try:
        result = fetch_definition(args.word)
        # Output pretty-printed JSON to stdout
        print(json.dumps(result, ensure_ascii=False, indent=args.indent))
        sys.exit(0)
        
    except ValueError as e:
        # Word not found
        error = {
            "error": "Word not found",
            "message": str(e),
            "word": args.word
        }
        print(json.dumps(error, ensure_ascii=False, indent=args.indent), file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        # Other errors (network, parsing, etc.)
        error = {
            "error": "Failed to fetch definition",
            "message": str(e),
            "word": args.word
        }
        print(json.dumps(error, ensure_ascii=False, indent=args.indent), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()


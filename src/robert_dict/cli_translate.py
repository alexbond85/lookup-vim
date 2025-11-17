"""Command-line interface for ChatGPT translation service"""

import sys
import json
import logging
import argparse
import os

from robert_dict.chatgpt_service import ChatGPTTranslationService
from robert_dict.printers.translation import TranslationPrinter
from robert_dict.constants import ExitCode, DEFAULT_JSON_INDENT


# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main CLI entry point for translation service"""
    parser = argparse.ArgumentParser(
        description="Translate French text to Russian with contextual explanations using ChatGPT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  robert-translate "bien que"
  robert-translate "au fur et à mesure" --context "Il apprend au fur et à mesure."
  robert-translate "pourtant" --context "Il était fatigué, pourtant il a continué."
        """
    )
    
    parser.add_argument(
        'query',
        help='The French word or expression to translate'
    )
    
    parser.add_argument(
        '--context', '-c',
        help='The paragraph or sentence providing context for the query'
    )
    
    parser.add_argument(
        '--indent',
        type=int,
        default=DEFAULT_JSON_INDENT,
        help=f'JSON indentation level (default: {DEFAULT_JSON_INDENT})'
    )
    
    parser.add_argument(
        '--model',
        default='gpt-5.1',
        help='OpenAI model to use (default: gpt-5.1)'
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
    
    # Check for API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        error_msg = "OPENAI_API_KEY environment variable is not set"
        logger.error(error_msg)
        error = {
            "error": "Missing API key",
            "message": error_msg,
            "query": args.query
        }
        print(json.dumps(error, ensure_ascii=False, indent=args.indent), file=sys.stderr)
        sys.exit(ExitCode.GENERAL_ERROR)
    
    # Create service and printer
    logger.debug(f"Translating query: {args.query}")
    service = ChatGPTTranslationService(api_key=api_key, model=args.model)
    printer = TranslationPrinter(indent=args.indent)
    
    # Perform translation
    try:
        result = service.translate(args.query, context=args.context)
        output = printer.print(result)
        print(output)
        logger.debug(f"Successfully translated: {args.query}")
        sys.exit(ExitCode.SUCCESS)
        
    except Exception as e:
        # Handle errors
        logger.error(f"Failed to translate '{args.query}': {e}", exc_info=args.verbose)
        error = {
            "error": "Translation failed",
            "message": str(e),
            "query": args.query
        }
        print(json.dumps(error, ensure_ascii=False, indent=args.indent), file=sys.stderr)
        sys.exit(ExitCode.GENERAL_ERROR)


if __name__ == "__main__":
    main()


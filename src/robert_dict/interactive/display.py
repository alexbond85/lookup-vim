"""Rich formatting for dictionary and translation results"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from robert_dict.models import WordResult, TranslationResult


console = Console()


def display_greeting():
    """Display welcome message"""
    greeting = Panel(
        "[bold cyan]🔍 Robert Dictionary Interactive Watcher[/bold cyan]\n\n"
        "Waiting for selections from Vim or enter words directly...",
        box=box.ROUNDED,
        border_style="cyan"
    )
    console.print(greeting)
    console.print()


def display_word_result(result: WordResult):
    """Display dictionary word result with definitions, examples, and combinations"""
    
    # Header with word
    header_text = f"[bold green]{result.word}[/bold green]"
    if result.original_word and result.original_word != result.word:
        header_text += f" [dim](from: {result.original_word})[/dim]"
    
    console.print(Panel(header_text, box=box.HEAVY, border_style="green"))
    
    # Definitions section
    if result.definitions:
        console.print("\n[bold yellow]📖 Definitions:[/bold yellow]\n")
        for idx, definition in enumerate(result.definitions, 1):
            # Category
            if definition.category:
                console.print(f"[bold cyan]{definition.category}[/bold cyan]")
            
            # Definition text
            console.print(f"  {idx}. {definition.definition}")
            
            # Examples for this definition
            if definition.examples:
                for example in definition.examples[:3]:  # Limit to 3 examples per definition
                    console.print(f"     [dim italic]→ {example}[/dim italic]")
            console.print()
    
    # Usage examples section
    if result.usage_examples:
        console.print("[bold yellow]💡 Usage Examples:[/bold yellow]\n")
        for example in result.usage_examples[:5]:  # Show up to 5 examples
            console.print(f"  • [italic]{example}[/italic]")
        console.print()
    
    # Word combinations section
    if result.word_combinations:
        console.print("[bold yellow]🔗 Word Combinations:[/bold yellow]\n")
        # Display in rows of 3
        combos = result.word_combinations[:15]  # Limit to 15
        for i in range(0, len(combos), 3):
            row = combos[i:i+3]
            console.print("  " + " • ".join(row))
        console.print()
    
    console.print(f"[dim]Source: {result.url}[/dim]\n")


def display_translation_result(result: TranslationResult):
    """Display translation result with explanations"""
    
    # Query header
    query_text = f"[bold magenta]{result.query}[/bold magenta]"
    console.print(Panel(query_text, box=box.HEAVY, border_style="magenta"))
    
    # Translation (highlighted)
    translation_panel = Panel(
        f"[bold green]{result.translation}[/bold green]",
        title="Translation",
        box=box.ROUNDED,
        border_style="green"
    )
    console.print("\n")
    console.print(translation_panel)
    
    # Explanations
    if result.explanations:
        console.print("\n[bold yellow]📝 Explanations:[/bold yellow]\n")
        console.print(f"  {result.explanations}\n")
    
    # Context if provided
    if result.context:
        console.print("[bold yellow]📄 Context:[/bold yellow]\n")
        console.print(f"  [dim italic]{result.context}[/dim italic]\n")


def display_error(message: str):
    """Display error message"""
    console.print(f"[bold red]❌ Error:[/bold red] {message}\n")


def display_prompt(has_context: bool = False):
    """Display input prompt with available options"""
    if has_context:
        console.print("[dim]Options: [1] Translate phrase | [2] Translate paragraph | [word/phrase] New lookup | [q/exit] Quit[/dim]")
    else:
        console.print("[dim]Enter word/phrase to lookup, or [q/exit] to quit[/dim]")
    console.print("[bold cyan]>[/bold cyan] ", end="")


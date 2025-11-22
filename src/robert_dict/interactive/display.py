"""Rich formatting for dictionary and translation results"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from robert_dict.models import WordResult, TranslationResult


# Console with recording enabled for history logging
console = Console(record=True)


def display_greeting():
    """Display welcome message"""
    greeting = Panel(
        "[blue]🔍 Robert Dictionary Interactive Watcher[/blue]\n\n"
        "[dim]Waiting for selections from Vim or enter words directly...[/dim]",
        box=box.ROUNDED,
        border_style="blue"
    )
    console.print(greeting)
    console.print()


def display_word_result(result: WordResult):
    """Display dictionary word result with definitions, examples, and combinations"""
    
    # Header with word
    header_text = f"[cyan]{result.word}[/cyan]"
    if result.original_word and result.original_word != result.word:
        header_text += f" [dim](from: {result.original_word})[/dim]"
    
    console.print()  # Add blank line before
    console.print(Panel(header_text, box=box.ROUNDED, border_style="cyan", expand=False))
    
    # Definitions section
    if result.definitions:
        console.print("\n[dim]📖 Definitions:[/dim]\n")
        for idx, definition in enumerate(result.definitions, 1):
            # Category
            if definition.category:
                console.print(f"[dim]{definition.category}[/dim]")
            
            # Definition text
            console.print(f"  [white]{idx}.[/white] {definition.definition}")
            
            # Examples for this definition
            if definition.examples:
                for example in definition.examples[:3]:  # Limit to 3 examples per definition
                    console.print(f"     [dim italic]→ {example}[/dim italic]")
            console.print()
    
    # Usage examples section
    if result.usage_examples:
        console.print("[dim]💡 Usage Examples:[/dim]\n")
        for example in result.usage_examples[:5]:  # Show up to 5 examples
            console.print(f"  • [dim italic]{example}[/dim italic]")
        console.print()
    
    # Word combinations section
    if result.word_combinations:
        console.print("[dim]🔗 Word Combinations:[/dim]\n")
        # Display in rows of 3
        combos = result.word_combinations[:15]  # Limit to 15
        for i in range(0, len(combos), 3):
            row = combos[i:i+3]
            console.print(f"  [dim]{' • '.join(row)}[/dim]")
        console.print()
    
    console.print(f"[dim italic]Source: {result.url}[/dim italic]\n")


def display_translation_result(result: TranslationResult):
    """Display translation result with explanations"""
    
    # Query header
    query_text = f"[cyan]{result.query}[/cyan]"
    console.print()  # Add blank line before
    console.print(Panel(query_text, box=box.ROUNDED, border_style="cyan", expand=False))
    
    # Translation (highlighted)
    translation_panel = Panel(
        f"[white]{result.translation}[/white]",
        title="[dim]Translation[/dim]",
        box=box.ROUNDED,
        border_style="blue"
    )
    console.print("\n")
    console.print(translation_panel)
    
    # Explanations
    if result.explanations:
        console.print("\n[dim]📝 Explanations:[/dim]\n")
        console.print(f"  [dim]{result.explanations}[/dim]\n")
    
    # Context if provided
    if result.context:
        console.print("[dim]📄 Context:[/dim]\n")
        console.print(f"  [dim italic]{result.context}[/dim italic]\n")


def display_error(message: str):
    """Display error message"""
    console.print(f"[bold red]❌ Error:[/bold red] {message}\n")


def display_prompt(has_context: bool = False):
    """Display input prompt with available options"""
    if has_context:
        console.print("[dim]Options: [1] Translate phrase | [2] Translate paragraph | [h]istory | [q/exit] Quit[/dim]")
    else:
        console.print("[dim]Enter word/phrase, [h]istory to view, or [q/exit] to quit[/dim]")
    console.print("[blue]>[/blue] ", end="")


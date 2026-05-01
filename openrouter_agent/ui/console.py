try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.rule import Rule
    from rich.box import ROUNDED, DOUBLE
    RICH = True
    console = Console()
except Exception:
    RICH = False
    console = None
    Panel = Table = Rule = None
    ROUNDED = DOUBLE = None

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    def green(x): return Fore.GREEN + str(x) + Style.RESET_ALL
    def red(x): return Fore.RED + str(x) + Style.RESET_ALL
    def yellow(x): return Fore.YELLOW + str(x) + Style.RESET_ALL
    def cyan(x): return Fore.CYAN + str(x) + Style.RESET_ALL
    def magenta(x): return Fore.MAGENTA + str(x) + Style.RESET_ALL
except Exception:
    def _c(code, x): return f"\033[{code}m{x}\033[0m"
    def green(x): return _c(92, x)
    def red(x): return _c(91, x)
    def yellow(x): return _c(93, x)
    def cyan(x): return _c(96, x)
    def magenta(x): return _c(95, x)

def info(x=""): print(magenta(x))
def success(x=""): print(green(x))
def warn(x=""): print(yellow(x))
def error(x=""): print(red(x))
def agent(x=""): print(green(x))
def step(x=""): print(yellow(x))

def panel(text, title="", style="cyan"):
    if RICH:
        console.print(Panel(str(text), title=title, border_style=style, box=ROUNDED))
    else:
        print(cyan(f"[{title}]"))
        print(text)

def banner(app_title, provider_mode, auto_mode, smart_auto):
    if RICH:
        console.print(Panel.fit(
            f"[bold cyan]{app_title}[/bold cyan]\n"
            f"[green]Provider mode:[/green] {provider_mode}\n"
            f"[green]Auto mode:[/green] {auto_mode} | [green]Smart auto:[/green] {smart_auto}",
            border_style="cyan",
            box=DOUBLE
        ))
    else:
        success("=" * 60)
        success(app_title)
        info(f"Provider mode: {provider_mode}")
        info(f"Auto mode: {auto_mode} | Smart auto: {smart_auto}")
        success("=" * 60)

def table(title, rows):
    if RICH:
        t = Table(title=title, box=ROUNDED)
        t.add_column("Key", style="bold")
        t.add_column("Value")
        for k, v in rows:
            t.add_row(str(k), str(v))
        console.print(t)
    else:
        info(title)
        for k, v in rows:
            print(f"{k}: {v}")

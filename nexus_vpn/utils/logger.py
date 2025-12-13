from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "cmd": "grey70 italic"
})
console = Console(theme=custom_theme)

class Logger:
    @staticmethod
    def info(msg): console.print(f"[info]ℹ️  {msg}[/info]")
    @staticmethod
    def success(msg): console.print(f"[success]✅ {msg}[/success]")
    @staticmethod
    def warning(msg): console.print(f"[warning]⚠️  {msg}[/warning]")
    @staticmethod
    def error(msg): console.print(f"[error]❌ {msg}[/error]")
    @staticmethod
    def run_cmd(cmd): console.print(f"[cmd]> {cmd}[/cmd]")

log = Logger()

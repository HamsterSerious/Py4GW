"""
Zero To Hero Bot - Main Entry Point
"""
from Py4GWCoreLib import ActionQueueManager
import Py4GW

from core.bot import get_bot


def main():
    """Main execution loop."""
    try:
        bot = get_bot()
        bot.update()
        ActionQueueManager().ProcessQueue("ACTION")
    except Exception as e:
        Py4GW.Console.Log("ZeroToHero", f"Crash: {str(e)}", Py4GW.Console.MessageType.Error)


if __name__ == "__main__":
    main()

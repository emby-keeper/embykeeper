import os

from embykeeper.cli import app
from embykeeper.var import console

if __name__ == "__main__":
    os.system("cls")
    console.rule("Embykeeper")
    console.print()
    app()

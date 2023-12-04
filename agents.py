from trading_objects import Agent
from command_display import CommandDisplay, Command, Argument

class ManualAgent(Agent):

    def __init__(self) -> None:
        super().__init__()
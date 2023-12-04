import pygame

from trading_objects import Agent
from command_display import CommandDisplay, Command, Argument


class ManualAgent(Agent):
    def __init__(self) -> None:
        super().__init__()
        self.gui = CommandDisplay(commands=[
            Command
        ], draw_fn=self.visualize)

    def visualize(self, screen: pygame.surface.Surface, x: int, y: int, w: int, h: int):
        pass

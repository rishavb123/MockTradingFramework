from simulation import Simulation, SimulationObject, Time
from command_display import CommandDisplay, Argument, Command


class TestObject(SimulationObject):
    def __init__(self, s, z) -> None:
        super().__init__(z)
        self.s = s

    def update(self) -> None:
        super().update()
        print(self.s, Time.now)


def main():
    s = Simulation(dt=1, iter=10)
    s.add_object(TestObject("B", 0))
    s.add_object(TestObject("C", 1))
    s.add_object(TestObject("A", -2))
    s.start()

    c = CommandDisplay(
        [
            Command(
                f=lambda: "hello world",
                name="hello_world",
                args_definitions=[],
                short_name="h",
            ),
            Command(
                f=lambda: "yoo world my name is Rishav Bhagat isn't that cool",
                name="hello_rishav",
                args_definitions=[],
                short_name="r",
            ),
        ]
    )
    s.connect_display(c)

    c.run()


if __name__ == "__main__":
    main()

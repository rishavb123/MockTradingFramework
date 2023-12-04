from simulation import Simulation, SimulationObject, Time


class TestObject(SimulationObject):
    def __init__(self, s, z) -> None:
        super().__init__(z)
        self.s = s

    def update(self) -> None:
        print(self.s, Time.now)


def main():
    s = Simulation(dt=1, iter=10)
    s.add_object(TestObject("B", 0))
    s.add_object(TestObject("C", 1))
    s.add_object(TestObject("A", -2))
    s.start()
    s.join()


if __name__ == "__main__":
    main()

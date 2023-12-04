from simulation import Simulation, SimulationObject, Time

class TestObject(SimulationObject):

    def __init__(self) -> None:
        super().__init__()

    def update(self) -> None:
        print(Time.now)

def main():
    s = Simulation(dt=1, iter=10)
    s.add_object(TestObject())
    s.start()
    s.join()

if __name__ == "__main__":
    main()
from __future__ import annotations


class Time:
    now = 0

    @staticmethod
    def incr_time():
        Time.now += 1


class SimulationObject:
    last_id = -1
    __objects = {}

    def __init__(self) -> None:
        self.created_at = Time.now
        self.id = self.__class__.generate_id()
        self.global_id = f"{self.__class__.__name__.lower()}{self.id}"
        SimulationObject.__objects[self.global_id] = self

    def update(self) -> None:
        pass

    def display_str(self) -> str:
        return self.global_id

    @classmethod
    def generate_id(cls) -> int:
        cls.last_id += 1
        return cls.last_id

    @staticmethod
    def get_object(global_id: str) -> SimulationObject:
        return SimulationObject.__objects.get(global_id, None)


class Simulation:
    def __init__(self) -> None:
        self.__objects = []

    def add_object(self, object: SimulationObject) -> None:
        self.__objects.append(object)

    def update(self) -> None:
        for obj in self.__objects:
            obj.update()

        Time.incr_time()

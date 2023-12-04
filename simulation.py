from __future__ import annotations
from typing import Union

import time
import threading


class Time:
    now = 0

    @staticmethod
    def incr_time():
        Time.now += 1


class SimulationObject:
    last_id = -1
    __objects = {}

    def __init__(self, z_index: int = 0) -> None:
        self.created_at = Time.now
        self.id = self.__class__.generate_id()
        self.global_id = f"{self.__class__.__name__.lower()}{self.id}"
        self.__z_index = z_index
        SimulationObject.__objects[self.global_id] = self

    def update(self) -> None:
        pass

    def display_str(self) -> str:
        return self.global_id

    @property
    def z_index(self):
        return self.__z_index

    @classmethod
    def generate_id(cls) -> int:
        cls.last_id += 1
        return cls.last_id

    @staticmethod
    def get_object(global_id: str) -> SimulationObject:
        return SimulationObject.__objects.get(global_id, None)


class Simulation(threading.Thread):
    def __init__(
        self,
        dt: Union[float, None] = None,
        iter: int = 1e5,
        lock: Union[threading.Lock, None] = None,
    ) -> None:
        super().__init__()

        self.__objects = {}
        self.__z_ordering = []

        self.last_update = 0
        self.should_update = True

        self.dt = dt
        self.iter = iter

        self.lock = threading.Lock() if lock is None else lock

    def add_object(self, object: SimulationObject) -> None:
        if object.z_index not in self.__objects:
            self.__objects[object.z_index] = []
            inserted = False
            for i in range(len(self.__z_ordering)):
                if self.__z_ordering[i] > object.z_index:
                    self.__z_ordering.insert(i, object.z_index)
                    inserted = True
                    break
            if not inserted:
                self.__z_ordering.append(object.z_index)
        self.__objects[object.z_index].append(object)

    def update(self) -> None:
        for z in self.__z_ordering:
            for obj in self.__objects[z]:
                obj.update()

        Time.incr_time()
        self.should_update = False

    def manual_update(self) -> None:
        with self.lock:
            self.should_update = True

    def run(self) -> None:
        while Time.now < self.iter:
            cur_time = time.time()
            if self.dt is not None and cur_time - self.last_update >= self.dt:
                self.should_update = True
                self.last_update = cur_time
            should_update = False
            with self.lock:
                if self.should_update:
                    should_update = True
            if should_update:
                self.update()

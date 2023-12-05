from __future__ import annotations
from typing import Union, Self, List

import time
import threading
import pygame

from command_display import CommandDisplay, Command


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
        self.global_id = self.__class__.to_global_id(self.id)
        self.__z_index = z_index
        self.simulation = None
        self.dependents = []

        SimulationObject.__objects[self.global_id] = self

    def update(self) -> None:
        pass

    def set_simulation(self, simulation: Simulation) -> None:
        self.simulation = simulation
        for dependent in self.dependents:
            self.simulation.add_object(dependent)

    def add_dependent(self, dependent: SimulationObject) -> None:
        self.dependents.append(dependent)
        if self.simulation is not None:
            self.simulation.add_object(dependent)

    def display_str(self) -> str:
        return self.global_id

    def on_start(self) -> None:
        pass

    def on_finish(self) -> None:
        pass

    def __del__(self) -> None:
        del SimulationObject.__objects[self.global_id]

    @property
    def z_index(self):
        return self.__z_index

    @classmethod
    def generate_id(cls) -> int:
        cls.last_id += 1
        return cls.last_id

    @classmethod
    def to_global_id(cls, id: int) -> str:
        return f"{cls.__name__.lower()}{id}"

    @staticmethod
    def get_object(global_id: str) -> SimulationObject:
        return SimulationObject.__objects.get(global_id, None)

    @classmethod
    def get_instance(cls, id: int) -> Self:
        return SimulationObject.get_object(cls.to_global_id(id))


class Simulation(threading.Thread):
    def __init__(
        self,
        dt: Union[float, None] = None,
        iter: int = 1e5,
        lock: Union[threading.Lock, None] = None,
        simulation_objs: List[SimulationObject] = [],
    ) -> None:
        super().__init__()

        self.__objects = {}
        self.__z_ordering = []

        self.last_update = 0
        self.should_update = True

        self.dt = dt
        self.paused = False
        self.killed = False
        self.started = False
        self.finished = False
        self.iter = iter

        self.lock = threading.Lock() if lock is None else lock

        [self.add_object(obj) for obj in simulation_objs]

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
        object.set_simulation(self)
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

    def pause(self) -> None:
        with self.lock:
            self.paused = True

    def kill(self) -> None:
        self.killed = True

    def unpause(self) -> None:
        with self.lock:
            self.paused = False

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def on_start(self) -> None:
        for z in self.__z_ordering:
            for obj in self.__objects[z]:
                obj.on_start()

    def on_finish(self) -> None:
        for z in self.__z_ordering:
            for obj in self.__objects[z]:
                obj.on_finish()

    def run(self) -> None:
        self.started = True
        self.on_start()
        while Time.now < self.iter:
            cur_time = time.time()
            time_update = False
            if self.dt is not None and cur_time - self.last_update >= self.dt:
                time_update = True
                self.last_update = cur_time
            should_update = False
            with self.lock:
                if time_update and not self.paused:
                    should_update = True
                if self.should_update:
                    should_update = True
                if self.killed:
                    break
            if should_update:
                self.update()
        self.finished = True
        self.on_finish()

    def connect_display(self, c: CommandDisplay):
        def quit():
            c.running = False
            self.kill()

        c.add_commands(
            Command(f=self.toggle_pause, short_name="p"),
            Command(f=self.manual_update, short_name="m"),
            Command(f=self.kill, short_name="k"),
            Command(f=quit, short_name="q"),
        )
        c.add_macro(pygame.K_SPACE, "p")
        c.add_macro(pygame.K_RETURN, "m")
        c.add_macro(pygame.K_KP_ENTER, "m")

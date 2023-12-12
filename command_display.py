from typing import Any, Callable, List, Union, Tuple, Dict
import pygame


class Argument:
    def __init__(self, type_converter: Callable[[str], Any], default_arg: Any) -> None:
        self.type_converter = type_converter
        self.default_arg = default_arg

    def get(self, str_arg: Union[str, None] = None) -> Any:
        return self.default_arg if str_arg is None else self.type_converter(str_arg)


class Command:
    def __init__(
        self,
        f: Callable,
        name: Union[str, None] = None,
        args_definitions: List[Union[Argument, Any]] = [],
        short_name: Union[str, None] = None,
        f_kwargs: Dict[str, Any] = {},
    ) -> None:
        self.name = name.lower() if name is not None else f.__name__.lower()
        self.short_name = short_name.lower() if short_name is not None else None
        self.f = f
        self.args_definitions = args_definitions
        self.f_kwargs = f_kwargs

    def run(self, str_args: List[str]) -> None:
        try:
            args = []
            i = 0
            for arg_definition in self.args_definitions:
                if isinstance(arg_definition, Argument):
                    str_arg = None
                    if i < len(str_args):
                        str_arg = str_args[i]
                        if len(str_arg) == 0:
                            str_arg = None
                    args.append(arg_definition.get(str_arg))
                    i += 1
                else:
                    args.append(arg_definition)
            return self.f(*args, **self.f_kwargs)
        except Exception as e:
            return f"{e.__class__.__name__}: {e}"


class CommandDisplay:
    SPLIT_CHAR = " "

    COMMAND_EDIT_MODE = 0
    MACRO_EDIT_MODE = 1

    def __init__(
        self,
        commands: List[Command] = [],
        macros: Dict[int, Union[str, Callable[[None], str]]] = {},
        w: int = 1280,
        h: int = 720,
        margin: int = 10,
        fps: int = 60,
        output_box_width=300,
        blinks_per_second: int = 3,
        font: str = "Courier New",
        font_size: int = 20,
        font_bold: bool = True,
        command_font_size: int = 32,
        command_font_bold: bool = True,
        background_color: Tuple[int, int, int] = (0, 0, 0),
        command_color: Tuple[int, int, int] = (0, 255, 0),
        command_box_color: Tuple[int, int, int] = (30, 30, 30),
        output_color: Tuple[int, int, int] = (255, 255, 255),
        output_box_color: Tuple[int, int, int] = (50, 50, 50),
        draw_fn_map: Dict[str, Callable[[int, int, int, int], None]] = {},
        start_draw_state: Union[str, None] = None,
        handle_event_fn: Union[Callable[[pygame.event.Event], None], None] = None,
    ) -> None:
        super().__init__()
        self.commands = {}
        self.macros = macros | {
            pygame.K_UP: "vu",
            pygame.K_DOWN: "vd",
        }

        default_draw_state = list(draw_fn_map.keys())[0]

        base_commands = [
            Command(f=self.quit, short_name="q"),
            Command(
                f=self.view,
                short_name="v",
                args_definitions=[Argument(str, default_draw_state)],
            ),
            Command(
                f=self.view_idx, short_name="vi", args_definitions=[Argument(int, 0)]
            ),
            Command(
                f=self.view_up_or_down,
                name="view_up",
                args_definitions=[1],
                short_name="vu",
            ),
            Command(
                f=self.view_up_or_down,
                name="view_up",
                args_definitions=[-1],
                short_name="vd",
            ),
        ]
        self.add_commands(*(base_commands + commands))

        pygame.init()

        self.set_screen_size(w, h)
        self.margin = margin
        self.fps = fps
        self.blinks_per_second = blinks_per_second

        self.command_buffer = ""
        self.log_buffer = []
        self.ran_command_strs = []
        self.ran_command_strs_idx = 0

        self.command_font = pygame.font.SysFont(
            font, command_font_size, command_font_bold
        )
        self.font = pygame.font.SysFont(font, font_size, font_bold)
        self.clock = pygame.time.Clock()
        self.running = True

        self.output_box_width = output_box_width

        self.background_color = background_color
        self.command_color = command_color
        self.command_box_color = command_box_color
        self.output_color = output_color
        self.output_box_color = output_box_color

        if len(draw_fn_map) == 0:
            self.draw_fn_map = {"empty": lambda: None}
            self.draw_state = "empty"
        else:
            self.draw_fn_map = draw_fn_map
            self.draw_state = (
                default_draw_state if start_draw_state is None else start_draw_state
            )
        self.handle_event_fn = handle_event_fn

        self.cur_edit_mode = CommandDisplay.COMMAND_EDIT_MODE

    def quit(self) -> None:
        self.running = False

    def view_idx(self, i: int) -> None:
        v = list(self.draw_fn_map.keys())
        if 0 <= i < len(v):
            self.draw_state = v[i]
            return f"Switched to {self.draw_state} view"
        else:
            return f"Index {i} view does not exist"

    def view_up_or_down(self, dir: int) -> None:
        i = list(self.draw_fn_map.keys()).index(self.draw_state)
        i += dir
        self.view_idx(i % len(self.draw_fn_map))
        return f"Switched to {self.draw_state} view"

    def view(self, s: str) -> None:
        if s in self.draw_fn_map:
            self.draw_state = s
            return f"Switched to {s} view"
        else:
            return f"{s.title()} view does not exist"

    def add_commands(self, *commands: List[Command]) -> None:
        self.commands = (
            self.commands
            | {c.name: c for c in commands}
            | {c.short_name: c for c in commands if c.short_name is not None}
        )

    def add_macro(
        self,
        pygame_keycode: int,
        command_str_or_generator: Union[str, Callable[[None], str]],
    ) -> None:
        self.macros[pygame_keycode] = command_str_or_generator

    def set_screen_size(self, w: int, h: int) -> None:
        self.w = w
        self.h = h
        self.screen = pygame.display.set_mode((w, h))

    def run_command(self, command_str: str, add_to_ran_commands: str = True) -> None:
        split_command = command_str.split(CommandDisplay.SPLIT_CHAR)
        command_name = split_command[0]
        if add_to_ran_commands:
            if (
                len(self.ran_command_strs) == 0
                or self.ran_command_strs[-1] != command_str
            ):
                self.ran_command_strs.append(command_str)
        if command_name in self.commands:
            result = self.commands[command_name].run(split_command[1:])
            if result is not None:
                self.log_buffer.insert(0, str(result))
        else:
            self.log_buffer.insert(0, f"Command {command_name} not found")

    def wrap_text(
        self,
        text_lst: List[str],
        x: int,
        y: int,
        w: int,
        h: int,
        color: Tuple[int, int, int],
    ) -> List[str]:
        cur_y = y
        new_text_lst = []
        font_height = None

        for text in text_lst:
            words = text.split(" ")
            lines = []
            while len(words) > 0:
                line = ""
                cur_line_w = 0
                while len(words) > 0:
                    fw, fh = self.font.size(" " + words[0])
                    if font_height is None:
                        font_height = fh
                    if cur_line_w + fw > w:
                        if cur_line_w > 0:
                            break
                        else:
                            words = [
                                words[0][: len(words[0]) // 2],
                                words[0][len(words[0]) // 2 :],
                                *words[1:],
                            ]
                    else:
                        cur_line_w += fw
                        line += words.pop(0) + " "
                lines.append(line[:-1])

            s = ""
            for line in lines:
                block = self.font.render(
                    line,
                    True,
                    color,
                )
                rect = block.get_rect()
                rect.left = x
                rect.top = cur_y
                cur_y += font_height
                if rect.bottom > y + h:
                    if len(s[:-1]) > 0:
                        new_text_lst.append(s[:-1])
                    return new_text_lst
                self.screen.blit(block, rect)
                s += line + " "

            new_text_lst.append(s[:-1])

            cur_y += self.margin * 2

        return new_text_lst

    def run(self) -> None:
        counter = 0

        while self.running:
            counter += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if self.cur_edit_mode == CommandDisplay.COMMAND_EDIT_MODE:
                        if (
                            event.key == pygame.K_RETURN
                            or event.key == pygame.K_KP_ENTER
                        ):
                            self.run_command(self.command_buffer)
                            self.command_buffer = ""
                            self.ran_command_strs_idx = 0
                        elif event.key == pygame.K_BACKSPACE:
                            self.command_buffer = self.command_buffer[:-1]
                        elif event.key == pygame.K_UP:
                            if self.ran_command_strs_idx > -len(self.ran_command_strs):
                                self.ran_command_strs_idx -= 1
                            if len(self.ran_command_strs) != 0:
                                self.command_buffer = self.ran_command_strs[
                                    self.ran_command_strs_idx
                                ]
                        elif event.key == pygame.K_DOWN:
                            if self.ran_command_strs_idx < 0:
                                self.ran_command_strs_idx += 1
                            if self.ran_command_strs_idx < 0:
                                self.command_buffer = self.ran_command_strs[
                                    self.ran_command_strs_idx
                                ]
                            else:
                                self.command_buffer = ""
                        elif event.key == pygame.K_ESCAPE:
                            self.cur_edit_mode = CommandDisplay.MACRO_EDIT_MODE
                        else:
                            self.command_buffer += event.unicode
                    elif self.cur_edit_mode == CommandDisplay.MACRO_EDIT_MODE:
                        if event.key == pygame.K_i:
                            self.cur_edit_mode = CommandDisplay.COMMAND_EDIT_MODE
                        if event.key in self.macros:
                            command_str = (
                                self.macros[event.key]
                                if type(self.macros[event.key]) == str
                                else self.macros[event.key]()
                            )
                            self.run_command(command_str, False)

                    if self.handle_event_fn is not None:
                        self.handle_event_fn(event)

            self.screen.fill(self.background_color)

            blink = (counter * self.blinks_per_second // self.fps) % 2 == 0

            prefix = "> "
            suffix = (
                " "
                if blink or self.cur_edit_mode == CommandDisplay.MACRO_EDIT_MODE
                else "_"
            )
            block = self.command_font.render(
                prefix + self.command_buffer + suffix,
                True,
                self.command_color,
            )

            rect = block.get_rect()
            rect.left = self.margin
            rect.bottom = self.h - self.margin

            self.draw_fn_map[self.draw_state](
                x=self.margin,
                y=self.margin,
                w=self.w - self.output_box_width - 2 * self.margin,
                h=self.h - rect.height - 3 * self.margin,
            )

            pygame.draw.rect(
                self.screen,
                self.command_box_color,
                (
                    0,
                    self.h - rect.height - self.margin,
                    self.w,
                    rect.height + self.margin,
                ),
            )
            self.screen.blit(block, rect)

            pygame.draw.rect(
                self.screen,
                self.output_box_color,
                (
                    self.w - self.output_box_width,
                    0,
                    self.output_box_width,
                    self.h - rect.height - self.margin,
                ),
            )
            self.log_buffer = self.wrap_text(
                text_lst=self.log_buffer,
                x=self.w - self.output_box_width + self.margin,
                y=self.margin,
                w=self.output_box_width - 2 * self.margin,
                h=self.h - rect.height - 2 * self.margin,
                color=self.output_color,
            )

            pygame.display.flip()

            self.clock.tick(self.fps)

        pygame.quit()

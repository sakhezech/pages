import dataclasses
import typing
from argparse import ArgumentParser
from collections.abc import Callable
from types import NoneType
from typing import Concatenate


def _add_args_from[**Pargs, Targs, **Pwrap, Twrap](_: Callable[Pargs, Targs]):
    type Combined = Callable[Concatenate[Callable[Pwrap, Twrap], Pargs], Targs]  # type: ignore

    def wrapper(func_to_wrap: Combined) -> Combined:
        return func_to_wrap

    return wrapper


@dataclasses.dataclass
class _Hint:
    name: str
    class_: Callable
    default: object


@_add_args_from(ArgumentParser)
def make_parser(func: Callable, *args, **kwargs) -> ArgumentParser:
    EMPTY = object()

    raw_hints = typing.get_type_hints(func)
    raw_hints.pop('return', None)
    defaults = func.__defaults__ or tuple()

    hints = [_Hint(name, class_, EMPTY) for name, class_ in raw_hints.items()]
    for hint_with_def, default in zip(hints[-len(defaults) :], defaults):
        hint_with_def.default = default

    parser = ArgumentParser(*args, **kwargs)
    for hint in hints:
        if not callable(hint.class_):
            possible_classes = [
                possible
                for possible in typing.get_args(hint.class_)
                if possible is not NoneType and callable(possible)
            ]

            if hint.default is EMPTY:
                raise ValueError('union types without defaults not allowed')
            if len(possible_classes) != 1:
                raise ValueError('unclear which callable use as constructor')

            hint.class_ = possible_classes[0]

        if hint.default is EMPTY:
            parser.add_argument(hint.name, type=hint.class_)
        else:
            parser.add_argument(
                f'--{hint.name}', type=hint.class_, default=hint.default
            )

    return parser


if __name__ == '__main__':
    from .__version__ import __version__
    from .builder import PageBuilder, serve

    parser = make_parser(PageBuilder.__init__, prog='pagebuilder')
    parser.add_argument('-a', '--addr', default=None)
    parser.add_argument(
        '-v', '--version', action='version', version=__version__
    )
    args = parser.parse_args()
    builder_args = args.__dict__.copy()
    addr_port: str = builder_args.pop('addr')

    builder = PageBuilder(**builder_args)
    if addr_port:
        addr, _, port = addr_port.partition(':')
        with builder:
            serve(addr, int(port), builder.dist_path)
    else:
        builder.build()

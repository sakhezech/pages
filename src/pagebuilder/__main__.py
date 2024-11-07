from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from .__version__ import __version__
from .builder import PageBuilder, serve


def cli(argv: Sequence[str] | None = None) -> None:
    parser = ArgumentParser(
        prog='pagebuilder',
        description='a static site generator i built',
    )

    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=__version__,
    )

    parser.add_argument(
        '-w',
        '--watch',
        metavar='ADDR',
        nargs='?',
        const='localhost:5000',
        default=None,
        help="watcher mode (serves by default on 'localhost:5000')",
    )

    parser.add_argument(
        '--serve-dir',
        type=Path,
        default=None,
        help="""
        directory to serve from
        (use if impossible to imply from where to serve)
        """,
    )

    builder_select_group = parser.add_mutually_exclusive_group()

    builder_select_group.add_argument(
        '--args',
        metavar='ARG',
        nargs='*',
        help="""
        list of arguments for a builder in order 
        (pages_path,
        templates_path,
        assets_path,
        dist_path,
        extension (defaults to '.html'),
        data_start (defaults to '<!-- YAML:\\n'),
        data_end (defaults to '-->\\n'))
        """,
    )

    builder_select_group.add_argument(
        '-b',
        '--builder',
        action='append',
        help="""
        builder instance to run, in the format '<module>:<instance>'
        (can be used multiple times)
        """,
    )

    args = parser.parse_args(argv)
    builders: list[PageBuilder] = []
    if args.builder:
        for builder_path in args.builder:
            import_path, _, builder_name = builder_path.partition(':')
            module = __import__(import_path)
            builder = getattr(module, builder_name, None)
            if not isinstance(builder, PageBuilder):
                raise ValueError(f'not a builder: {builder}')
            builders.append(builder)
    else:
        if not 4 <= len(args.args) <= 7:
            raise ValueError(
                'number of arguments should be between '
                f'4 and 7: {len(args.args)}'
            )
        paths = [Path(p) for p in args.args[:4]]
        kwargs = {
            key: val
            for key, val in zip(
                ('ext', 'data_start', 'data_end'), args.args[4:]
            )
        }
        builder = PageBuilder(*paths, **kwargs)
        builders.append(builder)

    if args.watch:
        if not args.serve_dir:
            if len(builders) == 1:
                args.serve_dir = builders[0].dist_path
            else:
                raise ValueError(
                    'with 2 or more builders and no --serve-dir '
                    'impossible to imply from where to serve'
                )

        addr, _, port = args.watch.partition(':')
        try:
            for builder in builders:
                builder.observe()
            serve(addr, int(port), args.serve_dir)
        finally:
            for builder in builders:
                builder.stop_observing()
    else:
        for builder in builders:
            builder.build()


if __name__ == '__main__':
    cli()

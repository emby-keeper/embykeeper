from typing import Any, Iterable, Union

import click


class CommandWithOptionalFlagValues(click.Command):
    def parse_args(self, ctx, args):
        """Translate any flag `--opt=value` as flag `--opt` with changed flag_value=value"""
        flags = [
            o for o in self.params if isinstance(o, click.Option) and o.is_flag and not isinstance(o.flag_value, bool)
        ]
        prefixes = {p: o for o in flags for p in o.opts if p.startswith("--")}
        for i, flag in enumerate(args):
            flag = flag.split("=")
            if flag[0] in prefixes and len(flag) > 1:
                prefixes[flag[0]].flag_value = flag[1]
                args[i] = flag[0]

        return super(CommandWithOptionalFlagValues, self).parse_args(ctx, args)


def to_iterable(var: Union[Iterable, Any]):
    if var is None:
        return ()
    if isinstance(var, str) or not isinstance(var, Iterable):
        return (var,)
    else:
        return var

#!/usr/bin/env python
# coding: utf8
from __future__ import unicode_literals

import sys
import argparse
import itertools

from configparser import (BasicInterpolation, DuplicateOptionError,
                          DuplicateSectionError, SectionProxy,
                          MissingSectionHeaderError)

from clldutils.inifile import INI as ClldIni


class BasicReadInterpolation (BasicInterpolation):
    """Interpolation as implemented in the classic ConfigParser.

    The option values can contain format strings which refer to other values in
    the same section or the parser's default section.

    For example:

        something: %(dir)s/whatever

    would resolve the "%(dir)s" to the value of dir.  All reference
    expansions are done early, at read time. If a user needs to use a
    bare % in a configuration file, she can escape it by writing
    %%. Other % usage is considered a user error and raises
    `InterpolationSyntaxError'.

    This class, together with INI, handles multiline interpolation
    line by line, so

        val: line1
          line2
          %(val)s
          line4

    would be expanded at read-time of line 3, therefore to

        val: line1
          line2
          line1
          line2
          line4

    """

    def before_read(self, parser, section, option, value):
        lines = []
        interpolations = dict(parser[parser.default_section])
        interpolations.update(parser[section])
        self._interpolate_some(
            parser, option, lines, value, section, interpolations, 1)

        # Because we expect work with the raw data up to here, we may
        # have substituted a list. A list would come from parsing a
        # multi-line option.

        return "".join([
            "\n".join(l) if isinstance(l, list) else l
            for l in lines])

    def before_get(self, parser, section, option, value, defaults):
        return value


class INI (ClldIni):
    def _read(self, fp, fpname):
        """Parse a sectioned configuration file.

        Each section in a configuration file contains a header, indicated by
        a name in square brackets (`[]'), plus key/value options, indicated by
        `name' and `value' delimited with a specific substring (`=' or `:' by
        default).

        Values can span multiple lines, as long as they are indented deeper
        than the first line of the value. Depending on the parser's mode, blank
        lines may be treated as parts of multiline values or ignored.

        Configuration files may include comments, prefixed by specific
        characters (`#' and `;' by default). Comments may appear on their own
        in an otherwise empty line or may be entered in lines holding values or
        section names.
        """
        elements_added = set()
        cursect = None                        # None, or a dictionary
        sectname = None
        optname = None
        lineno = 0
        indent_level = 0
        e = None                              # None, or an exception
        for lineno, line in enumerate(fp, start=1):
            comment_start = sys.maxsize
            # strip inline comments
            inline_prefixes = {p: -1 for p in self._inline_comment_prefixes}
            while comment_start == sys.maxsize and inline_prefixes:
                next_prefixes = {}
                for prefix, index in inline_prefixes.items():
                    index = line.find(prefix, index + 1)
                    if index == -1:
                        continue
                    next_prefixes[prefix] = index
                    if index == 0 or (index > 0 and line[index - 1].isspace()):
                        comment_start = min(comment_start, index)
                inline_prefixes = next_prefixes
            # strip full line comments
            for prefix in self._comment_prefixes:
                if line.strip().startswith(prefix):
                    comment_start = 0
                    break
            if comment_start == sys.maxsize:
                comment_start = None
            value = line[:comment_start].strip()
            if not value:
                if self._empty_lines_in_values:
                    # add empty line to the value, but only if there was no
                    # comment on the line
                    if ((comment_start is None and
                         cursect is not None and
                         optname and
                         cursect[optname] is not None)):
                        # newlines added at join
                        cursect[optname].append('')
                else:
                    # empty line marks end of value
                    indent_level = sys.maxsize
                continue

            # continuation line?
            first_nonspace = self.NONSPACECRE.search(line)
            cur_indent_level = first_nonspace.start() if first_nonspace else 0
            if ((cursect is not None and
                 optname and cur_indent_level > indent_level)):

                # ====================================================
                # This is the thing that makes this different from the
                # basic ConfigParser: Do the before_read interpolation
                # *before* writing the value back!
                value = self._interpolation.before_read(
                    self, sectname, optname, value)
                # ====================================================

                cursect[optname].append(value)
            # a section header or option header?
            else:
                indent_level = cur_indent_level
                # is it a section header?
                mo = self.SECTCRE.match(value)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        if self._strict and sectname in elements_added:
                            raise DuplicateSectionError(sectname, fpname,
                                                        lineno)
                        cursect = self._sections[sectname]
                        elements_added.add(sectname)
                    elif sectname == self.default_section:
                        cursect = self._defaults
                    else:
                        cursect = self._dict()
                        self._sections[sectname] = cursect
                        self._proxies[sectname] = SectionProxy(self, sectname)
                        elements_added.add(sectname)
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    mo = self._optcre.match(value)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        if not optname:
                            e = self._handle_error(e, fpname, lineno, line)
                        optname = self.optionxform(optname.rstrip())
                        if ((self._strict and
                             (sectname, optname) in elements_added)):
                            raise DuplicateOptionError(sectname, optname,
                                                       fpname, lineno)
                        elements_added.add((sectname, optname))
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            optval = optval.strip()

                            # =========================================
                            # This is the thing that makes this
                            # different from the basic ConfigParser:
                            # Do the before_read interpolation
                            # *before* writing the value back!
                            optval = self._interpolation.before_read(
                                self, sectname, optname, optval)
                            # =========================================

                            cursect[optname] = [optval]
                        else:
                            # valueless option handling
                            cursect[optname] = None
                    else:
                        # a non-fatal parsing error occurred. set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        e = self._handle_error(e, fpname, lineno, line)
        self._join_multiline_values()
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

    def _join_multiline_values(self):
        defaults = self.default_section, self._defaults
        all_sections = itertools.chain((defaults,),
                                       self._sections.items())
        for section, options in all_sections:
            for name, val in options.items():
                if isinstance(val, list):
                    val = '\n'.join(val).rstrip()
                options[name] = val


def main(*args):
    """Execute CLI functionality.

    Parse command line arguments to find config files and distill a an
    aggregated, interpolated configuration from them.

    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Combine multiple configuration files into one.")
    parser.add_argument(
        "config",
        type=argparse.FileType("r"),
        help="ConfigParser-style configuration file(s)",
        default=None,
        nargs="+")
    parser.add_argument(
        "-o", "--output",
        type=argparse.FileType("w"),
        help="Output filename, for example `-o gold.ini`",
        default=sys.stdout)
    args = parser.parse_args(args or None)

    config = INI(interpolation=BasicReadInterpolation())
    for file in args.config:
        config.read_file(file)

    # We would like to use clldutils.INI.write directly, but it does
    # not support file objects.
    args.output.write(config.write_string())

    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv)

import re
import semver

from copy import copy
from enum import Enum
from functools import total_ordering


@total_ordering
class SemVer(object):
    def __init__(self, version):
        # type: (str) -> None
        self._version = version

    def __eq__(self, other):
        # type: (SemVer, SemVer) -> bool
        return semver.compare(self._version, other._version) == 0

    def __lt__(self, other):
        # type: (SemVer, SemVer) -> bool
        return semver.compare(self._version, other._version) < 0

    def __str__(self):
        # type: (SemVer) -> str
        return self._version


class ReqType(Enum):
    GREATER = ">="
    EXACT = "=="
    ANY = None


class ReqMergeException(RuntimeError):
    def __init__(self, req, other):
        # type: (Requirement, Requirement) -> None
        self.req = req
        self.other = other

    def __str__(self):
        # type: () -> str
        return "Cannot merge requirements {} and {}".format(self.req, self.other)


class Requirement(object):
    name_regex = re.compile("^[A-Za-z0-9_-]+$")

    def __init__(self, string):
        # type: (str) -> None
        for operation in [ReqType.GREATER, ReqType.EXACT, ReqType.ANY]:
            fields = string.split(operation.value)
            if len(fields) > 1:
                break

        self.name = fields[0]
        if not self.name_regex.match(self.name):
            raise RuntimeError("Invalid requirement name {}, must match {}".format(
                string, self.name_regex.pattern))

        self.operation = operation
        try:
            self.version = SemVer(fields[1])
        except IndexError:
            self.version = None

    def __str__(self):
        # type: () -> str
        return "{}{}{}".format(
            self.name,
            self.operation.value if self.operation.value else "",
            self.version if self.version else ""
        )

    def __add__(self, other):
        # type: (Requirement) -> Requirement
        if self.name != other.name:
            raise ReqMergeException(self, other)

        operation_map = {
            self.operation: self,
            other.operation: other,
        }
        operation_set = set(operation_map)

        if operation_set == {ReqType.EXACT}:
            if self.version == other.version:
                return copy(self)
            else:
                raise ReqMergeException(self, other)

        elif operation_set == {ReqType.EXACT, ReqType.GREATER}:
            if operation_map[ReqType.EXACT].version >= operation_map[ReqType.GREATER].version:
                return copy(operation_map[ReqType.EXACT])
            else:
                raise ReqMergeException(self, other)

        elif operation_set == {ReqType.GREATER}:
            out = copy(operation_map[ReqType.GREATER])
            out.version = max(self.version, other.version)
            return out

        elif ReqType.ANY in operation_set:
            if len(operation_set) == 1:
                return copy(self)
            else:
                out = copy(self)
                out.operation = (operation_set - {ReqType.ANY}).pop()
                out.version = operation_map[out.operation].version
                return out

import csv
import datetime

from urllib.parse import urlparse, parse_qsl

from beanquery import tables
from beanquery import query_compile

# Support conversions from all fundamental types supported by the BQL parser:
#
#   literal
#       =
#       | date
#       | decimal
#       | integer
#       | string
#       | null
#       | boolean
#       ;
#


def _parse_bool(value):
    x = value.strip().lower()
    if x == '1' or x == 'true':
        return True
    if x == '0' or x == 'false':
        return False
    raise ValueError(value)


_TYPES_TO_PARSERS = {
    bool: _parse_bool,
    datetime.date: datetime.date.fromisoformat,
}


class Column(query_compile.EvalColumn):
    def __init__(self, key, datatype, func):
        super().__init__(datatype)
        self.key = key
        self.func = func

    def __call__(self, row):
        return self.func(row[self.key])


class Table(tables.Table):
    def __init__(self, name, columns, data, header=False, **fmtparams):
        self.name = name
        self.data = data
        self.header = header
        # Skip white space after field separator by default to make parsing
        # columns accordingly to their type easier, unless the setting is
        # overridden by the user.
        fmtparams.setdefault('skipinitialspace', True)
        self.reader = csv.reader(data, **fmtparams)
        self.columns = {}
        for cname, ctype in columns:
            converter = _TYPES_TO_PARSERS.get(ctype, ctype)
            self.columns[cname] = Column(len(self.columns), ctype, converter)

    def __iter__(self):
        self.data.seek(0)
        it = iter(self.reader)
        if self.header:
            next(it)
        return it


def create(name, columns, using):
    parts = urlparse(using)
    filename = parts.path
    params = dict(parse_qsl(parts.query))
    encoding = params.pop('encoding', None)
    header = params.pop('header', columns is None)
    if filename:
        data = open(filename, encoding=encoding)
    return Table(name, columns, data, header=header, **params)

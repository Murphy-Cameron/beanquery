__copyright__ = "Copyright (C) 2014-2016  Martin Blais"
__license__ = "GNU GPLv2"

import datetime
import io
import unittest
import collections
from decimal import Decimal
from itertools import zip_longest

from beancount.core.number import D
from beancount.core.amount import A
from beancount.core import inventory
from beancount.core import position
from beancount.core import display_context
from beanquery import query_render



class ColumnRendererBase(unittest.TestCase):

    # pylint: disable=not-callable
    RendererClass = None

    def setUp(self):
        dcontext = display_context.DisplayContext()
        dcontext.update(D('1.00'), 'USD')
        dcontext.update(D('1.00'), 'CAD')
        dcontext.update(D('1.0000'), 'USD')
        dcontext.update(D('1.0000'), 'USD')
        dcontext.update(D('1.000'), 'HOOL')
        dcontext.update(D('1'), 'CA')
        dcontext.update(D('1.00'), 'AAPL')
        self.ctx = query_render.RenderContext(dcontext, expand=True)

    def get(self, *values):
        rdr = self.RendererClass(self.ctx)
        for value in values:
            rdr.update(value)
        rdr.prepare()
        return rdr

    def prepare(self, values):
        renderer = self.renderer(self.ctx)
        for value in values:
            renderer.update(value)
        renderer.prepare()
        return renderer

    def render(self, values):
        renderer = self.prepare(values)
        width = renderer.width()
        strings = [renderer.format(value) for value in values]
        self.assertTrue(all(len(s) == width for s in strings))
        return strings


class ObjectRenderer(ColumnRendererBase):

    renderer = query_render.ObjectRenderer

    def test_object(self):
        self.assertEqual(self.render(["foo", 1, D('1.23'), datetime.date(1970, 1, 1)]), [
            'foo       ',
            '1         ',
            '1.23      ',
            '1970-01-01',
        ])


class TestBoolRenderer(ColumnRendererBase):

    renderer = query_render.BoolRenderer

    def test_bool(self):
        self.assertEqual(self.render([True, True]), [
            'TRUE',
            'TRUE',
        ])
        self.assertEqual(self.render([False, True]), [
            'FALSE',
            'TRUE ',
        ])
        self.assertEqual(self.render([False, False]), [
            'FALSE',
            'FALSE',
        ])




class TestStringRenderer(ColumnRendererBase):

    renderer = query_render.StringRenderer

    def test_string(self):
        self.assertEqual(self.render(['a', 'bb', 'ccc', '']), [
            'a  ',
            'bb ',
            'ccc',
            '   ',
        ])


class TestSetRenderer(ColumnRendererBase):

    renderer = query_render.SetRenderer

    def test_stringset(self):
        self.ctx.listsep = '+'
        self.assertEqual(self.render([{}, {'aaaa'}, {'bb', 'ccc'}]), [
            '      ',
            'aaaa  ',
            'bb+ccc',
        ])


class TestDateRenderer(ColumnRendererBase):

    renderer = query_render.DateRenderer

    def test_date(self):
        self.assertEqual(self.render([datetime.date(2014, 10, 3)]), ['2014-10-03'])

class TestIntegerRenderer(ColumnRendererBase):

    RendererClass = query_render.IntegerRenderer

    def test_integers(self):
        rdr = self.get(1, 222, 33)
        self.assertEqual('  0', rdr.format(0))
        self.assertEqual('  1', rdr.format(1))
        self.assertEqual('444', rdr.format(444))

    def test_integers_negative(self):
        rdr = self.get(1, -222, 33)
        self.assertEqual('   0', rdr.format(0))
        self.assertEqual('   1', rdr.format(1))
        self.assertEqual(' 444', rdr.format(444))
        self.assertEqual('-444', rdr.format(-444))

    def test_overflow(self):
        rdr = self.get(1, 100, 1000)
        self.assertEqual('   1', rdr.format(1))
        # Note: Unfortunately we can't quite prevent it with a single format
        # string, but we don't really need to, so we won't bother.
        self.assertEqual('3456789', rdr.format(3456789))

    def test_zeros_only(self):
        rdr = self.get(0)
        self.assertEqual('1', rdr.format(1))



class TestDecimalRenderer(ColumnRendererBase):

    RendererClass = query_render.DecimalRenderer

    def test_integer(self):
        rdr = self.get(D('1'))
        self.assertEqual('2', rdr.format(D('2')))

    def test_integers(self):
        rdr = self.get(D('1'), D('222'), D('33'))
        self.assertEqual('444', rdr.format(D('444')))

    def test_fractional(self):
        rdr = self.get(D('1.23'), D('1.2345'), D('2.345'))
        self.assertEqual('1     ', rdr.format(D('1')))
        self.assertEqual('2.3456', rdr.format(D('2.34567890')))

    def test_mixed(self):
        rdr = self.get(D('1000'), D('0.12334'))
        self.assertEqual('   1      ', rdr.format(D('1')))

    def test_zero_integers(self):
        rdr = self.get(D('0.1234'))
        self.assertEqual('1     ', rdr.format(D('1')))

    def test_nones(self):
        rdr = self.get(None, D('0.1234'), None)
        self.assertEqual('1     ', rdr.format(D('1')))
        self.assertEqual('      ', rdr.format(None))

    def test_virgin(self):
        rdr = self.get()
        self.assertEqual('', rdr.format(None))


class TestAmountRenderer(ColumnRendererBase):

    RendererClass = query_render.AmountRenderer

    def test_single_frac(self):
        pos = A('100.00 USD')
        rdr = self.get(pos)
        self.assertEqual('100.00   USD',
                         rdr.format(pos))

    def test_single_int(self):
        pos = A('5 HOOL')
        rdr = self.get(pos)
        self.assertEqual('5     HOOL',
                         rdr.format(pos))

    def test_many(self):
        amounts = [A(x)
                   for x in ('0.0001 USD', '20.002 HOOL', '33 CA', '1098.20 AAPL')]
        rdr = self.get(*amounts)
        self.assertEqual(['   0.0001 USD ',
                          '  20.002  HOOL',
                          '  33      CA  ',
                          '1098.20   AAPL'],
                         [rdr.format(amount_) for amount_ in amounts])



class TestPositionRenderer(ColumnRendererBase):

    RendererClass = query_render.PositionRenderer

    def test_various(self):
        pos = position.from_string('100.00 USD')
        rdr = self.get(pos)
        self.assertEqual('100.00   USD',
                         rdr.format(pos))

        pos = position.from_string('5 HOOL {500.23 USD}')
        rdr = self.get(pos)
        self.assertEqual('5     HOOL {500.23   USD}',
                         rdr.format(pos))


class TestInventoryRenderer(ColumnRendererBase):

    RendererClass = query_render.InventoryRenderer

    def test_various(self):
        inv = inventory.from_string('100.00 USD')
        rdr = self.get(inv)
        self.assertEqual('100.00   USD',
                         rdr.format(inv))

        inv = inventory.from_string('5 HOOL {500.23 USD}')
        rdr = self.get(inv)
        self.assertEqual('5     HOOL {500.23   USD}',
                         rdr.format(inv))

        inv = inventory.from_string('5 HOOL {500.23 USD}, 12.3456 CAAD')
        rdr = self.get(inv)
        self.assertEqual([' 5      HOOL {500.23   USD}',
                          '12.3456 CAAD               '],
                         rdr.format(inv))


class TestQueryRender(unittest.TestCase):

    # pylint: disable=invalid-name
    def assertMultiLineEqualNoWS(self, expected, actual):
        for left, right in zip_longest(
                expected.strip().splitlines(), actual.strip().splitlines()):
            self.assertEqual(left.strip(), right.strip())

    def setUp(self):
        self.dcontext = display_context.DisplayContext()
        self.dcontext.update(D('1.00'), 'USD')
        self.dcontext.update(D('1.00'), 'CAD')

    # pylint: disable=invalid-name

    def test_render_str(self):
        types = [('account', str)]
        Row = collections.namedtuple('TestRow', [name for name, type in types])
        rows = [
            Row('Assets:US:Babble:Vacation'),
            Row('Expenses:Vacation'),
            Row('Income:US:Babble:Vacation'),
        ]
        oss = io.StringIO()
        query_render.render_text(types, rows, self.dcontext, oss)
        # FIXME:
        # with box():
        #     print(oss.getvalue())

    def test_render_Decimal(self):
        types = [('number', Decimal)]
        Row = collections.namedtuple('TestRow', [name for name, type in types])
        rows = [
            Row(D('123.1')),
            Row(D('234.12')),
            Row(D('345.123')),
            Row(D('456.1234')),
            Row(D('3456.1234')),
        ]
        oss = io.StringIO()
        query_render.render_text(types, rows, self.dcontext, oss)
        self.assertMultiLineEqualNoWS("""
           number
           ---------
            123.1
            234.12
            345.123
            456.1234
           3456.1234
        """, oss.getvalue())

        # Test it with commas too.
        # FIXME: This should ideally render with commas, but the renderers don't
        # support that yet. I wrote the test to show it.  See discussion at
        # https://groups.google.com/d/msgid/beancount/CAK21%2BhMdq4KtZrm7pX9EZ1-tRWi7THMWzybS5B%3Dumb6OSK03Qw%40mail.gmail.com
        self.dcontext.set_commas(True)
        oss = io.StringIO()
        query_render.render_text(types, rows, self.dcontext, oss)
        self.assertMultiLineEqualNoWS("""
            number
            ---------
             123.1
             234.12
             345.123
             456.1234
           3456.1234
        """, oss.getvalue())



# Add a test like this, where the column's result ends up being zero wide.
# bean-query $L  "select account, sum(units(position)) from open on 2014-01-01
#   close on 2015-01-01 clear  where account ~ 'PnL'  group by 1"


if __name__ == '__main__':
    unittest.main()

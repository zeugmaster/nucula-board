"""Regression examples for copper contacts that ordinary continuity can accept."""
import unittest

from check_routing_quality import audit


def pad(name, x, y):
    return {'id': name, 'type': 'pad', 'net': 'signal', 'layers': [0], 'xy': [x, y],
            'poly': [[[x-.3, y-.3], [x+.3, y-.3], [x+.3, y+.3], [x-.3, y+.3]]]}


def trace(name, start, end, width=.2):
    return {'id': name, 'type': 'track', 'net': 'signal', 'layers': [0],
            'start': start, 'end': end, 'w': width}


class CopperContacts(unittest.TestCase):
    def check_items(self, *items):
        return audit({'items': list(items)})

    def test_centred_pad_entries_pass(self):
        self.assertTrue(self.check_items(pad('a', 0, 0), pad('b', 2, 0),
                                        trace('t', [0, 0], [2, 0]))['passed'])

    def test_touching_end_caps_are_not_a_robust_junction(self):
        result = self.check_items(pad('a', 0, 0), pad('b', 2, 0),
                                  trace('t1', [0, 0], [.95, 0]),
                                  trace('t2', [1.1, 0], [2, 0]))
        self.assertEqual(result['statistics']['weak_connection_groups'], 1)
        self.assertEqual(result['statistics']['shallow_ends'], 2)

    def test_grazing_pad_entry_fails(self):
        result = self.check_items(pad('a', 0, 0), pad('b', 2, 0),
                                  trace('t', [0, 0], [1.61, 0]))
        self.assertEqual(result['statistics']['weak_connection_groups'], 1)
        self.assertEqual(result['statistics']['shallow_ends'], 1)

    def test_short_segment_buried_in_pad_is_not_a_routing_runt(self):
        result = self.check_items(pad('a', 0, 0), pad('b', 2, 0),
                                  trace('t1', [0, 0], [.05, 0]),
                                  trace('t2', [.05, 0], [2, 0]))
        self.assertTrue(result['passed'])

    def test_acute_return_bend_fails_even_with_full_connectivity(self):
        result = self.check_items(pad('a', 0, 0), pad('b', 0, 1),
                                  trace('t1', [0, 0], [1, 1]),
                                  trace('t2', [1, 1], [0, 1]))
        self.assertFalse(result['checks']['no_acute_two_segment_return_bends'])
        self.assertTrue(result['checks']['no_connections_depend_only_on_edge_overlap'])


if __name__ == '__main__':
    unittest.main()

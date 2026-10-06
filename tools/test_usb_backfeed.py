#!/usr/bin/env python3
"""Fault injection: a self-consistent schematic and PCB can still backfeed."""
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from check_usb_backfeed import ROOT, audit
from kicad_sexpr import child, children, dump, parse, uq


class BackfeedTests(unittest.TestCase):
    def test_saved_design(self):
        self.assertTrue(audit(ROOT/'nucula-v2.kicad_pcb', ROOT/'docs/netlist.xml')['passed'])

    def mutate_pin(self, ref, number, target_ref, target_pin, failing_check):
        xml = ET.parse(ROOT/'docs/netlist.xml')
        nets = xml.findall('./nets/net')
        source = next(n for n in nets if any(p.get('ref') == ref and p.get('pin') == number for p in n))
        target = next(n for n in nets if any(p.get('ref') == target_ref and p.get('pin') == target_pin for p in n))
        node = next(p for p in source if p.get('ref') == ref and p.get('pin') == number)
        source.remove(node)
        target.append(node)
        board = parse((ROOT/'nucula-v2.kicad_pcb').read_text())
        fp = next(f for f in children(board, 'footprint') if any(
            uq(p[1]) == 'Reference' and uq(p[2]) == ref for p in children(f, 'property')))
        pad = next(p for p in children(fp, 'pad') if uq(p[1]) == number)
        import json
        child(pad, 'net')[-1] = json.dumps(target.get('name').replace(' / ', ' {slash} '))
        with tempfile.TemporaryDirectory() as tmp:
            pcb, net = Path(tmp)/'fault.kicad_pcb', Path(tmp)/'fault.xml'
            pcb.write_text(dump(board)); xml.write(net)
            result = audit(pcb, net)
        self.assertTrue(result['checks']['all_affected_PCB_pads_match_schematic'])
        self.assertFalse(result['checks'][failing_check])
        self.assertFalse(result['passed'])

    def test_data_TVS_attached_to_VBUS(self):
        self.mutate_pin('U4', '3', 'C14', '1', 'data_TVS_has_no_supply_or_VBUS_connection')

    def test_switch_permanently_enabled(self):
        self.mutate_pin('U10', '9', 'U10', '5', 'active_low_enable_is_driven_by_existing_VBUS_detector')

    def test_wrong_switch_port_selected(self):
        self.mutate_pin('U10', '1', 'U10', '10', 'switch_select_and_ground_are_grounded')

    def test_VBUS_used_as_switch_supply(self):
        self.mutate_pin('U10', '10', 'C14', '1', 'switch_3V3_supply_is_decoupled')

    def test_unused_port_bridged(self):
        self.mutate_pin('U10', '3', 'U10', '4', 'switch_unused_port_is_unconnected')


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Regression: matching schematic/PCB nets alone must not accept a reversed panel."""
import copy
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from check_display_mapping import ROOT, audit, props
from kicad_sexpr import child, children, dump, parse, uq


class MountedDisplayTests(unittest.TestCase):
    def test_saved_design_matches_mounted_panel(self):
        self.assertTrue(audit(ROOT / 'nucula-v2.kicad_pcb', ROOT / 'docs/netlist.xml')['passed'])

    def test_reversing_both_schematic_and_pcb_is_detected(self):
        board = parse((ROOT / 'nucula-v2.kicad_pcb').read_text())
        ds = next(f for f in children(board, 'footprint') if props(f)['Reference'] == 'DS1')
        pads = {int(uq(p[1])): p for p in children(ds, 'pad') if uq(p[1]).isdigit()}
        nets = {number: copy.deepcopy(child(pad, 'net')) for number, pad in pads.items()}
        for number, pad in pads.items():
            child(pad, 'net')[:] = nets[25-number]
        xml = ET.parse(ROOT / 'docs/netlist.xml')
        for pin in xml.findall('./nets/net/node'):
            if pin.get('ref') == 'DS1':
                pin.set('pin', str(25-int(pin.get('pin'))))
        with tempfile.TemporaryDirectory() as tmp:
            pcb, netlist = Path(tmp) / 'reversed.kicad_pcb', Path(tmp) / 'netlist.xml'
            pcb.write_text(dump(board))
            xml.write(netlist)
            result = audit(pcb, netlist)
        # The faulty schematic and PCB still agree with each other on every pad.
        self.assertTrue(all(r['pcb_net'] == r['schematic_net'] for r in result['contacts_left_to_right']))
        self.assertFalse(result['checks']['all_24_physical_contacts_match_panel'])
        self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()

"""Mutation checks for the production NFC freeze; run with KiCad Python."""
import tempfile
import unittest
from pathlib import Path
try:
    import pcbnew
except ImportError:
    raise unittest.SkipTest('Run NFC mutation checks separately with KiCad Python')
from check_nfc_rev_a import audit, ROOT, footprints
from kicad_sexpr import parse, dump, child, children

class NFCFreezeTest(unittest.TestCase):
    def check_mutation(self, edit, expected):
        tree = parse((ROOT/'nucula-v2.kicad_pcb').read_text())
        edit(tree)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'changed.kicad_pcb'
            path.write_text(dump(tree))
            report = audit(path)
            self.assertFalse(report['passed'])
            self.assertFalse(report['checks'][expected])

    def test_current_board(self):
        self.assertTrue(audit()['passed'])

    def test_controller_move_detected(self):
        self.check_mutation(lambda t: child(footprints(t)['U6'],'at').__setitem__(2,'63.55'),
                            'all_43_NFC_footprints_identical_except_reviewed_substitutions')

    def test_match_value_detected(self):
        def edit(t):
            for p in children(footprints(t)['C30'],'property'):
                if p[1]=='"Value"':p[2]='"82p"'
        self.check_mutation(edit,'all_43_NFC_footprints_identical_except_reviewed_substitutions')

    def test_small_via_resize_detected(self):
        def edit(t):
            for v in children(t,'via'):
                if child(v,'size')[1]=='0.45':
                    child(v,'size')[1]='0.7';break
        self.check_mutation(edit,'all_NFC_tracks_and_vias_identical')

    def test_substituted_inductor_move_detected(self):
        self.check_mutation(lambda t: child(footprints(t)['L2'],'at').__setitem__(1,'80'),
                            'all_43_NFC_footprints_identical_except_reviewed_substitutions')

    def test_unreviewed_substitute_detected(self):
        def edit(t):
            for p in children(footprints(t)['L2'],'property'):
                if p[1]=='"MPN"':p[2]='"0805CS-151XJRC"'
        self.check_mutation(edit,'all_43_NFC_footprints_identical_except_reviewed_substitutions')

    def test_substitute_pad_change_detected(self):
        def edit(t):
            child(children(footprints(t)['L2'],'pad')[0],'size')[1]='1.1'
        self.check_mutation(edit,'all_43_NFC_footprints_identical_except_reviewed_substitutions')

    def test_crossing_trace_with_external_endpoints_detected(self):
        self.check_mutation(lambda t: t.append(parse('(segment (start 50 60) (end 110 60) (width 0.2) (layer "F.Cu") (net "GND"))')),
                            'all_NFC_tracks_and_vias_identical')

    def test_generic_stackup_detected(self):
        self.check_mutation(lambda t: child(child(child(t,'setup'),'stackup'),'copper_finish').__setitem__(1,'"HASL"'),
                            'submitted_stackup_and_via_process_identical')

if __name__=='__main__':unittest.main()

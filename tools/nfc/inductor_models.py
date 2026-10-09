"""Manufacturer typical RF models; parameters are not guaranteed corner limits.

Coilcraft doc 158-27 (0805HP) and 158-6 rev 2025-01-16 (0805CS).
Topology: Rdc + ((k*sqrt(f) + jwL) || (Rpar + 1/jwC)).
"""
MODELS = {
    '0805HP-151XGRC': dict(rdc=.288, k=1.554e-4, l=148.8e-9, c=.135e-12, rpar=10.),
    '0805CS-151XGLC': dict(rdc=.56, k=2.23e-4, l=149e-9, c=.110e-12, rpar=24.),
}
SELECTED = '0805CS-151XGLC'

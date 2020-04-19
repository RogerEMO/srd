from srd import add_params_as_attr
import os
module_dir = os.path.dirname(os.path.dirname(__file__))
from srd.cpp import cpp 
from srd import qpip 
from srd import ei
import numpy as np

def create_stub():
        lines = ['cpp','cpp_supp','qpip','ei']
        return dict(zip(lines,np.zeros(len(lines))))

class payroll:
    """
    Calcul des cotisations sociales.

    Calcul des cotisations sociales provenant de l'assurance emploi, le RQAP (Québec) et le RRQ (RPC).

    Parameters
    ----------
    year: int 
        année pour le calcul 
    """
    def __init__(self, year):
        self.year = year
        self.qpp_rules = cpp.rules(qpp=True)
        self.cpp_rules = cpp.rules(qpp=False)
        self.qpip_prog = qpip.program(self.year)
        self.ei_prog = ei.program(self.year)
        return 
    def compute(self, hh):
        """
        Fonction qui fait le calcul et crée le rapport de cotisations.

        Parameters
        ----------
        hh: Hhold
            instance de la classe Hhold
        """
        for p in hh.sp:
            p.payroll = create_stub()
            p.payroll['ei'] = self.ei_prog.contrib(p,hh)
            if hh.prov=='qc':
                p.payroll['qpip'] = self.qpip_prog.contrib(p,hh)
            base, supp = self.get_cpp_contrib(p,hh)
            p.payroll['cpp'] = base 
            p.payroll['cpp_supp'] = supp
        return
    def get_cpp_contrib(self, p, hh):
        """
        Fonction pour le calcul des cotisations RPC et RRQ.

        Parameters
        ----------
        p: Person
            instance de la classe Person 
        hh: Hhold
            instance de la classe Hhold
        
        Returns
        -------
        list de float 
            les montants des prestations de base et le supplément RRQ/RRQ
        """
        rules = self.qpp_rules if hh.prov == 'qc' else self.cpp_rules
        if (p.age < 18) | (p.age > 69):
            return 0.0, 0.0
        else:
            acc = cpp.account(byear=self.year - p.age, rules=rules)
            acc.MakeContrib(year=self.year, earn=p.inc_earn)
            hist = acc.history[p.age - 18]
            return hist.contrib, hist.contrib_s1+hist.contrib_s2   
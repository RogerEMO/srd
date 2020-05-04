from srd import add_params_as_attr, add_schedule_as_attr
import os
import numpy as np
module_dir = os.path.dirname(os.path.dirname(__file__))

def create_return():
        lines = ['gross_income','deductions','net_income','taxable_income','gross_tax_liability',
        'non_refund_credits','refund_credits','net_tax_liability']
        return dict(zip(lines,np.zeros(len(lines))))

class template:
    """
    Gabarit pour impôt fédéral.
    """

    def file(self, hh):
        """
        Fonction qui permet de calculer les impôts.

        Cette fonction est celle qui éxécute le calcul des impôts.

        Parameters
        ----------
        hh: Hhold
            instance de la classe Hhold
        """
        for p in hh.sp:
            p.fed_return = create_return()
            self.calc_gross_income(p)
            self.calc_deductions(p, hh)
            self.calc_net_income(p)
            self.calc_taxable_income(p)
        for p in hh.sp:
            self.calc_tax(p)
            self.calc_non_refundable_tax_credits(p)
            p.fed_return['net_tax_liability'] = max(0.0, p.fed_return['gross_tax_liability']
                - p.fed_return['non_refund_credits'])
            self.calc_refundable_tax_credits(p,hh)
            p.fed_return['net_tax_liability'] -= p.fed_return['refund_credits']

    def calc_gross_income(self,p):
        """
        Fonction qui calcule le revenu total (brutte).

        Cette fonction correspond au revenu total d'une personne au fin de l'impôt.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        """
        p.fed_return['gross_income'] = p.inc_earn + p.inc_self_earn + p.inc_oas + p.inc_gis + p.inc_cpp + p.inc_rpp + p.inc_othtax + p.inc_rrsp
        return
    def calc_net_income(self, p):
        """
        Fonction qui calcule le revenu net au sens de l'impôt.

        Cette fonction correspond au revenu net d'une personne au fin de l'impôt. On y soustrait les déductions.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        """
        p.fed_return['net_income'] =  p.fed_return['gross_income'] - p.fed_return['deductions']

    def calc_taxable_income(self,p):
        """
        Fonction qui calcule le revenu imposable au sens de l'impôt.

        Cette fonction correspond au revenu imposable d'une personne au fin de l'impôt. On y soustrait une portion des gains en capitaux.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        """
        p.fed_return['taxable_income'] = p.fed_return['net_income']
        return
    def calc_deductions(self, p, hh):
        """
        Fonction qui calcule les déductions.

        Cette fonction fait la somme des différentes déductions du contribuable.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        """
        p.fed_return['deductions'] = p.con_rrsp + p.inc_gis + self.chcare(p, hh)

    def chcare(self, p, hh):
        """
        Déduction pour frais de garde.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        hh: Hhold
            instance de la classe Hhold
        Returns
        -------
        float
            Montant de la déduction pour frais de garde

            Cette fonction calcule le montant reçu en fonction des frais de garde,
            de l'âge des enfants et du revenu le moins élevé du couple. Le montant
            est reçu par le conjoint qui a le revenu le moins élevé.
        """

        p_low_inc = min(hh.sp, key = lambda p: p.inc_earn + p.inc_self_earn)

        if p != p_low_inc or hh.child_care_exp == 0:
            return 0

        nkids_0_6 = len([d for d in hh.dep if d.age <= self.chcare_max_age_young])
        nkids_7_16 = len([d for d in hh.dep
                          if self.chcare_max_age_young < d.age <= self.chcare_max_age_old])
        max_chcare = nkids_0_6 * self.chcare_young + nkids_7_16 * self.chcare_old

        return min(max_chcare, hh.child_care_exp,
                   self.chcare_rate_inc * (p.inc_earn + p.inc_self_earn))

    def calc_tax(self, p):
        """
        Fonction qui calcule l'impôt à payer selon la table d'impôt.

        Cette fonction utilise la table d'impôt de l'année cours.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        """
        ind = np.searchsorted(self.l_brackets, p.fed_return['taxable_income'], 'right') - 1
        p.fed_return['gross_tax_liability'] = self.l_constant[ind] + \
            self.l_rates[ind] * (p.fed_return['taxable_income'] - self.l_brackets[ind])

    def calc_non_refundable_tax_credits(self, p):
        """
        Fonction qui calcule les crédits d'impôt non-remboursable.

        Cette fonction fait la somme de tous les crédits d'impôt modélisés.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        """
        p.fed_return['non_refund_credits'] = self.rate_non_ref_tax_cred * (self.basic_amount
            + self.get_age_cred(p) + self.get_pension_cred(p) + self.get_disabled_cred(p))

    def get_age_cred(self, p):
        """
        Crédit d'impôt selon l'âge.

        Ce crédit est non-remboursable.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        """
        amount = self.age_cred_amount if p.age >= self.min_age_cred else 0.0
        clawback = self.age_cred_claw_rate * max(0, p.fed_return['net_income'] - self.age_cred_exemption)
        return max(0, amount - clawback)

    def get_pension_cred(self, p):
        """
        Crédit d'impôt pour revenu de retraite.

        Ce crédit est non-remboursable.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        """
        return min(p.inc_rpp, self.pension_cred_amount)

    def get_disabled_cred(self, p):
        """
        Crédit d'impôt pour invalidité.

        Ce crédit est non-remboursable.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        """
        amount = self.disability_cred_amount if p.disabled else 0
        return amount
        # disabled dependent not taken into account (see lines 316 and 318)

    def calc_refundable_tax_credits(self, p, hh):
        """
        Fonction qui fait la somme des crédits remboursables.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        hh: Hhold
            instance de la classe Hhold
        """
        p.fed_return['refund_credits'] = self.abatment(p,hh) + self.ccb(p,hh) \
                                         + self.witb(p, hh) + self.witbds(p, hh) \
                                         + self.gst_hst_credit(p, hh)

    def abatment(self, p, hh):
        """
        Abattement du Québec à l'impôt fédéral.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        hh: Hhold
            instance de la classe Hhold
        Returns
        -------
        float
            Montant de l'abatement
        """
        if hh.prov == 'qc':
            return p.fed_return['net_tax_liability'] * self.rate_abatment_qc
        else:
            return 0.0

    def ccb(self,p,hh,iclaw=True):
        """
        Allocation canadienne pour enfants (CCB).

        Parameters
        ----------
        p: Person
            instance de la classe Person
        hh: Hhold
            instance de la classe Hhold
        Returns
        -------
        float
            Montant de la ACE (CCB)
        """
        num_ch_0_5 = sum([1 for d in hh.dep if d.age <= self.ccb_young_max_age])
        num_ch_6_17 = sum([1 for d in hh.dep
                        if self.ccb_young_max_age < d.age <= self.ccb_old_max_age])
        if num_ch_0_5 + num_ch_6_17 == 0:
            return 0
        if hh.couple and p.male and hh.sp[0].male != hh.sp[1].male:
            return 0 # heterosexual couple: mother receives benefit
        else:
            amount = num_ch_0_5 * self.ccb_young + num_ch_6_17 * self.ccb_old
            claw_num_ch = min(num_ch_0_5 + num_ch_6_17, self.ccb_max_num_ch)
            adj_fam_net_inc = sum([p.fed_return['net_income'] for p in hh.sp])

            l_rates_1 = [self.ccb_rate_1_1ch, self.ccb_rate_1_2ch,
                        self.ccb_rate_1_3ch, self.ccb_rate_1_4ch]
            d_rates_1 = {k+1: v for k, v in enumerate(l_rates_1)}
            l_rates_2 = [self.ccb_rate_2_1ch, self.ccb_rate_2_2ch,
                        self.ccb_rate_2_3ch, self.ccb_rate_2_4ch]
            d_rates_2 = {k+1: v for k, v in enumerate(l_rates_2)}
            if iclaw:
                if adj_fam_net_inc > self.ccb_cutoff_2:
                    clawback = (d_rates_2[claw_num_ch] * (adj_fam_net_inc - self.ccb_cutoff_2) +
                                d_rates_1[claw_num_ch] * (self.ccb_cutoff_2 - self.ccb_cutoff_1))
                elif adj_fam_net_inc > self.ccb_cutoff_1:
                    clawback = d_rates_1[claw_num_ch] * (adj_fam_net_inc - self.ccb_cutoff_1)
                else:
                    clawback = 0
            else :
                clawback = 0.0
            if hh.couple and hh.sp[0].male == hh.sp[1].male:
                return max(0, amount - clawback) / 2 # same sex couples get 1/2 each
            else:
                return max(0, amount - clawback)


    def witb(self,p,hh):
        """
        Prestation fiscale pour le revenu de travail (WITB). A partir de 2019,
        cela devient l'Allocation canadienne pour les travailleurs (CWB).

        Dans le cas d'un couple, la prestation est répartie au pro-rata des revenus du travail.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        hh: Hhold
            instance de la classe Hhold
        Returns
        -------
        float
            Montant de la PFRT (WITB)
        """
        dep = (len([d for d in hh.dep if d.age <= self.witb_max_age_dep]) > 0)
        fam_work_inc = sum([p.inc_earn + p.inc_self_earn for p in hh.sp])

        if not hh.couple:
            base = self.witb_base_single_qc
            rate = self.witb_rate_single_dep_qc if dep else self.witb_rate_qc
            witb_max = self.witb_max_single_dep_qc if dep else self.witb_max_single_qc
            exemption = self.witb_exemption_single_dep_qc if dep else self.witb_exemption_single_qc
            factor = 1
        else:
            base = self.witb_base_couple_qc
            rate = self.witb_rate_couple_dep_qc if dep else self.witb_rate_qc
            witb_max = self.witb_max_couple_dep_qc if dep else self.witb_max_couple_qc
            exemption = self.witb_exemption_couple_dep_qc if dep else self.witb_exemption_couple_qc
            if fam_work_inc > 0:
                factor = (p.inc_earn + p.inc_self_earn) / fam_work_inc
            else:
                factor = 1/2


        return factor * self.compute_witb_witbds(p, hh, rate, base, witb_max,
                                                 self.witb_claw_rate_qc, exemption)

    def witbds(self, p, hh):
        """
        Supplément pour invalidité à Prestation fiscale pour le revenu de travail (WITBDS).
        A partir de 2019, cela devient le supplément pour invalidité à l'Allocation canadienne pour les travailleurs.


        Parameters
        ----------
        p: Person
            instance de la classe Person
        hh: Hhold
            instance de la classe Hhold
        Returns
        -------
        float
            Montant de la SIPFRT (WITBDS)
        """
        if not p.disabled:
            return 0

        dep = len([d for d in hh.dep if d.age <= self.witb_max_age_dep]) > 0
        couple_dis = sum([p.disabled for p in hh.sp]) == 2

        claw_rate = self.witb_dis_claw_rate_qc
        if not hh.couple:
            rate = self.witb_dis_rate_single_qc
            exemption = self.witb_dis_exemption_single_dep_qc if dep else self.witb_dis_exemption_single_qc
        else:
            rate = self.witb_dis_rate_couple_qc
            exemption = self.witb_dis_exemption_couple_dep_qc if dep else self.witb_dis_exemption_couple_qc
            if couple_dis:
                claw_rate = self.witb_dis_couple_claw_rate_qc
                exemption = self.witb_dis_exemption_couple_dep_qc if dep else self.witb_dis_exemption_couple_qc

        return self.compute_witb_witbds(p, hh, rate, self.witb_dis_base_qc,
                                         self.witb_dis_max_qc, claw_rate, exemption)

    def compute_witb_witbds(self, p, hh, rate, base, witb_max, claw_rate, exemption):
        """
        Calcule de la prestation fiscale pour le revenu de travail.

        Parameters
        ----------
        p: Person
            instance de la classe Person
        hh: Hhold
            instance de la classe Hhold
        rate: float
            Taux appliqué au revenu du travail
        base: float
            Montant de base
        witb_max: float
            Montant maximal
        claw_rate:
            Taux de réduction
        exemption: float
            Exemption

        Returns
        -------
        float
            Montant de la PFRT (WITB) / SIPFRT (WITBDS)
        """
        fam_net_inc = sum([p.fed_return['net_income'] for p in hh.sp])
        fam_work_inc = sum([p.inc_earn + p.inc_self_earn for p in hh.sp])
        amount = rate * max(0, fam_work_inc - base)
        adj_amount = min(witb_max, amount)
        clawback = claw_rate * max(0, fam_net_inc - exemption)
        return max(0, adj_amount - clawback)

    def gst_hst_credit(self, p, hh):
        """
        Crédit pour la taxe sur les produits et services/taxe de vente harmonisée (TPS/TVH)

        Parameters
        ----------
        p: Person
            instance de la classe Person
        hh: Hhold
            instance de la classe Hhold
        Returns
        -------
        float
            Montant du crédit
        """
        fam_net_inc = sum([p.fed_return['net_income'] for p in hh.sp])
        nkids = len([d for d in hh.dep if d.age < self.gst_cred_kids_max_age])

        clawback = self.gst_cred_claw_rate * max(0, fam_net_inc - self.gst_cred_claw_cutoff)
        amount = self.gst_cred_base

        if hh.couple or nkids >= 1:
            amount += amount + nkids * self.gst_cred_other # single with kids works same as couple
        else:
            amount += min(self.gst_cred_other,
                          self.gst_cred_rate * max(0, fam_net_inc - self.gst_cred_base_amount))
        return amount / ( 1 + hh.couple)
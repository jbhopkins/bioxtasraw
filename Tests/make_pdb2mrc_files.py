import os
import bioxtasraw.RAWAPI as raw
import bioxtasraw.SASM as SASM

#calculate a scattering profile from glucose isomerase using pdb2mrc
models = ['./data/dammif_data/1XIB_4mer.pdb']
results = raw.pdb2mrc(models)
pdb2mrc = results["1XIB_4mer"][0]

#save the profile as a .ift file to retain the information?
info = {
    'dmax'          : pdb2mrc.side,         # Dmax
    'rg'            : pdb2mrc.Rg,           # Real space Rg
    'rger'          : 0.0,        # Real space rg error
    'i0'            : pdb2mrc.I0,           # Real space I0
    'i0er'          : 0.0,        # Real space I0 error
    'chisq'         : 0.0,            # Actual chi squared value
    'alpha'         : 0.0,        # log(Alpha) used for the IFT
    'qmin'          : pdb2mrc.q_calc[0],         # Minimum q
    'qmax'          : pdb2mrc.q_calc[-1],        # Maximum q
    'algorithm'     : 'PDB2MRC',       # Lets us know what algorithm was used to find the IFT
    'filename'      : 'gi_pdb2mrc_modelonly.ift'
    }

#there's no P(r) curve, so just replace it with the I(q) curve
ift = SASM.IFTM(pdb2mrc.I_calc, pdb2mrc.q_calc, pdb2mrc.Iq_calc[:,2], pdb2mrc.I_calc, pdb2mrc.q_calc, pdb2mrc.Iq_calc[:,2], pdb2mrc.I_calc, info, pdb2mrc.I_calc, pdb2mrc.q_calc)

raw.save_ift(ift, 'gi_pdb2mrc_modelonly.ift', './data')

#now do the same, but this time do the fit instead.
#calculate a scattering profile from glucose isomerase using pdb2mrc
models = ['./data/dammif_data/1XIB_4mer.pdb']
profile_names = ['./data/glucose_isomerase.dat']
profiles = raw.load_profiles(profile_names)
results = raw.pdb2mrc(models, profiles=profiles)
pdb2mrc = results["1XIB_4mer_glucose_isomerase"][0]

#save the profile as a .ift file to retain the information?
info = {
    'dmax'          : pdb2mrc.side,         # Dmax
    'rg'            : pdb2mrc.Rg,           # Real space Rg
    'rger'          : 0.0,        # Real space rg error
    'i0'            : pdb2mrc.I0,           # Real space I0
    'i0er'          : 0.0,        # Real space I0 error
    'chisq'         : pdb2mrc.chi2,            # Actual chi squared value
    'alpha'         : 0.0,        # log(Alpha) used for the IFT
    'qmin'          : pdb2mrc.q_calc[0],         # Minimum q
    'qmax'          : pdb2mrc.q_calc[-1],        # Maximum q
    'algorithm'     : 'PDB2MRC',       # Lets us know what algorithm was used to find the IFT
    'filename'      : 'gi_pdb2mrc_fit.ift'
    }

#there's no P(r) curve, so just replace it with the I(q) curve
ift = SASM.IFTM(pdb2mrc.I_calc, pdb2mrc.q_calc, pdb2mrc.Iq_calc[:,2], pdb2mrc.fit[:,1], pdb2mrc.fit[:,0], pdb2mrc.fit[:,2], pdb2mrc.fit[:,3], info, pdb2mrc.I_calc, pdb2mrc.q_calc)

raw.save_ift(ift, 'gi_pdb2mrc_fit.ift', './data')

print(ift.getParameter('chisq'))
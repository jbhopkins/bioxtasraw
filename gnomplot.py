#!/usr/bin/env python 

import numpy as np
from sys import argv
from matplotlib import pyplot as plt

# Parse GNOM.out files

qfull = []
qshort = []
Jexp = []
Jerr  = []
Jreg = []
Ireg = []

R = []
P = []
Perr = []

fname = argv[1]

print "reading ", fname

fline = open(fname).readlines()

i = 0

while (i < len(fline)):
      if (fline[i].find('The measure of inconsistency AN1 equals to') > -1): 
	      tmp = fline[i].split()
	      AN1 = float(tmp[7])
	      print "AN1 = ", AN1
	      break 
      i = i + 1

while (i < len(fline)):
      if (fline[i].find('S          J EXP       ERROR       J REG       I REG') > -1): break 
      i = i + 1

print "found data profile section at ",i

i = i + 2

# extract experimental and fitted profiles

while (i < len(fline)):

	     tmp = fline[i].split()

	     if (len(tmp) == 2):
		     qfull.append(float(tmp[0]))
		     Ireg.append(float(tmp[1]))
       	     elif (len(tmp)==5):
		     qfull.append(float(tmp[0]))
		     qshort.append(float(tmp[0]))
		     Jexp.append(float(tmp[1]))
		     Jerr.append(float(tmp[2]))
		     Jreg.append(float(tmp[3]))
		     Ireg.append(float(tmp[4]))
       	     else: 
		     break

	     i = i + 1
	 
# now search for P(r)

i = i + 6

while (i < len(fline)):

	     tmp = fline[i].split()
	     
	     if (len(tmp) == 3):
		     R.append(float(tmp[0]))
		     P.append(float(tmp[1]))
		     Perr.append(float(tmp[2]))
       	     else: 
		     break

	     i = i + 1


# Perceptual Criteria

Idif2 = ((np.array(Jexp) - np.array(Jreg))/Jerr)**2

DISCRP = np.sqrt(Idif2.sum()/(len(Jexp)-1) - AN1**2)

print "DISCRP = ",DISCRP


Ns = 0

Idif  = np.array(Jexp) - np.array(Jreg)

for k in np.arange(len(Jexp)-1):
	prod = Idif[k]*Idif[k+1]
	if (prod < 0): Ns = Ns + 1

print "SYSDEV",Ns/((len(Jexp)-1)/2.0)

# plots

plt.figure()

plt.semilogy(qfull,Ireg)
plt.semilogy(qshort,Jexp,'.')
plt.xlabel('q ($\AA^{-1}$)')
plt.ylabel('I')
plt.title(fname)

plt.figure()
plt.plot(R,P)
plt.xlabel('r ($\AA$)')
plt.ylabel('P(r)')
plt.title(fname)

plt.figure()

krat = np.array(qfull)*np.array(qfull)*np.array(Ireg)
krat2 = np.array(qshort)*np.array(qshort)*np.array(Jexp)

plt.plot(qfull,krat)
plt.plot(qshort,krat2)
plt.xlabel('q ($\AA^{-1}$)')
plt.ylabel('I*$q^{2}$')
plt.title(fname)
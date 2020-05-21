Bead model reconstructions
----------------------------------------------------------
.. _saxs_bead_models:

This tutorial covers basic principles and best practices for creating
bead model (dummy atom) reconstructions of macromolecule shape from
SAXS data. This is not a tutorial on how to use RAW for this type of analysis.
For that, please see the RAW tutorial for :ref:`DAMMIF/N <dammif>`.


Overview
^^^^^^^^^^^^^^^^^

A natural desired outcome for many SAXS experiments is determining the
'solution structure' of the sample, i.e. the structure of the macromolecule
as it exists in solution. Unfortunately, unlike crystallography, cryoEM,
and NMR, SAXS data cannot be used to generate a high resolution 3D shape
(though it can be used to constrain other methods of structure determination).
What SAXS can often provide, and what is a common end point of SAXS analysis,
is a low resolution shape reconstruction of the sample.

For many years, bead modeling was the state of the art approach
for generating these low resolution shape reconstructions. Recently,
other techniques have been developed, such as direct reconstruction of
the electron density at low resolutions. Despite this, bead modeling
remains the de facto standard for shape reconstruction.


Why do we do bead model reconstructions?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bead models, despite their low resolution, can be powerful tools for understanding
the system in solution. High resolution structures can be docked into the bead
model, allowing visual analysis of how well the high resolution structure
agrees with the solution structure. In the absence of other structure
information, bead models can be used to provide important
clues to the overall shape and size of the system, which can often be
enough to draw conclusions about important aspects of the macromolecular
function or interactions with other systems. Also, and perhaps almost
as important as the other considerations, they make pretty pictures to
put in your presentations and publications.

While bead modeling can be quite useful, it is important to always keep in
mind two things. First, it is very easy to get poor reconstructions, even
with good quality data, and you must carefully evaluate the results of your
reconstructions before using them. Second, SAXS is much more accurate at
hypothesis testing than it is at generating bead models, put another way
SAXS is very good at telling you what something isn't, but not so good
at telling you what it is. For example, if you want to compare a high
resolution structure to SAXS data and see if they agree, you are always
better off testing the calculated scattering profile of the high resolution
structure against the measured scattering profile than docking the structure
into the bead model.


How do we do an bead model reconstructions?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are a number of different programs available to do bead modeling, some
suited for general systems and some tuned for very specific applications
like reconstructions of membrane proteins with detergent halos. Regardless.
all of these methods share a similar approach.

#.  Generate a volume of beads (aka 'dummy atoms') and randomly assign the
    beads to be one of the allowed phases. In general approaches beads
    are solvent or macromolecule, but some programs allow more than 2 phases,
    such as differentiating between protein and RNA or macromolecule and lipid.
#.  Calculate a scattering profile from the bead model and fit that against the data.
#.  Flip a randomly chosen set of beads between phases (e.g. from solvent to
    macromolecule or vice versa).
#.  Recalculate the scattering profile from the model and the to the data.
#.  If the fit is better, accept the changes to the beads. If the fit is
    worse, accept the changes to the beads with some probability (avoids
    local minima).
#.  Repeat steps 3-5 until the convergence criteria is met.

Additional, programs usually impose physical constraints on the bead models
to improve the model. Common constraints are requiring connectivity of the model,
imposing penalties for extended models, and constraining the size of the model
based on the |Rg| and/or |Dmax|. The model refinement described in steps 3-5
above is usually done with simulated annealing.

It turns out that a scattering profile does not generate a unique reconstruction,
so to account for this a Monte Carlo like approach is taken where a number
(usually 10-20) of models are generated, and then averaged to give a consensus
reconstruction.

The most common program for creating bead model reconstructions (though far from
the only such program) is DAMMIF (or DAMMIN) [1-2] from the ATSAS package.
For the remainder of this tutorial we will exclusively discuss using
DAMMIF/N, though much of the discussion should apply to other programs as well.


Using DAMMIF/N for bead model reconstructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

DAMMIF is the most commonly used program for bead model reconstructions. Here
we discuss some of the practical aspects. A detailed tutorial of
:ref:`how to use DAMMIF in RAW <dammif>` is also available.

Input data
*************

DAMMIF requires a P(r) function generated by GNOM (.out file) as input. Note
that, as mentioned in the :ref:`IFT tutorial <saxs_ift>`, the scattering profile
for the IFT should be truncated to a maximum *q* value of 8/R\ :sub:`g` or *q*
~0.25-0.30 1/Angstrom, whichever is smaller. This is because the hydration layer
and internal structure are not modeled by DAMMIF, which leads to errors at
higher *q*. The truncation removes the potentially problematic higher *q* data.

Generating models
**********************

As bead modeling does not generate a unique solution. In order to generate a
reasonable solution, we create 10-20 bead model reconstructions and then average them.
I recommend 15 reconstructions. This means that we need to run DAMMIF 15 different
times.

The most accessible settings for DAMMIF are the Mode, Symmetry, and Anisometry.

**Mode:** For mode, options are Fast or Slow. Fast is quick, but less detailed, Slow is
the opposite. For final reconstruction, use Slow mode.

**Symmetry:** Adding in symmetry constraints can improve the reconstruction.
If you know the symmetry of the particle, you can specify this. However,
it is always recommend that you do an additional set of reconstructions
with P1 symmetry, to verify that the symmetry did not overly constrain the
reconstructions.

**Anisometry:** Adding in anisometry constraints can improve the reconstruction.
If you know the anisometry of the particle, you can specify this. However,
it is always recommend that you do an additional set of reconstructions
with no anisometry, to verify that the symmetry did not overly constrain the
reconstructions.

Additional advanced options are available, and are described in the
`DAMMIF manual <https://www.embl-hamburg.de/biosaxs/manuals/dammif.html>`_.

If you only want a quick look at the shape (such as when collecting data
at a beamline) 3 reconstructions  in Fast mode will work for that purpose.

Averaging and clustering models
**********************************

After models are generated the next step is to average and cluster the models.
Averaging generates a consensus shape from the individual models, and provides
statistics on how stable the reconstruction is. This is done with DAMAVER [3].
The average outputs both damaver.pdb and damfilt.pdb model files. These correspond
to two different consensus shapes of the model, loosely and tightly defined
respectively. However, neither of these models actually fits the data, and so
generally should not be used to display your reconstructions. DAMAVER will
also specify the most probably individual model. If you do not refine the
results of DAMAVER (below) you should use the most probable model as your
final result.

Clustering is done with DAMCLUST [4] and clusters of models that are more
similar to each other than they are to the rest of the models. This is a
way of assessing the ambiguity of the reconstruction, and we will discuss
it further in the section on evaluating reconstructions below.

Creating a final refined model
********************************

The output of DAMAVER, specifically the damstart.pdb file, can be used
as input for DAMMIN to create a final refined model. Essentially, the
damstart.pdb represents a very conservative core of the most probably
occupied volume as determined by averaging all the reconstructions using
DAMAVER. DAMMIN keeps this core fixed, and refines the outside of the model
to match the scattering profile. I've seen mixed recommendations (even from
the makes of the software) on whether you should do a refinement. I typically
do, but it seems you can often do just as well with the most probable model
determined by DAMAVER.

Evaluating DAMMIF/N reconstructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SAXS data contains very limited information, both because it is measured at
relatively low *q*, and because it is measured from a large number of particles
in solution oriented at random angles. The SAXS curve ends up representing the
scattering from a single particle, averaged over all possible orientations.
This practical consequence of this is that there are often several possible
shapes that could generate the same (over so similar as to be indistinguishable
within experimental noise) scattering profiles. As such, it may simply not
be possible to generate a  bead model reconstruction from a dataset that
accurately represents the solution shape, regardless of the overall data
quality. If the sample is flexible or otherwise exists in multiple conformational
or oligomeric states in solution the reconstruction is also challenging or
impossible. **In summary, high quality SAXS data is not a guarantee of a good
bead model reconstruction. This makes it very important to critically evaluate
every reconstruction done, regardless of the underlying data quality.**

The information needed to evaluate the reconstructions is generated when
running DAMMIF, DAMAVER, DAMCLUST, SASRES [5] (run as part of DAMAVER) and
AMBIMETER [6]. While it can all be accessed through the files these programs
generate, RAW gathers and presents it for you when you run DAMMIF in RAW.

|dammif_results_png|

Criteria for a good DAMMIF/N reconstruction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*   Ambiguity score < 2.5 (preferably < 1.5)
*   NSD < 1.0
*   Few (0-2) models rejected from the average
*   Only one cluster of models
*   Model :math:`\chi^2` near 1.0 for all models
*   Model |Rg| and |Dmax| close to values from P(r) function for all models
*   M.W. estimated from model volume close to expected M.W.

More about each of these criteria can be found below.

Ambiguity
*************

It is possible to evaluate the potential ambiguity of your bead model reconstructions
before doing the reconstructions. The AMBIMETER program in the ATSAS package
can be run on P(r) functions from GNOM to assess how likely you are to get
a good reconstruction. The program has a database of scattering profiles
representing all shapes possible out of up to 7 beads. Your scattering profile
is compared against these shapes, and AMBIMETER reports how many match your
profile. The more profiles from AMBIMETER that match yours, the more possible
shapes could have generated your profile.

AMBIMETER reports both the number of shapes and the log (base 10) of the number
shapes, which is the Ambiguity score. They provide the following interpretations:

*   Ambiguity score < 1.5 - Reconstruction is likely unique
*   Ambiguity score of 1.5-2.5 - Take care when doing the reconstruction
*   Ambiguity score > 2.5 - Reconstruction is most likely ambiguous.

This provides a quick initial assessment of whether you should even bother
doing a shape reconstruction for your dataset.

Normalized spatial discrepancy
**********************************

DAMAVER reports a number of different results. The most useful is the normalized
spatial discrepancy (NSD). This is essentially a size normalized metric for comparing
how similar two different models are. When DAMAVER is run, it reports the
average and standard deviation of the NSD between all the reconstructions. It
also reports the average NSD for each model. If the average NSD of a given model
is more than two standard deviations above the mean NSD, that model is not included
in the average.

NSD is commonly used to evaluate the stability of the reconstruction. While the
exact thresholds vary a little, roughly speaking we evaluate reconstruction
stability as:

*   NSD < 0.6 - Good stability of reconstructions
*   NSD between 0.6 and 1.0 - Fair stability of reconstructions
*   NSD > 1.0 - Poor stability of reconstructions

Generally speaking, if your NSD is less than 1.0, the reconstruction can
probably be trusted (if all of the other validation metrics also check out),
while if it is greater than 1.0 you should proceed with caution, or not use
the reconstructions at all.

The normalized spatial discrepancy is also used to determine which models
to include in a reconstruction. If more than ~2 models are rejected (of 15), that
may be a sign of an unstable reconstruction.

Clusters
***********



Model fit and parameters
*****************************

Model resolution
*******************


Limitations of bead models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



Visualizing DAMMIF/N reconstructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


FAQ
^^^^^^^^





References
^^^^^^^^^^^^

1.  Franke, D. and Svergun, D.I. (2009) DAMMIF, a program for rapid ab-initio
    shape determination in small-angle scattering. J. Appl. Cryst., 42, 342-346.

2.  D. I. Svergun (1999) Restoring low resolution structure of biological
    macromolecules from solution scattering using simulated annealing. Biophys J. 2879-2886.

3.  V. V. Volkov and D. I. Svergun (2003). Uniqueness of ab-initio shape
    determination in small-angle scattering. J. Appl. Cryst. 36, 860-864.

4.  Petoukhov, M.V., Franke, D., Shkumatov, A.V., Tria, G., Kikhney, A.G.,
    Gajda, M., Gorba, C., Mertens, H.D.T., Konarev, P.V. and Svergun, D.I.
    (2012) New developments in the ATSAS program package for small-angle
    scattering data analysis. J. Appl. Cryst. 45, 342-350

5.  Anne T. Tuukkanen, Gerard J. Kleywegt and Dmitri I. Svergun(2016) Resolution
    of ab initio shapes determined from small-angle scattering IUCrJ. 3, 440-447.

6.  M.V. Petoukhov and D.I. Svergun (2015) Ambiguity assessment of small-angle
    scattering curves from monodisperse systems Acta Cryst. D71, 1051-1058.

.. |Rg| replace:: R\ :sub:`g`

.. |Dmax| replace:: D\ :sub:`max`

.. |dammif_results_png| image:: ../tutorial/images/dammif_results.png
    :target: ../_images/dammif_results.png

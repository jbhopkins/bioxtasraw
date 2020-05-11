import os

import matplotlib.pyplot as plt

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..', '..', '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw

settings = raw.load_settings(os.path.join('.', 'figure_data', 'SAXS.cfg'))

gi_83 = raw.load_ifts([os.path.join('.', 'figure_data', 'gi_83.out')], settings)[0]
gi_103 = raw.load_ifts([os.path.join('.', 'figure_data', 'gi_103.out')], settings)[0]
gi_123 = raw.load_ifts([os.path.join('.', 'figure_data', 'gi_123.out')], settings)[0]

plt.figure(figsize=(6,3))
ax1 = plt.subplot(1, 2, 1)
ax1.plot(gi_83.r, gi_83.p/gi_83.getParameter('i0'), '-', label='$D_{max}=83$ $\AA$',
    linewidth=2.0)
ax1.plot(gi_103.r, gi_103.p/gi_103.getParameter('i0'), '-', label='$D_{max}=103$ $\AA$',
    zorder=10, linewidth=2.0)
ax1.plot(gi_123.r, gi_123.p/gi_123.getParameter('i0'), '-', label='$D_{max}=123$ $\AA$',
    linewidth=2.0)
ax1.axhline(0, color='0', linewidth=1.0, zorder=-1)
ax1.legend(fontsize='x-small')
ax1.set_ylabel('P(r)/I(0)')
ax1.set_xlabel('r [$\AA$]')
ax1.yaxis.set_ticks([])

ax2 = plt.subplot(1, 2, 2)
ax2.plot(gi_83.r, gi_83.p/gi_83.getParameter('i0'), '-', label='$D_{max}=83$ $\AA$',
    linewidth=3.0)
ax2.plot(gi_103.r, gi_103.p/gi_103.getParameter('i0'), '-', label='$D_{max}=103$ $\AA$',
    zorder=10, linewidth=3.0)
ax2.plot(gi_123.r, gi_123.p/gi_123.getParameter('i0'), '-', label='$D_{max}=123$ $\AA$',
    linewidth=3.0)
ax2.axhline(0, color='0', linewidth=1.0, zorder=-1)
ax2.legend()
ax2.set_ylim(-0.00001, 0.0005)
ax2.set_xlim(73, 133)
ax2.set_ylabel('P(r)/I(0)')
ax2.set_xlabel('r [$\AA$]')
ax2.yaxis.set_ticks([])

plt.subplots_adjust(left=0.06, bottom=0.16, right=0.98, wspace=0.19, top=0.98)
plt.savefig('pr_dmax_variation.png', dpi=300)
plt.show()

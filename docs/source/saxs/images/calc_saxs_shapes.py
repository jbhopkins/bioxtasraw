import numpy as np
import scipy.integrate as integrate
import scipy.special
import matplotlib.pyplot as plt
import matplotlib as mpl

def sphere(q, R):
    return 9*((np.sin(q*R)-(q*R)*np.cos(q*R))/(q*R)**3)**2

def thin_rod(q, R):
    return (2*si(q*R)/(q*R) - (sinc(q*R/2))**2)

def thin_disc(q, R):
    return (2-2*scipy.special.jv(1, 2*q*R)/(q*R))/(q*R)**2

def sinc(x):
    return np.sinc(x/np.pi)

def si(t):
    if not isinstance(t, float):
        int_res = np.empty_like(t)
        for j in range(len(t)):
            int_res[j] = integrate.quad(sinc, 0, t[j])[0]
        return int_res
    else:
        return integrate.quad(sinc, 0, t)[0]


rg = 10
q = np.linspace(0.0001, np.sqrt(4)/rg, 1000)
# q = np.linspace(0.0001, 3, 1000)

r_sphere = np.sqrt(5/3.)*rg
r_rod = np.sqrt(12.)*rg
r_disc = np.sqrt(2.)*rg

sphere_i = sphere(q, r_sphere)
rod_i = thin_rod(q, r_rod)
disc_i = thin_disc(q, r_disc)
guinier_i = np.exp(-(q*rg)**2/3.)

sphere_i = sphere_i/sphere_i[0]
rod_i = rod_i/rod_i[0]
disc_i = disc_i/disc_i[0]
guinier_i = guinier_i/guinier_i[0]

def tick_formatter(x, pos):
    return "{}".format(round(x,1))

plt.figure(figsize=(6,4))
plt.axvline(1**2, color='0.6', linestyle='--')
plt.axvline(1.3**2, color='0.6', linestyle='--')
plt.semilogy((q*rg)**2, guinier_i, label='Guinier Approx.', color='k')
plt.semilogy((q*rg)**2, sphere_i, label='Sphere')
plt.semilogy((q*rg)**2, rod_i, label='Thin Rod')
plt.semilogy((q*rg)**2, disc_i, label='Thin Disc')
plt.legend()
plt.xlabel('$(qR_g)^2$')
plt.ylabel('Intensity (log scale)')
plt.title('Guinier approximation validity')
plt.subplots_adjust(left=0.11, right=0.96, top=0.94, bottom=0.12)
axes = plt.gca()
axes.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(tick_formatter))
axes.yaxis.set_minor_formatter(mpl.ticker.FuncFormatter(tick_formatter))
plt.savefig('guinier_shapes.png', dpi=300)
plt.show()

# plt.semilogy(q, sphere_i)
# plt.semilogy(q, rod_i)
# plt.semilogy(q, disc_i)
# # plt.semilogy(q, guinier_i)
# plt.show()

# err = np.random.randn(1000)
# err = err/100.
# print(err+1)
# np.savetxt('sphere.dat', np.column_stack((q, sphere_i*(err+1), err)))
# np.savetxt('rod.dat', np.column_stack((q, rod_i*(err+1), err)))
# np.savetxt('disc.dat', np.column_stack((q, disc_i*(err+1), err)))

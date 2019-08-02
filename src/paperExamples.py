#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 15:08:19 2019

@author: jkl
"""

import numpy as np
import matplotlib.pyplot as plt
from resipy.R2 import R2
plt.ioff() # this disable interactive plotting

figdir = './image/paper/'

#%% error plots
#k = R2()
#k.createSurvey('./resipy/test/syscalFile.csv')
#k.removeUnpaired()

#fig = plt.figure(figsize=(8,5))
#k.filterElec([3])
#ax = plt.subplot2grid((2,2), (0,1))
#k.surveys[0].manualFiltering(ax=ax)
#ax.set_title('(b) Filtered data')
#ax = plt.subplot2grid((2,2), (0,0))
##k = R2()
#k.createSurvey('./resipy/test/syscalFile.csv')
#k.removeUnpaired()
#k.surveys[0].manualFiltering(ax=ax) # need to click manually and same
#ax.set_title('(a) Manual filtering')
#ax = plt.subplot2grid((2,2), (1,0), colspan=2)
#k.errorDist(ax=ax)
#ax.set_title('(c) Error probability distribution')
#fig.show()


#%%
k = R2()
k.createSurvey('./resipy/test/syscalFile.csv')
k.removeUnpaired()
figsize=(5,2.5)

fig, ax = plt.subplots(figsize=figsize)
k.surveys[0].manualFiltering(ax=ax) # manually selection points
ax.set_title('(a) Select points/electrodes')
ax.set_ylabel('Pseudo-depth [m]')
ax.set_xlabel('Distance [m]')
fig.tight_layout()
fig.savefig(figdir + 'fig4-manualFiltering.png') # to be saved after selecting points
fig.show()

k.surveys[0].filterData(~k.surveys[0].iselect)

fig, ax = plt.subplots(figsize=figsize)
k.surveys[0].manualFiltering(ax=ax) # manually selection points
ax.set_title('(b) Filtered data')
ax.set_ylabel('Pseudo-depth [m]')
ax.set_xlabel('Distance [m]')
fig.tight_layout()
fig.savefig(figdir + 'fig4-filtered.png')
fig.show()

fig, ax = plt.subplots(figsize=(8,2.5))
k.errorDist(ax=ax)
ax.set_title('(c) Probability distribution of reciprocal errors')
fig.tight_layout()
fig.savefig(figdir + 'fig4-errorDist.png')
fig.show()





#%% 2D topo at Lancaster Castle Hill (Lancaster UK)
k = R2() # initiate an R2 instance
k.createSurvey('./resipy/test/syscalFileTopo.csv', ftype='Syscal') # import data
k.importElec('./resipy/test/elecTopo.csv')
k.pwlfit() # fit a power law
k.createMesh(typ='trian') # create quadrilateral mesh
k.invert() # run the inversion
k.showResults()

# graph section
fig, ax = plt.subplots(figsize=(7, 2))
k.showResults(ax=ax, zlim=[28, 29.6], sens=False) # show the inverted section
fig.tight_layout()
fig.savefig(figdir + 'castle.eps')
fig.savefig(figdir + 'castle.png')
fig.show()


#%% IP Calcite precipitation inversion (Rifle, CO, USA)
k = R2(typ = 'cR2') # initiate an R2 instance (considering there is IP data in the input data)
k.createSurvey('./resipy/test/IP/IP_MICP_all.csv', ftype='Syscal') # import data
k.filterRecip(percent=20) # remove\ing datapoints with > 20% reciprocal error
k.removenested() # removing nested measurements
k.iprangefilt(0,25) # setting phase shift range to 0 < -ϕ < 25
k.pwlfit() # adding resistance power-law error model to data
k.plotIPFit() # adding phase power-law error model to data
k.err = True # using error models (DC and IP) - automatically done in the GUI when fitting the error model
k.createMesh(typ='trian') # create triangular mesh
k.param['a_wgt'] = 0 # "a_wgt" = 0 when there is individual resistance error
k.param['b_wgt'] = 0 # "b_wgt" = 0 when there is individual phase error
k.param['tolerance'] = 1.2 # based on data, field site and experience
k.invert() # run the inversion (and write cR2.in and protocol.dat automatically)
k.showResults(attr='Sigma_real(log10)') # show the inverted real conductivity section
k.showResults(attr='Phase(mrad)') # show the inverted phase shift section

#%% graph section
fig, axs = plt.subplots(1, 2, figsize=(8,3))
ax = axs[0]
k.pwlfit(ax=ax)
ax.set_title('(a) ' + ax.get_title())
ax = axs[1]
k.plotIPFit(ax=ax)
ax.set_title('(b) ' + ax.get_title())
fig.tight_layout()
fig.savefig(figdir + 'ip-error-models.png')
fig.show()

fig, axs = plt.subplots(2, 1, figsize=(4, 3), sharex=True)
ax = axs[0]
ax.set_title('(a)')
k.showResults(attr='Sigma_real(log10)', zlim=[-8, 0], ax=ax, sens=False)
ax.set_xlabel(None)
ax = axs[1]
ax.set_title('(b)')
#k.showResults(attr='Phase(mrad)', zlim=[-8, 0], vmax=0, ax=ax, sens=False)
k.showResults(attr='Sigma_imag(log10)', zlim=[-8, 0], vmax=0, ax=ax, sens=False)
fig.tight_layout()
fig.savefig(figdir + 'micp.eps')
fig.savefig(figdir + 'micp.png')
fig.show()


#%% Time-lapse RWU at Woburn (UK)
k = R2() # initiate an R2 instance
k.createTimeLapseSurvey('./resipy/test/testTimelapse', ftype='Syscal') # import directory with the data
k.pwlfit() # fit a power-law
k.createMesh(typ='trian', cl=0.02, cl_factor=20) # create a triangular mesh with a characteristic length of 0.5
k.showMesh()
k.invert(parallel=True) # run the inversion (and write R2.in and protocol.dat automatically)
k.showResults(index=0) # show the first inverted section
k.showResults(index=1) # show the second inverted section
k.showResults(index=1, attr='difference(percent)') # show the differences between the first and second survey


#%% graph
fig, axs = plt.subplots(3, 1, figsize=(5, 6), sharex=True)
ax = axs[0]
ax.set_title('(a) 15th March to 3rd April')
k.showResults(ax=ax, index=1, attr='difference(percent)', vmin=0, vmax=50, sens=False)
ax.set_xlabel(None)
ax = axs[1]
ax.set_title('(b) 15th March to 27th April')
k.showResults(ax=ax, index=2, attr='difference(percent)', vmin=0, vmax=50, sens=False)
ax.set_xlabel(None)
ax = axs[2]
ax.set_title('(c) 15th March to 16th May')
k.showResults(ax=ax, index=3, attr='difference(percent)', vmin=0, vmax=50, sens=False)
fig.tight_layout()
fig.savefig(figdir + 'woburn.eps')
fig.savefig(figdir + 'woburn.png')
fig.show()


#%% ERT in River at Boxford (UK) with fixed region
k = R2()
k.createSurvey('./resipy/test/river-protocol.dat', ftype='Protocol')
# following lines will add electrode position, surface points and specify if electrodes are buried or not. Similar steps are done in the GUI in (a), (b), (c)
x = np.genfromtxt('./resipy/test/river-elec.csv', delimiter=',')
k.setElec(x[:,:2]) # electrode positions
surface = np.array([[0.7, 92.30],[10.3, 92.30]]) # additional surface point for the river level
buried = x[:,2].astype(bool) # specify which electrodes are buried (in the river here)
k.filterElec([21, 2]) # filter out problematic electrodes 21 and 2
k.createMesh(typ='trian', buried=buried, surface=surface, cl=0.1, cl_factor=10)
xy = k.elec[1:21,[0,2]] # adding river water level using 2 topo points
k.addRegion(xy, res0=32, blocky=True, fixed=False) # fixed river resistivity to 32 Ohm.m
k.param['b_wgt'] = 0.05 # setting up higher noise level
k.invert()
k.showResults(sens=False, vmin=1.2, vmax=2.2, zlim=[88, 93])

#%% graph
fig, ax = plt.subplots(figsize=(7, 2))
k.showResults(ax=ax, sens=False, vmin=1.2, vmax=2.2, zlim=[89, 93])
ax.plot([10.5, 11.88, 12.85, 16.5],[91.9, 91.42, 91.83, 91.79],'k--')
#ax.plot([0, 10.4, 12.5, 16.5],[90.7, 90.7, 89.6, 89.6],'k--')
ax.text(6.87, 92.2, '1', color='red', fontsize=14)
ax.text(8.5, 90.5, '3', color='red', fontsize=14)
ax.text(14, 92.1, '2', color='red', fontsize=14)
#ax.text(6, 89.2, '4', color='red', fontsize=14)
xyb = np.r_[xy, xy[[0],:]]
xyb[0,1] = 92.36
xyb[-2,1] = 92.36
xyb[-1,1] = 92.36
ax.plot(xyb[:,0], xyb[:,1], 'r--')
fig.tight_layout()
fig.savefig(figdir + 'fixedRiver.eps')
fig.savefig(figdir + 'fixedRiver.png')
fig.show()


#%% Forward modelling for dipole-dipole array
k1 = R2(typ='R2')
k1.setElec(np.c_[np.linspace(0,24, 24), np.zeros((24, 2))])
k1.createMesh(typ='quad')
target = np.array([[7,-1],[10,-1],[10,-2],[7,-2]])
k1.addRegion(target, 10, -3)
k1.showMesh()

k1.createSequence(params=[('wenner_alpha',1),
                         ('wenner_alpha',2),
                         ('wenner_alpha',3),
                         ('wenner_alpha',4),
                         ('wenner_alpha',5),
                         ('wenner_alpha',6),
                         ('wenner_alpha',7),
                         ('wenner_alpha',8),
                         ('wenner_alpha',9),
                         ('wenner_alpha',10)])

k1.forward(iplot=True, noise=0.05)
k1.param['num_xy_poly'] = 0
k1.invert(iplot=True)
k1.showResults(index=0, attr='Resistivity(Ohm-m)', sens=False)
k1.showResults(index=1, attr='Resistivity(Ohm-m)', sens=False)

# now for the dipole dipole
k2 = R2(typ='R2')
k2.setElec(np.c_[np.linspace(0,24, 24), np.zeros((24, 2))])
k2.createMesh(typ='quad')
target = np.array([[7,-1],[10,-1],[10,-2],[7,-2]])
k2.addRegion(target, 10, -3)
k2.showMesh()

k2.createSequence([('dpdp1', 1, 8)])
k2.forward(iplot=True, noise=0.05)
k2.param['num_xy_poly'] = 0
k2.invert()
k2.showResults(index=1, attr='Resistivity(Ohm-m)', sens=False)

#%% graph
fig = plt.figure(figsize=(6, 8))
ax = plt.subplot2grid((3,3), (0,1), colspan=1)
ax.set_title('(a)')
k1.showResults(index=0, ax=ax, sens=False, zlim=[-7,0])

ax = plt.subplot2grid((3,3), (1,0))
k1.surveys[0].pseudo(ax=ax, vmin=50, vmax=120)
ax.set_title('(b)')

ax = plt.subplot2grid((3,3), (1,1))
ax.set_title('(c)')
k1.showResults(index=1, ax=ax, sens=False, zlim=[-7,0], vmin=1, vmax=2)
target2 = np.vstack([target, target[0,:]])
ax.plot(target2[:,0], target2[:,1], 'r--')

ax = plt.subplot2grid((3,3), (2,0))
k2.surveys[0].pseudo(ax=ax, vmin=50, vmax=120)
ax.set_title('(d)')

ax = plt.subplot2grid((3,3), (2,1))
ax.set_title('(e)')
k2.showResults(index=1, ax=ax, sens=False, zlim=[-7,0], vmin=1, vmax=2)
ax.plot(target2[:,0], target2[:,1], 'r--')
fig.tight_layout()
#fig.savefig(figdir + 'forward.eps')
#fig.savefig(figdir + 'forward.png')
fig.show()

#%%

fig, axs = plt.subplots(5, 1, figsize=(5, 9), sharex=True)
ax = axs[0]
ax.set_title('(a) True')
k1.showResults(index=0, ax=ax, sens=False, zlim=[-7,0])
ax.set_xlabel(None)
fig.axes[-1].set_ylabel(r'$\log_{10}(\rho)$ [$\Omega$.m]')

ax = axs[1]
k1.surveys[0].pseudo(ax=ax, vmin=50, vmax=120)
ax.set_title('(b) Wenner')
ax.set_xlabel(None)

ax = axs[2]
k2.surveys[0].pseudo(ax=ax, vmin=50, vmax=120)
ax.set_title('(c) Dipole-Dipole')
ax.set_xlabel(None)

ax = axs[3]
ax.set_title('(d) Wenner')
k1.showResults(index=1, ax=ax, sens=False, zlim=[-7,0], vmin=1, vmax=2)
target2 = np.vstack([target, target[0,:]])
ax.plot(target2[:,0], target2[:,1], 'r--')
fig.axes[-1].set_ylabel(r'$\log_{10}(\rho)$ [$\Omega$.m]')
ax.set_xlabel(None)

ax = axs[4]
ax.set_title('(e) Dipole-Dipole')
k2.showResults(index=1, ax=ax, sens=False, zlim=[-7,0], vmin=1, vmax=2)
ax.plot(target2[:,0], target2[:,1], 'r--')
fig.axes[-1].set_ylabel(r'$\log_{10}(\rho)$ [$\Omega$.m]')
fig.tight_layout()
fig.savefig(figdir + 'forward.eps')
fig.savefig(figdir + 'forward.png')
fig.show()


#%% general figure miniatures
import matplotlib
matplotlib.rcParams.update({'font.size': 12})
figsize=(3, 1.5)

k = R2()
k.createSurvey(k.dirname + '/../test/IP/syscalFileIP.csv')
array = k.surveys[0].df[['a','b','m','n']].values
ie = (array <= 12).all(-1)
#k.surveys[0].df = k.surveys[0].df[ie].reset_index(drop=True)
#k.surveys[0].df.loc[[4], 'resist'] = 100

k.removeUnpaired()


fig, ax = plt.subplots(figsize=figsize)
k.pseudo(ax=ax)#, vmin=45, vmax=60)
ax.set_title('Data')
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.tight_layout()
fig.savefig(figdir + 'miniature-pseudo.png')
fig.show()

fig, ax = plt.subplots(figsize=figsize)
k.surveys[0].manualFiltering(ax=ax)
ax.set_title('(a) Filtering')
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.get_axes()[1].set_ylabel(r'$\rho_a$ [$\Omega$.m]')
fig.tight_layout()
fig.savefig(figdir + 'miniature-manualFiltering.png')
fig.show()


fig, ax = plt.subplots(figsize=figsize)
k.pwlfit(ax=ax)
ax.set_title('(b) DC Error Modelling')
ax.set_xticks([],[])
ax.set_yticks([],[])
#ax.set_xlabel('')
#ax.set_ylabel('')
ax.get_legend().remove()
fig.tight_layout()
fig.savefig(figdir + 'miniature-errorModelling.png')
fig.show()

fig, ax = plt.subplots(figsize=figsize)
k.plotIPFit(ax=ax)
ax.set_title('(c) IP Error Modelling')
ax.set_xticks([],[])
ax.set_yticks([],[])
#ax.set_xlabel('')
#ax.set_ylabel('')
ax.get_legend().remove()
fig.tight_layout()
fig.savefig(figdir + 'miniature-errorModellingIP.png')
fig.show()

k.filterElec([4])
fig, ax = plt.subplots(figsize=figsize)
k.pseudo(ax=ax)
ax.set_title('(d) Filtered Data')
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.tight_layout()
fig.savefig(figdir + 'miniature-pseudoFinal.png')
fig.show()


k.createMesh()

fig, ax = plt.subplots(figsize=figsize)
k.showMesh(ax=ax)
ax.set_xlim([0, 2.5])
ax.set_ylim([-1, 0])
ax.set_title('(e) Quad Mesh')
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.tight_layout()
fig.savefig(figdir + 'miniature-meshQuad.png')
fig.show()

k.createMesh('trian')


fig, ax = plt.subplots(figsize=figsize)
k.showMesh(ax=ax)
ax.set_xlim([0, 2.5])
ax.set_ylim([-1, 0])
ax.set_title('(f) Tri Mesh')
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.tight_layout()
fig.savefig(figdir + 'miniature-meshTrian.png')
fig.show()

k.invert()


fig, ax = plt.subplots(figsize=figsize)
k.showResults(ax=ax, sens=False, contour=True)
#ax.set_xlim([0, 1])
#ax.set_ylim([-0.7, 0])
ax.set_title('(j) Inverted Section')
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.tight_layout()
fig.savefig(figdir + 'minitature-invSection.png')
fig.show()


fig, ax = plt.subplots(figsize=figsize)
k.pseudoError(ax=ax)
ax.set_title('(k) Inversion Errors')
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.tight_layout()
fig.savefig(figdir + 'miniature-pseudoError.png')
fig.show()


k.createMesh(typ='quad')
target = np.array([[0,-0.2],[0,-0.4],[10,-0.4],[10,-0.2]])
k.addRegion(target, 100, -3)
target = np.array([[1,-0.3],[1,-0.7],[2,-0.7],[2,-0.3]])
k.addRegion(target, 10, -3)

fig, ax = plt.subplots(figsize=figsize)
k.showMesh(ax=ax)
ax.set_title('(g) Forward Model')
ax.set_xlim([0, 2.5])
ax.set_ylim([-1, 0])
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.tight_layout()
fig.savefig(figdir + 'miniature-forwardModel.png')
fig.show()


k.createSequence([('dpdp1', 1, 8)])


fig, ax = plt.subplots(figsize=figsize)
ax.table(cellText=k.sequence[:5,:].astype(str).tolist(),
         colLabels=['A','B','M','N'],
         loc=0.5)
ax.set_title('(h) Sequence Design')
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.tight_layout()
fig.savefig(figdir + 'miniature-forwardSequence.png')
fig.show()


k.forward(iplot=False, noise=0.05)

fig, ax = plt.subplots(figsize=figsize)
k.pseudo(ax=ax)
ax.set_title('(i) Synthetic Data')
ax.set_xticks([],[])
ax.set_yticks([],[])
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_axis_off()
fig.tight_layout()
fig.savefig(figdir + 'miniature-forwardPseudo.png')
fig.show()

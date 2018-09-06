# -*- coding: utf-8 -*-
"""
Created on Wed May 30 16:48:54 2018

@author: jkl
"""

import numpy as np
import pandas as pd
import os
import sys
import shutil
import platform
import matplotlib.pyplot as plt
from subprocess import PIPE, call, Popen
OS = platform.system()

sys.path.append(os.path.relpath('..'))

from api.Survey import Survey
from api.r2in import write2in
import api.meshTools as mt
from api.meshTools import Mesh_obj, tri_mesh
from api.sequenceHelper import ddskip
from api.SelectPoints import SelectPoints


class R2(object): # R2 master class instanciated by the GUI
    """ Master class to handle all processing around the inversion codes.
    """
    def __init__(self, dirname=''):
        """ Create an R2 object.
        
        Parameters
        ----------
        dirnaname : str, optional
            Path of the working directory. Can also be set using `R2.setwd()`.
        """
        if dirname == '':
            dirname = os.getcwd()
            print('using the current directory:', dirname)
        self.dirname = dirname # working directory (for the datas)
        self.cwd = os.getcwd() # directory of the code
        self.surveys = [] # list of survey object
        self.surveysInfo = [] # info about surveys (date)
        self.mesh = None # mesh object (one per R2 instance)
        self.param = {} # dict configuration variables for inversion
        self.configFile = ''
        self.typ = 'R2' # or cR2 or R3, cR3
        self.errTyp = 'none' # type of error to add for DC
        self.errTypIP = 'none' # type of error to add for IP phase
        self.iBorehole = False
        self.iTimeLapse = False
        self.meshResults = [] # contains vtk mesh object of inverted section
        self.sequence = None # quadrupoles sequence if forward model
        
    def setwd(self, dirname):
        """ Set the working directory.
        
        Parameters
        ----------
        dirname : str
            Path of the working directory.
        """
        # get rid of some stuff
        files = os.listdir(dirname)
        if 'ref' in files: # only for timelapse survey
            shutil.rmtree(os.path.join(dirname, 'ref'))
        if 'R2.exe' in files:
            os.remove(os.path.join(dirname, 'R2.exe'))
        if 'cR2.exe' in files:
            os.remove(os.path.join(dirname, 'cR2.exe'))
        if 'mesh.dat' in files:
            os.remove(os.path.join(dirname, 'mesh.dat'))
        if 'Start_res.dat' in files:
            os.remove(os.path.join(dirname, 'Start_res.dat'))
        self.dirname = dirname
    
    
    def createSurvey(self, fname='', ftype='Syscal', info={}, spacing=None):
        """ Read electrodes and quadrupoles data and return 
        a survey object.
        
        Parameters
        ----------
        fname : str
            Filename to be parsed.
        ftype : str, optional
            Type of file to be parsed. Either 'Syscal' or 'Protocol'.
        info : dict, optional
            Dictionnary of info about the survey.
        spacing : float, optional
            Electrode spacing to be passed to the parser function.
        """    
        self.surveys.append(Survey(fname, ftype, spacing=spacing))
        self.surveysInfo.append(info)
        
        # define electrode position according to first survey
        if len(self.surveys) == 1:
            self.elec = self.surveys[0].elec
            
            # attribute method of Survey object to R2
            self.pseudoIP = self.surveys[0].pseudoIP
            self.pseudoCallback = self.surveys[0].pseudo
            self.plotError = self.surveys[0].plotError
            self.linfit = self.surveys[0].linfit
            self.lmefit = self.surveys[0].lmefit
            self.pwlfit = self.surveys[0].pwlfit
            self.phaseplotError = self.surveys[0].phaseplotError
            self.plotIPFit = self.surveys[0].plotIPFit
            self.heatmap = self.surveys[0].heatmap
            self.iprangefilt = self.surveys[0].iprangefilt
            self.removerecip = self.surveys[0].removerecip
            self.removenested = self.surveys[0].removenested
            

    def createTimeLapseSurvey(self, dirname, ftype='Syscal', info={}, spacing=None, isurveys=[]):
        """ Read electrodes and quadrupoles data and return 
        a survey object.
        
        Parameters
        ----------
        fname : str
            Filename to be parsed.
        ftype : str, optional
            Type of file to be parsed. Either 'Syscal' or 'Protocol'.
        info : dict, optional
            Dictionnary of info about the survey.
        spacing : float, optional
            Electrode spacing to be passed to the parser function.
        isurveys : list
            List of surveys index that will be used for error modelling and so
            reciprocal measurements. By default all surveys are used.
        """    
        self.iTimeLapse = True
        self.iTimeLapseReciprocal = [] # true if survey has reciprocal
        files = np.sort(os.listdir(dirname))
        for f in files:
            self.createSurvey(os.path.join(dirname, f))
            haveReciprocal = all(self.surveys[-1].df['irecip'].values == 0)
            self.iTimeLapseReciprocal.append(haveReciprocal)
            print('---------', f, 'imported')
            if len(self.surveys) == 1:
                ltime = len(self.surveys[0].df)
            if len(self.surveys) > 1:
                if len(self.surveys[-1].df) != ltime:
                    print('ERROR:', f, 'survey doesn\'t have the same length')
                    return
        self.iTimeLapseReciprocal = np.array(self.iTimeLapseReciprocal)
        self.elec = self.surveys[0].elec
        
        
        # create bigSurvey
        print('creating bigSurvey')
        self.bigSurvey = Survey(os.path.join(dirname, files[0]), ftype=ftype)
        # then override the df
        if len(isurveys) == 0: # assume all surveys would be use for error modelling
            isurveys = np.ones(len(self.surveys), dtype=bool)
        isurveys = np.where(isurveys)[0] # convert to indices
        df = self.bigSurvey.df.copy()
        c = 0
        for i in isurveys:
            df2 = self.surveys[i].df
            ipos = df2['irecip'].values > 0
            ineg = df2['irecip'].values < 0
            df2.loc[ipos, 'irecip'] = df2[ipos]['irecip'] + c
            df2.loc[ineg, 'irecip'] = df2[ineg]['irecip'] - c
            df = df.append(df2)
            c = c + df2.shape[0]
        self.bigSurvey.df = df.copy() # override it
        self.bigSurvey.dfOrigin = df.copy()
        self.bigSurvey.ndata = df.shape[0]
        self.pseudoCallback = self.surveys[0].pseudo # just display first pseudo section
            
        self.plotError = self.bigSurvey.plotError
        self.linfit = self.bigSurvey.linfit
        self.lmefit = self.bigSurvey.lmefit
        self.pwlfit = self.bigSurvey.pwlfit
        self.phaseplotError = self.bigSurvey.phaseplotError
        self.plotIPFit = self.bigSurvey.plotIPFit
    
    def pseudo(self, **kwargs):
        """ Create a pseudo section.
        
        Parameters
        ----------
        **kwargs :
            To be passed to `R2.pseudoCallback()`.
        """
        if self.iBorehole == True:
            print('NOT PLOTTING PSEUDO FOR BOREHOLE FOR NOW')
        else:
            self.pseudoCallback(**kwargs)
    
    def createMesh(self, typ='default', **kwargs):
        """ Create a mesh.
        
        Parameters
        ----------
        typ : str, optional
            Type of mesh. Eithter 'quad' or 'trian'. If no topography, 'quad'
            mesh will be chosen.
        """
        if typ == 'default':
            if self.elec[:,2].sum() == 0:
                typ = 'quad'
                print('Using a quadrilateral mesh')
            else:
                typ = 'trian'
                print('Using a triangular mesh')
        if typ == 'quad':
#            mesh = QuadMesh(elec, nnode=4)
            elec_x = self.elec[:,0]
            elec_y = self.elec[:,1]
            mesh,meshx,meshy,topo,e_nodes = mt.quad_mesh(elec_x,elec_y,**kwargs)
#            mesh = QuadMesh()
#            meshx, meshy, topo, e_nodes = mesh.createMesh(elec=self.elec, **kwargs)            
            self.param['meshx'] = meshx
            self.param['meshy'] = meshy
            self.param['topo'] = topo
            self.param['mesh_type'] = 4
            self.param['node_elec'] = np.c_[1+np.arange(len(e_nodes)), e_nodes, np.ones(len(e_nodes))].astype(int)
            if 'regions' in self.param: # allow to create a new mesh then rerun inversion
                del self.param['regions']
            if 'num_regions' in self.param:
                del self.param['num_regions']
        if typ == 'trian':
            mesh = tri_mesh({'electrode':[self.elec[:,0], self.elec[:,1]]}, path=os.path.join(self.cwd, 'api', 'exe'), save_path=self.dirname)
            self.param['mesh_type'] = 3
            self.param['num_regions'] = len(mesh.regions)
            regs = np.array(np.array(mesh.regions))[:,1:]
            if self.typ == 'R2':
                regions = np.c_[regs, np.ones(regs.shape[0])*50]
            if self.typ == 'cR2':
                regions = np.c_[regs, np.ones(regs.shape[0])*50, np.ones(regs.shape[0])*-0.1]
            self.param['regions'] = regions
            self.param['num_xy_poly'] = 5
            # define xy_poly_table
            doi = np.abs(self.elec[0,0]-self.elec[-1,0])*2/3
            xy_poly_table = np.array([
            [self.elec[0,0], self.elec[0,1]],
            [self.elec[-1,0], self.elec[-1,1]],
            [self.elec[-1,0], self.elec[-1,1]-doi],
            [self.elec[0,0], self.elec[0,1]-doi],
            [self.elec[0,0], self.elec[0,1]]])
            self.param['xy_poly_table'] = xy_poly_table
            e_nodes = np.arange(len(self.elec))+1
            self.param['node_elec'] = np.c_[1+np.arange(len(e_nodes)), e_nodes, np.ones(len(e_nodes))].astype(int)
        self.mesh = mesh
        self.param['mesh'] = mesh
        
        self.regid = 0
        self.regions = np.zeros(len(self.mesh.elm_centre[0]))
        self.resist0 = np.ones(len(self.regions))*100
        
        
    def showMesh(self, ax=None):
        """ Display the mesh.
        """
        if self.mesh is None:
            raise Exception('Mesh undefined')
        else:
#            xlim = (np.min(self.elec[:,0]-20, np.max(self.elec[:,0])))
#            ylim = (0, 110) # TODO
#            self.mesh.show(xlim=xlim, ylim=ylim) # add ax argument
            self.mesh.show(ax=ax, color_bar=False)
    
    def write2in(self, param={}, typ=''):
        """ Create configuration file for inversion.
        
        Parameters
        ----------
        param : dict
            Dictionnary of parameters and values for the inversion settings.
        typ : str, optional
            Type of inversion. By default given by `R2.typ`.
        """
        if typ == '':
            typ = self.typ
        if all(self.surveys[0].df['irecip'].values == 0):
            if 'a_wgt' not in self.param:
                self.param['a_wgt'] = 0.01
            if 'b_wft' not in self.param:
                self.param['b_wgt'] = 0.02
        if typ == 'cR2':
            if self.errTypIP != 'none': # we have individual errors
                if 'b_wgt' not in self.param:
                    self.param['b_wgt'] = 0
                if 'c_wgt' not in self.param:
                    self.param['c_wgt'] = 0
                if 'a_wgt' not in self.param:
                    self.param['a_wgt'] = 0.01 # not sure of that (Gui)
            else:
                if 'c_wgt' not in self.param:
                    self.param['c_wgt'] = 1 # better if set by user !!
                if 'd_wgt' not in self.param:
                    self.param['d_wgt'] = 2
                
        # all those parameters are default but the user can change them and call
        # write2in again
        for p in param:
            self.param[p] = param[p]
        
        if self.iTimeLapse == True:
            refdir = os.path.join(self.dirname, 'ref')
            if os.path.exists(refdir) == False:
                os.mkdir(refdir)
            param = self.param.copy()
            param['a_wgt'] = 0.01
            param['b_wgt'] = 0.02
            param['num_xy_poly'] = 0
            param['reg_mode'] = 0 # set by default in ui.py too
            self.configFile = write2in(param, refdir, typ=typ)
            param = self.param.copy()
            param['num_regions'] = 0
            param['reg_mode'] = 2
            param['timeLapse'] = 'Start_res.dat'
            write2in(param, self.dirname, typ=typ)
        else:
            self.configFile = write2in(self.param, self.dirname, typ=typ)
        

    def write2protocol(self, errTyp='', errTypIP='', errTot=False, **kwargs):
        """ Write a protocol.dat file for the inversion code.
        
        Parameters
        ----------
        errTyp : str
            Type of the DC error. Either 'pwl', 'lin', 'obs'.
        errTypIP : str
            Type of the IP error. Either 'pwl'.
        """
        if self.typ == 'R2':
            ipBool = False
        elif self.typ == 'cR2':
            ipBool = True
        else:
            print('NOT IMPLEMENTED YET')

        if errTyp == '':
            errTyp = self.errTyp
#        if ipBool == True:
        if errTypIP == '':
            errTypIP = self.errTypIP
        
        
        if self.iTimeLapse == False:
            self.surveys[0].write2protocol(os.path.join(self.dirname, 'protocol.dat'),
                        errTyp=errTyp, ip=ipBool, errTypIP=errTypIP, errTot=errTot)
        else:
            # a bit simplistic but assign error to all based on Transfer resistance
#            allHaveReciprocal = all(self.iTimeLapseReciprocal == True)
            # let's assume it's False all the time for now
            content = ''
            for i, s in enumerate(self.surveys[1:]):
                content = content + str(len(s.df)) + '\n'
                s.df['resist0'] = self.surveys[0].df['resist']
                if errTyp != 'none': # there is an error model
                    s.df['error'] = self.bigSurvey.errorModel(s.df['resist'].values)
                    s.df['index'] = np.arange(1, len(s.df)+1)
                    content = content + s.df[['index','a','b','m','n','resist', 'resist0','error']].to_csv(sep='\t', header=False, index=False)
                else:
                    s.df['index'] = np.arange(1, len(s.df)+1)
                    content = content + s.df[['index','a','b','m','n','resist', 'resist0']].to_csv(sep='\t', header=False, index=False)
                if i == 0:
                    refdir = os.path.join(self.dirname, 'ref')
                    if os.path.exists(refdir) == False:
                        os.mkdir(refdir)
                    if 'mesh.dat' in os.listdir(self.dirname):
                        shutil.copy(os.path.join(self.dirname, 'mesh.dat'),
                                os.path.join(self.dirname, 'ref', 'mesh.dat'))
                    with open(os.path.join(refdir, 'protocol.dat'), 'w') as f:
                        f.write(content) # write the protocol for the reference file
            with open(os.path.join(self.dirname, 'protocol.dat'), 'w') as f:
                f.write(content)
        
        
    def runR2(self, dirname='', dump=print):
        """ Run the executable in charge of the inversion.
        
        Parameters
        ----------
        dirname : str, optional
            Path of the directory where to run the inversion code.
        dump : function, optional
            Function to print the output of the invrsion code while running.
        """
        # run R2.exe
        exeName = self.typ + '.exe'
        cwd = os.getcwd()
        if dirname == '':
            dirname = self.dirname
        os.chdir(dirname)
        targetName = os.path.join(dirname, exeName)
        actualPath = self.cwd
#        actualPath = os.path.dirname(os.path.relpath(__file__))
        
        # copy R2.exe
        if ~os.path.exists(targetName):
            shutil.copy(os.path.join(actualPath, 'api', 'exe', exeName), targetName)  
        
            
        if OS == 'Windows':
            cmd = [exeName]
        else:
            cmd = ['wine',exeName]
            
#        p = Popen(cmd, stdout=PIPE, shell=False)
#        while p.poll() is None:
#            line = p.stdout.readline().rstrip()
#            dump(line.decode('utf-8'))
        
        def execute(cmd):
            popen = Popen(cmd, stdout=PIPE, shell=False, universal_newlines=True)
            for stdout_line in iter(popen.stdout.readline, ""):
                yield stdout_line
            popen.stdout.close()
            return_code = popen.wait()
            if return_code:
                print('error on return_code')
        
        for text in execute(cmd):
                dump(text.rstrip())

        os.chdir(cwd)
        
        
    def invert(self, param={}, iplot=False, dump=print, modErr=False):
        """ Invert the data, first generate R2.in file, then run
        inversion using appropriate wrapper, then return results.
        
        Parameters
        ----------
        param : dict, optional
            Dictionary of parameters for inversion. Will be passed to
            `R2.write2in()`.
        iplot : bool, optional
            If `True`, will plot the results of the inversion using
            `R2.showResults()`.
        dump : function, optinal
            Function to print the output of the inversion. To be passed to 
            `R2.runR2()`.
        """
        # clean meshResults list
        self.meshResults = []
        
        # create mesh if not already done
        if 'mesh' not in self.param:
            self.createMesh()
        
        # compute modelling error if selected
        if modErr is True:
            self.computeModelError()
            errTot = True
        else:
            errTot = False
        
        # write configuration file
#        if self.configFile == '':
        self.write2in(param=param)
        
        self.write2protocol(errTot=errTot)
             
        if self.iTimeLapse == True:
            refdir = os.path.join(self.dirname, 'ref')
            self.runR2(refdir, dump=dump)
            print('----------- finished inverting reference model ------------')
            shutil.copy(os.path.join(refdir, 'f001_res.dat'),
                    os.path.join(self.dirname, 'Start_res.dat'))
        self.runR2(dump=dump)
        
        if iplot is True:
#            self.showResults()
            self.showSection() # TODO need to debug that for timelapse and even for normal !
            # pass an index for inverted survey time

    
    def showResults(self, index=0, ax=None, edge_color='none', attr='', sens=True, color_map='viridis', **kwargs):
        """ Show the inverteds section.
        
        Parameters
        ----------
        index : int, optional
            Index of the inverted section (mainly in the case of time-lapse
            inversion)
        ax : matplotlib axis, optional
            If specified, the inverted graph will be plotted agains `ax`.
        edge_color : str, optional
            Color of the edges of the mesh.
        attr : str, optional
            Name of the attribute to be plotted.
        sens : bool, optional
            If `True` and if sensitivity is available, it will be plotted as
            a white transparent shade on top of the inverted section.
        color_map : str, optional
            Name of the colormap to be used.
        """
        if (attr == '') & (self.typ == 'R2'):
            attr = 'Resistivity(log10)'
        if (attr == '') & (self.typ == 'cR2'):
            attr = 'Sigma_real(log10)'
        if len(self.meshResults) == 0:
            self.getResults()
        if len(self.meshResults) > 0:
            self.meshResults[index].show(ax=ax, edge_color=edge_color, attr=attr, sens=sens, color_map=color_map, **kwargs)
        else:
            print('Unexpected Error')

    
    def getResults(self):
        """ Collect inverted results after running the inversion and adding
        them to `R2.meshResults` list.
        """
        if self.typ == 'R2':
            if self.iTimeLapse == True:
                fresults = os.path.join(self.dirname, 'ref', 'f001_res.vtk')
                print('reading ref', fresults)
                mesh = mt.vtk_import(fresults)
                mesh.elec_x = self.elec[:,0]
                mesh.elec_y = self.elec[:,1]
                self.meshResults.append(mesh)
            for i in range(100):
                fresults = os.path.join(self.dirname, 'f' + str(i+1).zfill(3) + '_res.vtk')
                if os.path.exists(fresults):
                    print('reading ', fresults)
                    mesh = mt.vtk_import(fresults)
                    mesh.elec_x = self.elec[:,0]
                    mesh.elec_y = self.elec[:,1]
                    self.meshResults.append(mesh)
                else:
                    break
        if self.typ == 'cR2':
            fresults = os.path.join(self.dirname, 'f001.vtk')
            print('reading ref', fresults)
            mesh = mt.vtk_import(fresults)
            mesh.elec_x = self.elec[:,0]
            mesh.elec_y = self.elec[:,1]
            self.meshResults.append(mesh)

            
    def showSection(self, fname='', ax=None, ilog10=True, isen=False, figsize=(8,3)):
        """ Show inverted section based on the `_res.dat``file instead of the
        `.vtk`.
        
        Parameters
        ----------
        fname : str, optional
            Name of the inverted `.dat` file produced by the inversion.
        ax : matplotlib axis, optional
            If specified, the graph will be plotted along `ax`.
        ilog10 : bool, optional
            If `True`, the log10 of the resistivity will be used.
        isen : bool, optional
            If `True`, sensitivity will be displayed as white transparent
            shade on top of the inverted section.
        figsize : tuple, optional
            Size of the figure.
        """
        print('showSection called')
        if fname == '':
            fname = os.path.join(self.dirname, 'f001.dat')
        res = pd.read_csv(fname, delimiter=' *', header=None, engine='python').values
        lenx = len(np.unique(res[:,0]))
        leny = len(np.unique(res[:,1]))
        x = res[:,0].reshape((leny, lenx), order='F')
        y = res[:,1].reshape((leny, lenx), order='F')
        z = res[:,2].reshape((leny, lenx), order='F')
        if isen:
            sen = pd.read_csv(fname.replace('res','sen'), delimiter=' *', header=None, engine='python').values
            lenx = len(np.unique(sen[:,0]))
            leny = len(np.unique(sen[:,1]))
        #            xs = sen[:,0].reshape((leny, lenx), order='F')
        #            ys = sen[:,1].reshape((leny, lenx), order='F')
            zs = sen[:,2].reshape((leny, lenx), order='F')
            zs = np.log10(zs)
            zs -= np.min(zs)
            alpha = zs/np.max(zs)
        #            alpha[alpha < 0] = 0
            print(np.max(alpha), np.min(alpha))
        if ilog10:
            z = np.log10(z)
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.get_figure()
        cax = ax.pcolormesh(x, y, z)
        ax.plot(self.elec[:,0], self.elec[:,1], 'ko')
    #    fig.canvas.draw() # need to draw the figure to have the cax.get_facecolors()
    #    print(cax.get_facecolors().shape)
    #    print(alpha.flatten().shape)
    #    for a in cax.get_facecolors():
    #        a[3] = 0
        #for a, b in zip(cax.get_facecolors(), alpha.flatten()):
        #    a[3] = 0.5
        #    print(a)
    #    fig.canvas.draw()
        cbar = fig.colorbar(cax, ax=ax)
        if ilog10:
            cbar.set_label(r'$\log_{10}(\rho) [\Omega.m]$')
        else:
            cbar.set_label(r'$\rho [\Omega.m]$')
        ax.set_ylabel('Depth [m]')
        ax.set_xlabel('Distance [m]')
#        fig.tight_layout()
    #    fig.show()
#        return fig
    
    def addRegion(self, xy, res0, ax=None):
        """ Add region according to a polyline defined by `xy` and assign it
        the starting resistivity `res0`.
        
        Parameters
        ----------
        xy : array
            Array with two columns for the x and y coordinates.
        res0 : float
            Resistivity values of the defined area.
        ax : matplotlib.axes.Axes
            If not `None`, the region will be plotted against this axes.
        """
        
        if ax is None:
            fig, ax = plt.subplots()
        self.mesh.show(ax=ax)
        selector = SelectPoints(ax, np.array(self.mesh.elm_centre).T,
                                typ='poly')
        selector.setVertices(xy)
        selector.getPointsInside()
        idx = selector.iselect
        self.regid = self.regid + 1
        self.regions[idx] = self.regid
        self.resist0[idx] = res0
        

    def createModel(self, ax=None, dump=print, typ='poly', addAction=None):
        """ Interactive model creation for forward modelling.
        
        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Axes to which the graph will be plotted.
        dump : function, optional
            Function that outputs messages from the interactive model creation.
        typ : str
            Type of selection either `poly` for polyline or `rect` for
            rectangle.
        addAction : function
            Function to be called once the selection is finished (design for
            GUI purpose).
        
        Returns
        -------
        fig : matplotlib.figure
            If `ax` is `None`, will return a figure.
        """
        if self.mesh is None:
            print('will create a mesh before')
            self.createMesh()
        if ax is None:
            fig, ax = plt.subplots()
        else:
            fig = ax.figure
        # regions definition
#        self.mesh.add_attribute()
        def callback(idx):
            print('nb elements selected:', np.sum(idx))
#                res = input('Input the resistivity [Ohm.m] of the section:')
#                print(res)
            self.regid = self.regid + 1
            self.regions[idx] = self.regid
            self.mesh.cell_attributes = list(self.regions)
#            self.mesh.show(ax=ax)
            # TODO change the collection of the cells impacted and update canvas
            # or just use cross of different colors
            if addAction is not None:
                addAction()
        self.mesh.show(ax=ax)
        # we need to assign a selector to self otherwise it's not used
        self.selector = SelectPoints(ax, np.array(self.mesh.elm_centre).T,
                                     typ=typ, callback=callback)
        if ax is None:
            return fig
            
        
    def assignRes0(self, regionValues={}):
        """ Assign starting resitivity values.
        
        Parameters
        ----------
        regionValues : dict
            Dictionnary with key beeing the region number and the value beeing
            the resistivity in [Ohm.m].
        """
        for key in regionValues.keys():
            self.resist0[self.regions == key] = regionValues[key]
        
        
    def createSequence(self, skipDepths=[(0, 10)]):
        """ Create a dipole-dipole sequence.
        
        Parameters
        ----------
        skipDepths : list of tuple, optional
            Each tuple in the list is of the form `(skip, depths)`. The `skip` is the number of electrode between the A B and M N electrode. The `depths` is the number of quadrupole which will have the same current electrode (same A B). The higher this number, the deeper the investigation.
        """
        qs = []
        nelec = len(self.elec)
        for sd in skipDepths:
            elec, quad = ddskip(nelec, spacing=1, skip=int(sd[0]), depth=int(sd[1]))
            qs.append(quad)
        qs = np.vstack(qs)
        self.sequence = qs
    
    
    def importElec(self, fname=''):
        """ Import electrodes positions.
        
        Parameters
        ----------
        fname : str
            Path of the CSV file containing the electrodes positions. It should contains 3 columns maximum with the X, Y, Z positions of the electrodes.
        """
        elec = pd.read_csv(fname)
        if elec.shape[1] > 3:
            raise ValueError('The file should have no more than 3 columsn')
        else:
            self.elec = elec
            
    
    def importSequence(self, fname=''):
        """ Import sequence for forward modelling.
        
        Parameters
        ----------
        fname : str
            Path of the CSV file to be imported. The file shouldn't have any headers just 4 columns with the 4 electrodes numbers.
        """
        seq = pd.read_csv(fname)
        if seq.shape[1] != 4:
            raise ValueError('The file should be a CSV file wihtout headers with exactly 4 columns with electrode numbers.')
        else:
            self.sequence = seq
    
    
    def forward(self, noise=0.05, iplot=False):
        """ Operates forward modelling.
        
        Parameters
        ----------
        noise : float, optional 0 <= noise <= 1
            Noise level from a Gaussian distribution that should be applied on the forward apparent resistivities obtained. 
        iplot : bool, optional
            If `True` will plot the pseudo section after the forward modelling.
        """
        fwdDir = os.path.join(self.dirname, 'fwd')
        if os.path.exists(fwdDir):
            shutil.rmtree(fwdDir)
        os.mkdir(fwdDir)
        
        # write the resistivity.dat
        centroids = np.array(self.mesh.elm_centre).T
        resFile = np.zeros((centroids.shape[0],3)) # centroix x, y, z, res0
#        resFile[:,:centroids.shape[1]] = centroids
        resFile[:,-1] = self.resist0
        np.savetxt(os.path.join(fwdDir, 'resistivity.dat'), resFile,
                   fmt='%.3f')
        shutil.copy(os.path.join(self.dirname, 'mesh.dat'),
                    os.path.join(fwdDir, 'mesh.dat'))
        
        # write the forward .in file
        fparam = self.param.copy()
        fparam['job_type'] = 0
        if fparam['mesh_type'] == 3:
            fparam['num_regions'] = 0
            fparam['timeLapse'] = 'resistivity.dat' # just starting resistivity
        else:
            raise ValueError('For now you need to use a triangular mesh for forward modelling')
        write2in(fparam, fwdDir, typ=self.typ)
        
        # write the protocol.dat (that contains the sequence)
        if self.sequence is None:
            self.createSequence()
        seq = self.sequence
        protocol = pd.DataFrame(np.c_[1+np.arange(seq.shape[0]),seq])
        outputname = os.path.join(fwdDir, 'protocol.dat')
        with open(outputname, 'w') as f:
            f.write(str(len(protocol)) + '\n')
        with open(outputname, 'a') as f:
            protocol.to_csv(f, sep='\t', header=False, index=False)
    
        # fun the inversion
        self.runR2(fwdDir) # this will copy the R2.exe inside as well
        
        # create a protocol.dat file (overwrite the method)
        def addnoise(x, level=0.05):
            return np.random.normal(x,level,1)
        addnoise = np.vectorize(addnoise)
        self.noise = noise
        
        elec = self.elec.copy()
        self.createSurvey(os.path.join(fwdDir, 'R2_forward.dat'), ftype='Protocol')
        self.surveys[0].df['resist'] = addnoise(self.surveys[0].df['resist'], noise)
        self.elec = elec
        
        self.write2protocol()
        self.pseudo()
        
        
    def computeModelError(self):
        """ Compute modelling error due to the mesh.
        """
        if self.mesh is None:
            raise ValueError('You fist need to generate a mesh to compute the modelling error.')
            return
        fwdDir = os.path.join(self.dirname, 'err')
        if os.path.exists(fwdDir):
            shutil.rmtree(fwdDir)
        os.mkdir(fwdDir)
        
        # write the resistivity.dat and fparam
        fparam = self.param.copy()
        fparam['job_type'] = 0
        centroids = np.array(self.mesh.elm_centre).T
        if self.param['mesh_type'] == 4:
            fparam['num_regions'] = 1
            maxElem = centroids.shape[0]
            fparam['regions'] = np.array([[1, maxElem, 100]])
        else:
            if '2' in self.typ:
                n = 2
            else:
                n = 3
            resFile = np.zeros((centroids.shape[0],n+1)) # centroix x, y, z, res0
            resFile[:,-1] = 100
            np.savetxt(os.path.join(fwdDir, 'resistivity.dat'), resFile,
                       fmt='%.3f')
            shutil.copy(os.path.join(self.dirname, 'mesh.dat'),
                        os.path.join(fwdDir, 'mesh.dat'))
            fparam['num_regions'] = 0
            fparam['timeLapse'] = 'resistivity.dat'
        write2in(fparam, fwdDir, typ=self.typ)
        
        # write the protocol.dat based on measured sequence
        seq = self.surveys[0].df[['a','b','m','n']].values
        protocol = pd.DataFrame(np.c_[1+np.arange(seq.shape[0]),seq])
        outputname = os.path.join(fwdDir, 'protocol.dat')
        with open(outputname, 'w') as f:
            f.write(str(len(protocol)) + '\n')
        with open(outputname, 'a') as f:
            protocol.to_csv(f, sep='\t', header=False, index=False)
    
        # fun the inversion
        self.runR2(fwdDir) # this will copy the R2.exe inside as well
        
        # get error model
        x = np.genfromtxt(os.path.join(fwdDir, 'R2_forward.dat'), skip_header=1)
        modErr = np.abs(100-x[:,-1])/100
        self.surveys[0].df['modErr'] = modErr
        
        # eventually delete the directory to space space
        
        
    
    def showIter(self, ax=None):
        """ Dispay temporary inverted section after each iteration.
        
        Parameters
        ----------
        ax : matplotib axis, optional
            If specified, the graph will be plotted along `ax`.
        """
        files = os.listdir(self.dirname)
        fs = []
        for f in files:
            if (f[-8:] == '_res.dat') & (len(f) == 16):
                fs.append(f)
        fs = sorted(fs)
        print(fs)
        if len(fs) > 0:
            if self.param['mesh_type'] == 4:
                self.showSection(os.path.join(self.dirname, fs[-1]), ax=ax)
            else:
                x = np.genfromtxt(os.path.join(self.dirname, fs[-1]))
                self.mesh.add_attr_dict({'iter':x[:,-2]})
                self.mesh.show(ax=ax, attr='iter', edge_color='none', color_map='viridis')
                
    def pseudoError(self, ax=None):
        """ Plot pseudo section of errors from file `f001_err.dat`.
        
        Parameters
        ----------
        ax : matplotlib axis
            If specified, the graph will be plotted against `ax`.
        """
        err = np.genfromtxt(os.path.join(self.dirname, 'f001_err.dat'), skip_header=1)
        array = err[:,[-2,-1,-4,-3]].astype(int)
        errors = err[:,0]
        spacing = np.diff(self.elec[[0,1],0])
        pseudo(array, errors, spacing, ax=ax, label='Normalized Errors', log=False, geom=False, contour=False)
    
#    def showOnMesh(self, fname=''):
#        if fname == '':
#            fname = os.path.join(self.dirname, 'f001_res.dat')
#        x = np.genfromtxt(fname)
#        self.mesh.add_attribute(x[:,3], 'iter')
#        self.mesh.show(attr='iter')




def pseudo(array, resist, spacing, label='', ax=None, contour=False, log=True, geom=True):
    nelec = np.max(array)
    elecpos = np.arange(0, spacing*nelec, spacing)
    resist = resist
    
    if geom: # compute and applied geometric factor
        apos = elecpos[array[:,0]-1]
        bpos = elecpos[array[:,1]-1]
        mpos = elecpos[array[:,2]-1]
        npos = elecpos[array[:,3]-1]
        AM = np.abs(apos-mpos)
        BM = np.abs(bpos-mpos)
        AN = np.abs(apos-npos)
        BN = np.abs(bpos-npos)
        K = 2*np.pi/((1/AM)-(1/BM)-(1/AN)+(1/BN)) # geometric factor
        resist = resist*K
        
    if log:
        resist = np.sign(resist)*np.log10(np.abs(resist))
    if label == '':
        if log:
            label = r'$\log_{10}(\rho_a)$ [$\Omega.m$]'
        else:
            label = r'$\rho_a$ [$\Omega.m$]'
    
    cmiddle = np.min([elecpos[array[:,0]-1], elecpos[array[:,1]-1]], axis=0) \
        + np.abs(elecpos[array[:,0]-1]-elecpos[array[:,1]-1])/2
    pmiddle = np.min([elecpos[array[:,2]-1], elecpos[array[:,3]-1]], axis=0) \
        + np.abs(elecpos[array[:,2]-1]-elecpos[array[:,3]-1])/2
    xpos = np.min([cmiddle, pmiddle], axis=0) + np.abs(cmiddle-pmiddle)/2
    ypos = - np.sqrt(2)/2*np.abs(cmiddle-pmiddle)
    
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    cax = ax.scatter(xpos, ypos, c=resist, s=70)#, norm=mpl.colors.LogNorm())
    cbar = fig.colorbar(cax, ax=ax)
    cbar.set_label(label)
    ax.set_title('Pseudo Section')

        
#%% test code
#os.chdir('/media/jkl/data/phd/tmp/r2gui/')
#k = R2('/media/jkl/data/phd/tmp/r2gui/api/invdir')
#k.typ = 'cR2'
#k.createSurvey('/media/jkl/data/phd/tmp/projects/ahdb/survey2018-08-14/data/ert/18081401.csv', spacing=0.5)
#k.createSurvey('api/test/syscalFile.csv', ftype='Syscal')
#k.createMesh(typ='trian')
#k.computeModelError()
#k.pwlfit()
#k.write2protocol(errTyp='pwl', errTot=True)
#k.invert(modErr=True)
#k.createSurvey('api/test/rifleday8.csv', ftype='Syscal')
#k.pwlfit()
#k.invert(iplot=False)
#k.showIter()
#k.showResults()
#k.surveys[0].dca()
#k.pseudo(contour=True)
#k.linfit(iplot=True)
#k.pwlfit()
#k.errTyp='obs'
#k.lmefit(iplot=True)
#k.createMesh(typ='quad', elemx=8)
#k.createMesh(typ='trian')
#k.mesh.show()
#fig, ax = plt.subplots()
#fig.suptitle('kkk')
#k.mesh.show(ax=ax)
#k.write2in()
#k.plotIPFit()
#k.errTyp = 'pwl'
#k.errTypIP = 'pwl'
#k.invert(iplot=False)
#k.showIter()
#k.showResults(edge_color='k')
#k.pseudoError()
#k.showSection()
#fig, ax = plt.subplots()
#fig.suptitle('hkk')
#k.showResults()
#k.showResults(edge_color='none', sens=True)
#k.showResults(attr=attr[0])
#fig, ax = plt.subplots()
#fig.suptitle('kkk')
#k.showResults(ax=ax)
#print(os.path.dirname(os.path.realpath(__file__)))


#fresults = os.path.join('./test/f001_res.vtk')
#if os.path.isfile(fresults):
#    print('kk')
#    mesh_dict=mt.vtk_import(fresults)#makes a dictionary of a mesh 
#    mesh = Mesh_obj.mesh_dict2obj(mesh_dict)# this is a mesh_obj class instance 
#    mesh.show()
#


#%% test for IP
#os.chdir('/media/jkl/data/phd/tmp/r2gui/')
#k = R2('/media/jkl/data/phd/tmp/r2gui/api/invdir')
#k.typ = 'cR2'
#k.createSurvey('api/test/rifleday8.csv', ftype='Syscal')
#k.invert()


#%% test for timelapse inversion
#os.chdir('/media/jkl/data/phd/tmp/r2gui/')
#k = R2('/media/jkl/data/phd/tmp/r2gui/api/invdir/')
#k.createTimeLapseSurvey(os.path.join(k.dirname, '../test/testTimelapse'))
#k.linfit()
#k.pwlfit()
#k.errTyp = 'pwl'
#k.param['a_wgt'] = 0
#k.param['b_wgt'] = 0
#k.createMesh()
#k.write2in()
#k.write2protocol()
#k.invert(iplot=False)
#k.showResults(index=0)
#k.showResults(index=1)
#k.showSection(os.path.join(k.dirname, 'f001_res.vtk'))
#k.showSection(os.path.join(k.dirname, 'f002_res.vtk'))


#%% forward modelling
#os.chdir('/media/jkl/data/phd/tmp/r2gui/')
#k = R2('/media/jkl/data/phd/tmp/r2gui/api/invdir/')
#k.elec = np.c_[np.arange(24), np.zeros((24, 2))]
#k.createMesh(typ='trian')
#
## full API function
#k.addRegion(np.array([[2,0],[8,0],[8,-8],[2,-8],[2,0]]), 10)
#
## full GUI function
#k.createModel()
#k.assignRes0({1:30,2:30,3:40,4:120})
#
#k.forward(iplot=True, noise=0)
#k.invert()

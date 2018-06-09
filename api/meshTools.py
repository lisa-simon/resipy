# -*- coding: utf-8 -*-
"""
Created on Wed May 30 10:19:09 2018, python 3.6.5
@author: jamyd91
Import a vtk file with an unstructured grid (triangular/quad elements) and 
creates a mesh object (with associated functions). The mesh object can have quad or
triangular elements. It is assigned a cell type according the convention in vtk files. 
(ie. cell type 9 <- quad, cell type 5 <- triangle)

Functions: 
    tri_cent() - computes the centre point for a 2d triangular element
    vtk_import() - imports a triangular / quad unstructured grid from a vtk file
    readR2_resdat () - reads resistivity values from a R2 file. 
    quad_mesh () - creates a quadrilateral mesh given electrode x and y coordinates 
                 (returns info needed for R2in)
Classes: 
    mesh_obj
    
Dependencies: 
    matplotlib
    numpy
    tkinter (python standard)
"""
#import standard python packages
#import tkinter as tk
#from tkinter import filedialog
#import anaconda libraries
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap
import time

#%% triangle centriod 
def tri_cent(p,q,r):#code expects points as p=(x,y) and so on ... (counter clockwise prefered)
    Xm=(p[0]+q[0])/2
    Ym=(p[1]+q[1])/2
    k=2/3
    Xc=r[0]+(k*(Xm-r[0]))
    Yc=r[1]+(k*(Ym-r[1]))
    return(Xc,Yc)
    
#%% import a vtk file 
def vtk_import(file_path='ask_to_open',parameter_title='default'):
    #imports a 2d mesh file into the python workspace, can have triangular or quad type elements 
#INPUT:
    #file_path - file path to mesh file. note that a error will occur if the file format is not as expected
    #save_path - leave this as default to save the file in the working directory, make this 'ask_to_open' to open a dialogue box, else enter a custom file path.
    #parameter_title - name of the parameter table in the vtk file, if left as default the first look up table found will be returned 
#OUTPUT: 
    #dictionary with some 'useful' info about the mesh, which can be converted in to a mesh object 
###############################################################################
    if file_path=='ask_to_open':#use a dialogue box to open a file
        print("please select the vtk file to import using the pop up dialogue box. \n")
        root=tk.Tk()
        root.withdraw()
        file_path=filedialog.askopenfilename(title='Select mesh file',filetypes=(("VTK files","*.vtk"),("all files","*.*")))#
    #open the selected file for reading
    fid=open(file_path,'r')
    print("importing vtk (2D mesh) file into python workspace...")
    
    #read in header info and perform checks to make sure things are as expected
    vtk_ver=fid.readline().strip()#read first line
    if vtk_ver.find('vtk')==-1:
        raise ImportError("Unexpected file type... ")
    elif vtk_ver.find('3.0')==-1:#not the development version for this code
        print("Warning: vtk manipulation code was developed for vtk datafile version 3.0, unexpected behaviour may occur")
    title=fid.readline().strip()#read line 2
    format_type=fid.readline().strip()#read line 3
    if format_type=='BINARY':
        raise ImportError("expected ASCII type file format, not binary")
    dataset_type=fid.readline().strip().split()#read line 4
    if dataset_type[1]!='UNSTRUCTURED_GRID':
        print("Warning: code intended to deal with an 'UNSTRUCTURED_GRID' data type not %s"%dataset_type[1])
    
    #read node data
    print("importing mesh nodes...")
    node_info=fid.readline().strip().split()#read line 5
    no_nodes=int(node_info[1])
    #now read in node data
    x_coord=[]#make lists for each of the relevant parameters for each node
    y_coord=[]
    z_coord=[]
    node_num=[]
    for i in range(no_nodes):
        coord_data=fid.readline().strip().split()
        x_coord.append(float(coord_data[0]))
        y_coord.append(float(coord_data[1]))
        z_coord.append(float(coord_data[2]))
        node_num.append(i)
    
    #now read in element data
    print("importing mesh element info...")
    elm_info=fid.readline().strip().split()#read line with cell data
    no_elms=int(elm_info[1])
    no_pts=[]#assign lists to nodes 
    node1=[]
    node2=[]
    node3=[]
    node4=[]
    elm_num=[]
    centriod_x=[]#list will contain the centre points of elements 
    centriod_y=[]
    areas=[]#areas of cells (might be useful in the future)
    ignored_cells=0
    #import element data ... expects triangles or quads 
    for i in range(no_elms):
        elm_data=fid.readline().strip().split()
        if int(elm_data[0])==3:
            if i==0:
                print("triangular elements detected")
                vert_no=3
            no_pts.append(int(elm_data[0]))
            #nodes
            node1.append(int(elm_data[1]))
            node2.append(int(elm_data[2]))
            node3.append(int(elm_data[3]))
            elm_num.append(i+1)
            #find the centriod of the element for triangles
            n1=(x_coord[int(elm_data[1])],y_coord[int(elm_data[1])])#in vtk files the 1st element id is 0 
            n2=(x_coord[int(elm_data[2])],y_coord[int(elm_data[2])])
            n3=(x_coord[int(elm_data[3])],y_coord[int(elm_data[3])])
            xy_tuple=tri_cent(n1,n2,n3)#actual calculation
            centriod_x.append(xy_tuple[0])
            centriod_y.append(xy_tuple[1])
            #find area of element (for a triangle this is 0.5*base*height)
            base=(((n1[0]-n2[0])**2) + ((n1[1]-n2[1])**2))**0.5
            mid_pt=((n1[0]+n2[0])/2,(n1[1]+n2[1])/2)
            height=(((mid_pt[0]-n3[0])**2) + ((mid_pt[1]-n3[1])**2))**0.5
            areas.append(0.5*base*height)
        elif int(elm_data[0])==4:
            if i==0:
                print("quad elements detected")
                vert_no=4
            no_pts.append(int(elm_data[0]))
            #nodes
            node1.append(int(elm_data[1]))
            node2.append(int(elm_data[2]))
            node3.append(int(elm_data[3]))
            node4.append(int(elm_data[4]))
            elm_num.append(i+1)
            #assuming element centres are the average of the x - y coordinates for the quad
            n1=(x_coord[int(elm_data[1])],y_coord[int(elm_data[1])])#in vtk files the 1st element id is 0 
            n2=(x_coord[int(elm_data[2])],y_coord[int(elm_data[2])])
            n3=(x_coord[int(elm_data[3])],y_coord[int(elm_data[3])])
            n4=(x_coord[int(elm_data[4])],y_coord[int(elm_data[4])])
            centriod_x.append(np.mean((n1[0],n2[0],n3[0],n4[0])))
            centriod_y.append(np.mean((n1[1],n2[1],n3[1],n4[1])))
            #finding element areas, base times height.  
            elm_len=abs(n2[0]-n1[0])#element length
            elm_hgt=abs(n2[1]-n3[1])#element hieght
            areas.append(elm_len*elm_hgt)
        else: 
            print("WARNING: unkown cell type encountered!")
            ignored_cells+=1
    #compile some information        
    centriod=(centriod_x,centriod_y)#centres of each element in form (x...,y...)
    if vert_no==3:
        node_maps=(node1,node2,node3)
    elif vert_no==4:
        node_maps=(node1,node2,node3,node4)
        
    if ignored_cells>0:
        print("%i cells ignored in the vtk file"%ignored_cells)
    
    #now for final part of file - cell type info
    cell_type_data=fid.readline().strip()
    cell_type=fid.readline().strip().split()
    _=fid.readline()#read point data line
    _=fid.readline()#read cell data line ... i'm not sure why these need to be repeated, must be for the table lookup process
    cell_attributes=fid.readlines()#reads the last portion of the file
    #finished reading the file
    fid.close()
    print("reading cell attributes...")
    # read through cell attributes to find the relevant parameter table?
    if parameter_title=='default' and title=='Output from R2':    
        parameter_title='Resistivity(Ohm-m)'# the name of title if the output is from R2
        do_find=1
    elif parameter_title == 'n/a':#dont bother looking for attributes
        do_find=0
    elif parameter_title=='default':
        do_find=2
    else:
        do_find=1
    #now that conditions for finding a parameter table have been decided... 
    if do_find==1:
        for i in range(len(cell_attributes)):
            probe=cell_attributes[i].split()
            if probe[1]==parameter_title:
               #then the following line should read "LOOKUP_TABLE default"
               check=cell_attributes[i+1]
               print("identified relevant table for element attributes...")
               indx=i+2
               break
            if i==range(len(cell_attributes)):
               print("WARNING: could not find relevant table for element attributes! Make sure you havent made a mistake with table name in the VTK file. \n")
               indx=3
        values=[float(k) for k in cell_attributes[indx].split()]
    elif do_find==2:
        if len(cell_attributes)>=3:
            probe=cell_attributes[1].split()
            parameter_title=probe[1]
            values=[float(k) for k in cell_attributes[3].split()]
        else:
            values='n/a'    
    elif do_find==0:
        values='n/a'
#need two options here, either find depth or find if the elements lie in a certain region
    print("finished importing mesh.\n")
#return information in a dictionary: 
    return {'num_nodes':no_nodes,#number of nodes
            'num_elms':no_elms,#number of elements 
            'node_x':x_coord,#x coordinates of nodes 
            'node_y':y_coord,#y coordinates of nodes
            'node_z':z_coord,#z coordinates of nodes 
            'node_id':node_num,#node id number 
            'elm_id':elm_num,#element id number 
            'num_elm_nodes':no_pts,#number of points which make an element
            'node_data':node_maps,#nodes of element vertices
            'elm_centre':centriod,#centre of elements (x,y)
            'elm_area':areas,#area of each element
            'cell_type':cell_type,
            'parameters':values,#the values of the attributes given to each cell 
            'parameter_title':parameter_title,
            'cell_attribute_dump':cell_attributes,
            'dict_type':'mesh_info',
            'original_file_path':file_path} 
    
#%% Read in resistivity values from R2 output 
def readR2_resdat(file_path):
    #reads resistivity values in f00#_res.dat file output from R2, 
#INPUT:
    #file_path - string which maps to the _res.dat file
#OUTPUT:
    #res_values - resistivity values returned from the .dat file 
################################################################################
    if not isinstance (file_path,str):
        raise NameError("file_path variable is not a string, and therefore can't be parsed as a file path")
    fh=open(file_path,'r')
    dump=fh.readlines()
    fh.close()
    res_values=[]
    for i in range(len(dump)):
        line=dump[i].split()
        res_values.append(float(line[2]))
    return res_values   

#%% read in sensitivity values 
def readR2_sensdat(file_path):
    #reads resistivity values in f00#_res.dat file output from R2, 
#INPUT:
    #file_path - string which maps to the _res.dat file
#OUTPUT:
    #res_values - resistivity values returned from the .dat file 
################################################################################
    if not isinstance (file_path,str):
        raise NameError("file_path variable is not a string, and therefore can't be parsed as a file path")
    fh=open(file_path,'r')
    dump=fh.readlines()
    fh.close()
    sens_values=[]
    for i in range(len(dump)):
        line=dump[i].split()
        sens_values.append(float(line[2]))
    return sens_values   

#%% create mesh object
class Mesh_obj: 
    """
    create a mesh class
    put class variables here 
    """
    no_attributes = 1 # it follows we may want to add "attributes to each cell"
    #... we begin assuming each cell has a resistivity assocaited with it but
    #... we may also want associate each cell with a sensitivity for example
    
    def __init__(self,#function constructs our mesh object. 
                 num_nodes,#number of nodes
                 num_elms,#number of elements 
                 node_x,#x coordinates of nodes 
                 node_y,#y coordinates of nodes
                 node_z,#z coordinates of nodes 
                 node_id,#node id number 
                 elm_id,#element id number 
                 node_data,#nodes of element vertices
                 elm_centre,#centre of elements (x,y)
                 elm_area,#area of each element
                 cell_type,#according to vtk format
                 cell_attributes,#the values of the attributes given to each cell 
                 atribute_title,#what is the attribute? we may use conductivity instead of resistivity for example
                 original_file_path='N/A') :
        #assign varaibles to the mesh object 
        self.num_nodes=num_nodes
        self.num_elms=num_elms
        self.node_x = node_x
        self.node_y = node_y
        self.node_z = node_z
        self.node_id=node_id
        self.elm_id=elm_id
        self.node_data = node_data
        self.elm_centre=elm_centre
        self.elm_area=elm_area
        self.cell_type=cell_type
        self.cell_attributes=cell_attributes 
        self.atribute_title=atribute_title
        self.original_file_path=original_file_path
        self.ndims=2
    
    def add_e_nodes(self,e_nodes):
        self.e_nodes = e_nodes
        self.elec_x = np.array(self.node_x)[np.array(e_nodes)]
        self.elec_y = np.array(self.node_y)[np.array(e_nodes)]
    
    #add some functions to allow adding some extra attributes to mesh 
    def add_sensitvity(self,values):#sensitivity of the mesh
        if len(values)!=self.num_elms:
            raise ValueError("The length of the new attributes array does not match the number of elements in the mesh")
        self.sensitivities = values
        
    def add_conductivities(self,values):
        if len(values)!=self.num_elms:
            raise ValueError("The length of the new attributes array does not match the number of elements in the mesh")
        self.conductivities = values
        
    def log10(self):#adds a log 10 (resistivity) to the mesh
        Mesh_obj.no_attributes += 1
        self.log_attribute=np.log10(self.cell_attributes)
        
    def file_path(self):#returns the file path from where the mesh was imported
        return(format(self.original_file_path))
       
    def Type2VertsNo(self):#converts vtk cell types into number of vertices each element has 
        if int(self.cell_type[0])==5:#then elements are triangles
            return 3
        elif int(self.cell_type[0])==8 or int(self.cell_type[0])==9:#elements are quads
            return 4
        #add element types as neccessary 
        else:
            print("WARNING: unrecognised cell type")
            return 0
        
    def summary(self):
        #prints summary information about the mesh
        print("\n_______mesh summary_______")
        print("Number of elements: %i"%int(self.num_elms))
        print("Number of nodes: %i"%int(self.num_nodes))
        print("Attribute title: %s"%self.atribute_title)
        print("Number of cell vertices: %i"%self.Type2VertsNo())
        print("Number of cell attributes: %i"%int(self.no_attributes))
        print("original file path: %s"%self.file_path())

    def show(self,color_map = 'Spectral',#displays the mesh using matplotlib
             color_bar = True,
             xlim = "default",
             ylim = "default",
             ax = None,
             electrodes = True,
             sens = False,
             edge_color = 'k',
             vmin=None,
             vmax=None,
             attr='None'):
        """
        Show a mesh object using matplotlib. The color map variable should be 
        a string refering to the color map you want (default is "jet").
        As we're using the matplotlib package here any color map avialable within 
        matplotlib package can be used to display the mesh here also. See: 
        https://matplotlib.org/2.0.2/examples/color/colormaps_reference.html
        """ 
        #INPUT:
            #color_map - color map reference 
            #color_bar - Boolian, True to plot colorbar 
            #xlim -  axis x limits as (ymin, ymax)
            #ylim - axis y limits as (ymin, ymax)
            #ax - axis handle if preexisting (error will thrown up if not)
            #electrodes - Boolian, enter true to add electrodes to plot
            #sens - Boolian, enter true to plot sensitivities 
        #OUTPUT:
            #matplotlib figure with mesh 
        #######################################################################
        #check color map argument is a string 
        if not isinstance(color_map,str):#check the color map variable is a string
            raise NameError('color_map variable is not a string')
            #not currently checking if the passed variable is in the matplotlib library
                #make figure
        if ax is None:
            fig,ax=plt.subplots()
        #if no dimensions are given then set the plot limits to edge of mesh
        try: 
            if xlim=="default":
                xlim=[min(self.elec_x),max(self.elec_x)]
            if ylim=="default":
                doiEstimate = 2/3*np.abs(self.elec_x[0]-self.elec_x[-1]) # TODO depends on longest dipole
                print(doiEstimate)
                ylim=[min(self.elec_y)-doiEstimate,max(self.elec_y)]
        except AttributeError:
            if xlim=="default":
                xlim=[min(self.node_x),max(self.node_x)]
            if ylim=="default":
                ylim=[min(self.node_y),max(self.node_y)]
        #print('xlim', xlim, ylim)
        a = time.time() #time how long it takes to plot the mesh? 
        
        ##plot mesh! ## 
        #compile mesh coordinates into polygon coordinates  
        nodes = np.c_[self.node_x, self.node_y]
        connection = np.array(self.node_data).T # connection matrix 
        #compile polygons patches into a "patch collection"
        X=np.array(self.cell_attributes) # maps resistivity values on the color map
        coordinates = nodes[connection]
        if vmin is None:
            vmin = np.min(X)
        if vmax is None:
            vmax = np.max(X)
        coll = PolyCollection(coordinates, array=X, cmap=color_map, edgecolors=edge_color)
        coll.set_clim(vmin=vmin, vmax=vmax)
        #coll = PolyCollection(nodes[connection], array=X, cmap=color_map, edgecolors=edge_color)
        ax.add_collection(coll)#blit polygons to axis
        ax.autoscale()
        #were dealing with patches and matplotlib isnt smart enough to know what the right limits are, hence set axis limits 
        ax.set_ylim(ylim)
        ax.set_xlim(xlim)
        
        if color_bar:#add the color bar 
            cbar = plt.colorbar(coll, ax=ax)#add colorbar
            cbar.set_label(self.atribute_title) #set colorbar title      
        ax.set_aspect('equal')#set aspect ratio equal (stops a funny looking mesh)

        #biuld alpha channel if we have sensitivities 
        if sens:
            try:
                weights = np.log10(np.array(self.sensitivities)) #values assigned to alpha channels 
                alphas = np.linspace(1, 0, self.num_elms)#array of alpha values 
                raw_alpha = np.ones((self.num_elms,4),dtype=float) #raw alpha values 
                raw_alpha[..., -1] = alphas
                alpha_map = ListedColormap(raw_alpha) # make a alpha color map which can be called by matplotlib
                #make alpha collection
                alpha_coll = PolyCollection(coordinates, array=weights, cmap=alpha_map, edgecolors=None)
                #*** the above line can cuase issues "attribute error" no np.array has not attribute get_transform, 
                #*** i still cant figure out why this is becuase its the same code used to plot the resistivities 
                ax.add_collection(alpha_coll)
            except AttributeError:
                print("no sensitivities in mesh object to plot")
        
        if electrodes: #try add electrodes to figure if we have them 
            try: 
                ax.plot(self.elec_x,self.elec_y,'ko')
            except AttributeError:
                print("no electrodes in mesh object to plot")
        print('Mesh plotted in %6.5f seconds'%(time.time()-a))

            
    def add_attribute(self,values):
        #add a new attribute to mesh 
        if len(values)!=self.num_elms:
            raise ValueError("The length of the new attributes array does not match the number of elements in the mesh")
        Mesh_obj.no_attributes += 1
        self.new_attribute=values #allows us to add an attributes to each element.
        #this function needs fleshing out more to allow custom titles and attribute names
    
    def update_attribute(self,new_attributes,new_title='default'):
        #allows you to reassign the cell attributes in the mesh object 
        if len(new_attributes)!=self.num_elms:
            raise ValueError("The length of the new attributes array does not match the number of elements in the mesh")
        self.cell_attributes=new_attributes
        self.atribute_title=str(new_title)
    
    @classmethod # creates a mesh object from a mesh dictionary
    def mesh_dict2obj(cls,mesh_info):
        #converts a mesh dictionary produced by the vtk import function into a 
        #mesh object, its an alternative way to make a mesh object. 
    #INPUT: mesh_info - dictionary type mesh
    #OUTPUT: mesh obj
    ###########################################################################
        #check the dictionary is a mesh
        try: 
            if mesh_info['dict_type']!='mesh_info':
                raise NameError("dictionary is not a mesh type")
        except KeyError:
                raise ImportError("dictionary has no dict type variable") 
        #covert into an object 
        obj=cls(mesh_info['num_nodes'],
                     mesh_info['num_elms'], 
                     mesh_info['node_x'],
                     mesh_info['node_y'],
                     mesh_info['node_z'],
                     mesh_info['node_id'],
                     mesh_info['elm_id'],
                     mesh_info['node_data'],
                     mesh_info['elm_centre'],
                     mesh_info['elm_area'],
                     mesh_info['cell_type'],
                     mesh_info['parameters'],
                     mesh_info['parameter_title'],
                     mesh_info['original_file_path'])
        return (obj)
    
    @staticmethod
    def help_me():#a basic help me file, needs fleshing out
        available_functions=["show","summary","show_mesh","log10","add_attribute","mesh_dict2obj","Type2VertsNo"]
        print("\n_______________________________________________________")#add some lines, make info look pretty
        print("available functions within the mesh_obj class: \n")
        for i in range(len(available_functions)):
            print("%s"%available_functions[i])
        print("_______________________________________________________")
        
#%% build a quad mesh        
def quad_mesh(elec_x,elec_y,#doi=-1,nbe=-1,cell_height=-1,
              elemx=4, xgf=1.5, elemy=20, yf=1.1, ygf=1.5):
# creates a quaderlateral mesh given the electrode x and y positions. Function
# relies heavily on the numpy package.
# INPUT: 
#     elec_y - electrode x coordinates 
#     elec_y - electrode y coordinates 
#     doi - depth of investigation (if left as -1 = half survey width)
#     cell_height - cell thicknesses in the mesh (if left as -1 = 1/4 electrode spacing)
#     nbe - number of element nodes in between each electrode (if left as -1 = 3)
# OUTPUT: 
#     Mesh - mesh object 
#     meshx - mesh x locations for R2in file 
#     meshy - mesh y locations for R2in file (ie node depths)
#     topo - topography for R2in file
#     elec_node - x columns where the electrodes are 
###############################################################################
    ###
    elec = np.c_[elec_x, elec_y]
    
    # create meshx
    meshx = np.array([])
    for i in range(len(elec)-1):
        elec1 = elec[i,0]
        elec2 = elec[i+1,0]
        espacing = np.abs(elec1-elec2)
        dx = espacing/elemx # we ask for elemx nodes between electrodes
        if i == 0:
            xx2 = np.arange(elec1-espacing, elec1, dx)
            xx3 = np.ones(elemx)*elec1-espacing
            dxx = espacing
            for i in range(1,elemx):
                xx3[i] = xx3[i-1]-dxx*xgf
                dxx = dxx*xgf
            meshx = np.r_[meshx, xx3[::-1], xx2[1:]]
        xx = np.arange(elec1, elec2, dx)
        meshx = np.r_[meshx, xx]
        if i == len(elec)-2:
            xx2 = np.arange(elec2, elec2+espacing, dx)
            xx3 = np.ones(elemx)*elec2+espacing
            dxx = espacing
            for i in range(1,elemx):
                xx3[i] = xx3[i-1]+dxx*xgf
                dxx = dxx*xgf
            meshx = np.r_[meshx, xx2, xx3]
    
    # create e_nodes
    elec_node = np.arange(2*elemx-1, 2*elemx-1+len(elec)*elemx, elemx)

    #TODO make sure it's dividable by patchx and patch y
    
    # create meshy
    meshy = np.zeros(elemy)
#    dyy = espacing/(elemx*4)
    dyy = 0.05
    for i in range(1, elemy):
        meshy[i] = meshy[i-1]+dyy*yf
        dyy = dyy*yf
    elemy2 = int(elemy/2)
    yy = np.ones(elemy2)*meshy[-1]
    for i in range(1, elemy2):
        yy[i] = yy[i-1]+dyy*xgf
        dyy = dyy*xgf
    meshy = np.r_[meshy, yy[1:]]
    
    # create topo
    topo = np.interp(meshx, elec[:,0], elec[:,1])
    
    no_electrodes = len(elec)
    
    ###
    #find the columns relating to the electrode nodes? 
#    elec_node=[meshx.index(elec_x[i])+1 for i in range(len(elec_x))]
    
    #print some warnings for debugging 
    if len(topo)!=len(meshx):
        print("WARNING: topography vector and x coordinate arrays not the same length! ")
    elif len(elec_node)!=no_electrodes:
        print("WARNING: electrode node vector and number of electrodes mismatch! ")
     
    # what is the number of regions? (elements)
    no_elms=(len(meshx)-1)*(len(meshy)-1)
    no_nodes=len(meshx)*len(meshy)
    
    # compute node mappins 
    y_dim=len(meshy)
    fnl_node=no_nodes-1
    
    node_mappins=(np.arange(0,fnl_node-y_dim),
                  np.arange(y_dim,fnl_node),
                  np.arange(y_dim+1,fnl_node+1),
                  np.arange(1,fnl_node-y_dim+1))
    
    del_idx=np.arange(y_dim-1,len(node_mappins[0]),y_dim)
    
    node_mappins = [list(np.delete(node_mappins[i],del_idx)) for i in range(4)]#delete excess node placements
    #compute node x and y  (and z)
    node_x,node_y=np.meshgrid(meshx,meshy)
    #account for topography in the y direction 
    node_y = [topo-node_y[i,:] for i in range(y_dim)]#list comprehension to add topography to the mesh
    node_y=list(np.array(node_y).flatten(order='F'))
    node_x=list(node_x.flatten(order='F'))
    node_z=[0]*len(node_x)
    
    #compute element centres and areas
    centriod_x=[]
    centriod_y=[]
    areas=[]
    for i in range(no_elms):
        #assuming element centres are the average of the x - y coordinates for the quad
        n1=(node_x[int(node_mappins[0][i])],node_y[int(node_mappins[0][i])])#in vtk files the 1st element id is 0 
        n2=(node_x[int(node_mappins[1][i])],node_y[int(node_mappins[1][i])])
        n3=(node_x[int(node_mappins[2][i])],node_y[int(node_mappins[2][i])])
        n4=(node_x[int(node_mappins[3][i])],node_y[int(node_mappins[3][i])])
        centriod_x.append(np.mean((n1[0],n2[0],n3[0],n4[0])))
        centriod_y.append(np.mean((n1[1],n2[1],n3[1],n4[1])))
        #finding element areas, base times height.  
        elm_len=abs(n2[0]-n1[0])#element length
        elm_hgt=abs(n2[1]-n3[1])#element hieght
        areas.append(elm_len*elm_hgt)
    
    #make mesh object    
    Mesh = Mesh_obj(no_nodes,
                    no_elms,
                    node_x,
                    node_y,
                    node_z,
                    list(np.arange(0,no_nodes)),
                    list(np.arange(0,no_elms)),
                    node_mappins,
                    (centriod_x,centriod_y),
                    areas,
                    [9],
                    [0]*no_elms,
                    'no attribute')
    
    elec_node2 = elec_node*len(meshy) # because we use columns based flattening
    Mesh.add_e_nodes(elec_node2)
    
    return Mesh,meshx,meshy,topo,elec_node


#%% test code
#mesh, meshx, meshy, topo, elec_node = quad_mesh(np.arange(10), np.zeros(10))
#mesh.show()


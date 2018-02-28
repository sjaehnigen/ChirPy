#!/usr/bin/env python3
import numpy as np
import copy
import sys
from scipy.interpolate import griddata
from scipy.integrate import simps

#from classes.domain import Domain3D,Domain2D
from reader.volume import cubeReader
from fileio.cube import WriteCubeFile #Replace it ?

eijk = np.zeros((3, 3, 3))
eijk[0, 1, 2] = eijk[1, 2, 0] = eijk[2, 0, 1] = 1
eijk[0, 2, 1] = eijk[2, 1, 0] = eijk[1, 0, 2] = -1

class ScalarField():
    def __init__(self,**kwargs): #**kwargs for named (dict), *args for unnamed
        fn = kwargs.get('fn')
        self.fmt = kwargs.get('fmt')
        if self.fmt is None and not fn is None: self.fmt = kwargs.get('fmt',fn.split('.')[-1])
        if self.fmt=="cube":
            buf = cubeReader(fn)
            self.comments  = buf['comments'].strip()
            self.origin_au = np.array(buf['origin_au'])
            self.cell_au   = np.array(buf['cell_au'])
            self.pos_au    = np.array(buf['coords_au'])
            self.n_atoms   = self.pos_au.shape[0]
            self.numbers   = np.array(buf['numbers'])
            self.data      = buf['volume_data']
        elif self.fmt=='wfn':
            raise Exception('Not implemented.')
        elif self.fmt=='manual':
            cell_au  = kwargs.get('cell_au',np.empty((0)))
            data     = kwargs.get('data',np.empty((0)))
            if any([cell_au.size==0,data.size==0]): raise Exception('ERROR: Please give cell_au and data for "manual" initialisation!')
            origin_au = kwargs.get('origin_au',np.zeros((3)))
            self.origin_au = np.array(origin_au)
            self.cell_au   = np.array(cell_au)
            self.data      = data
            #Check for optional data 
            for key,value in kwargs.items():
                if not hasattr(self,key): setattr(self,key,value)
#            [setattr(self,key,value) for key,value in kwargs.iteritems() if not hasattr(self,key)]
        else:
            raise Exception('Unknown format.')
        self.voxel     = np.dot(self.cell_au[0],np.cross(self.cell_au[1],self.cell_au[2]))

    @classmethod
    def from_domain(cls,domain,**kwargs):
        return cls(fmt='manual',data=domain.expand(),**kwargs)
        
    def integral(self):
        return self.voxel*simps(simps(simps(self.data)))

    def grid(self):
        '''Return an empty copy of grid'''
        return np.zeros(self.data.shape)

    def pos_grid(self):
        #Generate grid point coordinates (only for tetragonal cells)
        self.n_x       = self.data.shape[-3]
        self.n_y       = self.data.shape[-2]
        self.n_z       = self.data.shape[-1]
        xaxis = self.cell_au[0,0]*np.arange(0,self.n_x) + self.origin_au[0]
        yaxis = self.cell_au[1,1]*np.arange(0,self.n_y) + self.origin_au[1]
        zaxis = self.cell_au[2,2]*np.arange(0,self.n_z) + self.origin_au[2]

        #Can function be overwritten?
        return np.array(np.meshgrid(xaxis,yaxis,zaxis,indexing='ij')) ##Order?

    def crop(self,r,**kwargs):
        dims = kwargs.get('dims','xyz')
        if 'x' in dims:
            self.data=self.data[r:-r,:   ,:]
        self.origin_au[0] += self.cell_au[0,0]*r
        if 'y' in dims:
            self.data=self.data[:   ,r:-r,:]
        self.origin_au[1] += self.cell_au[1,1]*r
        if 'z' in dims:
            self.data=self.data[:   ,:   ,r:-r]
        self.origin_au[2] += self.cell_au[2,2]*r


    def auto_crop(self,**kwargs):
        '''crop after threshold (default: ...)'''
        thresh=kwargs.get('thresh',1.E-3)
        a=np.amin(np.array(self.data.shape)-np.argwhere(np.abs(self.data) > thresh))
        b=np.amin(np.argwhere(np.abs(self.data) > thresh))
        self.crop(min(a,b))

    def write(self,fn,**kwargs): #Replace by new write routine?
        '''Generalise this routine with autodetection for scalar and velfield, since div j is a scalar field, but attr of vec field class.'''
        fmt  = kwargs.get('fmt',fn.split('.')[-1])
        attr = kwargs.get('attribute','data')
        if not hasattr(self,attr): raise Exception('ERROR: Attribute %s not (yet) part of object!'%attr)
        if fmt=="cube":
            comment1 = kwargs.get('comment1',self.comments.split('\n')[0])
            comment2 = kwargs.get('comment2',self.comments.split('\n')[1])
            pos_au   = kwargs.get('pos_au',self.pos_au)
            n_atoms  = pos_au.shape[0]
            numbers  = kwargs.get('numbers',self.numbers)
            if numbers.shape[0] != n_atoms: raise Exception('ERROR: Given numbers inconsistent with positions')
            cell_au  = kwargs.get('cell_au',self.cell_au)
            origin_au= kwargs.get('origin_au',self.origin_au)
            data = getattr(self,attr)
            WriteCubeFile(fn, comment1, comment2, numbers, pos_au, cell_au, data, origin=origin_au)
        else:
            raise Exception('Unknown format (Not implemented).')

class VectorField(ScalarField):
    ###parser partly deprectaed (see Scalar Field)
    def __init__(self,fn1,fn2,fn3,**kwargs): #**kwargs for named (dict), *args for unnamed
        self.fmt = kwargs.get('fmt',fn1.split('.')[-1])
        if self.fmt=="cube":
            buf_x = cubeReader(fn1)
            buf_y = cubeReader(fn2)
            buf_z = cubeReader(fn3)
            self.comments  = np.array([buf_x['comments'].strip(), buf_y['comments'].strip(), buf_z['comments'].strip()])
            self.origin_au = np.array(buf_x['origin_au'])
            self.cell_au   = np.array(buf_x['cell_au'])
            self.pos_au    = np.array(buf_x['coords_au'])
            self.n_atoms   = self.pos_au.shape[0]
            self.numbers   = np.array(buf_x['numbers'])
            self.data      = np.array([buf_x['volume_data'],buf_y['volume_data'],buf_z['volume_data']])
            self.voxel     = np.dot(self.cell_au[0],np.cross(self.cell_au[1],self.cell_au[2]))

        elif self.fmt=='wfn':
            raise Exception('Not implemented.')
        else:
            raise Exception('Unknown format.')

    def crop(self,r,**kwargs):
        dims = kwargs.get('dims','xyz')
        if 'x' in dims:
            self.data=self.data[:,r:-r,:   ,:]
        self.origin_au[0] += self.cell_au[0,0]*r
        if 'y' in dims:
            self.data=self.data[:,:   ,r:-r,:]
        self.origin_au[1] += self.cell_au[1,1]*r
        if 'z' in dims:
            self.data=self.data[:,:   ,:   ,r:-r]
        self.origin_au[2] += self.cell_au[2,2]*r

    def streamlines(self,p0,**kwargs):
        '''pn...starting points of shape (n_points,3)'''
        def get_value(p):
            return griddata(points, values, (p[0],p[1],p[2]), method='nearest')

        sparse=kwargs.get('sparse',4)
        fw = kwargs.get('forward',True)
        bw = kwargs.get('backward',True)
        l  = kwargs.get('length',400)
        dt = kwargs.get('timestep',0.5)
        ext= kwargs.get('external_object',False)
        if ext: 
            ext_p0, ext_v = kwargs.get('ext_p'),kwargs.get('ext_v')
            if any([ext_p0 is None,ext_v is None]): 
                print('WARNING: Missing external object for set keyword! Please give ext_p and ext_v.')
                ext=False
            if ext_p0.shape != ext_v.shape: 
                print('WARNING: External object with inconsistent ext_p and ext_v! Skippping.')
                ext=False

        pos_grid = self.pos_grid()[:,::sparse,::sparse,::sparse]
        v_field  = self.data[:,::sparse,::sparse,::sparse]
        gl_norm = np.amax(np.linalg.norm(v_field,axis=0))
        ds=np.linalg.norm(self.cell_au,axis=1)
    
        points = np.array([pos_grid[0].ravel(),pos_grid[1].ravel(),pos_grid[2].ravel()]).swapaxes(0,1)
        values = np.array([v_field[0].ravel(),v_field[1].ravel(),v_field[2].ravel()]).swapaxes(0,1)
    
        traj=list() 
        ext_t=list()
    
        if bw:
            pn = copy.deepcopy(p0)
            vn = get_value(p0.swapaxes(0,1))     
            traj.append(np.concatenate((copy.deepcopy(pn),copy.deepcopy(vn)),axis=-1))    
            if ext: 
                ext_p = copy.deepcopy(ext_p0)
                ext_t.append(np.concatenate((copy.deepcopy(ext_p),copy.deepcopy(ext_v)),axis=-1))    

            for t in range(l):
                pn -= vn/gl_norm*ds[None]*dt
                vn = get_value(pn.swapaxes(0,1))     
                traj.append(np.concatenate((copy.deepcopy(pn),copy.deepcopy(vn)),axis=-1))    
                if ext:
                    ext_p -= ext_v/gl_norm*ds*dt
                    ext_t.append(np.concatenate((copy.deepcopy(ext_p),copy.deepcopy(ext_v)),axis=-1))    
            if fw: 
                traj = traj[1:][::-1]
                if ext: ext_t = ext_t[1:][::-1]

        if fw:
            pn = copy.deepcopy(p0)
            vn = get_value(pn.swapaxes(0,1))     
            traj.append(np.concatenate((copy.deepcopy(pn),copy.deepcopy(vn)),axis=-1))    
            if ext: 
                ext_p = copy.deepcopy(ext_p0)
                ext_t.append(np.concatenate((copy.deepcopy(ext_p),copy.deepcopy(ext_v)),axis=-1))    

            for t in range(l):
                pn += vn/gl_norm*ds[None]*dt
                vn = get_value(pn.swapaxes(0,1)) 
                traj.append(np.concatenate((copy.deepcopy(pn),copy.deepcopy(vn)),axis=-1))    
                if ext:
                    ext_p += ext_v/gl_norm*ds*dt
                    ext_t.append(np.concatenate((copy.deepcopy(ext_p),copy.deepcopy(ext_v)),axis=-1))    

        if ext: return np.array(traj),np.array(ext_t)
        else: return np.array(traj)
        
    def streamtubes(self):
        '''See notebook 24b'''
        pass 

###These are scripts adapted from Arne Scherrer
    def divergence_and_rotation(self):
        """current of shape n_frames, 3, x, y, z"""
        gradients = np.array(np.gradient(self.data,1,self.cell_au[0][0],self.cell_au[1][1],self.cell_au[2][2])[1:])
        self.div = gradients.trace(axis1=0,axis2=1)
        self.rot = np.einsum('ijk,jklmn->ilmn',eijk,gradients)

    def helmholtz_decomposition(self):

        def divergence_and_rotation(current,cell_au):
            """current of shape n_frames, 3, x, y, z"""
            gradients = np.array(np.gradient(current,1,cell_au[0][0],cell_au[1][1],cell_au[2][2])[1:])
            div = gradients.trace(axis1=0,axis2=1)
            rot = np.einsum('ijk,jklmn->ilmn',eijk,gradients)
            return div, rot

        def GetCell(n1, n2, n3, a1, a2, a3):
            from numpy.fft import fftfreq
            r1 = np.arange(n1)*(a1/n1)-a1/2
            k1 = 2*np.pi*fftfreq(n1,a1/n1)
            ix, iy, iz = (slice(None), None, None), (None, slice(None), None), (None, None, slice(None))
            (X, Kx), (Y, Ky), (Z, Kz) = [(r1[_i], k1[_i]) for _i in [ix, iy, iz]]
            R = np.sqrt(X**2 + Y**2 + Z**2)
            K = np.sqrt(Kx**2 + Ky**2 + Kz**2)
            return R,K

        def Vk(k):
            """Fourier transform of Coulomb potential $1/r$"""
            with np.errstate(divide='ignore'):
                return np.where(k==0.0, 0.0, np.divide(4.0*np.pi, k**2))

        def Potential(data, cell_au):
            from numpy.fft import ifftn,fftn
            n1, n2, n3 = data.shape
            a1, a2, a3 = tuple(cell_au.diagonal())
            R,K        = GetCell(n1, n2, n3, a1*n1, a2*n2, a3*n3)
            V_R        = ifftn(Vk(K)*fftn(data)).real
            return R, V_R

        self.div,self.rot = divergence_and_rotation(self.data,self.cell_au)
        self.V = Potential(self.div, np.array(self.cell_au))[1]/(4*np.pi)
        A1 = Potential(self.rot[0], np.array(self.cell_au))[1]
        A2 = Potential(self.rot[1], np.array(self.cell_au))[1]
        A3 = Potential(self.rot[2], np.array(self.cell_au))[1]
        self.A = np.array([A1,A2,A3])/(4*np.pi)
        self.irrotational_field = -np.array(np.gradient(self.V,self.cell_au[0][0],self.cell_au[1][1],self.cell_au[2][2]))
        self.solenoidal_field = divergence_and_rotation(self.A, self.cell_au)[1]
    
###############################################################

    def write(self,fn1,fn2,fn3,**kwargs): #Replace by new write routine?
        '''Generalise this routine with autodetection for scalar and velfield, since div j is a scalar field, but attr of vec field class.'''
        fmt  = kwargs.get('fmt',fn1.split('.')[-1])
        attr = kwargs.get('attribute','data')
        if fmt=="cube":
            comment1 = kwargs.get('comment1',[c.split('\n')[0] for c in self.comments])
            comment2 = kwargs.get('comment2',[c.split('\n')[1] for c in self.comments])
            pos_au   = kwargs.get('pos_au',self.pos_au)
            numbers  = kwargs.get('numbers',self.numbers)
            cell_au  = kwargs.get('cell_au',self.cell_au)
            origin_au= kwrags.get('origin_au',self.origin_au)
            data = getattr(self,attr)
            WriteCubeFile(fn1, comment1[0], comment2[0], numbers, pos_au, cell_au, data[0], origin=origin_au)
            WriteCubeFile(fn2, comment1[1], comment2[1], numbers, pos_au, cell_au, data[1], origin=origin_au)
            WriteCubeFile(fn3, comment1[2], comment2[2], numbers, pos_au, cell_au, data[2], origin=origin_au)
        else:
            raise Exception('Unknown format (Not implemented).')

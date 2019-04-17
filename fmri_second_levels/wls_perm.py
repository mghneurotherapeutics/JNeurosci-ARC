import sys
sys.path.append('..')
from my_settings import (os, op, np, version, read_csv, root_dir,
                         sm, fd, X, n_subj, n_pred, prepare_image,
                         load_sparse_coo, wls)
from scipy.sparse import coo_matrix
from mne.stats.cluster_level import _find_clusters as find_clusters

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
### Define parameters.
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
'''Input from cmdline: Model_Name Space Condition Permutations'''
args = sys.argv[1:]

## I/O parameters.
model_name = args[0]
space = args[1]
condition = args[2]

## Permutation parameters.
permutations = int(args[3])

## TFCE parameters.
threshold = dict(start=0.1, step=0.1, h_power=2, e_power=0.5)
tail = 0
max_step = 1

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
### Load and prepare data.
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

out_dir = op.join(root_dir, 'fmri_second_levels', 
    '%s.%s.%s.%s.%s.%s.%s.%s' % (version, task, model_name, condition, epochs_type, sm, fd, space))

## Load data.
npz = np.load(os.path.join(out_dir, 'first_levels.npz'))
ces = npz['ces']
cesvar = np.abs( 1. / npz['cesvar'] )

## Define indices.
connectivity = load_sparse_coo(os.path.join(root_dir, 'fmri_second_levels',
                               '%s_%s_connectivity.npz' % (version, space)))
index,  = np.where(~np.isinf(cesvar).sum(axis=1).astype(bool))
include = ~np.isinf(cesvar).sum(axis=1).astype(bool)
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
### Setup for permutation testing.
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

## If specified, load precomputed sign flips.
if permutations: 
    sign_flips = np.load(os.path.join(root_dir, 'fmri_second_levels', 
                                      'permutations',
                                      '%s_sign_flips_%s.npy' % (version, permutations)))
else: 
    sign_flips = np.ones((1,n_subj))
n_shuffles = sign_flips.shape[0]

## Preallocate arrays for results.
shape = [n_shuffles] + list(ces.shape[:-1])
Bmap = np.zeros(shape)
Fmap = np.zeros(shape)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
### Main loop.
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

## Loop it!
for n, sf in enumerate(sign_flips):
    #
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
    ### Compute statistics.
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
    #
    for m in index:
        #
        ## Update variables.
        W = np.diag(cesvar[m])
        Y = ces[m]
        #
        ## Permute values.
        ## See Winkler et al. (2014), pg. 385
        ## To compute Hat Matrix, see: https://en.wikipedia.org/wiki/Projection_matrix and 
        Z = X[:,1:]
        ZZ = Z.dot( np.linalg.inv( Z.T.dot(W).dot(Z) ) ).dot(Z.T).dot(W)
        Rz = np.identity(n_subj) - ZZ
        Y = np.diag(sf).dot(Rz).dot(Y)
        #
        ## Perform WLS.
        Bmap[n,m], Fmap[n,m] = wls(X,Y,W) 
    #
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
    ### Perform TFCE.
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
    #
    _, Fmap[n] = find_clusters(Fmap[n], threshold, tail=tail, connectivity=connectivity, 
                               include=include, max_step=max_step, show_info=False)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
### Save results.
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#  
        
if permutations: 
    f = op.join(out_dir, ('%s.%s.%s.%s.%s.%s.%s.%s_perm-%s' % 
                          (version, task, model_name, condition,
                           epochs_type, sm, fd, space, permutations)))
else:
    f = op.join(out_dir, ('%s.%s.%s.%s.%s.%s.%s.%s_obs' % 
                          (version, task, model_name, condition,
                           epochs_type, sm, fd, space)))
np.savez_compressed(f, Bmap=Bmap, Fmap=Fmap)
    
print('Done.')

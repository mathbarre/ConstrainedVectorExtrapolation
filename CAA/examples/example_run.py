# %%
import time
import numpy as np
from numpy.linalg import norm
from scipy import sparse

from CAA.logreg import solver_logreg
from libsvmdata import fetch_libsvm
from CAA.utils.utils import power_method


# data generation
# X, y = fetch_libsvm("phishing", normalize=False)
# X, y = fetch_libsvm("madelon", normalize=False)
# X, y = fetch_libsvm("german.numer", normalize=False) # good
# X, y = fetch_libsvm("liver-disorders", normalize=False) # good
# X, y = fetch_libsvm("phishing", normalize=False) # good
dataset = "german.numer"

X, y = fetch_libsvm(dataset, normalize=False)  # good

tol = 1e-10
C0 = 10
all_algos = [
    # ('gd', False, None, None, 1),
    ('AA no reg', True, None, None, 1),
    ('CAA adapt', True, C0, None, 1),
    # ('AA reg 1e-7', True, None, 1e-7, 1),
    # ('AA reg 1e-8', True, None, 1e-8, 1),
    # ('AA reg 1e-9', True, None, 1e-9, 1),
    # ('AA reg 1e-10', True, None, 1e-10, 1),
    # ('AA reg 1e-11', True, None, 1e-11, 1),
    ]
all_Es = {}
all_Ts = {}


fgap = 2_00
# max_iter = 150_001
max_iter = 20_001
verbose = True
w = 0

is_sparse = sparse.issparse(X)
if is_sparse:
    L = power_method(X, max_iter=1000) ** 2 / 4
else:
    L = norm(X, ord=2) ** 2 / 4
solver_logreg(
        X, y, rho=1e-12, C0=10, adaptive_C=True, use_acc=True, max_iter=100, f_grad=fgap, K=5)

conditioning = 1e-8

for algo in all_algos:
    algo_name = algo[0]
    use_acc = algo[1]
    C = algo[2]
    reg = algo[3]
    iters = algo[4]
    start_time = time.time()
    # _, E, gaps = solver_enet(
    #     X, y, 1/C, rho=0.01, verbose=verbose,
    #     tol=tol, algo=algo_name, use_acc=use_acc, max_iter=max_iter, f_gap=fgap)
    w, E, T = solver_logreg(
        X, y, rho=conditioning*L, verbose=verbose,
        tol=tol, C0=C, adaptive_C=True, use_acc=use_acc, max_iter=max_iter*iters, f_grad=fgap, K=5, reg_amount=reg)
    print("%s --- %s seconds ---" % (algo_name, time.time() - start_time))
    all_Es[algo] = E
    all_Ts[algo] = T




res = np.array([])
for algo in all_algos:
    res = np.hstack([res,all_Es[algo]])

res = res.reshape((len(all_algos),-1))
for algo in all_algos:
    res = np.vstack([res, all_Ts[algo]])
res = np.vstack([res,fgap * np.arange(res.shape[1])])


name = "./CAA/examples/results/logreg_%s_C0_%i_rho_%e.txt" % (dataset, C0, conditioning)
np.savetxt(name, res.T)
# %%
# Import packages.


# %%

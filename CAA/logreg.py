# This implementation is mainly based on
# the code from https://github.com/mathurinm/andersoncd

import numpy as np
from numba import njit
from scipy import sparse
from numpy.linalg import norm
from CAA.utils.FWsolver import FW
from scipy.sparse.linalg import svds
import time


@njit
def sigmoid(x):
    return 1 / (1. + np.exp(- x))


def solver_logreg(
        X, y, rho=0, max_iter=10000, max_time=100, tol=1e-4, f_grad=10, K=5,
        use_acc=False, C0=None, adaptive_C=False, reg_amount=None,
        verbose=False):
    """Solve l2 regularized logistic regression with Gradient descent,
    eventually using Anderson extrapolation.

    The minimized objective is:
    np.sum(np.log(1 + np.exp(- y * Xw))) / 2 + rho/2 * norm(w) ** 2

    Parameters
    ----------
    X : {array_like, sparse matrix}, shape (n_samples, n_features)
        Design matrix

    y : ndarray, shape (n_samples,)
        Observation vector

    rho : float (optional, default=0)
        L2 regularization strength.

    max_iter : int, default=1000
        Maximum number of iterations

    tol : float, default=1e-4
        The algorithm early stops if the duality gap is less than tol.

    f_grad: int, default=10
        The gradient is stored every f_grad iterations.

    K : int, default=5
        Number of points used for Anderson extrapolation.

    use_acc : bool, default=False TODO change to True?
        Whether or not to use Anderson acceleration.

    reg_amount : float or None (default=None)
        Amount of regularization used when solving for the extrapolation
        coefficients. None means 0 and should be preferred.

    C0 : float or None (default=None)
        Bound on the l1 norm of the coefficients used in
        the extrapolation.

    verbose : bool, default=False
        Verbosity.

    Returns
    -------
    W : array, shape (n_features,)
        Estimated coefficients.

    E : ndarray
        Gradient norms every grad_freq iterations.

    T : ndarray
        Time every grad_freq iterations
    """

    is_sparse = sparse.issparse(X)
    n_features = X.shape[1]

    if not is_sparse and not np.isfortran(X):
        X = np.asfortranarray(X)

    if use_acc:
        last_K_w = np.zeros([n_features, K + 1])
        R = np.zeros([n_features, K])

    if is_sparse:
        L = svds(X, k=1)[1][0]**2 / 4 + rho
    else:
        L = norm(X, ord=2) ** 2 / 4 + rho

    w = np.zeros(n_features)
    c = np.zeros(K)
    c[0] = -1
    Xw = np.zeros(len(y))
    E = []
    T = []
    start_time = time.time()
    border = True
    C_prev = C0
    for it in range(max_iter):
        if time.time() - start_time > max_time:
            break
        grad_w = -X.T @ (y / (1. + np.exp(y * Xw))) + rho*w
        if it % f_grad == 0:
            norm_grad = norm(grad_w)
            E.append(norm_grad)
            T.append(time.time()-start_time)
            if norm_grad < tol:
                print("Early exit")
                break
            else:
                if verbose:
                    print("Iteration %d, norm_grad::%.10f" % (it, norm_grad))

        w[:] = w - 1/L*grad_w
        Xw[:] = X @ w

        if use_acc:
            last_K_w[:, it % (K + 1)] = w
            if it % (K + 1) == K:
                norm_grad = norm(grad_w)
                for k in range(K):
                    R[:, k] = last_K_w[:, k + 1] - last_K_w[:, k]

                RTR = R.T @ R
                if reg_amount is not None:
                    RTR += reg_amount * norm(RTR, ord=2) * np.eye(RTR.shape[0])
                if C0 is not None:
                    C = C0
                    if adaptive_C:
                        # C *= (norm(grad_w)/L)**(-2)
                        C *= (norm_grad/L)**(-0.49)*it/K
                        C = max(C, C0)
                    try:
                        if not border:
                            C = C_prev
                        else:
                            C_prev = C
                        c = np.zeros(K)
                        c[-1] = 1
                        (c, gap, border) = FW(RTR, c, 1e-12*norm(R[:, 0]), C,
                                              max_iter=5000, verbose=0)
                    except np.linalg.LinAlgError:
                        if verbose:
                            print("----------FW error")
                else:
                    try:
                        z = np.linalg.solve(RTR, np.ones(K))
                        c = z / z.sum()
                    except np.linalg.LinAlgError:
                        if verbose:
                            print("----------Linalg error")
                w_acc = last_K_w[:, :-1] @ c
                Xw_acc = X @ w_acc
                norm_grad_acc = norm(-X.T @ (y / (1. + np.exp(y * Xw_acc))) +
                                     rho*w_acc)
                if norm_grad_acc < norm_grad:
                    w = w_acc
                    Xw = Xw_acc

    return w, E, T

from numba import njit
import numpy as np


@njit
def design_matrix(x):
    """
    Build the design matrix for linear regression for
    a given array of x-values.

    This creates a (N, 2) matrix, where the first column are the
    x values and the second contains all 1.
    """
    X = np.empty((len(x), 2), dtype=x.dtype)
    X[:, 0] = x
    X[:, 1] = 1

    return X


@njit
def linear_regression(X, y):
    """
    Analytical linear regression

    Arguments
    ---------
    X: np.array
        Design matrix of shape (N, 2), as created by ``~ctapipe.fitting.design_matrix``
    y: np.array
        y values
    """
    return np.linalg.inv(X.T @ X) @ X.T @ y


@njit
def residual_sum_of_squares(X, y, beta):
    """Calculate the residual sum of squares

    Arguments
    ---------
    X: np.array
        Design matrix of shape (N, 2), as created by ``~ctapipe.fitting.design_matrix``
    y: np.array
        y values
    beta: np.array
        Parameter vector of the linear regression
    """
    return y @ y - beta @ X.T @ y


@njit
def residuals(X, y, beta):
    """Calculate the residuals of a linear regression

    Arguments
    ---------
    X: np.array
        Design matrix of shape (N, 2), as created by ``~ctapipe.fitting.design_matrix``
    y: np.array
        y values
    beta: np.array
        Parameter vector of the linear regression
    """
    return y - X @ beta


@njit
def _lts_single_sample(X, y, sample_size, max_iterations, eps=1e-12):

    # randomly draw 2 points for the initial fit
    sample = np.random.choice(len(y), 2, replace=False)

    # perform the initial fit
    beta = linear_regression(X[sample], y[sample])
    last_error = residual_sum_of_squares(X[sample], y[sample], beta)

    for i in range(max_iterations):

        squared_residuals = residuals(X, y, beta) ** 2

        # select the subset with the smallest squared residuals
        sample = np.argsort(squared_residuals)[:sample_size]

        # redo regression with new sample
        beta = linear_regression(X[sample], y[sample])
        error = residual_sum_of_squares(X[sample], y[sample], beta)

        # test for convergences
        if abs(last_error - error) < eps:
            break

        last_error = error

    return beta, error


@njit
def lts_linear_regression(
    x, y, samples=20, relative_sample_size=0.85, max_iterations=20, eps=1e-12
):
    """
    Perform a Least Trimmed Squares regression based on algorithm (2) described in [lts_regression]_

    We start from randomly sampled two points of the dataset and then
    iteratively choose the `relative_sample_size` fraction of points with the smallest
    residuals to redo the fit until it convergtes.

    This is done for ``samples`` initial samples and the solution with the
    lowest residual sum of squares is returned along with that error.

    Arguments
    ---------
    x: np.array
        x values for the linear regression
    y: np.array
        y values for the linear regression
    samples: int
        How many initial samples to generate.
        For each sample, the C-step optimization is performed and the result
        with the lowest sum of squares is returned.
    relative_sample_size: float
        Portion of points to be used for the fit, should be > 0.5
    max_iterations: int
        maximum number of C-Steps performed for each sample.
        The fit should converge much faster (normally after < 10 iterations)
    eps: float
        differences in residual sum of squares at which the iteration will be stopped

    Returns
    -------
    beta: np.array
        Parameter vector of the linear regression
    error: float
        Residual sum of squares of the best fit
    """

    X = design_matrix(x)
    sample_size = int(relative_sample_size * len(x))

    best_beta = np.full(2, np.nan)
    best_error = np.inf

    for i in range(samples):
        beta, error = _lts_single_sample(X, y, sample_size, max_iterations, eps)
        if error < best_error:
            best_error = error
            best_beta[:] = beta

    return best_beta, best_error

"""Model classes for species distribution modeling"""

import numpy as np
import pandas as pd
from glmnet.logistic import LogitNet

from elapid import features as _features
from elapid.utils import MAXENT_DEFAULTS, _ncpus


class Maxent(object):
    def __init__(
        self,
        feature_types=MAXENT_DEFAULTS["feature_types"],
        tau=MAXENT_DEFAULTS["tau"],
        clamp=MAXENT_DEFAULTS["clamp"],
        scorer=MAXENT_DEFAULTS["scorer"],
        beta_multiplier=MAXENT_DEFAULTS["beta_multiplier"],
        beta_lqp=MAXENT_DEFAULTS["beta_lqp"],
        beta_hinge=MAXENT_DEFAULTS["beta_hinge"],
        beta_threshold=MAXENT_DEFAULTS["beta_lqp"],
        beta_categorical=MAXENT_DEFAULTS["beta_categorical"],
        n_hinge_features=MAXENT_DEFAULTS["n_hinge_features"],
        n_threshold_features=MAXENT_DEFAULTS["n_threshold_features"],
        n_cpus=_ncpus,
        use_lambdas=MAXENT_DEFAULTS["use_lambdas"],
    ):
        """
        Creates a model estimator for Maxent-style species distribution models.

        :param use_lambdas: Select from ["best", "last"]
        """
        self.feature_types_ = _features.validate_feature_types(feature_types)
        self.tau_ = tau
        self.clamp_ = clamp
        self.beta_multiplier_ = beta_multiplier
        self.beta_hinge_ = beta_hinge
        self.beta_lqp_ = beta_lqp
        self.beta_threshold_ = beta_threshold
        self.beta_categorical_ = beta_categorical
        self.n_hinge_features_ = n_hinge_features
        self.n_threshold_features_ = n_threshold_features
        self.n_cpus_ = n_cpus
        self.scorer_ = scorer
        self.use_lambdas_ = use_lambdas

        self.initialized_ = False
        self.beta_scores_ = None
        self.entropy_ = None
        self.estimator = None

    def fit(self, x, y, labels=None):
        """
        Trains a maxent model.
        """

        # data pre-processing
        # TODO df = create_covariate_df(x)
        features = _features.compute_features(x)
        weights = _features.compute_weights(y)
        regularization = _features.compute_regularization(features, y)
        lambdas = _features.compute_lambdas(y, weights, regularization)

        # model fitting
        if not self.initialized_:
            self.initialize(lambdas=lambdas)
        self.estimator.fit(
            features,
            y,
            sample_weight=weights,
            relative_penalties=regularization,
        )
        if self.use_lambdas_ == "last":
            self.beta_scores_ = self.estimator.coef_path_[0, :, -1]
        elif self.use_lambdas_ == "best":
            self.beta_scores_ = self.estimator.coef_path_[0, :, self.estimator.lambda_best_inx_]

        # maxent specific transformations
        rr = self.predict(features[y == 0], transform="exponential")
        raw = rr / np.sum(rr)
        self.entropy_ = -np.sum(raw * np.log(raw))

    def predict(self, x, transform="logistic", is_features=False):
        """
        Applies a maxent model to a set of covariates or features. Requires that a model has been fit.

        :param x: the covariate/feature data to apply the model to.
        :param transform: the maxent model transformation type. Select from ["raw", "exponential", "logistic", "cloglog"].
        :param is_reatures: boolean to specify that the x data has already been transformed from covariates to features
        """
        assert self.initialized_, "Model must be fit first"

        if is_features:
            features = x
        else:
            features = self.transform_features(x)

        if self.clamp_:
            features = _features.clamp(features)

        # applly the transformations
        link = np.matmul(x, self.beta_scores_)
        if transform == "raw":
            return link
        elif transform == "exponential":
            return np.exp(link)
        elif transform == "logistic":
            return 1 / (1 + np.exp(-self.entropy_ - link))
        elif transform == "cloglog":
            return 1 - np.exp(0 - np.exp(self.entropy_ + link))

    def initialize_model(
        self,
        lambdas,
        alpha=1,
        standardize=False,
        fit_intercept=True,
    ):
        """
        Creates the Logistic Regression with elastic net penalty model object.

        :param lambdas: the lambda values for the model. Get from features.compute_lambdas()
        :param alpha: the elasticnet mixing parameter. alpha=1 for lasso, alpha=0 for ridge
        :param standardize: boolean flag to specify coefficient normalization
        :param fit_intercept: boolean flag to include an intercept parameter
        :return none: updates the self.estimator with an sklearn model estimator
        """
        estimator = LogitNet(
            alpha=alpha,
            lambda_path=lambdas,
            standardize=standardize,
            fit_intercept=fit_intercept,
            scoring=self.scorer_,
            n_jobs=self.n_cpus_,
        )

        self.estimator = estimator

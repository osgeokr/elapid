"""Backend helper functions that don't need to be exposed to users"""
import gzip
import multiprocessing as mp
import os
import pickle

import numpy as np
import pandas as pd

_ncpus = mp.cpu_count()

MAXENT_DEFAULTS = {
    "clamp": True,
    "beta_multiplier": 1.0,
    "beta_hinge": 1.0,
    "beta_lqp": 1.0,
    "beta_threshold": 1.0,
    "beta_categorical": 1.0,
    "feature_types": ["linear", "hinge", "product"],
    "n_hinge_features": 50,
    "n_threshold_features": 50,
    "scorer": "roc_auc",
    "tau": 0.5,
    "tolerance": 1e-7,
    "use_lambdas": "last",
}


def repeat_array(x, length=1, axis=0):
    """
    Repeats a 1D numpy array along an axis to an arbitrary length

    :param x: the n-dimensional array to repeat
    :param length: the number of times to repeat the array
    :param axis: the axis along which to repeat the array (valid values include 0 to n+1)
    :returns: an n+1 dimensional numpy array
    """
    return np.expand_dims(x, axis=axis).repeat(length, axis=axis)


def load_sample_data(name="bradypus"):
    """
    Loads example species presence/background and covariate data.

    :param name: the sample dataset to load. options currently include ["bradypus"], from the R 'maxnet' package
    :returns: (x, y), a tuple of dataframes containing covariate and response data, respectively
    """
    assert name.lower() in ["bradypus"], "Invalid sample data requested"

    package_path = os.path.realpath(__file__)
    package_dir = os.path.dirname(package_path)

    if name.lower() == "bradypus":

        file_path = os.path.join(package_dir, "data", "bradypus.csv.gz")
        df = pd.read_csv(file_path, compression="gzip").astype("int64")
        y = df["presence"].astype("int8")
        x = df[df.columns[1:]].astype({"ecoreg": "category"})
        return x, y


def save_object(obj, path, compress=True):
    """
    Writes a python object to disk for later access.

    :param obj: a python object to be saved (e.g., a MaxentModel() instance)
    :param path: the output file path
    :returns: none
    """
    obj = pickle.dumps(obj)

    if compress:
        obj = gzip.compress(obj)

    with open(path, "wb") as f:
        f.write(obj)


def load_object(path, compressed=True):
    """
    Reads a python object into memory that's been saved to disk.

    :param path: the file path of the object to load
    :param compressed: flag to specify whether the file was compressed prior to saving
    :returns: obj, the python object that has been saved (e.g., a MaxentModel() instance)
    """
    with open(path, "rb") as f:
        obj = f.read()

    if compressed:
        obj = gzip.decompress(obj)

    return pickle.loads(obj)

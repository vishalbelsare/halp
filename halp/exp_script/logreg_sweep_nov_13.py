import os, sys
import math
from copy import deepcopy
from halp.utils.launching_utils import run_experiment


if __name__ == "__main__":
    exp_name = "logreg_hyper_sweep_2018_nov_13"
    n_epochs = 100
    # n_epochs = 2
    batch_size = 100
    n_classes = 10
    l2_reg_list = [1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 1e-1]
    lr_list = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
    # momentum_list = [0.9]
    # seed_list = [1,]
    seed_list = [1, 2, 3]
    # lr_list = [0.01, ]
    momentum_list = [0.9, 0.0]
    # seed_list = [1,]
    opt_algo_list = ["bc-svrg", "bc-sgd", "sgd", "svrg", "lp-sgd", "lp-svrg"]
    # opt_algo_list = ["bc-svrg", "svrg"]
    # opt_algo_list = ["bc-sgd", "sgd"]
    # opt_algo_list = ["lp-sgd", "lp-svrg"]

    rounding_list = ["near"]
    T_list = [600]
    dataset = "mnist"
    model = "logreg"
    #run_option = "dryrun"
    run_option = "run"
    run_experiment(
        exp_name,
        n_epochs,
        batch_size,
        n_classes,
        l2_reg_list,
        lr_list,
        momentum_list,
        seed_list,
        opt_algo_list,
        rounding_list,
        T_list,
        dataset,
        model,
        #cluster="dawn",
        cluster="starcluster",
        run_option=run_option)
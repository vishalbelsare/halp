import torch
import numpy as np
from torch.nn import Parameter
from halp.layers.relu_layer import BitCenterReLU, bit_center_relu
from halp.utils.utils import void_cast_func, single_to_half_det, single_to_half_stoc
from unittest import TestCase
from halp.utils.utils import set_seed
from halp.utils.test_utils import HalpTest
from torch.autograd.gradcheck import get_numerical_jacobian, iter_tensors, make_jacobian
from halp.layers.bit_center_layer_test import TestBitCenterLayer
import logging
import sys
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()


class TestBitCenterReLULayer(TestBitCenterLayer, TestCase):
    '''
    Test the functionality of bit centering conv2d layers
    '''

    def get_config(self, type="grad_check"):
        config = {}
        if type == "grad_check":
            config["n_train_sample"] = 35
            config["channel_in"] = 17
            config["w_in"] = 24
            config["h_in"] = 13
            config["cast_func"] = void_cast_func
            config["do_double"] = True
            config["seed"] = 0
            config["batch_size"] = 35
        elif type == "fw_bw_proc":
            config["n_train_sample"] = 98
            config["channel_in"] = 13
            config["w_in"] = 31
            config["h_in"] = 17
            config["cast_func"] = single_to_half_det
            config["do_double"] = False
            config["seed"] = 0
            config["batch_size"] = 33
        else:
            raise Exception("Config type not supported!")
        return config

    def prepare_layer(self,
                      channel_in,
                      w_in,
                      h_in,
                      cast_func=void_cast_func,
                      bias=False,
                      do_double=True,
                      seed=0,
                      batch_size=1,
                      n_train_sample=1):
        layer = BitCenterReLU(
            cast_func=cast_func, n_train_sample=n_train_sample)

        # Note do_double = setup layer for gradient check, otherwise, it is for checking
        # the tensor properties, and layer behaviors
        if do_double:
            layer.double()
        layer.cuda()
        return layer

    def check_layer_param_and_cache(self, layer):
        t_list = [(layer.input_cache, torch.half, False, False),
                  (layer.grad_output_cache, torch.half, False, False)]
        self.CheckLayerTensorProperty(t_list)
        self.CheckLayerTensorGradProperty(t_list)

    def get_input(self,
                  channel_in,
                  w_in,
                  h_in,
                  cast_func=void_cast_func,
                  bias=False,
                  do_double=True,
                  seed=0,
                  batch_size=1,
                  n_train_sample=1):
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)

        if do_double:
            input_delta = Parameter(
                torch.randn(
                    n_train_sample, channel_in, w_in, h_in,
                    dtype=torch.double).cuda(),
                requires_grad=True)
            input_fp = Parameter(
                torch.randn(
                    n_train_sample, channel_in, w_in, h_in,
                    dtype=torch.double).cuda(),
                requires_grad=True)
        else:
            input_delta = Parameter(
                cast_func(
                    torch.randn(
                        n_train_sample,
                        channel_in,
                        w_in,
                        h_in,
                        dtype=torch.double).cuda()),
                requires_grad=True)
            input_fp = Parameter(
                torch.randn(
                    n_train_sample, channel_in, w_in, h_in,
                    dtype=torch.float).cuda(),
                requires_grad=True)
        return [
            input_fp,
        ], [
            input_delta,
        ]

    def get_analytical_grad(self, layer, input_fp, input_delta, target=None):
        layer.set_mode(do_offset=True)
        grad_list = []
        output_fp = layer(*input_fp)
        output_fp_copy = output_fp.data.clone()
        loss_fp = torch.sum(0.5 * output_fp * output_fp)
        loss_fp.backward()
        grad_input_fp = layer.input_grad_for_test.clone()

        layer.set_mode(do_offset=False)
        output_lp = layer(*input_delta)
        loss_lp = torch.sum(0.5 * output_lp * output_lp)
        loss_lp.backward()
        grad_input_delta = layer.input_grad_for_test.clone()
        # as we only have 1 minibatch, we can directly use layer.grad_output_cache
        input_grad = grad_input_fp + grad_input_delta
        grad_list.append(input_grad)
        return output_lp + output_fp, grad_list

    def get_numerical_grad(self,
                           layer,
                           input_fp,
                           input_delta,
                           perturb_eps,
                           target=None):
        grad_list = []
        layer.set_mode(do_offset=True)
        output_final = layer(*[x + y for x, y in zip(input_fp, input_delta)])
        # use the gradient from 0.5*sum(output**2)
        num_input_grad = output_final.clone()
        num_input_grad[output_final == 0.0] = 0.0
        grad_list.append(num_input_grad)
        return output_final, grad_list


if __name__ == "__main__":
    print(torch.__version__)
    unittest.main()
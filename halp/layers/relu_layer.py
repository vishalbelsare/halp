import torch
import torch.nn as nn
from torch.nn import ReLU
import torch.nn.functional as F
from torch.nn.parameter import Parameter
from torch.autograd import Function
from torch.autograd import Variable
import numpy as np
from halp.utils.utils import void_cast_func, single_to_half_det, single_to_half_stoc
from halp.layers.bit_center_layer import BitCenterLayer
import logging
import sys
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()


class BitCenterReLUFunction(Function):
    @staticmethod
    def forward(ctx, input_delta, input_lp, grad_output_lp):
        input_full = input_lp + input_delta
        out = F.threshold(input_full, threshold=0, value=0) \
            - F.threshold(input_lp, threshold=0, value=0)

        # print("check out relu input ", torch.sum(input_full**2).item(), torch.sum(input_lp**2).item(), torch.sum(input_delta**2).item())

        # print("check out relu output ", torch.sum(F.threshold(input_full, threshold=0, value=0)**2).item())

        ctx.save_for_backward(grad_output_lp, input_full, input_lp)
        return out

    @staticmethod
    def backward(ctx, grad_output):
        grad_output_lp, input_full, input_lp = ctx.saved_tensors
        grad_input_delta = grad_output + grad_output_lp

        # print("functional grad output relu ", torch.sum(grad_input_delta**2).item(), torch.sum(grad_input_delta != 0).item(), grad_input_delta.numel())

        # grad_input_delta[input_full < 0].zero_()
        grad_input_delta[input_full < 0] = 0.0

        # print("functional grad input relu ", torch.sum(grad_input_delta**2).item(), torch.sum((input_full <= 0)).item(), torch.sum(grad_input_delta != 0).item())


        grad_input_delta[input_lp >= 0] -= grad_output_lp[input_lp >= 0]
        grad_input_lp = None
        grad_grad_output_lp = None
        return grad_input_delta.clone(), grad_input_lp, grad_grad_output_lp


bit_center_relu = BitCenterReLUFunction.apply


class BitCenterReLU(BitCenterLayer, nn.ReLU):
    def __init__(self, cast_func=void_cast_func, n_train_sample=1):
        BitCenterLayer.__init__(
            self,
            fp_functional=F.relu,
            lp_functional=bit_center_relu,
            bias=None, # TODO this is dummy, consider remove after the test is refactored properly
            cast_func=cast_func,
            n_train_sample=n_train_sample)
        nn.ReLU.__init__(self)
        self.register_backward_hook(self.update_grad_output_cache)

    def forward_lp(self, input):
        # Need to test do_offset mode whether gradient is updated properly
        input_lp = self.input_cache[self.cache_iter:(
            self.cache_iter + input.size(0))].cuda()
        grad_output_lp = \
            self.grad_output_cache[self.grad_cache_iter:(self.grad_cache_iter + input.size(0))].cuda()
        input_delta = input

        # print("test fp input fetching relu ", torch.sum(input_lp**2).item())


        output = self.lp_func(input_delta, input_lp, grad_output_lp)
        self.cache_iter = (
            self.cache_iter + input.size(0)) % self.n_train_sample
        self.grad_cache_iter = (
            self.grad_cache_iter + input.size(0)) % self.n_train_sample
        return output

    def forward_fp(self, input):
        if self.input_cache is None:
            self.input_cache = self.setup_cache(input)
            self.cache_iter = 0
        output = self.fp_func(input)
        if self.grad_output_cache is None:
            self.grad_output_cache = self.setup_cache(output)
            self.grad_cache_iter = 0
        self.update_input_cache(input)

        # print("test fp input saving relu ", torch.sum(input**2).item())


        return output


    def update_grad_output_cache(self, self1, input, output):
        # use duplicated self to adapt to the pytorch API requirement
        # as this is a class member function.
        # Specific layer might need to update this function. This is
        # because the returned gradient is not in the order as shown
        # in the Python API, e.g. the linear layer

        # print("check relu output grad ", torch.sum(output[0]**2).item())

        if self.do_offset:
            self.grad_output_cache[self.grad_cache_iter:min(
                self.grad_cache_iter +
                output[0].size()[0], self.n_train_sample)].data.copy_(
                    self.cast_func(output[0].cpu()))
            self.grad_cache_iter = (
                self.grad_cache_iter + output[0].size(0)) % self.n_train_sample
        self.input_grad_for_test = input[0]
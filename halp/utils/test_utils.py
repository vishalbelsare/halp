import torch
import torch.nn as nn
from torch.autograd import Variable
import numpy as np
from torch.autograd import gradcheck
from halp.layers.bit_center_layer import BitCenterModule, BitCenterModuleList
from halp.layers.linear_layer import BitCenterLinear
from halp.utils.utils import void_cast_func, single_to_half_det, single_to_half_stoc
from unittest import TestCase
from halp.utils.utils import get_recur_attr


class HalpTest(object):
    def CheckLayerTensorProperty(self, t_list):
        # each element of t_list is a tuple containing (t, dtype, is_cuda)
        def CheckSingleTensor(t, dtype, is_cuda, requires_grad):
            if isinstance(dtype, list):
                assert t.dtype in dtype
            else:
                assert t.dtype == dtype
            if isinstance(is_cuda, list):
                assert t.is_cuda in is_cuda
            else:
                assert t.is_cuda == is_cuda
            if isinstance(requires_grad, list):
                assert t.requires_grad in requires_grad
            else:
                assert t.requires_grad == requires_grad

        for i, (t, dtype, is_cuda, requires_grad) in enumerate(t_list):
            if t is None:
                continue
            CheckSingleTensor(t, dtype, is_cuda, requires_grad)

    def CheckLayerTensorGradProperty(self, t_list):
        # each element of t_list is a tuple containing (t, dtype, is_cuda)
        # We check if the gradient is of the right type and in the right device
        def CheckSingleTensorGrad(t, dtype, is_cuda, requires_grad):
            assert t.grad.dtype == dtype
            assert t.grad.is_cuda == is_cuda

        for i, (t, dtype, is_cuda, requires_grad) in enumerate(t_list):
            if (t is None) or (t.grad is None):
                continue
            CheckSingleTensorGrad(t, dtype, is_cuda, requires_grad)

    @staticmethod
    def GetMultipleLayerLinearModel(n_layer, n_train_sample):
        class Net(BitCenterModule):
            def __init__(self, n_layer, n_feat_in, final_dim, n_train_sample):
                # super(Net, self).__init__()
                BitCenterModule.__init__(self)
                self.layers = BitCenterModuleList([])
                n_feat_in = np.hstack((n_feat_in, final_dim))
                for i in range(n_layer):
                    self.layers.append(
                        BitCenterLinear(
                            n_feat_in[i],
                            n_feat_in[i + 1],
                            cast_func=single_to_half_det,
                            n_train_sample=n_train_sample,
                            bias=True))
                self.loss = torch.nn.MSELoss()
                self.n_feat_in = n_feat_in

            def forward(self, input, label):
                fw_input = input
                for layer in self.layers:
                    fw_input = layer(fw_input)
                return self.loss.forward(fw_input, label)

        # n_layer = np.random.randint(low=1, high=3)
        n_feat_in = np.random.randint(low=10, high=100, size=(n_layer, ))
        # final_dim = np.random.randint(low=10, high=100)
        final_dim = 1
        net = Net(n_layer, n_feat_in, final_dim, n_train_sample=n_train_sample)
        return net


# def assert_model_grad_equal(model1, model2, model2_is_bc=False):
#     # we assume all model1's params can be found in model2
#     for name, param in model1.named_parameters():
#         if name.endswith("_lp") or name.endswith("_delta"):
#             continue
#         if name not in model2.state_dict().keys():
#             continue
#         old_param = get_recur_attr(model1, name.split("."))
#         new_param = get_recur_attr(model2, name.split("."))
#         if old_param.requires_grad and new_param.requires_grad:
#             if model2_is_bc:
#                 new_param_delta = get_recur_attr(model2, (name + "_delta").split("."))
#                 np.testing.assert_allclose(old_param.grad.data.cpu().numpy(),
#                     new_param.grad.data.cpu().numpy() + new_param_delta.grad.data.cpu().numpy())
#             else:
#                 np.testing.assert_allclose(old_param.grad.data.cpu().numpy(),
#                     new_param.grad.data.cpu().numpy())
        
        




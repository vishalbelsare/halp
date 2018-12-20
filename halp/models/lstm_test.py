import torch
import numpy as np
from torch.autograd import Variable
# from halp.utils.test_utils import assert_model_grad_equal
from halp.utils.utils import single_to_half_det, single_to_half_stoc, void_cast_func
from halp.utils.utils import copy_model_weights, set_seed, get_recur_attr
from unittest import TestCase
from halp.utils.test_utils import HalpTest
from halp.models.resnet import ResNet, ResNet_PyTorch
from halp.models.resnet import BasicBlock, BitCenterBasicBlock
from halp.models.model_test import BitCenterModelTest
from halp.models.lstm import BitCenterLSTMTagger, LSTMTagger
from halp.models.lstm import copy_lstm_cell_weights
from halp.models.lstm import copy_lstm_weights_to_non_bc_lstm_cell, copy_lstm_weights_to_bc_lstm_cell


class LSTMTaggerTest(BitCenterModelTest, TestCase):
    """ Test the bit centering LSTM tagger """

    def get_config(self):
        config = {}
        # config["batch_size"] = 1
        # config["n_minibatch"] = 1
        # config["n_classes"] = 1
        # config["embedding_dim"] = 1
        # config["num_embeddings"] = 1
        # config["hidden_dim"] = 1
        # config["seq_length"] = 1
        config["batch_size"] = 25
        config["n_minibatch"] = 1
        config["n_classes"] = 10
        config["embedding_dim"] = 15
        config["num_embeddings"] = 20
        config["hidden_dim"] = 5
        config["seq_length"] = 3
        return config

    def get_models(self, n_minibatch, batch_size, n_classes, embedding_dim,
                   num_embeddings, hidden_dim, seq_length):
        n_train_sample = batch_size * n_minibatch
        native_model = LSTMTagger(
            embedding_dim=embedding_dim,
            hidden_dim=hidden_dim,
            vocab_size=num_embeddings,
            tagset_size=n_classes).cuda().double()
        fp_model = BitCenterLSTMTagger(
            num_embeddings=num_embeddings,
            embedding_dim=embedding_dim,
            hidden_size=hidden_dim,
            cast_func=void_cast_func,
            n_train_sample=n_train_sample,
            seq_length=seq_length,
            n_classes=n_classes,
            dtype="fp").cuda().double()
        copy_model_weights(native_model, fp_model)
        copy_lstm_weights_to_non_bc_lstm_cell(native_model.lstm,
                                              fp_model.lstm_cell)
        lp_model = BitCenterLSTMTagger(
            num_embeddings=num_embeddings,
            embedding_dim=embedding_dim,
            hidden_size=hidden_dim,
            cast_func=void_cast_func,
            n_train_sample=n_train_sample,
            seq_length=seq_length,
            n_classes=n_classes,
            dtype="lp").cuda().double()
        copy_model_weights(native_model, lp_model)
        copy_lstm_weights_to_non_bc_lstm_cell(native_model.lstm,
                                          lp_model.lstm_cell)
        bc_model = BitCenterLSTMTagger(
            num_embeddings=num_embeddings,
            embedding_dim=embedding_dim,
            hidden_size=hidden_dim,
            cast_func=void_cast_func,
            n_train_sample=n_train_sample,
            seq_length=seq_length,
            n_classes=n_classes,
            dtype="bc").double()
        copy_model_weights(native_model, bc_model)
        copy_lstm_weights_to_bc_lstm_cell(native_model.lstm,
                                          bc_model.lstm_cell)
        return native_model, fp_model, lp_model, bc_model

    def get_inputs(self, n_minibatch, batch_size, n_classes, embedding_dim,
                   num_embeddings, hidden_dim, seq_length):
        x_list = []
        y_list = []
        for i in range(n_minibatch):
            x_list.append(
                torch.nn.Parameter(
                    torch.LongTensor(seq_length, batch_size).random_(num_embeddings),
                    requires_grad=False).cuda())
            y_list.append(torch.LongTensor(seq_length*batch_size).random_(n_classes).cuda())
        return x_list, y_list

    def check_layer_status(self, bc_model, do_offset=True):
        assert bc_model.embedding.do_offset == do_offset
        assert bc_model.lstm_cell.input_linear.do_offset == do_offset
        assert bc_model.lstm_cell.hidden_linear.do_offset == do_offset
        assert bc_model.lstm_cell.hidden_linear.do_offset == do_offset
        assert bc_model.lstm_cell.hidden_linear.do_offset == do_offset
        assert bc_model.lstm_cell.i_activation.do_offset == do_offset
        assert bc_model.lstm_cell.f_activation.do_offset == do_offset
        assert bc_model.lstm_cell.g_activation.do_offset == do_offset
        assert bc_model.lstm_cell.o_activation.do_offset == do_offset
        assert bc_model.lstm_cell.f_c_mult.do_offset == do_offset
        assert bc_model.lstm_cell.i_g_mult.do_offset == do_offset
        assert bc_model.lstm_cell.c_prime_activation.do_offset == do_offset
        assert bc_model.lstm_cell.o_c_prime_mult.do_offset == do_offset
        assert bc_model.linear.do_offset == do_offset
        assert bc_model.criterion.do_offset == do_offset

    def assert_model_grad_equal(self, model1, model2, model2_is_bc=False):
        # we assume all model1's params can be found in model2
        for name, param in model1.named_parameters():
            if name.endswith("_lp") or name.endswith("_delta"):
                continue
            if name not in model2.state_dict().keys():
                continue
            old_param = get_recur_attr(model1, name.split("."))
            new_param = get_recur_attr(model2, name.split("."))
            if old_param.requires_grad and new_param.requires_grad:
                if model2_is_bc:
                    new_param_delta = get_recur_attr(model2, (name + "_delta").split("."))
                    np.testing.assert_allclose(old_param.grad.data.cpu().numpy(),
                        new_param.grad.data.cpu().numpy() + new_param_delta.grad.data.cpu().numpy())
                else:
                    np.testing.assert_allclose(old_param.grad.data.cpu().numpy(),
                        new_param.grad.data.cpu().numpy())


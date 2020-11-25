from abc import ABC

from torch import nn
from torch import optim
from torch import inverse

import cca_zoo.DCCA
import cca_zoo.deep_models
import cca_zoo.objectives

"""
Lagrangian Linear Deconfounding Deep CCA

All of my deep architectures have forward methods inherited from pytorch as well as a method:

loss(): which calculates the loss given some inputs and model outputs i.e.

loss(inputs,model(inputs))

This allows me to wrap them all up in the deep wrapper. Obviously this isn't required but it is helpful
for standardising the pipeline for comparison
"""


class DeCCAnl_reg(nn.Module, ABC):
    def __init__(self, input_size_1: int, input_size_2: int, input_size_c: int, hidden_layer_sizes_1: list = None,
                 hidden_layer_sizes_2: list = None, hidden_layer_sizes_c: list = None, latent_dims: int = 2,
                 loss_type: str = 'cca', model_1: str = 'fcn', model_2: str = 'fcn', model_c: str = 'fcn',
                 learning_rate=1e-3):
        super(DeCCAnl_reg, self).__init__()

        if model_1 == 'fcn':
            if hidden_layer_sizes_1 is None:
                hidden_layer_sizes_1 = [128]
            self.encoder_1 = cca_zoo.deep_models.Encoder(hidden_layer_sizes_1, input_size_1, latent_dims).double()
        elif model_1 == 'cnn':
            if hidden_layer_sizes_1 is None:
                hidden_layer_sizes_1 = [1, 1, 1]
            self.encoder_1 = cca_zoo.deep_models.CNN_Encoder(hidden_layer_sizes_1, input_size_1, latent_dims).double()
        elif model_1 == 'brainnet':
            self.encoder_1 = cca_zoo.deep_models.BrainNetCNN_Encoder(input_size_1, latent_dims).double()

        if model_2 == 'fcn':
            if hidden_layer_sizes_2 is None:
                hidden_layer_sizes_2 = [128]
            self.encoder_2 = cca_zoo.deep_models.Encoder(hidden_layer_sizes_2, input_size_2, latent_dims).double()
        elif model_2 == 'cnn':
            if hidden_layer_sizes_2 is None:
                hidden_layer_sizes_2 = [1, 1, 1]
            self.encoder_2 = cca_zoo.deep_models.CNN_Encoder(hidden_layer_sizes_2, input_size_2, latent_dims).double()
        elif model_2 == 'brainnet':
            self.encoder_2 = cca_zoo.deep_models.BrainNetCNN_Encoder(input_size_2, latent_dims).double()

        if model_c == 'fcn':
            if hidden_layer_sizes_c is None:
                hidden_layer_sizes_c = [128]
            self.decoder_c1 = cca_zoo.deep_models.Decoder(hidden_layer_sizes_c, latent_dims, input_size_c).double()
            self.decoder_c2 = cca_zoo.deep_models.Decoder(hidden_layer_sizes_c, latent_dims, input_size_c).double()

        self.latent_dims = latent_dims

        if loss_type == 'cca':
            self.cca_objective = cca_zoo.objectives.cca(self.latent_dims)
        if loss_type == 'gcca':
            self.cca_objective = cca_zoo.objectives.gcca(self.latent_dims)
        if loss_type == 'mcca':
            self.cca_objective = cca_zoo.objectives.mcca(self.latent_dims)

        self.learning_rate = learning_rate
        self.optimizer = optim.Adam(list(self.encoder_1.parameters()) + list(self.encoder_2.parameters()),
                                    lr=self.learning_rate)
        self.optimizer_c = optim.Adam(list(self.decoder_c1.parameters())+list(self.decoder_c2.parameters()), lr=self.learning_rate)
        self.lambda_1 = 1000000
        self.lambda_2 = 1000000

    def encode(self, x_1, x_2, x_c):
        z_1 = self.encoder_1(x_1)
        z_2 = self.encoder_2(x_2)
        z_c1 = self.decoder_c1(z_1)
        z_c2 = self.decoder_c2(z_2)
        return z_1, z_2, z_c1, z_c2

    def forward(self, x_1, x_2, x_c):
        z_1, z_2, z_c1, z_c2 = self.encode(x_1, x_2, x_c)
        return z_1, z_2

    def update_weights(self, x_1, x_2, x_c):
        self.optimizer.zero_grad()
        loss = self.loss(x_1, x_2, x_c)
        loss.backward()
        self.optimizer.step()
        self.optimizer_c.zero_grad()
        confound_loss = -self.loss(x_1, x_2, x_c)
        confound_loss.backward()
        self.optimizer_c.step()
        return loss

    def loss(self, x_1, x_2, x_c):
        z_1, z_2, z_c1, z_c2 = self.encode(x_1, x_2, x_c)
        cca = self.cca_objective.loss(z_1, z_2)
        conf_cca_1 = nn.functional.mse_loss(x_c, z_c1)
        conf_cca_2 = nn.functional.mse_loss(x_c, z_c2)
        return cca - self.lambda_1 * conf_cca_1 - self.lambda_2 * conf_cca_2

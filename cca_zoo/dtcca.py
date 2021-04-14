"""
All of my deep architectures have forward methods inherited from pytorch as well as a method:

loss(): which calculates the loss given some inputs and model outputs i.e.

loss(inputs,model(inputs))

This allows me to wrap them all up in the deep wrapper. Obviously this isn't required but it is helpful
for standardising the pipeline for comparison
"""

from typing import Iterable

from torch import nn

from cca_zoo.dcca import DCCA
from cca_zoo.deep_models import BaseEncoder, Encoder
from cca_zoo.objectives import TCCA
from cca_zoo import wrappers


class DTCCA(DCCA, nn.Module):
    def __init__(self, latent_dims: int, encoders: Iterable[BaseEncoder] = (Encoder, Encoder),
                 learning_rate=1e-3, r: float = 0,
                 schedulers: Iterable = None, optimizers: Iterable = None):
        super().__init__(latent_dims, objective=TCCA, encoders=encoders, learning_rate=learning_rate, r=r,
                         schedulers=schedulers, optimizers=optimizers)

    def post_transform(self, *z_list, train=False):
        if train:
            self.cca = wrappers.TCCA(latent_dims=self.latent_dims)
            self.cca.fit(*z_list)
            z_list = self.cca.transform(*z_list)
        else:
            z_list = self.cca.transform(*z_list)
        return z_list
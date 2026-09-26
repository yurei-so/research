# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import torch
from torch import nn


class ConvGRUCell(nn.Module):
    def __init__(self, channels: int, ego_channels: int = 3):
        super().__init__()
        total = channels * 2 + ego_channels
        self.gates = nn.Conv2d(total, channels * 2, 3, padding=1)
        self.candidate = nn.Conv2d(total, channels, 3, padding=1)

    def forward(self, value, previous, ego):
        expanded = ego[:, :, None, None].expand(-1, -1, value.shape[-2], value.shape[-1])
        joined = torch.cat((value, previous, expanded), dim=1)
        update, reset = self.gates(joined).chunk(2, dim=1)
        update, reset = update.sigmoid(), reset.sigmoid()
        candidate_input = torch.cat((value, previous * reset, expanded), dim=1)
        candidate = self.candidate(candidate_input).tanh()
        return (1 - update) * previous + update * candidate


class SpatialBeliefModel(nn.Module):
    def __init__(self, maximum_depth: float = 20.0):
        super().__init__()
        self.maximum_depth = maximum_depth
        self.encoder = nn.Sequential(
            nn.Conv2d(1, 16, 5, stride=2, padding=2), nn.SiLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1), nn.SiLU(),
            nn.Conv2d(32, 48, 3, padding=1), nn.SiLU(),
        )
        self.memory = ConvGRUCell(48)
        self.depth_head = nn.Sequential(nn.Conv2d(48, 32, 3, padding=1), nn.SiLU(), nn.Conv2d(32, 1, 1))
        self.edge_head = nn.Sequential(nn.Conv2d(48, 24, 3, padding=1), nn.SiLU(), nn.Conv2d(24, 1, 1))

    def forward(self, images, ego):
        state = None
        for index in range(images.shape[1]):
            encoded = self.encoder(images[:, index])
            if state is None:
                state = torch.zeros_like(encoded)
            state = self.memory(encoded, state, ego[:, index])
        depth = self.depth_head(state).sigmoid() * self.maximum_depth
        edges = self.edge_head(state)
        return depth[:, 0], edges[:, 0]

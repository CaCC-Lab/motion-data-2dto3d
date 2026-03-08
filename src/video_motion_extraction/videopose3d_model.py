"""VideoPose3D時間畳み込みモデル定義.

公式リポジトリ (facebookresearch/VideoPose3D) の pretrained_h36m_cpn.bin
チェックポイントに対応するアーキテクチャ。
"""

from typing import Optional

try:
    import torch
    import torch.nn as nn

    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


if _TORCH_AVAILABLE:
    class TemporalModel(nn.Module):
        """VideoPose3D公式アーキテクチャ準拠の時間畳み込みモデル.

        チェックポイントのレイヤー名:
          expand_conv, expand_bn, layers_conv.0~7, layers_bn.0~7, shrink
        """

        def __init__(
            self,
            num_joints_in: int = 17,
            in_features: int = 2,
            num_joints_out: int = 17,
            filter_widths: tuple = (3, 3, 3, 3, 3),
            channels: int = 1024,
            dropout: float = 0.25,
            causal: bool = False,
        ):
            super().__init__()
            self.num_joints_in = num_joints_in
            self.num_joints_out = num_joints_out
            self.in_features = in_features
            self.causal = causal

            in_channels = num_joints_in * in_features

            # 拡張層
            self.expand_conv = nn.Conv1d(
                in_channels, channels, filter_widths[0],
                bias=False,
                padding=(filter_widths[0] - 1) // 2 if not causal else 0,
            )
            self.expand_bn = nn.BatchNorm1d(channels, momentum=0.1)

            # 残差ブロック層（conv + skip conv + bn のペア）
            self.layers_conv = nn.ModuleList()
            self.layers_bn = nn.ModuleList()
            self.causal_shift = []

            next_dilation = filter_widths[0]
            for fw in filter_widths[1:]:
                # メイン畳み込み
                self.layers_conv.append(nn.Conv1d(
                    channels, channels, fw,
                    dilation=next_dilation,
                    bias=False,
                    padding=((fw - 1) * next_dilation) // 2 if not causal else 0,
                ))
                self.layers_bn.append(nn.BatchNorm1d(channels, momentum=0.1))
                self.causal_shift.append(
                    (fw - 1) * next_dilation if causal else 0
                )

                # 1x1 skip畳み込み
                self.layers_conv.append(nn.Conv1d(
                    channels, channels, 1, dilation=1, bias=False,
                ))
                self.layers_bn.append(nn.BatchNorm1d(channels, momentum=0.1))
                self.causal_shift.append(0)

                next_dilation *= fw

            # 縮小層
            self.shrink = nn.Conv1d(channels, num_joints_out * 3, 1)

            self.relu = nn.ReLU(inplace=True)
            self.drop = nn.Dropout(dropout)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            """順伝播.

            Args:
                x: (B, T, J*2) 入力2Dキーポイント

            Returns:
                (B, T, J, 3) 3D位置推定結果
            """
            b, t, _ = x.shape
            x = x.permute(0, 2, 1)  # (B, C, T)

            # 拡張
            x = self.drop(self.relu(self.expand_bn(self.expand_conv(x))))

            # 残差ブロック
            for i in range(0, len(self.layers_conv), 2):
                res = x
                if self.causal and self.causal_shift[i] > 0:
                    x = nn.functional.pad(x, (self.causal_shift[i], 0))
                x = self.drop(self.relu(self.layers_bn[i](self.layers_conv[i](x))))
                x = self.drop(self.relu(self.layers_bn[i + 1](self.layers_conv[i + 1](x))))
                x = res + x

            # 縮小
            x = self.shrink(x)
            x = x.permute(0, 2, 1)  # (B, T, C)
            x = x.view(b, -1, self.num_joints_out, 3)
            return x


def load_videopose3d_model(
    weights_path: str,
    device: str = "cpu",
    receptive_field: int = 243,
) -> Optional[object]:
    """VideoPose3D事前学習済みモデルをロード.

    Args:
        weights_path: 重みファイルパス (pretrained_h36m_cpn.bin)
        device: デバイス文字列 ("cpu" or "cuda")
        receptive_field: 受容野サイズ

    Returns:
        eval済みTemporalModel、またはロード失敗時None
    """
    if not _TORCH_AVAILABLE:
        return None

    try:
        checkpoint = torch.load(weights_path, map_location=device, weights_only=True)

        if "model_pos" in checkpoint:
            state_dict = checkpoint["model_pos"]
        else:
            state_dict = checkpoint

        # チャンネル数をstate_dictから推測
        channels = 1024
        if "expand_bn.weight" in state_dict:
            channels = state_dict["expand_bn.weight"].shape[0]

        # フィルタ幅: 公式デフォルト (3,3,3,3,3) → conv8層 = (3x2層+初期expand)
        filter_widths = (3, 3, 3, 3, 3)

        model = TemporalModel(
            num_joints_in=17,
            in_features=2,
            num_joints_out=17,
            filter_widths=filter_widths,
            channels=channels,
        )

        # 重みロード
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        if missing:
            print(f"VideoPose3D: missing keys: {missing}")
        if unexpected:
            print(f"VideoPose3D: unexpected keys: {unexpected}")

        model.to(device)
        model.eval()
        return model
    except Exception as exc:
        print(f"VideoPose3D load failed: {exc}")
        return None

"""Vendored BS-RoFormer architecture (GPL-3.0).

Source: ZFTurbo/Music-Source-Separation-Training, ``models/bs_roformer/``
(https://github.com/ZFTurbo/Music-Source-Separation-Training), retrieved 2026-09-22.

Licensed under the GNU General Public License v3.0 — see the upstream repository for
the full license text. Vendored here, unmodified except for the import path, so the
``anvuew/dereverb_bs_roformer`` checkpoint can run without pulling the whole training
framework. If you redistribute this project, the GPL-3.0 obligations for these files
apply.
"""

from harvester.vendor.msst.bs_roformer import BSRoformer

__all__ = ["BSRoformer"]

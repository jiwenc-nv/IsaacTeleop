# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Extract the nlopt package files from the standalone nlopt wheel into the
isaacteleop wheel staging directory so they are co-installed by the isaacteleop
wheel (making a separate 'pip install nlopt' unnecessary).

Usage: python bundle_nlopt.py <wheels_dir> <staging_dir>
"""

import sys
import zipfile
import pathlib

wheels_dir = pathlib.Path(sys.argv[1])
staging_dir = pathlib.Path(sys.argv[2])

wheels = sorted(wheels_dir.glob("nlopt-*.whl"))
if not wheels:
    raise FileNotFoundError(f"No nlopt wheel found in {wheels_dir}")

with zipfile.ZipFile(wheels[0]) as z:
    members = [
        n for n in z.namelist() if n.startswith("nlopt/") and ".dist-info" not in n
    ]
    z.extractall(str(staging_dir), members)

print(f"Bundled {wheels[0].name} → {staging_dir}/nlopt/ ({len(members)} files)")

.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: Apache-2.0

Contributing
============

We welcome contributions. Please see the repository's `CONTRIBUTING.md <https://github.com/NVIDIA/IsaacTeleop/blob/main/CONTRIBUTING.md>`_ for:

- Code of conduct and how to contribute
- Development setup and coding standards
- Pull request process

Previewing documentation changes
--------------------------------

Local build
~~~~~~~~~~~

Build the docs locally to catch broken links and rendering issues before opening
a pull request:

.. code-block:: bash

   cd docs
   pip install -r requirements.txt
   make current-docs

The output is written to ``docs/build/current/``. Open ``index.html`` in a
browser to inspect it. Sphinx is run with ``-W --keep-going``, so warnings are
treated as errors — fix them locally before pushing.

PR preview on GitHub Pages
~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``Build & deploy docs`` workflow runs on every push that touches the
documentation, looks up the open pull request on ``NVIDIA/IsaacTeleop`` for
the pushed branch, and publishes a preview to **the running repository's**
GitHub Pages site under ``preview/pr-<N>/``:

- Pushing to a branch on ``NVIDIA/IsaacTeleop`` (canonical) publishes to:

  .. code-block:: text

     https://nvidia.github.io/IsaacTeleop/preview/pr-<N>/

- Pushing to a branch on your fork (e.g. ``<your-user>/IsaacTeleop``) publishes
  to your fork's Pages site:

  .. code-block:: text

     https://<your-user>.github.io/IsaacTeleop/preview/pr-<N>/

The preview link is also added to the workflow run's *Summary* tab and is
refreshed on every push.

.. note::

   PRs are looked up at deploy time, so the workflow needs the PR to already
   exist when it runs. If you push **before** opening the PR, the run will
   skip the preview and note "No open PR for head=…" in its summary. After
   opening the PR, either push another commit or trigger the workflow
   manually from the *Actions* tab (``Run workflow``).

One-time setup for forks
~~~~~~~~~~~~~~~~~~~~~~~~

Forks need a small amount of setup before previews work:

1. **Enable Actions.** Settings → Actions → General → "Allow all actions
   and reusable workflows".
2. **Bootstrap the ``gh-pages`` branch.** Push a branch with any docs change.
   The workflow will create ``gh-pages`` on its first successful deploy.
3. **Enable Pages.** Settings → Pages → Source = "Deploy from a branch",
   Branch = ``gh-pages`` / root. Save.
4. **(Optional) Private CloudXR Web SDK.** If you have access to the private
   NGC SDK, add a repository secret named
   ``NGC_TELEOP_CORE_GITHUB_SERVICE_KEY`` under Settings → Secrets and
   variables → Actions. Without it, the workflow falls back to the public
   SDK, which is fine for docs and most preview use cases.

After the first deploy, subsequent pushes update the preview automatically.
Old branch previews can be cleaned up by running the ``Cleanup docs PR
previews`` workflow from the Actions tab (it removes the entire ``preview/``
tree).

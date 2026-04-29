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

Every PR preview is published to a single canonical location:

.. code-block:: text

   https://nvidia.github.io/IsaacTeleop/preview/pr-<N>/

How the preview gets built depends on where the PR's branch lives.

PRs from a branch on ``NVIDIA/IsaacTeleop``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``Build & deploy docs`` workflow runs automatically on every push to the
PR branch and publishes the preview. The preview URL is added to the workflow
run's *Summary* tab and refreshed on every push. No extra action required.

PRs from a fork
^^^^^^^^^^^^^^^

GitHub Actions on PRs from forks run with a read-only token, so the workflow
cannot push to ``gh-pages`` automatically. Instead:

1. When a fork PR is opened, a bot comments with instructions.
2. A maintainer (anyone with write access to ``NVIDIA/IsaacTeleop``) deploys
   the preview by commenting on the PR:

   .. code-block:: text

      /preview

3. The maintainer-triggered workflow checks out the PR's head, builds the
   docs, deploys to ``preview/pr-<N>/``, and reacts to the comment with 👀
   while building and 👍 once published. A follow-up comment posts the
   preview URL.

Re-running ``/preview`` after new commits land on the PR redeploys with the
latest changes. Previews are not auto-cleaned; maintainers can run the
``Cleanup docs PR previews`` workflow from the *Actions* tab to clear the
``preview/`` tree.

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

---
title: BluEcho Sonar
emoji: 🌊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
license: agpl-3.0
pinned: false
---

# BluEcho · SIH 2026

Created by Khushi Mhamane, Sharon Melhi, Kirti Rajput, Peeyush Rampal, and Aditya Banerjee for Smart India Hackathon 2026.

This CPU demonstration runs the existing side-scan pipeline detector. Uploads are processed on Hugging Face, with signed browser-session ownership for files, jobs, review records and exports. Use non-sensitive imagery. Temporary storage and session access reset when the service restarts. Download your reports before leaving.

Limits: 32 MiB per source, 20 sources and 40 standard inspections per session, one CPU worker, four queued jobs, 180 seconds per job, and an 8 GiB address-space worker limit. Large recordings and offline operation are supported through the local application instead.

The only hosted model is `sss-pipeline-v3`, using `SSS_LF` input. Shipwrecks, cylinders and entangled nets are not supported by this hosted model. Scores are uncalibrated; coordinates require verified source metadata. The model has correlated single-survey development evidence, not independent-site validation.

- [Application source](https://github.com/Sharon-codes/SIH-2026)
- [Model weights, licences and manifests](https://huggingface.co/SharonMelhi/BluEcho-SSS-Pipeline)
- [Local package](https://pypi.org/project/bluecho-sonar/)

Software/weights preserve AGPL terms. SubPipe data attribution: OceanScan-MST / REMARO, CC BY 4.0. Raw datasets are not hosted here.
